# 下一代 SOTA SM 操作数供给架构设计目标：OSF (Operand Supply Fabric)

> **版本**: v0.3 DRAFT — 2026-10-27（v0.1 critic REJECT / 3 BLOCKER；v0.2 复审 B2 部分闭合、重武装语义仍矛盾；v0.3 收敛为「FILL 是进入 LIVE 的唯一路径」；见 §11 评审记录）
> **状态**: 🟡 **设计目标声明**（非当前实现；非 NVIDIA 官方；**未经 Oracle/ADR 评审**，本文的开放问题需经评审裁决）
> **Owner**: CppTLM Team
> **文档分类**: 第 1 层 · 设计目标声明（🟡 DRAFT 愿景）—— per 根 `AGENTS.md` §DOC HYGIENE 文档路径决策树「实现目标声明 → `docs/designs/<topic>/<name>-design-target.md`」与 `docs/architecture/README.md:17-21` 判断标准（**SM 属通用 TLM 框架侧**；"不确定时优先放 `docs/architecture/`"）
> **上游依据**: [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md)（Operand Collector 与寄存器架构演进总结）+ [`docs/research/SM/CudaCore/`](../research/SM/CudaCore/overview.md) 8 篇逐篇解析
> **定位说明**:
> - **本文不是"现状真相"**：本目录其余文档描述 dGPU SoC 的**当前**架构；本文描述**尚未实现**的设计目标。二者不得混引——引用本文时必须带"设计目标"限定。
> - **本文 2026-10-27 自 CppTLM 仓迁入**（原 `CppTLM/docs/architecture/14-sm-operand-supply-design-target.md`；编号 `14` 在本仓已被 `14-stage-a-architecture-audit.md` 占用 → 改 `33-`）。**silicon 侧真源在本仓**（SoC 架构建模）；CppTLM 仓 = 仿真框架 + 基本 SoC 验证，**只消费本文的建模口径**（`CppTLM/docs/research/` 已同步拆分）。
> - **不创建 openspec change**（本文未实施，不消耗 Proposed KPI slot；实施时另起 change，并同步回写本文）。
> - **不声称与任何专利实现等价**：下文引用专利仅作**设计思路对照**（per `docs/research/AGENTS.md` §1 使用原则）。
> **关联 OpenSpec changes**: 无（当前无 active change 涉及 SM 操作数供给）
> **编号说明**: 本目录编号 `14` 此前用于 `14-dgpu-board-ideal-arch.md`（已于 2026-09-26 迁至 `docs/designs/dgpu-board/architecture.md`），该编号已退役并由本文占用；SM 微架构的另一份历史文档 `15-sm-microarchitecture-design.md` 已迁至 ArchForge 仓（不在 CppTLM）

---

## 0. TL;DR

> **核心主张**：不要更好地**仲裁**冲突，而要让冲突**没有机会发生**。
>
> 冲突是"从 RF 读操作数"的副产品。**减少读**，就同时减少冲突、带宽、能耗与固定延迟窗口的浪费。

**四个机制**：

| 机制 | 全称 | 解的问题 | 面积成本 | 状态 |
|------|------|---------|---------|------|
| **MCOS** | Multi-Consumer Operand Slot（多消费者操作数槽） | **P3** — RFC 读一次即失效，producer→N consumer 无法复用 | **≈ 0**（只扩 tag 位，不加条目） | **核心** |
| **ERW** | Elastic Read Window（弹性读窗口 + 提前收集） | **P2** — 定长 3 拍窗口对 2 源指令浪费 25% 带宽 | 中（读端口流水化 + slot buffer） | 重要 |
| **WABR** | Width-Adaptive Bank Read（宽度自适应 bank 读） | **P4** — 窄值仍按 1024-bit 全宽读 | 低（bank 条带已支持子读） | 重要 |
| **SOP** | Speculative Operand Provisioning（推测供给） | **P1（部分）** — load 路径的值延迟 | 高（预测表 + tag 校验） | **探索** |

**明确不解决**：**P1 的主因**——定长延迟指令的 4-cycle 依赖延迟由 **ALU 流水线深度**决定，不是操作数供给层能单独解决的（见 §4.4 边界声明）。

---

## 1. 设计出发点：四条遗留问题

> 编号与证据见 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §4。

| # | 问题 | 量化证据 | 现有手段为何不够 |
|---|------|---------|----------------|
| **P1** | 依赖链延迟钉死 4 cycle | Volta `FFMA` 依赖延迟 4（Pascal 6）；Ampere `mad.lo.f32` 依赖 CPI 4 | NVIDIA 已有 result queue + bypassing，但那是**流水线级内**旁路，缩短的是 RF 往返，**不是 ALU 流水线深度** |
| **P2** | 定长 3 周期窗口对 2 源指令浪费带宽 | "all the fixed-latency instructions spend three cycles for reading source operands, **even if some of these cycles the instruction is idle** (for instance when there are only two source operands)" | 窗口**每指令独占**，空档不能被后续指令填 |
| **P3** | RFC 读一次即失效，producer→N consumer 链无法复用 | "A cached value is unavailable after a read request arrives to the same bank and operand position, **regardless of whether it hits**"；论文 Listing 2 Example 1 vs 2 精确展示：要让第 3 条指令命中，**每条消费者都须重置 `.reuse`** | NVIDIA 的 `.reuse` 是 **1-bit、read-once** 语义，结构性限制复用次数 |
| **P4** | 窄值仍按全宽读取 | RF 物理上已是 8 sub-bank × 128-bit 条带（Fermi 起），但 bank 读口固定 1024 bit | CORF 的寄存器打包在**写端 + 读端合并**，**没有"按需少读"** |

---

## 2. 第一性原理：把 RF 从"值的仓库"降级为"值的持久化存储"

现状的隐含假设是：

> **每次需要操作数，都要去 RF 读一次。**

这个假设决定了后面所有的麻烦：读端口稀缺（I1）→ 冲突 → 气泡；读带宽浪费 → 固定窗口（P2）；重复读 → 浪费 + 槽失效（P3）。

**OSF 的假设翻转**：

> **值在生产时刻被"寄存"到一个带 tag 的槽里，消费者按 tag 领取；RF 只是"值最终要落到的地方"，而不是"每次取值的必经之路"。**

于是：

- **RF 读变成"miss 才发生"**——是例外路径，不是主路径；
- **冲突频率 ∝ RF 读次数** → RF 读降为 1/N，冲突同频降为 1/N；
- **P2/P3/P4 都是"减少读"的特例**，可以用同一套机制承载。

---

## 3. 架构总览

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                      Issue / Decode                        │
                    │  ┌───────────────┐                                       │
                    │  │  Warp Sched.  │  ← 编译器提示（reuse / width / budget）│
                    │  └───────┬───────┘                                       │
                    │          │ 指令 + 控制位                                  │
                    │          ▼                                               │
                    │  ┌───────────────────────────────────────────────┐         │
                    │  │  Allocate（端口预约，NVIDIA 已有）            │         │
                    │  │  · 预约 RF 读端口                              │         │
                    │  │  · 冲突 → 向上游压气泡                        │         │
                    │  └───────┬───────────────────────────────────────┘         │
                    │          │                                                 │
                    │          ▼                                                 │
                    │  ┌────────────────────────────────────────────────────┐    │
                    │  │         OSF  值供给层（新增）                      │    │
   ┌──────────┐    │  │  ┌──────────────┐   ┌───────────────┐              │    │
   │    RF    │◄───┼──┤  │ ERW 读窗口   │   │  MCOS 槽阵列  │              │    │
   │ (持久化) │    │  │  │ (3 级流水)   │   │ (tag+budget)  │              │    │
   │ 2 bank   │    │  │  │ 提前收集      │   │  多消费者      │              │    │
   │ /subcore │    │  │  └──────┬───────┘   └───────┬───────┘              │    │
   └────▲─────┘    │  │         │                   │                      │    │
        │          │  │         └─────────┬─────────┘                      │    │
        │          │  │                   ▼                                │    │
        │ 写回     │  │            ┌──────────────┐                        │    │
        └──────────┼──┤            │  值路由/校验 │  ← tag 校验 + 前递      │    │
                   │  │            └──────┬───────┘                        │    │
                   │  └───────────────────┼────────────────────────────────┘    │
                   │                      ▼                                     │
                   │  ┌────────────────────────────────────────────────────┐    │
                   │  │  Execute（FU）    ← 严格在 issue + 3 进入（I2 保持）│    │
                   │  └───────┬────────────────────────────────────────────┘    │
                   │          │ 结果                                            │
                   └──────────┼───────────────────────────────────────────────┘
                              │  同时写入：
                              ├─► RF 写端口（WABR：按实际宽度写）
                              └─► MCOS 槽（budget = 编译器 hint + 硬件自适应）
```

**与 NVIDIA 现状的差异**（只有一处是结构性新增，其余都是既有结构的语义升级）：

| 结构 | NVIDIA | OSF |
|------|--------|-----|
| RF | 2 bank/sub-core，每 bank 1×1024-bit 读口 + 1×1024-bit 写口 | 同 + **多粒度读口**（WABR） |
| Allocate | 有，预约端口，产生气泡 | 同（**保留**，冲突仍只值 1–2 拍气泡） |
| RFC | 每 bank 1 entry × 3 op_pos，**valid 位** | 同条目数，**valid 位升级为 tag + budget**（MCOS） |
| 读窗口 | 每指令独占 3 拍 | **3 级流水 + 提前收集**（ERW），Execute 时机不变 |
| result queue + bypassing | 有（隐式） | 显式化并扩展到 slot 投递（CVF，**建模辅助为主**） |

---

## 4. 机制详解

### 4.1 MCOS — 多消费者操作数槽（核心机制）

#### 4.1.1 现状与目标语义

**NVIDIA Ampere RFC（实测）**：

```
槽 = (bank, op_pos) → { tag: (warp_id, reg_id), value: 1024 bit, valid }

命中：同 warp + 同 reg_id + 同 op_pos
失效：任意读请求到达同 bank 同 op_pos（无论是否命中）
额外要求：消费者必须重新置 `.reuse` 位
```

**OSF MCOS**：

```
槽 = (bank, op_pos) → {
    tag         : { warp_id(6b), reg_id(10b), op_pos(2b) }   // 18b（NVIDIA 现状隐含在索引里）
    value       : 1024 bit                                   // 不变
    width       : 2b      // 有效宽度：0=1024, 1=512, 2=256, 3=128  ← 与 WABR 联动
    producer_pc : 16b     // 生产者 PC（截断，调试用；见 §9 开放问题 1）
    budget      : 3b      // 剩余消费者预算；**0 = EMPTY（不可交付）**  ★ 新增
}
```

> **v0.3 修正**（critic 第 2 轮 BLOCKER）：v0.2 保留了独立的 `valid` 位，与"由 budget 派生"的注释冲突，且状态机出现 `(valid=1, budget=0)` 的未定义组合。v0.3 **删除 `valid` 位**——`budget` 是**唯一真源**，`budget == 0` 即 EMPTY。这同时省下 1 bit/槽。

**语义变化只有一条**：**槽的有效期由"读一次"改为"被领取 budget 次"**。

#### 4.1.1b 槽状态机（**规范定义**，v0.3 收敛为两态）

槽只有两个状态，由 `budget` 唯一确定：

| `budget` | 状态 | 消费者请求命中 tag 时 | 进入该状态的唯一方式 |
|----------|------|---------------------|---------------------|
| 0 | **EMPTY**（等价 DEAD） | **不交付** → 走 RF 读路径 | CONSUME 耗尽 / INVALIDATE |
| > 0 | **LIVE**（有效，可交付） | **交付槽值**；`budget--` | **仅 FILL** |

**三个状态转移（穷举，不存在第四条路径）**：

| 转移 | 触发者 | 动作 | 条件 |
|------|--------|------|------|
| **FILL** | 生产者（写回端） | 写 `value` + `tag`；`budget := budget_at_fill`（见 §4.1.3c）；**无条件覆盖**目标槽 | 与 RF 写入**同拍** |
| **CONSUME** | 消费者 | 交付 `value`；`budget--`（归零即 EMPTY） | `budget > 0` 且 `tag` 匹配 |
| **INVALIDATE** | 写回端 | 对**同一 `(warp_id, reg_id)` 在所有 op_pos 上的槽**：`budget := 0`；并清零该 warp 该 op_pos 的 `demand_streak` | 任何对 `(warp_id, reg_id)` 的 RF 写入 |

**规范条款**：

- **C-1**：`budget == 0` 的槽**一律不交付**。这是"读一次即失效"（NVIDIA Ampere 实测口径）与"被领取 budget 次"（OSF 口径）的**唯一分界**。
- **C-2**：**进入 LIVE 的唯一路径是 FILL**。任何其它路径都不得把 `budget` 从 0 变为 >0——**包括自适应通道**。因此**不存在"空槽被重新武装但 value 陈旧"的路径**。
- **C-3**：**写回即失效**（write-invalidate）是**独立的正确性前提**，与 `budget` 正交：任何对 `(warp_id, reg_id)` 的 RF 写入，都必须立即把**该 `(warp_id, reg_id)` 在所有 op_pos 上的槽**置为 EMPTY（`budget := 0`），并清零对应 `demand_streak`。
  - **覆盖所有 op_pos 是必需的**：生产者只填充自己 annotation 的那一个 op_pos 槽；若只失效"指向它的那一个"，同一 `(warp_id, reg_id)` 在**其它 op_pos** 上的槽会带着**陈旧 value** 残留 → 后续 tag 命中将交付陈旧值。
  - **顺序**：写回时先 **INVALIDATE**（清旧值的所有槽），**再 FILL**（填新值到目标 op_pos 槽）。
- **C-4**：**读一次即失效**（read-once，NVIDIA Ampere 实测口径）在 OSF 中退化为 `budget_max = 1` 的特例。

#### 4.1.2 正确性论证（可证）

> **命题**：MCOS 不改变任何指令的语义。

**证明**：
1. 槽中的 `value` 是 RF 中 `(warp_id, reg_id)` 的**权威副本**，由生产者（写回端）在写 RF 的**同一拍**通过 FILL 写入。
2. 消费者领取槽值时，靠 **tag 精确匹配**（warp_id + reg_id + op_pos 全等）确认这是它要的那个操作数。
3. 由 **C-3**，若 RF 中该寄存器被改写，**该寄存器在所有 op_pos 上的槽**立即 EMPTY（且 `demand_streak` 清零）→ 不会有陈旧 value 残留。
4. 由 **C-2**，**进入 LIVE 的唯一路径是 FILL**，而 FILL 必然写入当拍的最新值 → **槽值恒等于 RF 当前值**。
5. 由 **C-1**，EMPTY 槽不会被交付 → 不会出现"交付陈旧值"或"交付已耗尽的值"。
6. 领取操作**只减少一次 RF 读**，不产生、不修改任何值。
7. 预算自适应（§4.1.3c）**只影响 FILL 时分配的 `budget`**，不改变 `value`；且每次交付仍需 tag 匹配。
8. ∴ 所有被 MCOS 供给的操作数与"从 RF 直接读"**逐位相同**。∎

**推论（v0.3）**：

> **当 `budget_max = 1` 时，MCOS 精确退化为 NVIDIA 现状**——FILL 时 `budget = min(1, budget_max) = 1`，CONSUME 一次后 `budget` 归零即 EMPTY（C-1 + C-2），与 Ampere 的 read-once 语义**逐拍等价**。
>
> 该推论**不再依赖"禁用自适应重武装"这一额外前提**：v0.3 把自适应从"重武装"改为"**FILL 时分配 budget**"，因此 `budget_max = 1` 时自适应**在数学上无法放大 budget**（`min(1, budget_max)` 与 R-G2 上限共同封死）。
>
> R-G1 仍然保留，但它的作用退化为**"预算分配不依赖启发式信号"**：当 `budget_max = 1` 时**不维护 `demand_streak` 计数器**（无额外状态、零面积）。

#### 4.1.3 预算来源：编译器 hint + 硬件自适应双通道

**通道 A — 编译器 hint（`budget_hint`）**：

编译器在 GEMM 这类已知模式下能算出"该值将被 N 条指令消费"。但：
- 编译器**不可能总知道**（运行时 warp 分支、间接寻址、动态边界）；
- 让编译器为每个值标注 N 会**大幅增加指令编码宽度**（NVIDIA 的控制字只有 4 bit reuse flags + 4 bit stall cycles）。

**提案**：控制字里用 **2 bit** 编码 `budget_hint ∈ {0=不复用, 1=单次, 2=少量(≤4), 3=多(≤16)}`，硬件按 hint 上限截断。

#### 4.1.3b 门控表（**规范**）

| `budget_hint` | `budget_max` | 自适应预算通道 | 等价于 NVIDIA 现状？ |
|---------------|--------------|----------------|-------------------|
| 0（不复用） | 0 | **禁用**（槽从不 LIVE） | 是 |
| 1（单次） | 1 | **禁用**（`demand_streak` 不维护） | **是**（FILL→1 次交付→EMPTY） |
| 2（少量 ≤4） | 4 | 启用（`demand_streak ≥ 3` → FILL 分配 4） | 否（多消费者） |
| 3（多 ≤16） | 16 | 启用（`demand_streak ≥ 3` → FILL 分配 16） | 否（多消费者） |

**规则 R-G1**：**自适应预算仅在 `budget_max > 1` 时可用**。`budget_max ≤ 1` 时，`demand_streak` 计数器**不被维护**（零额外状态），FILL 恒分配 `min(1, budget_max) = 1`。

**规则 R-G2**：`budget_max` **只能由编译器 hint 决定**；硬件自适应分配的 budget **不得超过 `budget_max`**，绝不允许把 `budget_max` 提到 hint 之上。

**规则 R-G3**：`budget_max > 1` 属于**显式 opt-in**——须由 `sm.operand_supply.rfc.multi_consumer = true` 打开（见 §8.3）。**默认 `false`**，此时 `budget_max` 恒为 1，MCOS 精确退化为现状。

#### 4.1.3c 自适应预算（**受 R-G1 门控**）与伪代码

**自适应信号**：`demand_streak[warp][op_pos]`（2 bit，**不属于槽条目**，是 per-warp 的小计数器）——统计"该 warp 在该 op_pos 上**连续需要重新取数**"的次数：

| 事件 | `demand_streak` 变化 |
|------|---------------------|
| **FILL**（该 warp 在该 op_pos 上又发生一次 RF 读） | `= min(3, demand_streak + 1)`（**先判定，后自增**） |
| **CONSUME 命中** | 不变 |
| **INVALIDATE**（该 warp 该 op_pos 的值被改写） | `= 0` |

**语义**：连续多次"又要从 RF 取同一个 op_pos 的数"= **该 warp 对这个操作数有持续需求** → 值得让这一批消费者共享同一次 RF 读。

```
/* ---- 生产者侧：FILL，与 RF 写入同拍 ---- */
FILL(warp, reg, op_pos, value, budget_max):
    slot.value = value;
    slot.tag   = { warp, reg, op_pos };
    slot.budget = (R-G1 允许 && demand_streak[warp][op_pos] >= 3)
                  ? budget_max                 // 自适应放大（R-G2 上限内）
                  : min(1, budget_max);        // 保守起点
    demand_streak[warp][op_pos] = min(3, demand_streak[warp][op_pos] + 1);

    // budget_max <= 1 时 R-G1 旁路 → slot.budget = 1（read-once，与 NVIDIA 现状逐拍等价）

/* ---- 消费者侧：CONSUME ---- */
CONSUME(warp, reg, op_pos):
    if (slot.budget > 0 && slot.tag == { warp, reg, op_pos }) {
        deliver(slot.value);
        slot.budget--;                         // 归零 → EMPTY（C-1）
        return HIT;
    }
    return MISS;                               // → 走 RF 读路径（并触发 FILL）

/* ---- 写回端：INVALIDATE（C-3），必须覆盖所有 op_pos ---- */
INVALIDATE(warp, reg):
    for each op_pos:
        if (slot[op_pos].tag.warp == warp && slot[op_pos].tag.reg == reg) {
            slot[op_pos].budget = 0;            // EMPTY；清掉陈旧 value
            demand_streak[warp][op_pos] = 0;    // 值已变 → 需求信号归零
        }
```

**收敛性**：稳态下，连续 N 个消费者共享 1 次 RF 读（N = `budget_max`）。前 3 次 FILL 是"学习期"（各 1 次 RF 读），第 4 次起进入稳态。

**信号质量的诚实标注**：`demand_streak` 是**启发式**——它统计的是"该 op_pos 上连续需要取数"的次数，**不区分是不是同一个寄存器**（区分需要额外的 `last_tag` 状态，见 §9 开放问题 5）。因此在"同一 op_pos 反复读不同寄存器"的工作负载上，信号会**偏乐观**。**但这是安全的**：`budget` 的硬上限由 R-G2 锁在编译器给的 `budget_max` 内，信号错误最坏只导致**槽驻留更久 / 替换更频繁**（性能回退），**绝不会产生错误值**。

#### 4.1.3a 与 v0.1 / v0.2 的差异（critic BLOCKER 2 + 第 2 轮 BLOCKER 的修复记录）

| 项 | v0.1（有问题） | v0.2（仍有问题） | **v0.3（修正）** |
|---|---|---|---|
| `budget == 0` 时命中 | **仍 deliver** | 不交付（C-1） | 不交付（C-1） |
| 槽置 invalid 的时机 | 全文未定义 | `budget` 归零即 `valid = 0` | **`budget` 是唯一真源，删除 `valid` 位**；EMPTY ≡ `budget == 0` |
| 自适应触发态 | `budget == 0`（但仍可交付） | DEAD 态"重武装"——**不重填 value → 陈旧值交付漏洞** | **取消"重武装"概念**：自适应只在 **FILL 时**分配 budget，**进入 LIVE 的唯一路径是 FILL**（C-2） |
| 跨 op_pos 陈旧 value | 未定义 | C-3 只说"指向它的槽" → **其它 op_pos 残留** | **C-3 明确覆盖同一 `(warp_id, reg_id)` 的所有 op_pos 槽** |
| `demand_streak` 与写回失效的交互 | 无 | 未定义 | **INVALIDATE 时清零**（值已变 → 信号归零） |
| `budget_max == 1` 时的等价性 | 破坏（允许重武装） | 依赖"R-G1 禁用重武装"这一额外前提 | **数学上自动成立**（`min(1, budget_max)` + R-G2 双重封死）；R-G1 退化为"不维护计数器" |
| `multi_consumer` 门控 | 未覆盖自适应通道 | 显式覆盖（R-G3，默认 `false`） | 显式覆盖（R-G3，默认 `false`） |

#### 4.1.4 收益量化

**GEMM 内层循环**（`C = A × B`，A 的一行被 N 个 B 列消费）：

| | RF 读次数（A 的一个元素） | 槽驻留 | 跨 warp 争用 |
|---|---|---|---|
| NVIDIA 现状 | **N 次**（每次读都让槽失效；且每条消费者须重置 `.reuse`） | 1 拍 | 低 |
| MCOS（budget=N） | **1 次** | N 拍 | **高** |
| MCOS（自适应） | 1 + (自适应增长) | 中 | 中 |

**读次数降为 1/N** → 冲突频率同频降为 1/N（因为冲突 ∝ 读次数）→ **P3 与冲突频率一并解决**。

**实测锚点**：CORF 的寄存器合并（另一种"减少读"的手段）实测 **读次数 -23%、IPC +9%、RF 动态能耗 -17%**（Table 1）。MCOS 与之正交（一个减少**读**，一个减少**重复读**），可叠加。

#### 4.1.5 代价与护栏

| 代价 | 护栏 |
|------|------|
| 槽驻留时间变长 → 跨 warp 替换频率上升 | `budget_max` 硬上限（编译器给）；自适应需 `streak ≥ 3` 才加预算 |
| 同 bank 同 op_pos 只有一个槽 → 多 warp 想驻留时互相替换 | 保持 NVIDIA 的 per-(bank, op_pos) 结构（不加条目）；替换是**语义安全**的（槽只是缓存） |
| tag 需要 warp_id + reg_id + op_pos | 复用 NVIDIA 现有的隐含索引 + 少量额外位；**条目数不变** |

#### 4.1.6 面积成本估算（v0.2：producer_pc 已截断为 16 bit）

```
每 sub-core: 2 bank × 3 op_pos = 6 槽
每槽额外位: width(2) + producer_pc(16) + budget(3) = 20 bit   ← v0.3 删除 valid 位
每 sub-core 额外: 6 × 20 = 120 bit
每 SM (4 sub-core): 480 bit ≈ 60 B
另: demand_streak 计数器 2 bit × 3 op_pos × 64 warp = 384 bit/SM（budget_max ≤ 1 时不维护）
```

**相对 RF 256 KB/SM（2,097,152 bit）：0.023%**。若 `producer_pc` 省略（见 §9 开放问题 1），槽额外成本降到 **6 × 5 × 4 = 120 bit ≈ 0.006%**；`demand_streak`（384 bit/SM）仅在 `budget_max > 1` 时存在，总计仍 **< 0.05%**。

> **这是本设计最有说服力的地方：核心机制的面积成本几乎为零，因为它只扩 tag 位、不加条目。**
> **注意**：这是**额外状态位**的面积；**读端口、crossbar、bank 结构一律不变**——这是本设计区别于"加读端口"路线的关键。

---

### 4.2 ERW — 弹性读窗口 + 提前收集

#### 4.2.1 问题

NVIDIA 的定长指令读源窗口是**每指令独占 3 拍**：

```
issue(i)   [0]──[1]──[2]──[3]──▶ Execute(i)      ← 3 拍窗口，FFMA 用满
issue(i+1)                    [0]──[1]──[2]──[3]──▶ Execute(i+1)
```

- FFMA 3 源 → 3 拍用满；
- **FADD/FMUL 2 源 → 第 3 拍空转**（实测确认："even if some of these cycles the instruction is idle"）；
- 空档**不能被后续指令填**（因为窗口独占）。

#### 4.2.2 提案

**读端口 3 级流水 + 值提前到就预填下一条指令的槽**：

```
                    port0    port1    port2
读请求 i    ───────►[ ]──────►[ ]──────►[ ]     3 级流水
读请求 i+1  ─────────────────►[ ]──────►[ ]──────►[ ]
读请求 i+2  ───────────────────────────►[ ]──────►[ ]──────►[ ]

值到达时刻        t0        t1        t2
  i 的第1源 ─────► ●
  i 的第2源 ──────────────► ●
  i 的第3源 ────────────────────────► ●        (t2 到达 → Execute(i) 在 t3)
  i+1 的第1源 ────────────────────────► ●      ← ★ 填 i 留下的空档
  i+1 的第2源 ──────────────────────────────► ●
```

**关键约束（保 I2）**：**Execute(i) 仍然严格在 `issue(i) + 3` 进入**。提前到达的值只是**提前落位**（存进 slot buffer），不改变 Execute 时机。

**因此**：延迟契约完全不变（编译期已知 3 拍），但**读端口利用率从"每指令最多 3/3"提升到"接近 3/3 稳态"**。

#### 4.2.3 收益

| 场景 | 现状 | ERW 后 |
|------|------|--------|
| 全 FFMA 密集 | 3 源 × 1 拍 = 满 | 满（无变化） |
| FADD/FSEL 密集（2 源） | 3 源用 2 拍 → **33% 读带宽浪费** | 空档被下一条填 → **≈0 浪费** |
| 混合 | 波动 | 平滑 |

**2 源指令在向量/标量混合 kernel 中占比很高**（`LOP3`/`ISETP`/`IADD3` 常为 2–3 源）。

#### 4.2.4 代价（**v0.2 已补 warp 交错调度的语义定义**）

- 需要 issue 端提供 **前瞻窗口**（issue buffer 深度 +1）；
- 需要一个 **slot buffer**（每 bank 少量条目）存放提前到达的值；
- 提前收集要求"下一个要读的源"可预测。

> ⚠ **v0.1 遗漏**（critic SHOULD_FIX 3）：v0.1 假设"前瞻窗口 = 同 warp 的下一条指令，且顺序发射无分支"。**这在真实调度下不成立**：
> - 本仓 `include/tlm/gpu/sm/issue_unit_tlm.hh:6` 是 **round-robin 跨 warp 调度**（只记 `last_issued_warp_id_`）；现代 NVIDIA 实测调度策略是 **CGGTY（Compiler Guided Greedy Then Youngest）**，同样**跨 warp**。
> - 因此"下一条指令"属于哪个 warp **要到调度拍才确定**；跨 warp 时，一个 warp 的 slot buffer 内容对另一个 warp 无意义。
> - 分支（`BRA`/`EXIT`）会改变后续取指路径，前瞻的"下一条"可能根本不会被执行。

**v0.2 的语义定义（规范）**：

| 概念 | 定义 |
|------|------|
| **前瞻单元** | **调度序**上的下一条指令，**不是**同 warp 的下一条。即 ERW 填的是"端口空档"，不是"某 warp 的私有槽" |
| **slot buffer 命名空间** | 按 **(warp_id, op_pos)** 索引；**跨 warp 不可共享**。一个 warp 的提前值只能被**同一 warp** 的后续指令领取 |
| **跨 warp 切换时** | 切换本身**不 flush**（值已按 warp 命名空间隔离）；但**切换后新 warp 的首个指令无法享受前一条指令留下的空档**（空档属于上一个 warp 的源） |
| **分支时** | 分支**解析后 flush** slot buffer（保守）：已预取但可能不执行的源作废，flush 气泡计入预算 |
| **跨 warp 切换的额外代价** | 既有事实（Volta 论文 §2.1 实测）：yield flag 清空 → 调度器切 warp → **所有 reuse flags 失效，+1 cycle**。ERW **不改变**该行为，但会与之叠加 |

**净效果（修正后的诚实口径）**：

- **同 warp 连续发射**（ILP 好、编译器已排好序）→ ERW 收益显著；
- **跨 warp 交错**（本仓默认 round-robin、现代 NVIDIA 的 CGGTY）→ **收益大幅缩水**，因为空档无法被下一个 warp 复用；
- **分支密集** → flush 气泡可能让 ERW **净亏损**。

> **结论**：ERW 的收益**依赖"同 warp 连续发射"这一前提**，而这恰恰是**编译器可控**的（与 I3 一致）。因此 ERW 应与编译器的 **warp 内指令排序**协同设计，**不能**当作纯硬件优化。
> **并且**：ERW 已被列为 **P3 探索项**（§8.2），实施前必须先有基线 profiling（§9 开放问题 3）。

> **诚实标注**：ERW 的收益依赖 ILP 与指令混合度，**不是普适收益**；且分支密集 kernel 会因 flush 受损。设计时应**按 kernel 画像启用/禁用**（可作为 config 开关）。

---

### 4.3 WABR — 宽度自适应 bank 读

#### 4.3.1 问题

Ampere RF bank 读口固定 **1024 bit**（= 32 线程 × 32 bit = 一个 warp 寄存器全宽）。但：

- `HADD2`/`HMUL2`/`HFMA2` 的源是 **16-bit** 语义（实际按 32-bit 容器存）；
- `IMAD.WIDE` 的一半是 16-bit；
- 字节/半字处理 kernel 大量窄值。

**物理上已经支持子读**：Fermi 起的 bank 由 **8 个 128-bit sub-bank** 组成（一个 warp 的 32 线程寄存器条带化分布在 8 个 sub-bank 上），所以"只读 4 个 sub-bank"= 读 512 bit 是**物理可行**的。

**缺的只是"按需少读"的能力暴露**。

#### 4.3.2 提案（**v0.2 已修正物理描述**）

> ⚠ **v0.1 的物理描述有误**（critic SHOULD_FIX 2）：v0.1 写"半宽 = 只读 4 个 sub-bank"，与"32 线程寄存器条带化分布在 8 个 sub-bank"**自相矛盾**——条带化成立时，32 线程 × 16-bit = 512 bit 仍然**分布在全部 8 个 sub-bank**（每 sub-bank 64 bit），不会"只占 4 个 sub-bank"。下述为修正后的表述。

**前提（不变）**：一个 warp 的 32 线程的同一架构寄存器，被**条带化**分布在 bank 的 **8 个 128-bit sub-bank** 上（每 sub-bank 承载 4 个线程 × 32 bit）。因此：

- **全宽读** = 8 个 sub-bank 各出 128 bit = 1024 bit；
- **半宽读**（值实际只有 16 bit 有效）= 8 个 sub-bank **各出 64 bit** = 512 bit；
- **1/4 宽读** = 8 个 sub-bank **各出 32 bit** = 256 bit。

**关键澄清**：窄读**不减少 sub-bank 参与数**（8 个 sub-bank 全部参与），而是**减少每个 sub-bank 的输出位宽**。因此：

- 省的是 **读位宽（带宽与能耗）**，不是 sub-bank 数量；
- **不改变**"一个 warp 寄存器 = 一次物理读"的条带化语义；
- **不改变** bank 数、也不改变冲突判据（冲突仍按 bank 粒度）。

```
bank 读口支持 3 种粒度（由编译器在指令里给宽度提示）：
    1024 bit（默认，全宽）    ← 8 sub-bank × 128 bit
     512 bit（半宽）          ← 8 sub-bank ×  64 bit
     256 bit（1/4 宽）        ← 8 sub-bank ×  32 bit

指令编码：复用已有控制字位（CtrlBits::reserved_ctrl0/1 在 CppTLM 侧对应）
硬件行为：sub-bank 的**输出位宽门控**由槽条目的 width tag 决定（静态已知），
          因此窄读不需要额外路由，只需在每个 sub-bank 的输出级门控高位。
```

**收益（修正后口径）**：窄值密集 kernel 的 **RF 读位宽**降 **2–4×**（等价于读带宽与读能耗同比例下降）；由于冲突仍按 bank 粒度判据，**冲突频率不因此下降**（v0.1 的"冲突同频下降"是过度推论，已删）。

> **与 CORF 的关系**：CORF 的 register packing 是**写端**把窄值打包进物理寄存器的字节切片（每物理寄存器 4 × 1-byte 切片），读端再做合并与解包。**OSF 的 WABR 不做写端打包**（明确排除），因此它要求"窄值的 16 bit 有效信息在 32 bit 容器里本来就只占低位"这一前提成立——**这正是需要 width tag 记录实际有效宽度的原因**（见 §4.3.3）。两者是**不同**的优化：CORF 省的是"读了不用的高位"的能耗，WABR 省的是"读端口位宽"。

#### 4.3.3 代价与风险

- **编译器负担上升**（I3：这是 NVIDIA 一贯接受的代价）；
- **前提约束**：WABR **不改变存储布局**，只读"值的有效宽度"；因此**只有当值本来就没有占满 32 bit 容器时**才有收益（如 `HADD2` 的 16-bit 语义、部分字节指令）。**若编译器把窄值符号扩展到 32 bit，WABR 无收益**——这限制了它的适用范围（v0.1 未说明，已补）；
- **正确性风险**：若编译器给的宽度提示与实际值不符 → 读到错误数据。护栏：**写回时记录实际宽度**（值本身带宽度 tag），读时按 tag 而非按提示选择粒度 → **提示只是上界，tag 是权威**；
- 混合宽度会让 bank 的输出级增加位宽门控逻辑（面积代价待评估）。

#### 4.3.4 先例

CORF 的 **register packing** 已经证明"RF 内部可以放窄值"（每物理寄存器 4 个 1-byte 切片），并实测 **RF 动态能耗 -8%~-17%**。OSF 的差异是：**CORF 在写端打包 + 读端合并，OSF 在读端按需少读**——两者可叠加。

---

### 4.4 SOP — 推测供给（探索性）

#### 4.4.1 为什么放在"探索"

P1（4-cycle 依赖延迟）的**主因是 ALU 流水线深度**，不是操作数供给层。操作数供给层能做的只有：

| 手段 | 有效性 |
|------|-------|
| 值前递（bypassing） | **已被 NVIDIA 实现**（arXiv:2503.20481 证实 result queue + bypassing）→ 增量有限 |
| 推测执行 + 校验 | 可行但面积巨大，且**违反 I1/I2 的简单性前提** |
| 提前收集（ERW） | 只省**端口利用率**，不省**延迟** |

#### 4.4.2 唯一有希望的一处：load 路径的值预测

对 **memory dependence**（而非 ALU dependence）做预测：

- 同一个 warp 反复 load 同一地址 → 值大概率不变（"load forwarding" 的寄存器版）；
- 预测命中 → **跳过 memory latency**，直接供给；
- **护栏：tag 校验**——记录预测的地址 + 值 + 生产者，命中时校验 tag，不符则回退。

**边界声明**：这攻击的是 **memory latency**，**不是 operand supply latency**，严格说超出了本提案的题目范围。列为探索项是因为它可能与操作数供给层共享同一套"值槽 + tag 校验"机制。

#### 4.4.3 明确不做的事

- ❌ 不做 ALU 路径的值预测（无法在不动 ALU 流水线的前提下获得净收益）；
- ❌ 不做完整乱序执行（面积爆炸，见 §6）。

---

### 4.5 CVF — 值前递显式化（**建模辅助，非硅片创新**）

NVIDIA 的 bypassing 是**隐式**的（同 result queue 条目 → 紧邻消费者）。OSF 把它**显式化并扩展**：

- **扩展点**：消费者若需要的 `(warp, reg)` 正被某个 **in-flight 指令**作为目的寄存器，则可从该指令的 result queue 直接取，**不必等写回 RF 再读**（需一张 `dst_reg → producer` 反向索引）。

**但**：实测显示 NVIDIA 已有 bypassing，FFMA 依赖延迟仍是 4 cycle → **增量收益小**。

**本提案中对 OSF 的真实价值**：**在 CppTLM 里显式建模 bypassing**，否则 TLM 会把"写回 + 读出"的往返算进延迟，导致依赖链延迟被高估 1–2 拍。**这是建模准确性收益，不是硅片收益**。

---

## 5. 时序模型：如何保住 I2（编译期已知延迟）

**契约**：定长延迟指令的 Execute 进入时刻 = `issue + L`，`L` 由 ISA/编译器常量给定（NVIDIA：3 拍读源 + ALU 流水线）。

| 机制 | 是否破坏契约 | 说明 |
|------|------------|------|
| MCOS | ❌ 不破坏 | 槽只减少 RF 读；值总在 Execute 前就绪 |
| ERW | ❌ 不破坏（关键设计） | 提前到达的值只**落位**，Execute 时机仍严格 `issue + 3` |
| WABR | ❌ 不破坏 | 窄读更快，不更慢 |
| SOP | ⚠ **可能破坏** | 预测命中才早；**必须保证"最坏情况仍 ≤ L"**，否则需 fallback 路径 |

**ERW 的实现要点**（保证契约的机制）：

```
Execute(i) 的准入条件 = (cycle ≥ issue(i) + L) AND (所有源已就绪)
```

- 值**早到** → 提前落位，Execute 时机不变；
- 值**晚到**（端口冲突）→ 指令停在 Allocate（NVIDIA 现状）→ 向上游压气泡。

**因此 ERW 只会"填空"，不会"提前完成"。**

---

## 6. 定量目标与预期收益

> ⚠ **以下为设计目标值，非实测**。所有基线取自 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) 引用的实测数据。

| 指标 | NVIDIA Ampere 基线 | OSF 目标 | 依据 |
|------|-------------------|---------|------|
| RF 读次数（GEMM 内层，N 消费者） | N | **1** | MCOS |
| 读端口利用率（2 源指令密集） | 2/3 ≈ 67% | **≈ 95%+** | ERW |
| RF 读带宽（窄值 kernel） | 1× | **0.25–0.5×** | WABR |
| 槽面积成本 | — | **≈ 0.023% RF 面积**（`producer_pc` 省略则 0.006%；含 `demand_streak` 仍 < 0.05%） | MCOS 增量位估算 |
| 冲突气泡（GEMM 内层） | 0–2 拍/指令 | **≈ 0**（读降为 1/N） | MCOS 副作用 |
| 依赖链延迟 | 4 cycle | **4 cycle（不变）** | **明确不在范围内** |
| Execute 时机契约 | 编译期已知 | **编译期已知（不变）** | §5 |

---

## 7. 与 NVIDIA / 学术先例的 Novelty 对照

> **新颖度口径声明**（v0.2 补，critic SHOULD_FIX 1）：下表"新颖度"一律**相对于「NVIDIA Ampere 实测的 read-once RFC」口径**评估。**若改用「US8639882B2 专利的 write-invalidate + 多指令并发缓存」口径，MCOS 的"多消费者"本身已是既有能力**（该专利摘要逐字：`operands may be cached and reused in subsequent instructions … allowing operands for two or more instructions to be cached concurrently`；权项 7 要求容量容纳两条已译码指令；权项 1 **未限定** storage element 数量与命中条件 → 容量/复用语义属**可调工程参数**）。
>
> **因此 OSF 相对该专利的真实增量是三件事**：① **有界计数**（`budget` 计数器，专利的 cache table 只有 valid/invalidate 两态）；② **编译器 hint 编码**（2 bit `budget_hint`，把复用次数纳入指令语义）；③ **硬件自适应预算分配**（FILL 时按持续需求信号分配，受 R-G1 门控）。这三件**都不在**该专利的权项范围内。

| 机制 | NVIDIA 现状 | 学术 / 专利先例 | **OSF 的差异** | 新颖度（相对 Ampere read-once 口径） |
|------|-------------|---------------|--------------|-------|
| 操作数收集 | Tesla–Kepler 有，Volta+ 无 | CORF/Accel-Sim 假设有（**已被实测否定**） | 延续 Ampere 口径（无 OC），不复活 OC | 低（跟随） |
| bank 仲裁 | Allocate 预约 | wavefront 仲裁（GPGPU-Sim） | 延续 | 低 |
| **复用缓存（多消费者）** | `.reuse` 1-bit，**read-once**（Ampere 实测） | **US8639882B2**：write-invalidate + **多指令并发缓存**（多消费者已是既有能力）；CORF：无复用缓存 | **有界计数 `budget`** + **编译器 `budget_hint`** + **硬件自适应预算分配**（FILL 时，相对专利口径的增量） | **中高**（相对 Ampere read-once 口径）／**低**（相对专利 write-invalidate 口径） |
| 寄存器合并 | 无 | CORF（写端打包 + 读端合并，-23% 读） | 叠加 | 中（组合） |
| 窄读 | 无 | CORF packing 间接支持（**写端**） | **按需少读（读端粒度）** | 中 |
| 弹性窗口 | 无（每指令独占 3 拍） | 无 | **流水化 + 保 I2** | **中高** |
| 值前递 | 有（隐式 bypassing） | — | 显式化 + 扩展（**建模价值为主**） | 低 |
| RF 读端口数 | 1/bank | CORF：加端口**面积**成本极高 | **不加端口**（反方向） | 中（约束选择） |
| 依赖管理 | 编译器控制位 | scoreboard | 延续 | 低 |

**三条与 NVIDIA 分歧的取舍**：

1. **不加 RF 读端口**（NVIDIA 也不加，但本提案是**主动否决**这条路径）。**依据是面积与口径，不是建模精度**：
   - **面积**：CORF §1「the cost of a port is extremely high when considering the width of a warp register」——warp 寄存器 1024 bit 宽，多一个读口的面积代价极高。
   - **口径正确性**：真实 NVIDIA 实测每 bank 就是 **1 个读口**；建模成 2 读口会让 CppTLM 与硬件脱节。
   - ⚠ **不要用 Table 6 的 APE 数字当否决依据**（v0.1 的错误）：APE 是**仿真模型相对硬件的建模精度**指标。原文显示 2 读口在**性能上并不差**（MaxFlops speed-up 1.44× = Ideal 行同值、Cutlass 1.11× ≈ Ideal 1.12×、Cutlass APE 反而改善到 0.97%），而 MaxFlops APE 2.82%→28.97% **与 Ideal 行同值**，含义是"**该学术模型刻画不了多端口配置**"，**不是**"多端口硬件更差"。详见 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §2 修正说明。
2. **不加硬件条目数**（MCOS 只扩 tag 位）：保持 NVIDIA 的 per-(bank, op_pos) 结构。
3. **不复活 OC**：OC 的可变延迟与 I2 不可共存（arXiv:2503.20481 的论证）。

---

## 8. 与 CppTLM 的落地映射

### 8.1 现状约束（已实测确认）

| 事实 | 证据 | 对设计的影响 |
|------|------|-------------|
| `InstrDescriptor` 已有 `src_regs[4]` | `include/tlm/gpu/instruction_descriptor.hh` | **算 bank 不需要给 bundle 加字段** ✅ |
| `sizeof(InstrDescriptor)` **实测 = 128 字节**（2026-10-27 编译验证），而断言是 `static_assert(sizeof(InstrDescriptor) <= 128, ...)` → **余量 0 字节**。另有 `reserved_hdr`(4B) + `reserved_mem`(4B) = **8 字节可回收 padding**（未在 v0.1 的论证中计入） | 实测编译验证 + `include/tlm/gpu/instruction_descriptor.hh:74`/`:100`/`:115` | **当前无余量 → 新字段不能加**；但**回收 8B padding 可腾出空间**（若未来必须加字段） |
| `CtrlBits` 有 `reserved_ctrl0 / reserved_ctrl1` | 同上 | **reuse / budget_hint / width_hint 可塞进保留位，不涨 POD** ✅ |
| `RegFileUnit` 是 flat hash map，无 bank / 无端口 | `include/tlm/gpu/sm/reg_file.hh` | 需要新增 bank 维度 + 端口节流 |
| `IssueUnitTLM` 直接产出 `IssueToExecBundle` | `include/tlm/gpu/sm/issue_unit_tlm.hh` | 需要插入"已 issue 未就绪"的中间态 |
| `WritebackUnit` 是纯 FIFO，无节拍冲突 | `include/tlm/gpu/sm/writeback.hh` | 需要引入写端口节流 |
| `HazardTracker` 处理 RAW / vmcnt | `include/tlm/gpu/sm/hazard_tracker.hh` | **保持不变**（数据冒险与端口争用分层，见 SYNTHESIS C2） |

### 8.2 三期落地路径

| 期 | 名称 | 内容 | 产出 | 依赖 |
|----|------|------|------|------|
| **P1** | **现代口径基线** | `RegFileUnit` 加 bank 维度 + `register_bank()`（**硬件口径 `reg_index % N`**，非 gpgpu-sim 的 `+ warp_id`）；新增 `OperandSupplyUnit`（Allocate 级端口预约 + 气泡产生）；`IssueToExecBundle` **不动** | 与 Ampere 口径对齐的可信基线 | 无（可独立做） |
| **P2** | **RFC / MCOS(budget=1)** | `RegFileUnit` 加槽表（每 bank × op_pos 1 entry × 6 子条目）；`CtrlBits` 加 `reuse_mask`；**`eviction` 策略**（read_once / budgeted）**用 config 开关二选一** | 操作数复用可建模 | P1 |
| **P3** | **探索机制** | MCOS `budget` 语义 + 硬件自适应；ERW 提前收集；WABR 宽度自适应 | 前沿探索 | P2 + 评审通过 |

### 8.3 建议的 config 键（对标 gpgpu-sim 便于回归迁移）

```yaml
sm:
  operand_supply:
    model: modern            # none | modern | classic   # modern = Ampere 口径（默认）
    bank_count: 2            # per sub-core（现代口径）
    read_ports_per_bank: 1
    write_ports_per_bank: 1
    read_cycles: 3           # 定长读源窗口（保 I2）
    rfc:
      enabled: true
      slots_per_bank: 3      # 每 bank 每 op_pos 1 entry × 3 op_pos
      eviction: read_once    # read_once | budgeted（**生命周期策略**，见下表）
      multi_consumer: false  # MCOS budget>1（P3）——**同时门控自适应预算通道**（R-G1/R-G3）
    early_collect: false     # ERW（P3）
    width_adaptive: false    # WABR（P3）
```

#### 8.3.1 三种"失效/生命周期"语义的区分（**v0.2 澄清，critic SHOULD_FIX 5**）

v0.1 用一个 `invalidation: read_once | on_write` 键混装了**两个正交的概念**，导致实现方无法判断该键的语义。v0.2 拆清：

| 概念 | 性质 | 是否可配置 | 取值 | 归属 |
|------|------|------------|------|------|
| **写回即失效**（write-invalidate） | **正确性前提**（C-3） | ❌ **不可关闭** | 恒为 on | 槽的 `valid` 在 RF 写入时必须清零 |
| **读一次即失效**（read-once） | **生命周期/驻留策略** | ✅ 可配置 | `eviction: read_once`（= `budget_max = 1`，Ampere 实测口径，默认） | 槽交付一次后即 DEAD |
| **多消费者预算**（budgeted） | **生命周期/驻留策略** | ✅ 可配置 | `eviction: budgeted` + `multi_consumer: true`（P3，OSF 口径） | 槽交付 `budget` 次后 DEAD |

**实现契约**：

- `write-invalidate` **始终生效**，与 `eviction` 取值**正交**——它保证"槽值 == RF 当前值"（§4.1.2 证明第 3 条），**任何 `eviction` 取值下都不可省略**；
- `eviction: read_once` ⇒ `budget_max = 1` ⇒ **R-G1 旁路自适应通道**（`demand_streak` 不维护）⇒ FILL 恒分配 budget=1 ⇒ MCOS **精确退化为 Ampere 现状**（§4.1.2 推论）；
- `eviction: budgeted` + `multi_consumer: true` ⇒ 允许 `budget_max > 1`（由编译器 `budget_hint` 决定上界）⇒ R-G1 开放自适应预算通道；
- `multi_consumer: false` 时 **`budget_max` 恒为 1**，且自适应预算通道**静态旁路**（R-G3，`demand_streak` 不维护）。

> **⚠ 与既有调研文档的口径对齐**：[`US8639882B2` 解析](../research/SM/CudaCore/US8639882B2_源操作数收集器缓存_解析.md) 用的"失效"一词指 **write-invalidate**（专利口径）；[`arXiv:2503.20481` 解析](../research/SM/CudaCore/arXiv2503.20481_现代NVIDIA核心无操作数收集器_解析.md) 用的"失效"指 **read-once**（实测口径）。二者**不是同一个机制**——本节把两者明确拆为**正确性前提**与**驻留策略**，配置键也随之从 `invalidation` 改名为 `eviction`。

### 8.4 不做什么（明确边界）

- ❌ **不改 23 ABI**（per ADR-DGPU-08 §2.3）——本设计全部在 SM 内部；
- ❌ **不改 `InstrDescriptor` 布局**（实测 128 字节，断言 `<= 128`，**余量 0**）——控制位走 `CtrlBits::reserved_ctrl0/1`（若未来必须加字段，可回收 `reserved_hdr` + `reserved_mem` 共 8B padding，但那是**跨仓契约变更**，需 HSK 流程）；
- ❌ **不改 `IssueToExecBundle` / `WritebackToRegFileBundle`**——避免触碰 HSK-9 跨仓 size 约束；
- ❌ **不复活 OC 可变延迟模型**为默认（仅作 `classic` 对照模式）。

---

## 9. 风险、反例与开放问题

| # | 风险 / 反例 | 影响 | 缓解 |
|---|------------|------|------|
| R1 | **MCOS 槽驻留变长 → 跨 warp 替换变频繁**，在"每 warp 读不同寄存器"的工作负载下反而更差 | 性能回退 | `budget_max` 硬上限（R-G2）+ `streak ≥ 3` 才自适应 + **R-G3 显式 opt-in（默认关）**。**"最坏 = 不变差"仅在 `eviction: read_once`（默认）下成立**；`budgeted` 模式下**可能变差**，这是该模式的已知代价 |
| R1b | **驻留变长会放大跨 warp 切换的惩罚** | 性能回退 | Volta 论文 §2.1 实测：切 warp → 所有 reuse flags 失效，**+1 cycle**。`budgeted` 模式下驻留期内的 warp 切换次数上升 → 该惩罚被放大 → **`budget_max` 上限需按实测调参**（列入 §9 开放问题 3 的一部分） |
| R2 | **ERW 遇分支需 flush slot buffer** | 分支密集 kernel 受损 | 显式开关 + 按 kernel 画像启用；flush 气泡可计入预算。**且 v0.2 已明确**：ERW 收益依赖"同 warp 连续发射"，跨 warp 交错（round-robin / CGGTY）下收益大幅缩水 → 需与编译器 warp 内排序协同 |
| R3 | **WABR 宽度提示与实际不符 → 读错数据** | **正确性事故** | **tag 为权威、提示仅为上界**；写回时记录实际宽度 |
| R3b | **WABR 前提不成立时零收益**（窄值已被符号扩展到 32 bit 容器） | 收益落空 | 编译期统计窄值占比；占比过低则不启用该机制 |
| R4 | **SOP 预测错误** | 性能回退 | tag 校验 + fallback；**永不提交未校验值** |
| R5 | **OSF 全部机制都无法改善依赖链延迟（P1）** | 期望落空 | §4.4 已明确声明；本提案的价值定位在**带宽 / 冲突 / 复用**，不是延迟 |
| R6 | **"多消费者"在真实编译器里难以静态给出 budget** | MCOS 收益打折 | 硬件自适应通道兜底；且 GEMM 等主流 kernel 的消费关系是静态的 |
| R7 | **与未来 NVIDIA 实际实现脱节** | 调研价值衰减 | 本提案是**建模参考**，不是"预测 NVIDIA 未来"的赌注；CppTLM 的价值在**口径正确**而非"押中未来" |
| R8 | **沉默的语义漂移**：`budget` 自适应若实现不当，可能让**已被改写的寄存器**的值被错误领取 | **正确性事故** | **写回即失效（C-3）是硬前提，不可关闭、不可配置**（与 `eviction` 正交，见 §8.3.1）；另需在实现期补一张真值表核对（critic 验证建议） |
| R9 | **"退化为现状"推论被误读** | 实施方按错误前提实现 | 推论的前提已显式化：`budget_max = 1` **且** R-G1 静态旁路自适应 **且** `multi_consumer = false`（默认）；三条缺一则**不成立**（§4.1.2 推论 + §4.1.3b 门控表） |

### 开放问题（需评审裁决）

1. **`producer_pc` 是否必要**？占 16 bit × 6 槽 × 4 sub-core ≈ 384 bit/SM。省略可把槽面积成本从 **0.023% 降到 0.006%**。**建议省略**（调试可用独立 trace 机制）。
2. **MCOS 与 NVIDIA `.reuse` 的关系**：是把 `.reuse` 升级为 2-bit `budget_hint`，还是**新增独立字段**？后者会撞 128 字节上限（余量 0；可回收 8B padding，但属跨仓契约变更）→ **建议升级复用现有位**。
3. **ERW 是否值得做 + `budget_max` 上限取值**：ERW 收益依赖"同 warp 连续发射"（跨 warp 交错下大幅缩水，见 §4.2.4），需先有基线 profiling 才能判断；`budget_max` 的上限（4 / 16）也需按 R1b 的实测调参 → **建议 P3 阶段先做 profiling 再决策**。
4. **`eviction` 默认值**：`read_once`（= 实测口径，默认，已在 §8.3 定为 `read_once`）vs `budgeted`（= OSF 口径）。**建议默认 `read_once`**（对齐真实硬件，且保证"退化为现状"推论成立）；`budgeted` 作 opt-in 对照模式。
5. **`multi_consumer` 的门控粒度**：是全局 config 开关（本提案 v0.3 的做法），还是**按编译器的 `budget_hint` 逐指令生效**（`hint ≥ 2` 即自动允许，无需全局开关）？后者更细粒度但实现更复杂 → **待裁决**。
6. **`demand_streak` 是否需要区分寄存器**？v0.3 的信号只统计"该 op_pos 上连续需要取数"的次数，**不区分是不是同一个寄存器**（区分需额外存 `last_tag`，18 bit × 3 op_pos × 64 warp ≈ 3.4 Kbit/SM）。不加 `last_tag` 时信号会偏乐观（安全但可能浪费槽位）；加则更准但面积上升 → **待裁决**。

---

## 10. 被否决的备选方案

| 方案 | 否决理由 |
|------|---------|
| **加 RF 读端口（2/bank）** | **面积代价极高**（CORF §1：「the cost of a port is extremely high when considering the width of a warp register」——warp 寄存器 1024 bit 宽）；且与真实 NVIDIA 口径脱节（实测就是 1 读口）。⚠ **不作为依据的**：Table 6 的 APE 恶化（那是建模精度指标，含义是"该学术模型刻画不了多端口"；且 2 读口在性能上 MaxFlops 1.44×、Cutlass 1.11×，与 Ideal 行同值） |
| **硬件自动 reuse cache（无编译器提示）** | NVIDIA 两次都放弃（Kepler 的 cache table → Maxwell+ 的 `.reuse` 位）：自动命中条件不可预测，编译器无法规划 |
| **复活 OC（运行时收集）** | 引入可变延迟，与 I2 不可共存（arXiv:2503.20481 的核心论证）；NVIDIA 实测已否定 |
| **动态 bank 重排（运行时把源操作数搬到不同 bank）** | 需要 RF 支持间接寻址 + 可重排存储，面积与复杂度高；而冲突现在只值 1–2 拍气泡（**不值得**） |
| **完整乱序执行** | 面积爆炸；违反"简单 + 定长延迟"的根本前提（I1/I2） |
| **ML 驱动的操作数供给** | 与本仓"零债务 / 可解释"原则不符；且在固定延迟契约下无可插入点 |

---

## 附录 A：符号表

| 符号 | 含义 |
|------|------|
| `RF` | 寄存器堆（Register File），持久化存储 |
| `bank` / `sub-bank` | RF 的 bank 划分单元 / warp 线程条带化子单元（Fermi 起 8 × 128-bit） |
| `slot` | MCOS 操作数槽，(bank, op_pos) 索引 |
| `op_pos` | 源操作数在指令中的位置（0/1/2） |
| `tag` | 槽的匹配键 = (warp_id, reg_id, op_pos) |
| `budget` | 槽的剩余消费者预算（0 = 不复用） |
| `L` | 定长延迟指令的读源窗口（本提案取 3，NVIDIA Ampere 口径） |
| `Allocate` | 发射后、读源前的端口预约级 |
| `ERW` | Elastic Read Window，弹性读窗口 + 提前收集 |
| `MCOS` | Multi-Consumer Operand Slot，多消费者操作数槽 |
| `WABR` | Width-Adaptive Bank Read，宽度自适应 bank 读 |
| `SOP` | Speculative Operand Provisioning，推测供给 |
| `CVF` | （显式化）值前递 |
| `I1/I2/I3` | 三条不变式（见 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §3） |
| `P1–P4` | 四条遗留问题（见 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §4） |
| `C-1 ~ C-4` | MCOS 槽状态机规范条款（§4.1.1b） |
| `R-G1 ~ R-G3` | MCOS 门控规则（§4.1.3b） |

## 附录 B：关键证据索引

| 主张 | 证据 |
|------|------|
| 现代 NVIDIA 无 OC | arXiv:2503.20481 §5.3 原文 |
| 定长 3 周期窗口 + 2 源指令空转 | 同上 §5.3 |
| RFC 读一次即失效 + 命中三条件 | 同上 §5.3.1 + Listing 2 |
| RF 2 bank / 1×1024-bit 读口 / 1×1024-bit 写口 | 同上 §5.3 |
| 结果队列 + bypassing | 同上 §5.3 |
| 加 2 读口 → **性能** MaxFlops 1.44× / Cutlass 1.11×（与 Ideal 行同值）；**APE** MaxFlops 2.82%→28.97%（= Ideal 行同值，含义是"模型刻画不了多端口"，非硬件变差）；**Cutlass APE 反而 9.72%→0.97%** | 同上 Table 6（⚠ APE 是建模精度指标，不可当硬件代价用） |
| CUTLASS sgemm 关 RFC → 0.79×；RFC 覆盖 35.9% 静态指令 | 同上 §7.4 + Table 6 |
| `.reuse` 4 cache + 4 slot / 8-byte 粒度 | arXiv:1804.06826 §2.1 |
| Volta 2 bank × 64-bit，`bank = reg_index % 2` | 同上 §3.5 |
| Maxwell/Pascal 32-bit bank 每周期 1 值 | 同上 §1 |
| 跨 warp 切换使 reuse 失效 +1 拍 | 同上 §2.1 |
| 手工重写 SASS 优化 → +15.4% (132.05→152.43 GFlops/s per SMX) | 同上 §1 |
| 复用缓存硬件口径（6 槽 + cache table + 写回失效） | US8639882B2 说明书 + 权项 2/3/6/7 |
| OC 3 源同 bank ≥3 拍 | US7834881B2 说明书 FIG. 3 段 |
| 编译期 conflict-free + aligned 路线 | US8555035B1 摘要 + SUMMARY |
| 端口成本极高 / 合并读收益（-23% 读、+9% IPC、-17% 能耗） | ASPLOS'19 CORF §1 + Table 1 |
| GPGPU-Sim OC 建模（wavefront 仲裁 / 写优先 / sm_90 切 SIMPLE） | 本地 GPGPU-Sim 4.2.0 源码 `shader.h:1241` / `shader.cc:4597` / `configs/tested-cfgs/SM90_H100/gpgpusim.config:85` |
| 多消费者复用已是既有能力（专利口径） | US8639882B2 摘要（"two or more instructions … cached concurrently"）+ 权项 7 + 权项 1（未限定容量）——见 [`US8639882B2 解析`](../research/SM/CudaCore/US8639882B2_源操作数收集器缓存_解析.md) §4 |
| warp 寄存器条带化（32 线程 → 8 sub-bank） | ASPLOS'19 CORF Figure 1 基线描述（每 bank 8 个 128-bit sub-bank，32 线程连续 sub-bank 同 entry index） |

---

## 11. 评审记录

| 版本 | 日期 | 评审 | 结论 | 处理 |
|------|------|------|------|------|
| v0.1 | 2026-10-27 | critic（arch 档） | **REJECT**（`mergeable: no`），**3 BLOCKER** | 见下 |
| **v0.2** | 2026-10-27 | critic（arch 档，第 2 轮） | **REJECT**（`mergeable: no`）：B1 ✅ / B3 ✅ / **B2 ⚠ 部分闭合**——重武装语义三处互斥 + 陈旧值交付漏洞 | 见下 |
| **v0.3** | 2026-10-27 | — | 本版 | **第 2 轮 BLOCKER 已修**（评审预算 2/2 已用满，不再发起第 3 轮；余下项记入 §12 backlog） |

### v0.1 → v0.2 的 BLOCKER 闭合证据

| BLOCKER | 问题 | v0.2 闭合位置 |
|---------|------|-------------|
| **B1** | **落位违规**：`docs/research/` 是"附属 1 调研附属"，门槛"不进架构评审；仅作 reference"，而 v0.1 含三期落地路径 + config 键 + 需评审裁决的开放问题 → 方向反转 | **文件迁出** → 架构目录（状态标注改为 🟡 **设计目标声明**，并显式声明"本文不是现状真相"）。**最终落位：本仓 `docs/architecture/33-sm-operand-supply-design-target.md`**（2026-10-27 随硬件微架构调研拆分一并迁入；原 CppTLM 侧编号 `14`）。配套证据在本仓 `docs/research/SM/CudaCore/`。索引同步见本仓 `docs/architecture/INDEX.md` + `docs/research/AGENTS.md` + `docs/README.md` |
| **B2** | **MCOS 核心安全性质自相矛盾**：`budget == 0` 时仍 deliver（与"budget=0 = 不复用"矛盾）；槽置 invalid 时机全文未定义；`budget_max = 1` 下允许重武装 → 破坏"退化为现状"推论；`multi_consumer` 门控未覆盖自适应 | **新增 §4.1.1b 槽状态机规范**（EMPTY / LIVE / DEAD 三态 + 条款 C-1 ~ C-4：budget==0 一律不交付、budget 归零即 valid=0、写回失效为不可关闭的正确性前提、read-once 为 budget_max=1 特例）；**新增 §4.1.3b 门控表 + R-G1/R-G2/R-G3**（自适应重武装仅在 `budget_max > 1` 可用；`budget_max` 只由编译器 hint 决定；`multi_consumer` 默认 false 且同时门控自适应通道）；**重写 §4.1.3c 伪代码**（DEAD 态才可重武装）；**推论改为带前提的形式**；新增 **R9** 风险条目与 §4.1.3a 差异对照表 |
| **B3** | **"不加 RF 读端口"的证据类别误用**：把 Table 6 的 **APE**（仿真模型相对硬件的**建模精度**指标）当作硬件代价证据 | **§7 取舍 1 重写**：依据改为 ① CORF §1 的**面积**论据（warp 寄存器 1024 bit 宽，端口成本极高）② 与真实 NVIDIA「1 读口」实测口径对齐；**显式标注"不要用 APE 当否决依据"**并给出正确解读（2 读口性能 MaxFlops 1.44× / Cutlass 1.11× 与 Ideal 同值；MaxFlops APE 与 Ideal 行同值 = "该模型刻画不了多端口"）。**§10 被否决备选**同步改写。**[`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §2 轴 4 + C7 同步修正**（含 v0.2 修正说明框） |

### v0.1 → v0.2 的 SHOULD_FIX 处理

| SHOULD_FIX | 处理 |
|-----------|------|
| 新颖度对照漏掉 US8639882B2 | **§7 补口径声明**：新颖度一律相对「Ampere read-once RFC」口径评估；并写明**相对专利 write-invalidate 口径，MCOS 的"多消费者"已是既有能力**，OSF 真实增量 = ①有界计数 ②编译器 hint 编码 ③硬件自适应重武装（均不在该专利权项范围）。表格"复用缓存"行已补专利条目，新颖度从"高"改为"**中高**（相对 Ampere 口径）／**低**（相对专利口径）" |
| WABR 物理描述内部矛盾 | **§4.3.2 重写**：窄读**不减少 sub-bank 参与数**（8 个 sub-bank 全部参与），而是**减少每 sub-bank 的输出位宽**；收益口径改为"**读位宽/读带宽**降 2–4×"；**删除**"冲突同频下降"的过度推论（冲突仍按 bank 粒度判据）；新增 §4.3.3 前提约束（窄值须未被符号扩展，否则零收益）+ 新增 R3b |
| ERW 前瞻窗口在 warp 交错调度下未定义 | **§4.2.4 重写**：新增"前瞻单元 = **调度序**下一条"定义、slot buffer **按 (warp_id, op_pos) 命名空间隔离**、跨 warp 切换不 flush 但不共享空档、分支解析后 flush；并明确本仓 `issue_unit_tlm.hh:6` round-robin 与现代 NVIDIA CGGTY 均跨 warp → **收益依赖"同 warp 连续发射"**，需与编译器 warp 内排序协同 |
| `sizeof` 表述为未验证断言 | **§8.1 与 §8.4 修正**：表述为"实测 = 128 字节，断言 `<= 128` → **余量 0**"，并补充 `reserved_hdr`(4B) + `reserved_mem`(4B) = **8B 可回收 padding**（未在 v0.1 论证中计入）；`SYNTHESIS.md` C5 同步 |
| 三种失效口径并存关系未讲清 | **新增 §8.3.1**：拆为 ①**写回即失效 = 正确性前提，不可关闭/不可配置**（C-3）②**read-once = 驻留策略，可配置** ③**budgeted = 驻留策略，可配置**；config 键从 `invalidation` 改名为 **`eviction`**；明确 `eviction: read_once` ⇒ `budget_max = 1` ⇒ R-G1 静态旁路 ⇒ 精确退化为 Ampere 现状；并与两份上游解析的"失效"一词口径差异显式对齐 |

### v0.2 → v0.3 的第 2 轮 BLOCKER 闭合证据

| 第 2 轮 BLOCKER | 问题 | v0.3 闭合位置 |
|------------------|------|-------------|
| **B2'** | **重武装语义三处互斥 + 陈旧值交付漏洞**：①§4.1.2 证明第 5 条说"只增加 LIVE 状态的预算上限"；②§4.1.3c 伪代码从 DEAD 态"重武装"却**不重填 value**；③§4.1.3a 差异表说"需先重新填充槽值"——但填充后即 LIVE，`valid == 0` 的重武装条件**永不成立（死代码）**。且 C-3 只失效"指向它的槽"，同一 `(warp_id, reg_id)` 在**其它 op_pos** 的槽会带**陈旧 value** 进入 DEAD；`demand_streak` 在写回失效时**无清零规定** → 重武装后交付**陈旧值**，违反 §4.1.2 证明第 3 条与全文核心命题 | **取消"重武装"概念，改为「FILL 是进入 LIVE 的唯一路径」**：①**§4.1.1b 状态机收敛为两态**（`budget` 唯一真源，**删除 `valid` 位**，消除 `(valid=1,budget=0)` 未定义组合）；②**新增 C-2**（进入 LIVE 的唯一路径是 FILL，任何路径——包括自适应通道——都不得把 `budget` 从 0 变为 >0）；③**C-3 明确覆盖同一 `(warp_id, reg_id)` 的所有 op_pos 槽**并规定写回时 **先 INVALIDATE 后 FILL** 的顺序；④**自适应重定义为「FILL 时分配 budget」**（`demand_streak` 只影响 FILL 时刻的 budget 取值，**不改变 value**），伪代码重写为 FILL / CONSUME / INVALIDATE 三段；⑤**INVALIDATE 时清零 `demand_streak`**（值已变 → 需求信号归零）；⑥**§4.1.2 证明重写为 8 条**，逐条引用 C-1 / C-2 / C-3；⑦**"退化为现状"推论改为数学上自动成立**（`min(1, budget_max)` + R-G2 双重封死），不再依赖"禁用重武装"这一额外前提，R-G1 退化为"`budget_max ≤ 1` 时不维护计数器"；⑧**§4.1.3a 差异表扩为 v0.1 / v0.2 / v0.3 三列**；⑨面积估算同步（删 `valid` 位，槽 20 bit，槽面积 0.023%） |
| **SHOULD_FIX（残留）** | 开放问题 1 的面积数字仍是 v0.1 旧值（0.04% / 0.01%） | 已同步为 **0.023% → 0.006%**（§4.1.6 + §9 开放问题 1） |
| **SHOULD_FIX（残留）** | `valid` 字段注释"由 budget>0 派生"与状态机表 `(1,0)=DEAD` 行冲突 | **删除 `valid` 字段**（v0.3）→ 冲突消失 |
| **NIT** | §11 B1 闭合证据里的相对链接写作 `../architecture/14-...`（从 `docs/architecture/` 出发应为 `./14-...`） | 已改为 `./33-sm-operand-supply-design-target.md` |

### 未采纳 / 超出 critic 范围

- critic NIT（`overview.md` §3.7 / 阅读路径把"设计提案"与解析并列）——随 B1 迁移自然消解。
- critic 未审：`sm_bundles_tlm.hh:40` 的 HSK-9 size constraint 原文未在权威 spec 中检索到（沿用"未核实"标注）。

---

## 12. Backlog（评审预算用尽后转入的待验证项）

> **评审预算**: 2/2 轮已用满（per build agent 评审预算规则），**不再发起第 3 轮 critic 评审**。以下为第 2 轮 critic 提出的**验证建议**与本文**未自行执行**的核对项，转入实施/验证阶段处理。

| # | 待验证项 | 类型 | 建议动作 | 归属 |
|---|---------|------|---------|------|
| V1 | **MCOS 状态机真值表核对**：`budget==0` 时 hit 是否 deliver、槽置 EMPTY 的精确时机、`multi_consumer=false` 是否同时禁用自适应预算通道 | 静态核对 | 实现 P2 前由 build 补一张真值表，逐条比对 §4.1.1b / §4.1.3b / §8.3.1 | build（P2 实施前） |
| V2 | **`sizeof(InstrDescriptor)` 是否真 == 128、余量是否真为 0** | 编译期实测 | 本文声明为"实测"（2026-10-27 编译验证），但 critic 第 2 轮为只读未复跑；由 build/verifier 加一条 `sizeof` 打印核对 | build / verifier |
| V3 | **`openspec list --json` 实测确认无 active change 涉及 SM 操作数供给** | 仓库状态 | 本文头部标"未核实"；本提案**不创建** openspec change，但实施时需另起 | build（实施时） |
| V4 | **HSK-9 的 bundle size constraint 原文** | 契约 | `sm_bundles_tlm.hh:40` 注释称"per HSK-9 spec size constraint"，但**未在权威 spec**（`docs/superpowers/specs/2027-02-09-hsk-9-icompute-api-v1-sm-rewrite.md`）中检索到该原文（标注"未核实"） | 跨仓（HSK 流程） |
| V5 | **`demand_streak` 是否需要 `last_tag` 区分寄存器** | 开放问题 6 | 加 `last_tag`（18 bit × 3 op_pos × 64 warp ≈ 3.4 Kbit/SM）可提升信号精度；不加则信号偏乐观但**安全** | 评审裁决 |
| V6 | **ERW 的基线 profiling** | 性能数据 | §9 开放问题 3：ERW 收益依赖"同 warp 连续发射"，需先测基线再决定是否实现 | P3 前 |
| V7 | **`budget_max` 上限（4 / 16）实测调参** | 性能数据 | R1b：驻留变长会放大跨 warp 切换的 +1 cycle 惩罚 | P3 前 |
| V8 | **WABR 窄值占比统计** | 编译期数据 | R3b：若窄值已被符号扩展到 32 bit 容器，WABR 零收益 | P3 前 |

---

*本提案基于 2026-10-27 一手调研材料（3 件 NVIDIA 专利 PDF + 3 篇论文 PDF + 本机 GPGPU-Sim 4.2.0 源码 + CppTLM 源码实测）撰写。**非 NVIDIA 官方设计；未经验证；未经 Oracle/ADR 评审**。所有引号内英文为逐字引用。硅片侧真源在 ArchForge 仓（不在 CppTLM），本提案应作为**跨仓输入**同步过去。*
