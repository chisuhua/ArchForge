# 下一代 SOTA SM 操作数供给架构设计目标：OSF (Operand Supply Fabric)

> **版本**: v0.5 DRAFT — 2026-10-28（v0.1 critic REJECT / 3 BLOCKER；v0.2 复审 B2 部分闭合、重武装语义仍矛盾；v0.3 收敛为「FILL 是进入 LIVE 的唯一路径」；**v0.4 = IPC/时序专项复审：4 个 BLOCKER 修正 + IPC 目标补齐 + 读带宽口径 W 显式化**；**v0.5 = 开放项裁决：`W = 2`（O-1 关闭）、ALU 深度 `d = 1`（O-2 关闭）、WAR 改用 per-warp 依赖计数器（O-3 关闭）+ 上游「5/6/7」误读回写**；见 §11 评审记录）
> **状态**: 🟡 **设计目标声明**（非当前实现；非 NVIDIA 官方；**未经 Oracle/ADR 评审**，本文的开放问题需经评审裁决）
> **Owner**: CppTLM Team
> **文档分类**: 第 1 层 · 设计目标声明（🟡 DRAFT 愿景）—— 按本仓 [`docs/architecture/INDEX.md`](./INDEX.md) §2 分组 C「CDNA + SM 重构 + 审计」归位，并 per [`docs/research/AGENTS.md`](../research/AGENTS.md) §1「架构真源在本仓 `docs/architecture/` + `docs/adr/`；调研目录是附属证据层」判定（**SM 属通用 TLM 框架侧**；"不确定时优先放 `docs/architecture/`"）
> **上游依据**: [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md)（Operand Collector 与寄存器架构演进总结）+ [`docs/research/SM/CudaCore/`](../research/SM/CudaCore/overview.md) 8 篇逐篇解析
> **⚠ 适用域（v0.5 补充）**: **本文的全部量化结论（`W` / IPC / MCOS / ERW / WABR）均为【向量域】结论**（基于 VGPR + 3 源 FFMA）。引入**独立标量域**（SGPR + 独立标量运算单元）后，标量域**不适用**本文的 `W = 2` 带宽模型（标量域 2 源 vs 2 供给 ⇒ 无缺口）⇒ **标量域需独立参数与独立评估**，见 [`38-…`](./38-new-isa-dual-domain-structure.md) §5。
> **配套分析附录**: [`34-sm-operand-supply-ipc-timing-analysis.md`](./34-sm-operand-supply-ipc-timing-analysis.md) — **IPC 与时序分析**（IPC 模型 / 3 源 vs 2 源序列对比 / cycle 坐标时序图 / W 口径敏感性）。**本文的 §4.1.4 / §4.2 / §6 的量化结论均以该附录为推导依据**；两者口径冲突时以该附录的推导为准并回写本文。
> **配套架构方案**: [`35-sm-dependence-management-architecture.md`](./35-sm-dependence-management-architecture.md) — **五类依赖的统一框架与双后端**（RAW / WAR / WAW / 内存依赖 / 控制同步；四层分离；NV + CDNA 双后端；控制位与面积预算；CppTLM 落地映射）。**§5 的依赖规范条款以该文档为准**。
> **配套 ISA 设计**: [`36-new-isa-dependence-layer-design.md`](./36-new-isa-dependence-layer-design.md) — **新 ISA 依赖层设计方案**（候选架构比较 + 推荐方案 E：源锁存窗口不变式 ⇒ WAR 收缩 / 依赖状态 ∝ 在飞生产者数 / 复用提示语义化）。
> **⚠⚠ 后端适用范围（v0.5 补充，critic 复审追加）**：**本文 §5 的依赖规范条款（C-5 / C-8 等）只适用于「NVIDIA 行为基线建模后端」**（35 号 §3 的 NV 后端 / CppTLM 对标 NVIDIA 的实现路径）。**新 ISA 前端配置下不适用** —— 新 ISA 的 WAR 由 [`40-new-isa-spec-skeleton.md`](./40-new-isa-spec-skeleton.md) §4.5 **S-DEP-6** 覆盖（**不设 WAR 计数器**，改由 gap 内 `stall` 表达），依赖面积口径也随之改变（0.037% → **不适用**）。
> **⇒ 本文 §12 V13「WAR 计数器落地」是 NV 后端的实施阻塞项，不是新 ISA 的。** 新 ISA 机器**不得**实现 WAR 计数器（40 号 S-DEP-6 明确禁止"顺手加一个"）。
> **⇒ 本文 C-5 / C-8 与 36 号 Q-11 并非矛盾**：二者作用于**两台不同的机器**（建模宿主 vs 新 ISA）。**引用时必须带后端限定词。**
> **配套 ISA 总纲**: [`37-new-isa-design-charter.md`](./37-new-isa-design-charter.md) — **新 ISA 设计总纲**（Q-8 取代关系：新 ISA 为本仓 GPGPU 唯一 ISA，PTX/CDNA/SASS 降级为参考；ISA 范围 v1–v3；**编译器硬依赖**；连锁后果清单）。
> **配套 ISA 结构与编译器**: [`38-new-isa-dual-domain-structure.md`](./38-new-isa-dual-domain-structure.md)（**标量/向量双域结构**，借鉴 CDNA 的 SOP*/VOP* 风格）与 [`39-new-isa-compiler-backend.md`](./39-new-isa-compiler-backend.md)（**PTX/LLVM 前端 → 自研 ISA 的编译器后端方案**）。
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
> 冲突是"从 RF 读操作数"的副产品。**减少读**，就同时减少冲突、带宽占用与能耗。
> ⚠ **v0.4 修正**："减少读"**不必然**换来 IPC 提升——IPC 的收益取决于读带宽是否为瓶颈、以及该负载是 3 源还是 2 源（见下方 IPC 结论块与 §4.1.4b）。

**四个机制**：

| 机制 | 全称 | 解的问题 | 面积成本 | 状态 |
|------|------|---------|---------|------|
| **MCOS** | Multi-Consumer Operand Slot（多消费者操作数槽） | **P3** — RFC 读一次即失效；producer→N consumer 链需**每消费者各置 1 个 `.reuse` 位**才能续链（v0.4 修正："无法复用"表述过强） | **≈ 0**（只扩 tag 位，不加条目） | **核心** |
| **ERW** | Elastic Read Window（弹性读窗口 + 提前收集） | **P2** — 定长 3 拍窗口对 2 源指令**第三拍空转**（读窗口占用率 2/3；v0.4 修正：原写"浪费 25% 带宽"口径不准） | 中（读端口流水化 + slot buffer） | 重要 |
| **WABR** | Width-Adaptive Bank Read（宽度自适应 bank 读） | **P4** — 窄值仍按 1024-bit 全宽读 | 低（bank 条带已支持子读） | 重要 |
| **SOP** | Speculative Operand Provisioning（推测供给） | **P1（部分）** — load 路径的值延迟 | 高（预测表 + tag 校验） | **探索** |

**IPC 结论（v0.4 新增，推导见配套附录 [`34-…`](./34-sm-operand-supply-ipc-timing-analysis.md)）**：

| 指令序列 | 基线 IPC | 启用 MCOS 后 | **IPC 收益** | 瓶颈转移 |
|---------|---------|------------|------------|---------|
| 连续 **3 源**指令（FFMA，编译器均衡分配） | **0.667** | **1.000** | **+50%** | 读带宽 → 发射宽度 |
| 连续 **2 源**指令（FADD / FMUL，跨 bank） | **1.000** | 1.000 | **0%** | 发射宽度（读端口已 100% 饱和） |

> 单位：warp 指令 / cycle / sub-core（1 sub-core = 1 warp scheduler + 2 个 RF bank）。
>
> **三条设计准则**（v0.4 确立、v0.5 收口，取代此前「读↓ 即冲突↓ 即 IPC↑」的隐含等式）：
> 1. **MCOS 的 IPC 收益只存在于 3 源密集负载**（FFMA / GEMM）。2 源密集负载已同时打满**发射宽度**与**读端口** → MCOS / ERW / WABR 在 IPC 维度**全部为 0 收益**（只余能耗与冲突收益）。
> 2. **收益拐点在 `r = W = 2`**：3 源 → 2 读时 IPC 触顶 1.000（再降到 1 读不再涨，只剩能耗收益）。
> 3. **`W = 2` 已裁决**（v0.5，§3.1）：3 源流基线 IPC 0.667、MCOS 后 **1.000**（**+50%**）。**该提升不是自动的**——需每条 3 源指令 ≥1 个操作数由 MCOS 供给 + 剩余 2 源跨 bank（§4.1.4c）；**无复用机会的负载恒停在 0.667**（R14）。
>
> **由此，本设计的重心上移**：在 `W = 2` 下，**MCOS 不是「复用优化」，而是 3 源指令达到 FP32 峰值吞吐的必要机制**（`W = 2` 每拍只供 2 次读，而 1 warp-FFMA/cycle 需 3 次 → 缺口必须由复用补上；NVIDIA 用 RFC 补，OSF 用 MCOS 补）。

**明确不解决**：**P1 的主因**——定长延迟指令的 4-cycle 依赖延迟由 **ALU 流水线深度**决定，不是操作数供给层能单独解决的（见 §4.4 边界声明）。

---

## 1. 设计出发点：四条遗留问题

> 编号与证据见 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §4。

| # | 问题 | 量化证据 | 现有手段为何不够 |
|---|------|---------|----------------|
| **P1** | 依赖链延迟钉死 4 cycle | Volta `FFMA` 依赖延迟 4（Pascal 6）；Ampere `mad.lo.f32` 依赖 CPI 4 | NVIDIA 已有 result queue + bypassing，但那是**流水线级内**旁路，缩短的是 RF 往返，**不是 ALU 流水线深度** |
| **P2** | 定长 3 周期窗口对 2 源指令**第三拍空转** | "all the fixed-latency instructions spend three cycles for reading source operands, **even if some of these cycles the instruction is idle** (for instance when there are only two source operands)" | 空档是**延迟**现象（指令仍占满 3 拍窗口）；**稳态读带宽是否真被浪费，取决于端口是"每指令独占"还是"跨指令预约共享"**——实测气泡数据（跨 bank 无气泡 / 同 bank 1–2 拍气泡）支持后者 → **稳态带宽不浪费**，2 源流与 3 源流的差别是"每条指令多花多少读"，不是"读被浪费"（v0.4 修正，见 §4.2.1 + 附录 §3.4） |
| **P3** | RFC 读一次即失效；producer→N consumer 链的复用**需每消费者各置 1 个 `.reuse` 位**（v0.4 修正："链无法复用"表述过强——链是能复用的，代价是**编译期 N 个复用位**） | "A cached value is unavailable after a read request arrives to the same bank and operand position, **regardless of whether it hits**"；论文 Listing 2 Example 1 vs 2 精确展示：要让第 3 条指令命中，**每条消费者都须重置 `.reuse`** | NVIDIA 的 `.reuse` 是 **1-bit、read-once + 消费者可 re-arm** 语义，结构性限制复用次数（**每消费者 1 bit**） |
| **P4** | 窄值仍按全宽读取 | RF 物理上已是 8 sub-bank × 128-bit 条带（Fermi 起），但 bank 读口固定 1024 bit | CORF 的寄存器打包在**写端 + 读端合并**，**没有"按需少读"** |

---

## 2. 第一性原理：把 RF 从"值的仓库"降级为"值的持久化存储"

现状的隐含假设是：

> **每次需要操作数，都要去 RF 读一次。**

这个假设决定了后面所有的麻烦：读端口稀缺（I1）→ 冲突 → 气泡；读带宽需求（每条指令 2–3 次）→ 固定窗口（P2）；重复读 → 浪费 + 槽失效（P3）。

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
| 读窗口 | 定长 3 拍（**端口跨指令预约共享**，非"每指令独占"——v0.4 修正） | 同（ERW 只放宽读窗口的**时序约束**，**不改窗口长度 L=3**） |
| result queue + bypassing | 有（隐式） | 显式化并扩展到 slot 投递（CVF，**建模辅助为主**） |

#### 3.1 读带宽供给 `W`（**v0.5 裁决：`W = 2`**）

> **`W` = 每 sub-core 每周期可供给的 warp 寄存器读次数** = `bank 数 × 每 bank 读口数`。
> **1 次读 = 1 个 warp 寄存器（32 线程 × 32 bit = 1024 bit）**；窄读（WABR）只减**位宽**，不减**读次数**，故不进 `W`。

| 口径来源 | 取值 | 依据 | 裁决 |
|---------|------|------|------|
| **本文档硬件口径** | **W = 2** | §3 表 + §8.3 config（`bank_count: 2` × `read_ports_per_bank: 1`） | ✅ **采纳（v0.5，开放项 O-1 关闭）** |
| ERW 机制图隐含口径 | W = 1 | §4.2.2 v0.3 的单条 3 级读流水（1 source/cycle） | ❌ **已废弃**（与同文档硬件口径自相矛盾，v0.4 已删该图） |
| 硬件峰值反推口径 | W ≥ 3 | 若 1 warp-FFMA/cycle/sub-core 必须 3 次读/cycle | ❌ **不采纳**（需第 3 个 1024-bit 读口 + 写口，见下） |

##### 3.1.1 为什么是 `W = 2`（三条论据，v0.5 补）

**论据 1 — 面积（用户提出的主论据，成立）**：把 `W` 从 2 提到 3 需要**每 sub-core 再加一个 1024-bit 读口 + 一个写口**（或把 2 bank 拆成 3 bank，即同样多一组读写口）。CORF §1：「the cost of a port is extremely high when considering the width of a warp register」——warp 寄存器 1024 bit 宽，**宽读口是 RF 上最贵的单项**。§10 已否决"加 RF 读端口"这条路。

**论据 2 — RFC 的存在本身就是 `W = 2` 的证据（v0.5 新增，最强论据）**：若 `W = 3`，则 1 warp-FFMA/cycle/sub-core 无需任何复用即可达成，读复用缓存（RFC）就只是个节能/降冲突的锦上添花。但**实测相反**：
- CUTLASS sgemm **关掉 RFC → 掉到 0.79×**；**35.9% 的静态指令**至少 1 个操作数走 RFC（arXiv:2503.20481 §7.4）；
- Ampere 论文 §7.4 的端口敏感性实验：1 读口 + RFC vs 2 读口，MaxFlops 差 **44%**。

⇒ **RFC 在 Ampere 上是"够用与不够用"的分界线** ⇒ RF 读带宽就是当时的紧约束 ⇒ `W = 2` 是真值。**NVIDIA 用"复用"补上了 `W = 2` 相对峰值的缺口。**

**论据 3 — 峰值可达性分析（v0.5 修正 v0.4 的"不自洽"提法）**：

> ⚠ **v0.4 说"`W = 2` 与 128 FP32/SM/cycle 峰值不自洽"——这个提法本身是错的。** 正确的关系是：

```
1 warp-FFMA/cycle/sub-core  ⇒  每拍需 3 次源读
W = 2  ⇒  每拍只供 2 次读   ⇒  缺口 1 次读/指令

⇒ 峰值可达 ⟺ 每条 3 源指令至少有 1 个操作数【不占 bank 读槽】
   （即由 RFC / MCOS 供给，或由编译器复用消除）
```

⇒ **`W = 2` 与硬件峰值是自洽的，条件是"存在操作数复用"**——而这正是 RFC 存在的理由，也正是 **MCOS 的存在理由**。
⇒ **本设计的重心据此上移**：MCOS 不再只是"复用优化"，而是 **`W = 2` 下达成 3 源指令峰值吞吐的必要机制**（见 §4.1.4b / §6）。

##### 3.1.2 采纳 `W = 2` 后的连带结论

| 结论 | 内容 |
|------|------|
| **峰值门槛** | 3 源序列要达到 IPC 1.000，**必须**有 ≥1 个操作数由 MCOS 槽供给（编译器需具备复用意识 = I3）；否则停在 **0.667** |
| **MCOS 升级** | 从"核心机制 / P3 探索"升级为"**峰值吞吐使能器**"——命中率达 1/3 的复用即可让 3 源流打满发射口 |
| **bank 冲突一并消失** | `r = 2` 时每 bank 平均负载恰为 1.0 槽/指令 → `max_b_avg = 1` → **气泡归零**（§4.1.4b） |
| **WABR 价值下降** | `WABR` 省的是位宽不是读槽位 → 在 `W = 2` 下**不改变 IPC**（只省能耗） |
| **建模要求** | CppTLM 应把 `W` 做成**显式可配参数**（`read_ports_per_bank`），以便复现"无复用 0.667 / 有复用 1.000"两条基线（§8.3） |

> 推导、敏感性与时序图见配套附录 [`34-sm-operand-supply-ipc-timing-analysis.md`](./34-sm-operand-supply-ipc-timing-analysis.md) §3–§4。

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
| **INVALIDATE** | 写回端 | 对**同一 `(warp_id, reg_id)` 在所有 op_pos 上的槽**：`budget := 0`（**仅该 `bank = bank_of(reg)` 的 3 个 op_pos 槽**——v0.4 补齐 bank 维度）；**不清零 `demand_miss`**（v0.4：清零 = 自适应死代码，见 §4.1.3c） | 任何对 `(warp_id, reg_id)` 的 RF 写入 |

**规范条款**：

- **C-1**：`budget == 0` 的槽**一律不交付**。这是"读一次即失效"（NVIDIA Ampere 实测口径）与"被领取 budget 次"（OSF 口径）的**唯一分界**。
- **C-2**：**进入 LIVE 的唯一路径是 FILL**。任何其它路径都不得把 `budget` 从 0 变为 >0——**包括自适应通道**。因此**不存在"空槽被重新武装但 value 陈旧"的路径**。
- **C-3**：**写回即失效**（write-invalidate）是**独立的正确性前提**，与 `budget` 正交：任何对 `(warp_id, reg_id)` 的 RF 写入，都必须立即把**该 `(warp_id, reg_id)` 在所有 op_pos 上的槽**置为 EMPTY（`budget := 0`）。**清零 `demand_miss` 已从 C-3 移除**（v0.4：信号应在"消费者取数失败"时计数，见 §4.1.3c）。
  - **覆盖所有 op_pos 是必需的**：生产者只填充自己 annotation 的那一个 op_pos 槽；若只失效"指向它的那一个"，同一 `(warp_id, reg_id)` 在**其它 op_pos** 上的槽会带着**陈旧 value** 残留 → 后续 tag 命中将交付陈旧值。
  - **顺序**：写回时先 **INVALIDATE**（清旧值的所有槽），**再 FILL**（填新值到目标 op_pos 槽）。
- **C-4**：**读一次即失效**（read-once，NVIDIA Ampere 实测口径）在 OSF 中退化为 `budget_max = 1` 的特例。

#### 4.1.2 正确性论证（可证）

> **命题**：MCOS 不改变任何指令的语义。

**证明**：
1. 槽中的 `value` 是 RF 中 `(warp_id, reg_id)` 的**权威副本**，由生产者（写回端）在写 RF 的**同一拍**通过 FILL 写入。
2. 消费者领取槽值时，靠 **tag 精确匹配**（warp_id + reg_id + op_pos 全等）确认这是它要的那个操作数。
3. 由 **C-3**，若 RF 中该寄存器被改写，**该寄存器在所有 op_pos 上的槽**立即 EMPTY → 不会有陈旧 value 残留。
4. 由 **C-2**，**进入 LIVE 的唯一路径是 FILL**，而 FILL 必然写入当拍的最新值 → **槽值恒等于 RF 当前值**。
5. 由 **C-1**，EMPTY 槽不会被交付 → 不会出现"交付陈旧值"或"交付已耗尽的值"。
6. 领取操作**只减少一次 RF 读**，不产生、不修改任何值。
7. 预算自适应（§4.1.3c）**只影响 FILL 时分配的 `budget`**，不改变 `value`；且每次交付仍需 tag 匹配。
8. ∴ 所有被 MCOS 供给的操作数与"从 RF 直接读"**逐位相同**。∎

**推论（v0.4 修正：限定为"子语义等价"，**不再宣称"逐拍等价"**）**：

> **当 `budget_max = 1` 时，MCOS 在"槽只被匹配读消费"这一子语义上退化为 NVIDIA 的 read-once 行为**——FILL 时 `budget = min(1, budget_max) = 1`，CONSUME 一次后 `budget` 归零即 EMPTY（C-1 + C-2）。
>
> 该推论**不依赖"禁用自适应重武装"这一额外前提**：v0.3 把自适应从"重武装"改为"**FILL 时分配 budget**"，因此 `budget_max = 1` 时自适应**在数学上无法放大 budget**（`min(1, budget_max)` 与 R-G2 上限共同封死）。
>
> R-G1 仍然保留，但它的作用退化为**"预算分配不依赖启发式信号"**：当 `budget_max = 1` 时**不维护 `demand_miss` 计数器**（无额外状态、零面积）。

> ⚠ **v0.4 更正（critic 复审 B1）**：v0.3 的"**逐拍等价**"**不成立**——Ampere 的实测语义包含两条 OSF **未复现**的规则（§4.1.1 原文）：

> | 行为序列 | Ampere 现状（实测） | OSF（`budget_max = 1`） | 是否等价 |
> |---------|-------------------|------------------------|---------|
> | 槽有值 → 一次**不匹配**读打到同 `(bank, op_pos)` | 槽被销毁（"regardless of whether it hits"）→ 后续匹配读 **MISS** | 槽保留（CONSUME 仅在 tag 命中时 `budget--`）→ 后续匹配读 **HIT** | ❌ |
> | 生产者 `.reuse` → 消费者1 `.reuse` → 消费者2 | 消费者2 **HIT**（消费者 `.reuse` **re-arm** 槽） | 消费者2 **MISS**（`budget` 已耗尽；C-2 禁止 FILL 以外的置活路径） | ❌ |

> **第 2 行是 P3 的真正机制**：Ampere 靠"**每个消费者各自重置 `.reuse`**"实现链式复用；OSF 改为"**生产者在 FILL 时一次性发放 budget**"。这是**能力替换**，不是等价改写：
>
> - **收益**：复用决策从"每消费者 1 个 `.reuse` 位"压缩为"每生产者 1 个 `budget_hint`"，指令编码压力小（2 bit vs N bit）。
> - **代价**：**`budget_hint` 必须精确**——少给 → 后续消费者 MISS（性能回退，安全）；多给 → 槽驻留变久 → 跨 warp 替换与 R1b 的 +1 cycle 惩罚被放大（性能回退，安全）。**两者都只是性能问题，不产生错误值**（C-3 保证）。
> - **不可表达**：OSF 无法表达"N 个消费者各自 re-arm"的链（N 在运行时才确定时）。这类负载只能退回 RF 直读。
>
> **因此**：`budget_max = 1` 的准确表述是"**退化为 read-once 的槽生命周期**"，**不是**"与 NVIDIA 逐拍等价"。§4.1.1b 的 C-1~C-4 仍**不覆盖**上述第 1 行（"任意读即失效"）——本设计**有意不实现**它（槽多活一拍是**更保守**的方向：只可能多命中、不会多错值），但必须在 §9 登记为**显式偏离**（R11）。

#### 4.1.3 预算来源：编译器 hint + 硬件自适应双通道

**通道 A — 编译器 hint（`budget_hint`）**：

编译器在 GEMM 这类已知模式下能算出"该值将被 N 条指令消费"。但：
- 编译器**不可能总知道**（运行时 warp 分支、间接寻址、动态边界）；
- 让编译器为每个值标注 N 会**大幅增加指令编码宽度**（NVIDIA 的控制字只有 4 bit reuse flags + 4 bit stall cycles）。

**提案**：控制字里用 **2 bit** 编码 `budget_hint ∈ {0=不复用, 1=单次, 2=少量(≤4), 3=多(≤16)}`，硬件按 hint 上限截断。

#### 4.1.3b 门控表（**规范**）

| `budget_hint` | `budget_max` | 自适应预算通道 | 等价于 NVIDIA 的 read-once 行为？ |
|---------------|--------------|----------------|---------------------------|
| 0（不复用） | 0 | **禁用**（槽从不 LIVE） | ❌ **否**（比现状**更保守**：完全关闭复用；现状的 `.reuse` 至少能做 1 次复用）——v0.4 修正 |
| 1（单次） | 1 | **禁用**（`demand_miss` 不维护） | **是**（FILL→1 次交付→EMPTY；**仅在"槽只被匹配读消费"子语义下**，见 §4.1.2 推论） |
| 2（少量 ≤4） | 4 | 启用（`demand_miss ≥ 3` → FILL 分配 4） | 否（多消费者） |
| 3（多 ≤16） | 16 | 启用（`demand_miss ≥ 3` → FILL 分配 16） | 否（多消费者） |

**规则 R-G1**：**自适应预算仅在 `budget_max > 1` 时可用**。`budget_max ≤ 1` 时，`demand_miss` 计数器**不被维护**（零额外状态），FILL 恒分配 `min(1, budget_max) = 1`。

**规则 R-G2**：`budget_max` **只能由编译器 hint 决定**；硬件自适应分配的 budget **不得超过 `budget_max`**，绝不允许把 `budget_max` 提到 hint 之上。

**规则 R-G3**：`budget_max > 1` 属于**显式 opt-in**——须由 `sm.operand_supply.rfc.multi_consumer = true` 打开（见 §8.3）。**默认 `false`**，此时 `budget_max` 恒为 1，MCOS 退化为 read-once 生命周期（§4.1.2 推论的限定形式）。

#### 4.1.3c 自适应预算（**受 R-G1 门控**）与伪代码

**自适应信号（v0.4 重定义）**：`demand_miss[warp][op_pos]`（2 bit，**不属于槽条目**，是 per-warp 的小计数器）——统计"该 warp 在该 op_pos 上**取数失败（被迫 RF 直读）**"的次数：

> ⚠ **v0.4 更正（critic 复审 B2）**：v0.3 的 `demand_streak` **实现与定义不符，且在目标负载下是死代码**：
> - **定义 vs 实现不符**：v0.3 正文把该信号描述为"连续**需要重新取数**"（**消费者侧**事件），表格与伪代码却让它在 **FILL（生产者写回）**时自增。
> - **死代码**：C-3 规定写回时**先 INVALIDATE 后 FILL**，而 v0.3 的 INVALIDATE 会 `demand_streak := 0` → **FILL 读到的必然是 0** → `budget` 恒为 `min(1, budget_max) = 1` → **自适应永不触发**。且这恰好发生在**目标负载**（生产者每轮写同一寄存器，如 GEMM 内层）——"同一 op_pos 槽原本就存着 `(warp,reg)`"时 INVALIDATE 必然命中。
> - **结论**：v0.3 的信号**在最该有效的场景下被自己清零**，只在"槽里恰好是别的寄存器"（即信号本身偏不可靠的那类负载）才生效。

| 事件 | `demand_miss` 变化（v0.4） |
|------|---------------------------|
| **CONSUME 未命中**（消费者被迫 RF 直读） | `= min(3, demand_miss + 1)` |
| **CONSUME 命中**（槽值被交付） | `= max(0, demand_miss - 1)`（需求信号衰减，避免长期滞留导致过度分配） |
| **FILL**（生产者写回） | **不变**（FILL 不再自增——它计的是"取数失败"而非"写入次数"） |
| **INVALIDATE**（该 warp 该 op_pos 的值被改写） | **不变**（**值改变 ≠ 该 op_pos 的需求消失**；清零会造成 §4.1.3c 上述死锁） |

**语义**：该 op_pos 上**反复取不到**（槽已耗尽 / tag 不匹配）= **该 warp 对这个操作数位置有持续需求** → 值得让这一批消费者共享同一次 RF 读（因此 FILL 时分配更大 `budget`）。

```
/* ---- 生产者侧：FILL，与 RF 写入同拍 ---- */
FILL(warp, reg, op_pos, value, budget_max):
    slot.value = value;
    slot.tag   = { warp, reg, op_pos };
    slot.budget = (R-G1 允许 && demand_miss[warp][op_pos] >= 3)
                  ? budget_max                 // 自适应放大（R-G2 上限内）
                  : min(1, budget_max);        // 保守起点

    // v0.4：demand_miss 不在 FILL 时自增（v0.3 的自增 + INVALIDATE 清零 = 死代码）
    // budget_max <= 1 时 R-G1 旁路 → slot.budget = 1（read-once 生命周期）

/* ---- 消费者侧：CONSUME ---- */
CONSUME(warp, reg, op_pos):
    if (slot.budget > 0 && slot.tag == { warp, reg, op_pos }) {
        deliver(slot.value);
        slot.budget--;                                           // 归零 → EMPTY（C-1）
        demand_miss[warp][op_pos] = max(0, demand_miss[warp][op_pos] - 1);   // 命中 → 衰减
        return HIT;
    }
    demand_miss[warp][op_pos] = min(3, demand_miss[warp][op_pos] + 1);       // MISS → 递增
    return MISS;                                                 // → 走 RF 读路径

/* ---- 写回端：INVALIDATE（C-3），必须覆盖同一 (warp_id, reg_id) 在所有 op_pos 上的槽 ---- */
INVALIDATE(warp, reg):
    bank = bank_of(reg);                     // bank = reg_index % N（SYNTHESIS C3 硬件口径）
                                              // ⇒ (warp,reg) 只可能存在于这一个 bank
    for each op_pos in {0, 1, 2}:            // 该 bank 的 3 个 op_pos 槽（v0.4 补齐 bank 维度）
        if (slot[bank][op_pos].tag.warp == warp && slot[bank][op_pos].tag.reg == reg) {
            slot[bank][op_pos].budget = 0;   // EMPTY；清掉陈旧 value
            // v0.4：不再清零 demand_miss（清零 = 死代码，见上）
        }
```

**收敛性（v0.4 修正）**：v0.3 的"前 3 次 FILL 是学习期，第 4 次起进入稳态"**不成立**（学习期被 INVALIDATE 清零）。v0.4 的实际行为是**受控极限环**：

```
迭代 1..k:  budget=1 → 消费者 C1 命中、C2..CN 未命中（RF 直读）→ demand_miss 累加到 3
迭代 k+1:   FILL 分配 budget_max → C1..CN 全部命中 → demand_miss 衰减回 0
迭代 k+2:   FILL 回落 budget=1 → 回到起点
⇒ 极限环：budget 在 1 与 budget_max 之间周期振荡，周期由消费者数 N 决定
```

> **诚实标注**：这是**振荡**而非"稳态"。若要真稳态，需在 `budget_max` 方向加迟滞（如"命中后不清零、只在连续 M 拍无 miss 时才降档"），代价是额外的状态位。**当前取舍**：接受振荡（性能上是"平均 budget 介于 1 与 budget_max 之间"，不会错值），并在 §9 登记 **R12**（自适应预算为极限环，非稳态；`budget_max` 需按实测调参 → §12 V7）。

**信号质量的诚实标注**：`demand_miss` 是**启发式**——它统计的是"该 op_pos 上取数失败的次数"，**不区分是不是同一个寄存器**（区分需要额外的 `last_tag` 状态，见 §9 开放问题 5）。因此在"同一 op_pos 反复读不同寄存器"的工作负载上，信号会**偏乐观**。**但这是安全的**：`budget` 的硬上限由 R-G2 锁在编译器给的 `budget_max` 内，信号错误最坏只导致**槽驻留更久 / 替换更频繁**（性能回退），**绝不会产生错误值**。

#### 4.1.3a 与 v0.1 / v0.2 / v0.3 的差异（critic BLOCKER 2 + 第 2 轮 BLOCKER + v0.4 IPC/时序复审的修复记录）

| 项 | v0.1（有问题） | v0.2（仍有问题） | v0.3（修正） | **v0.4（IPC/时序复审）** |
|---|---|---|---|---|
| `budget == 0` 时命中 | **仍 deliver** | 不交付（C-1） | 不交付（C-1） | 同 v0.3 |
| 槽置 invalid 的时机 | 全文未定义 | `budget` 归零即 `valid = 0` | **`budget` 是唯一真源，删除 `valid` 位**；EMPTY ≡ `budget == 0` | 同 v0.3 |
| 自适应触发态 | `budget == 0`（但仍可交付） | DEAD 态"重武装"——**不重填 value → 陈旧值交付漏洞** | **取消"重武装"概念**：自适应只在 **FILL 时**分配 budget，**进入 LIVE 的唯一路径是 FILL**（C-2） | 同 v0.3 |
| 跨 op_pos 陈旧 value | 未定义 | C-3 只说"指向它的槽" → **其它 op_pos 残留** | **C-3 明确覆盖同一 `(warp_id, reg_id)` 的所有 op_pos 槽** | 同 v0.3；**并补齐 bank 维度**（`bank = bank_of(reg)` → 该 bank 的 3 个 op_pos 槽） |
| 自适应信号的定义 | 无 | 未定义 | `demand_streak`（**定义 = 消费者取数失败，实现 = FILL 计数，二者不符**） | **重命名为 `demand_miss`**，计"消费者取数失败"（命中衰减 / 未命中递增），**FILL 与 INVALIDATE 均不改它** |
| `demand_*` 与写回失效的交互 | 无 | 未定义 | INVALIDATE 时清零 → **与"FILL 读该信号"同拍 ⇒ 自适应死代码** | **INVALIDATE 不清零**（值变 ≠ 需求消失）；死代码根除 |
| `budget_max == 1` 时的等价性 | 破坏（允许重武装） | 依赖"R-G1 禁用重武装"这一额外前提 | **数学上自动成立**（`min(1, budget_max)` + R-G2 双重封死）；R-G1 退化为"不维护计数器" | 表述降级为"**read-once 生命周期的子语义等价**"，**删除"逐拍等价"**（Ampere 的"任意读即失效"与"消费者 `.reuse` re-arm"两条语义 OSF 未复现 → R11） |
| 自适应预算的收敛性 | 未定义 | 未定义 | 声称"第 4 次进入稳态"（**不成立**：学习期被清零） | 改述为**受控极限环**（budget 在 1 ↔ `budget_max` 间振荡），并登记 **R12** |
| `multi_consumer` 门控 | 未覆盖自适应通道 | 显式覆盖（R-G3，默认 `false`） | 显式覆盖（R-G3，默认 `false`） | 同 v0.3 |
| **IPC 目标** | 无 | 无 | 无 | **新增**（§4.1.4b / §6）：3 源序列 0.667 → 1.000（+50%）；2 源序列 1.000（MCOS 收益 0%）；**适用边界 = 3 源密集负载** |
| **读带宽口径 `W`** | 未定义 | 未定义 | 隐含 3 个互斥口径（硬件表 W=2 / ERW 图 W=1 / 峰值反推 W≥3） | **§3.1 显式化**（v0.4）→ **v0.5 裁决 `W = 2`**（面积 / RFC 存在性 / 峰值可达性三论据）；新增 §4.1.4c 达成条件 |

#### 4.1.4 收益量化

**GEMM 内层循环**（`C = A × B`，A 的一行被 N 个 B 列消费）：

| | RF 读次数（A 的一个元素） | 槽驻留 | 跨 warp 争用 |
|---|---|---|---|
| NVIDIA 现状 | **N 次**（每次读都让槽失效；且每条消费者须重置 `.reuse`） | 1 拍 | 低 |
| MCOS（`budget_hint = N`，`budget_max = N`） | **1 次** | N 拍 | **高** |
| MCOS（自适应，`budget_max = N`） | **1 次**（但 `budget` 在 1 ↔ N 之间**振荡**，见 §4.1.3c 收敛性） | 1…N 拍 | 中 |

**读次数降为 1/N** → 冲突频率同频降为 1/N（因为冲突 ∝ 读次数）→ **P3 与冲突频率一并解决**。

##### 4.1.4b **读次数 → IPC 的换算（v0.4 新增；B3 闭合）**

> **此前本文只写"读↓ / 冲突↓"，从未把它换算成 IPC**——而这正是设计目标的验收口径。推导见配套附录 [`34-…`](./34-sm-operand-supply-ipc-timing-analysis.md) §3。

**稳态 IPC 上界**（per sub-core，1 sub-core = 1 warp scheduler + 2 个 RF bank）：

```
IPC_max = min( I_issue , W / r , 1 / max_b_avg )
    I_issue   = 1   （每 scheduler 每 cycle 发 1 条）
    W         = 每周期可供给的 warp 寄存器读数（§3.1 口径，**待裁决 O-1**）
    r         = 每条指令实际需要的 RF 读数 = 源操作数 − 被 MCOS 命中的数
    max_b_avg = 跨指令平均后单 bank 的最大槽位负载
```

| 指令序列 | `r` | **基线 IPC** | **MCOS 后 IPC** | **IPC 收益** | 瓶颈转移 |
|---------|-----|------------|--------------|------------|---------|
| 连续 **3 源**（FFMA，编译器均衡分配） | 3 | **0.667** | **1.000**（`r`→2） | **+50%** | 读带宽 → 发射宽度 |
| 连续 **3 源**（FFMA，MCOS 复用 2 个操作数） | 1 | 0.667 | 1.000 | +50%（**已触顶**） | 发射宽度 |
| 连续 **2 源**（FADD/FMUL，跨 bank） | 2 | **1.000** | 1.000 | **0%** | 发射宽度（读端口已 100% 饱和） |

**三条结论**：

1. **收益拐点在 `r = W = 2`**：3 源 → 2 读时 IPC 触顶 1.000（被发射宽度卡住），再降到 1 读**不再涨**，只余能耗与冲突收益。
2. **MCOS 的 IPC 收益只存在于 3 源密集负载**。2 源密集负载已同时打满发射宽度与读端口 → **MCOS / ERW / WABR 在 IPC 维度全部为 0 收益**（只余能耗与冲突收益）。**这是 OSF 的适用边界，必须写进 §6。**
3. **对 `W` 敏感**：`W = 2`（本文档硬件口径）→ 3 源流 0.667、MCOS +50%；`W = 3` → 3 源流 **1.000**、**MCOS 的 IPC 收益归零**。**v0.5 已裁决 `W = 2`**（§3.1），故上述数字为**定值**而非条件式。

##### 4.1.4c **`W = 2` 下 IPC = 1.000 的达成条件（v0.5 补：把 §3.1 的结论落到可验收的条款）**

> **命题**：在 `W = 2` 下，**连续 3 源序列达到 IPC = 1.000** ⟺ **每条指令至少有 1 个源操作数由 MCOS 槽供给**（即 `r ≤ 2`），**且**剩余的 2 个源在 2 个 bank 上**跨 bank 分布**（`max_b_avg = 1`）。

| 条件 | 不满足时 | 满足时 |
|------|---------|--------|
| ① 复用机会存在（编译器具复用意识，I3） | 无复用 → `r = 3` → IPC **0.667** | `r = 2` |
| ② `budget_hint` 正确（§4.1.3b 门控表） | hint 少给 → 消费者 MISS → 实际 `r` 仍为 3 | `r = 2` 成立 |
| ③ 剩余 2 源跨 bank（编译器分配） | 同 bank → `max_b_avg = 2` → IPC **0.500** | `max_b_avg = 1` |
| **合计** | — | **IPC = min(1, 2/2, 1/1) = 1.000** |

**附带效果**：`r = 2` 且跨 bank 时，**每 bank 平均负载恰为 1.0 槽/指令** → **bank 冲突气泡归零**（`max_b_avg = 1` ⇒ 气泡 = `max_b − 1` = 0）→ **MCOS 同时解决带宽瓶颈与冲突气泡**。

> ⚠ **诚实的失败模式**：若工作负载**没有复用机会**（如寄存器压力极大的标量代码），则 `W = 2` 下的 3 源流**恒定停在 IPC 0.667**——这是"不加第 3 个读口"的**直接代价**，且**无法由硬件弥补**（编译器是唯一能创造复用机会的主体）。**故 OSF 的编译器侧协同（I3）与 MCOS 的 `budget_hint` 是同一件事的两端，缺一不可。**（风险登记：R14）

**实测锚点与弹性对照**：CORF 的寄存器合并（另一种"减少读"的手段）实测 **读次数 -23%、IPC +9%、RF 动态能耗 -17%**（Table 1）；CORF 基线为 **读 -10% → IPC +4%**。**弹性 ≈ 0.4**（远低于"读↓1% → IPC↑1%"的线性直觉）——因为真实 kernel 里读带宽**未必是唯一瓶颈**。MCOS 与 CORF 正交（一个减少**读**，一个减少**重复读**），可叠加；但 **§6 的 IPC 目标应按弹性 ≈ 0.4–1.0 区间取值，不应按线性外推**。

#### 4.1.5 代价与护栏

| 代价 | 护栏 |
|------|------|
| 槽驻留时间变长 → 跨 warp 替换频率上升 | `budget_max` 硬上限（编译器给）；自适应需 `demand_miss ≥ 3` 才加预算 |
| 同 bank 同 op_pos 只有一个槽 → 多 warp 想驻留时互相替换 | 保持 NVIDIA 的 per-(bank, op_pos) 结构（不加条目）；替换是**语义安全**的（槽只是缓存） |
| tag 需要 warp_id + reg_id + op_pos | 复用 NVIDIA 现有的隐含索引 + 少量额外位；**条目数不变** |
| `budget_hint` 必须精确（少给→miss，多给→槽驻留变久） | 少给/多给**都只是性能回退**，不会产生错误值（C-3 保证槽值恒等于 RF 当前值）；上限由 R-G2 锁死在 `budget_max` |

#### 4.1.6 面积成本估算（v0.2：producer_pc 已截断为 16 bit）

```
每 sub-core: 2 bank × 3 op_pos = 6 槽
每槽额外位: width(2) + producer_pc(16) + budget(3) = 20 bit   ← v0.3 删除 valid 位
每 sub-core 额外: 6 × 20 = 120 bit
每 SM (4 sub-core): 480 bit ≈ 60 B
另: demand_miss 计数器 2 bit × 3 op_pos × 64 warp = 384 bit/SM（budget_max ≤ 1 时不维护）
```

> **tag 位不计入"额外位"的依据（v0.4 补，N4）**：Ampere 的 RFC 条目**已经**必须存 `warp_id + reg_id`（命中条件要求逐位比较），`op_pos` 由子条目索引隐含 → **tag 的 18 bit 是存量结构，非增量**。本设计的**净增** = `width(2) + producer_pc(16) + budget(3) − valid(1)` ≈ **20 bit/槽**；若 `producer_pc` 省略（§9 开放问题 1）则为 **4 bit/槽**。

**相对 RF 256 KB/SM（2,097,152 bit）：0.023%**。若 `producer_pc` 省略（见 §9 开放问题 1），槽额外成本降到 **6 × 5 × 4 = 120 bit ≈ 0.006%**；`demand_miss`（384 bit/SM）仅在 `budget_max > 1` 时存在，总计仍 **< 0.05%**。

> **这是本设计最有说服力的地方：核心机制的面积成本几乎为零，因为它只扩 tag 位、不加条目。**
> **注意**：这是**额外状态位**的面积；**读端口、crossbar、bank 结构一律不变**——这是本设计区别于"加读端口"路线的关键。

---

### 4.2 ERW — 弹性读窗口 + 提前收集

#### 4.2.1 问题（**v0.4 修正前提**）

NVIDIA 的定长指令读源窗口是**定长 3 拍**：

```
issue(i)   [0]──[1]──[2]──[3]──▶ Execute(i)      ← 3 拍窗口
issue(i+1)                    [0]──[1]──[2]──[3]──▶ Execute(i+1)
```

- FFMA 3 源 → 3 拍用满；
- **FADD/FMUL 2 源 → 第 3 拍空转**（实测确认："even if some of these cycles the instruction is idle"）。

> ⚠ **v0.4 修正前提（critic 复审 B4）**：v0.3 写"窗口**每指令独占**，空档**不能被后续指令填**"——**该前提与本文档自身的硬件口径和实测证据都不自洽**，而整节 ERW 的收益量化都建立在它之上：
>
> | 证据 | 指向 |
> |------|------|
> | 本文档 §3 / §8.3：2 bank × 1×1024-bit 读口/sub-core | **端口可被多条指令共享**，非独占 |
> | 实测"跨 bank 无气泡 / 同 bank 1–2 拍气泡" | 若窗口独占，FMUL 同 bank（只需 2 拍）本可塞进 3 拍窗口 → **应为 0 气泡，与实测矛盾** |
> | 实测"FMUL 两源同 bank → 1 拍气泡" | 气泡 = `max_b − 1`，即**单 bank 槽位争用**，而非窗口独占 |
>
> **正确表述（v0.4）**：读端口是**跨指令预约共享**的；每条指令的源读必须落在自己的 `[issue, issue+2]` 窗口内（**时序约束**），但窗口与窗口之间**共享槽位**。2 源指令的第 3 拍"空转"指的是**该指令自身**没有第 3 个源要读，**不代表该拍的端口槽位闲置**——稳态下那些槽位由后续指令占用（见附录 §3.3 的槽位占用图）。
>
> **因此 v0.3 的"33% 读带宽浪费"结论不成立**（稳态利用率见 §4.2.3 修正表）。

#### 4.2.2 提案（**v0.4 重画：按 bank 分列，消除 v0.3 图的自相矛盾**）

**读端口按 bank 流水化 + 值提前到就预填下一条指令的槽**：

```
              bank0 读口                     bank1 读口
             (1 槽/cycle)                   (1 槽/cycle)
cycle:   t0    t1    t2    t3    t4    t5    t6    t7
b0    │  I0   I0   I1   I2   I2   I3   I4   I4        ← 每拍最多 1 个槽
b1    │  I0   I1   I1   I2   I3   I3   I4   I5
发射  │  I0   I1    —   I2   I3    —   I4   I5        ← 稳态 IPC = 0.667（3 源）
```

**每条指令的 3 个源的槽位分布**（以 I0 为例，issue@`t0`）：`b0@t0`、`b0@t1`、`b1@t0` —— 全部落在 `[t0, t0+2]` 窗口内 ✔；同 bank 的两个源占**不同拍** ✔。

**关键约束（保 I2）**：**Execute(i) 仍然严格在 `issue(i) + 3` 进入**。提前到达的值只是**提前落位**（存进 slot buffer），不改变 Execute 时机。

> ⚠ **v0.4 删除 v0.3 的 ERW 图**（S1）：该图只画了**一条** 3 级读流水（隐含 `W = 1`），且把 `i 的第3源` 与 `i+1 的第1源` 画在**同一拍 t2**——**单宽流水一拍不可能出 2 个值**。若按该图实现，读带宽会**减半**（3 源序列 IPC 从 0.667 掉到 0.333）。v0.4 改为**按 bank 分列**的槽位占用图（与 §3.1 的 `W` 口径一致）。

**ERW 真正改变的是什么**（v0.4 精确表述）：

| | v0.3 的表述 | **v0.4 的表述** |
|---|-----------|---------------|
| 机制 | "把独占窗口的空档填掉" | **放宽读窗口的时序约束**：允许某条指令的源读**早于** `issue`（提前收集到 slot buffer） |
| 解决 | "读带宽利用率 2/3 → 95%" | **bank 偏斜场景的气泡**：3 源同 bank 时本需连续 3 拍占用同一 bank；提前收集可让这次占用**跨过 issue 边界**，避开与邻居的争用 |
| 稳态带宽 | 声称可提升 | **不变**（端口总数与每拍槽位数不变） |

#### 4.2.3 收益（**v0.4 修正口径**）

| 场景 | 现状 | ERW 后 |
|------|------|--------|
| 全 FFMA 密集（3 源，均衡分配） | 读端口 100% 饱和，IPC **0.667** | **不变**（0.667）——瓶颈是**读带宽**，ERW 不增端口 |
| 全 FFMA 密集（3 源同 bank） | 单 bank 3 槽/指令 → IPC **0.333**，气泡 2 拍 | **气泡可减**（提前收集跨过 issue 边界）→ IPC 向 0.5 靠拢 |
| FADD/FSEL 密集（2 源，跨 bank） | 读端口 100% 饱和，IPC **1.000**（发射宽度上限） | **不变**——**已无带宽余量可回收**（v0.3 的"≈0 浪费"不可达：已经 0 浪费） |
| 混合 | 波动 | 平滑 |

> **v0.4 的结论反转**：v0.3 称 ERW 让 2 源密集场景"浪费 33% → ≈0"。**实测口径下 2 源流的稳态读带宽利用率本就是 100%**（每 bank 每拍 1 读，IPC 1.0 时刚好打满），**没有 33% 可回收**。ERW 的真实收益是**气泡削减**（bank 偏斜场景），量级远小于 v0.3 的表述。
>
> **ERW 的 IPC 收益 = 0**（在均衡分配的稳态下）；它只在 **bank 偏斜 / 混合指令流**下通过减少气泡间接提升 IPC。**这是与 v0.3 最大的口径差异，也是 §8.2 把 ERW 列为 P3 探索项的加强理由。**

**2 源指令在向量/标量混合 kernel 中占比很高**（`LOP3`/`ISETP`/`IADD3` 常为 2–3 源）——但按 v0.4 口径，**这一负载恰好是 OSF 收益最小的一类**（见 §4.1.4b 结论 2）。

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
| 提前收集（ERW） | 只省**端口利用率**，不省**延迟**（v0.4 修正：ERW 的稳态 IPC 收益为 **0**，只减气泡） |

#### 4.4.1b ALU 流水线深度与 P1 的 4-cycle（**v0.5：开放项 O-2 关闭，`d = 1`**）

> **口径声明（v0.5 重写）**：v0.4 曾据上游"5/6/7 cycle"推出 `d = 2`，并记为"与实测差 1 拍"。**v0.5 核查一手原文后判定：该推论基于对来源的误读，"1 拍差"不存在。**

##### ① 可测量的三个硬数字

| 量 | 值 | 性质 | 来源 |
|---|-----|------|------|
| **定长指令的依赖延迟**（issue → 结果可用） | **4 cycle** | **实测 + 语义验证** | arXiv:2503.20481 §4：「an addition whose latency is four cycles … encodes a four in the Stall counter」；并验证「if the Stall counter is not properly set, the result of the program is incorrect」 |
| **源操作数读窗** | **3 cycle** | **实测** | 同上 §5.3：「all the fixed-latency instructions spend three cycles for reading source operands」 |
| **FU 占用**（输入 latch） | **1 cycle**（全 warp 宽） | **实测** | 同上 §5.1.1：「Execution units have an input latch that must be free when the instruction reaches the execution stage. This latch is occupied for two cycles if the width of the execution unit is just half warp, and for **one cycle if its width is a full warp**」 |

⇒ **Ampere FP32 FU 是全 warp 宽 → 1 拍占用** ⇒ `Execute 进入 → 结果可用 = 1 拍` ⇒ **OSF 取 `d = 1`**。

##### ② 「5/6/7」的真身（**v0.5 更正上游误读**）

arXiv:2503.20481 §3 的 Listing 1 是 **6 条指令的序列**（`CLOCK / NOP / FFMA / FFMA / NOP / CLOCK`），原文逐字：

> 「Replacing R_X and R_Y by odd numbers (e.g., R19 and R21), we get an elapsed time of **five cycles (the minimum since each sub-core can issue one instruction per cycle)**. If we change R_X to an even number … the reported number of cycles is **six**. Finally, the elapsed time is **seven** cycles if we use an even number for both operands … In summary, **two consecutive instructions can have from 0 to 2 cycles of bubbles in between**, depending on which registers they use.」

⇒ **5/6/7 是"序列 elapsed"，不是"单条指令的 issue→result 延迟"**；5 是序列下界（每 sub-core 每拍发 1 条），6/7 是 bank 冲突多出的 1/2 拍**气泡**。
⇒ **上游 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §1 与两处 overview 的「issue 侧气泡：0/1/2 冲突 → 5/6/7 cycle」是误读**（已由 v0.5 回写标注，见 §11）。
⇒ **`d = 2` 的推论作废**；**`d = 1` 与实测 4-cycle 完全自洽**，**O-2 关闭**。

##### ③ 「不同指令有不同长度」——有，但**不是可变深度 ALU**

Volta 论文 Table 4.1（**实测，公开文献中唯一成体系的 SASS 延迟表**）：

| 架构 | 指令类 | 延迟 (cycle) |
|------|--------|------------|
| **Pascal** | FADD/FMUL/**FFMA**/LOP3/IADD/… | **6** |
| | DADD/DMUL/DFMA | 8 |
| | FSET/DSET/DSETP/ISETP/FSETP | 12 |
| | POPC/FLO/MUFU/F2F/F2I/I2F/I2I | 14 |
| | IMUL/IMAD（软件仿真） | ~86 |
| **Volta** | IADD3/SHF/LOP3/SEL/MOV/FADD/**FFMA**/FMUL/ISETP/FSET/FSETP | **4** |
| | IMAD/FMNMX/DSET/DSETP | 5 |
| | HADD2/HMUL2/HFMA2 | 6 |
| | DADD/DMUL/DFMA | 8 |
| | POPC | 10 |
| | FLO/BREV/MUFU | 14 |

> **结论**：**延迟按指令类分档（4/5/6/8/10/14），但每一档都是"编译期已知的固定值"**——NVIDIA 把长延迟算子放在**独立管线**（FP64 8 拍、half 6 拍、SFU/MUFU 14 拍），而不是把 ALU 做成"可变深度"。**没有"可变深度 ALU"这种东西。**
>
> **对称性提醒**：**矩阵单元两侧都变**——AMD MFMA 延迟随 shape/dtype 变（MI250X 实测：16×16×16 FP16 = **32** cycle、32×32×8 = **64**、16×16×4 FP32 = **32**），NVIDIA HMMA/IMMA 同样随 shape/dtype 变（论文 §6：「the latency of a tensor core instruction depends on its operand's numeric types and sizes」）。**"定长"约束只适用于标量/向量 ALU 管线。**

##### ④ GPGPU 的合理 ALU 深度：**4 拍**，四条论据

| # | 论据 | 证据 |
|---|------|------|
| 1 | **固定延迟必须编译期已知**（I2）——可变深度会摧毁整套"零硬件冒险检测"的省面积方案 | 「Operand collector units would introduce variability in the elapsed time between issue and write-back, making it impossible to have fixed-latency instructions」；软件依赖方案 41 bit/warp = **0.09% RF** vs 硬件 scoreboard **5.32% RF**（§5.2） |
| 2 | **编码位宽只有 4 bit**：Stall counter 范围 0–15 | 深度 > 15 编不进控制字；每 +1 cycle 都要静态插 NOP 或吃 bubble |
| 3 | **延迟靠 warp 数掩盖，不靠流水深度** | Volta 白皮书：「execution latencies of core math operations can be hidden by **as few as 4 warps per SM**, assuming 4-way ILP per warp」；AMD 官方：「GPUs hide memory and instruction latency through **massive hardware multithreading** rather than complex CPU techniques such as out-of-order execution」 |
| 4 | **加深 ALU 的收益远小于加读带宽** | Ampere §7.4：1 读口 + RFC vs 2 读口，MaxFlops 差 **44%** ⇒ 瓶颈在 RF 端口，不在 ALU 深度 |

> **产业实际选择一致**：V100 实测 4、A100 文档值 4、CDNA wave64 的 VALU 占用亦为 4 拍（16 lane SIMD × 4）。**3 与 5 无一手来源支持。**

> **对 OSF 的直接影响**：`d = 1` ⇒ 本文 §5 的时间线（`Execute = issue+3`、结果可用 `= issue+4`、**依赖链率 = 4 cycle/条**）与实测一致，**无需改动**。P1 仍**不在 OSF 范围内**（依赖链率由 ALU 占用 + 读窗决定，与操作数供给层正交）。

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

**契约**：定长延迟指令的 Execute 进入时刻 = `issue + L`，`L` 由 ISA/编译器常量给定（NVIDIA：3 拍读源窗口）。

#### 5.0 术语与坐标定义（**v0.4 新增：消除 "issue" 一词双义**）

> **v0.3 的问题（S3）**：本文档同时用 "issue" 指**调度器发射**与**离开 Allocate（端口预约成功）**。§5 自己也说"值晚到 → 指令停在 Allocate → 向上游压气泡"——该指令的整条时间线被**后移**，因此 `Execute = issue + 3` 只在后者成立。

| 记号 | 定义 |
|------|------|
| `dispatch(i)` | **调度器**把指令 i 送上分配级的那一拍（可因上游阻塞而推迟） |
| **`issue(i)`** | **指令 i 离开 Allocate、端口预约成功的那一拍** —— **本文档一切时序公式的坐标原点** |
| `L` | 读源窗口长度 = **3** |
| `d` | ALU 流水线深度 = **1**（§4.4.1b，开放项 O-2 待裁决） |
| 值就绪 | ≤ `issue(i) + 2`（窗口内最晚一拍） |
| Execute 进入 | `= issue(i) + 3`（**契约不变量**） |
| 结果可用 | `= issue(i) + 3 + d = issue(i) + 4` |
| RF 写回 / MCOS FILL | `= issue(i) + 4`（与结果可用同拍；写端口每 bank 1 个） |
| 消费者最早发射 | `= issue(i) + 4`（bypassing；实测存在）→ **依赖链率 = 4 cycle/条** ✔ 与 P1 实测一致 |

> ⚠ **"气泡"的坐标含义**：上游压气泡时，被推迟的是**后续指令的 `dispatch`**；被卡在 Allocate 的那条指令，其 `issue` 整体后移，`Execute = issue + 3` 仍成立。**因此 IPC 的分子是"成功分配的指令数"，不是"dispatch 数"。**

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

#### 5.1 读/写同拍定序（**v0.5 重写：WAR 由「per-warp 依赖计数器」解决，而非「值锁存」**）

> **v0.4 的方案已被 v0.5 推翻**。v0.4 提出 C-5「**源值在 `issue` 拍锁存**」+ 替代方案「靠编译器保证无 WAR」，并估算在飞读缓冲 ≈ 1.2% RF 面积。**v0.5 依据一手实测证据改用 NVIDIA 的做法**（见 §5.2）：WAR 用 **per-warp 依赖计数器**，在**读完源操作数时释放**——面积从 **1.2% RF 降到 ~0.04% RF**，且与真实硬件行为一致。

##### 5.1.1 问题（不变）

消费者的 RF 读窗口长达 3 拍（`[issue, issue+2]`），**可能跨越生产者的写回拍**。此时消费者对"刚被写回的寄存器"应读到**旧值**（它发射时旧值才是程序序上的正确值）还是**新值**？必须定序，否则实现方无从选择。

##### 5.1.2 v0.5 规范条款

| 规则 | 内容 | 与 NVIDIA 实测的对应 |
|------|------|------------------|
| **C-5（WAR 依赖计数器，读源时释放）**〔**仅 NV 建模后端**；新 ISA 见 40 号 S-DEP-6〕 | 每 warp 维护 **WAR 计数器**：消费者在 `issue` 拍**递增**其"正在读取的源寄存器"计数器，**在读完源操作数（`issue+2`）时递减**；生产者（写回端）在写该寄存器前**检查该计数器非零则等待**。⇒ 消费者读到**旧值**（程序序正确），生产者被阻塞而非消费者 | 原文：「For WAR hazards, the mechanism is similar, with the only difference being that **the counter is decreased after the instruction reads its source operands**, instead of decreasing the counter at write-back」；「**Clearing WAR dependencies after reading the source operands is an important optimization**, since source operands are sometimes read much earlier than the result is produced, especially for memory instructions」 |
| **C-6（MCOS 命中优先于 RF 读）** | 消费者在 `issue` 拍命中 MCOS 槽时，取**槽值**（= 写回当拍写入的值）；该值在 `issue` 拍**确定并交付**，不随之后续 INVALIDATE 改变 | OSF 特有（MCOS 侧）；与 NVIDIA 的"消费者不被延后（bypassing）"一致 |
| **C-7（写回不阻塞在飞读）** | 写回与在飞读同拍发生**不产生端口冲突**（读写端口独立，方向不同） | 「each register file bank has a dedicated write port of 1024 bits」；写冲突由 result queue 吸收 |
| **C-8（面积代价）**〔**仅 NV 建模后端**〕 | WAR 计数器：每 warp 2 个 × 6 bit = **12 bit/warp** → 64 warp/SM = **768 bit/SM ≈ 0.037% RF**（对比 v0.4 值锁存方案 ≈ 1.2% RF，**降低约 30×**） | NVIDIA 全套控制字 41 bit/warp = **0.09% RF** |

> **C-5 的代价（诚实标注）**：**写者可能被读者阻塞**——若消费者的源读迟迟不发生（e.g. 它自己被前面的依赖卡住），生产者要一直等。NVIDIA 真实硬件**就是这个行为**（写回端等计数器归零），且由编译器排程规避（把长延迟读挪到独立指令序列）。OSF 采纳同一取舍：**正确性优先，且与实测硬件一致**。
>
> **与 MCOS 的交互**：MCOS 命中时消费者**不占 bank 读槽**，但**仍然"读了源操作数"**（从槽取）→ **WAR 计数器照常在该拍递增/递减**（命中路径的"读完成时刻" = `issue` 拍，而非 `issue+2`）→ 需在实现时区分"RF 读完成"与"槽读完成"两个递减时机（**实现期注意项**，见 §12 V13）。

#### 5.2 依赖处理机制对比与 OSF 的选择（**v0.5 新增：覆盖 RAW / WAR / WAW / 内存 / 控制五类依赖**）

> **📄 完整架构方案见 [`35-sm-dependence-management-architecture.md`](./35-sm-dependence-management-architecture.md)**（五类依赖的判据 / 状态 / 时序 / 编译器与硬件责任划分 / 控制位预算 / CppTLM 落地映射）。
> **本节是"对比与选择"的摘要**；规范条款以 35 号文档为准。
##### 5.2.1 三家做法（实测 + 文档）

| 依赖类型 | **NVIDIA Volta+（实测）** | **AMD GCN/RDNA/CDNA（文档）** | **学术口径（GPGPU-Sim / Accel-Sim）** |
|---------|----------------------|------------------------------|--------------------------------------|
| **RAW（定长 ALU）** | **编译器静态调度**：Stall counter（4 bit，0–15），值 = 生产者延迟 − 中间指令数，每拍递减。**硬件完全不检查 RAW**：「the hardware does not check for RAW hazards, and simply relies on these compiler-set counters」 | **无需软件介入**：「AMD does not need software or compiler intervention to avoid data hazards with ALU instructions」；RDNA 3/3.5 另加 `DELAY_ALU` 缓解依赖停顿 | 硬件 scoreboard：`checkCollision` 查 RAW/WAW |
| **RAW（可变延迟：内存 / SFU）** | **Dependence counters**：每 warp **6 个 SB**（6 bit，上限 63）；每指令 **2 个 3-bit 计数字段 + 6-bit 等待 mask**；`DEPBAR.LE SBx, n` | `s_waitcnt` + 每 wavefront **3–4 个**计数器（vmcnt / vscnt / lgkmcnt / expcnt）；**普通指令不能靠控制位等计数器**，必须显式 `s_waitcnt` → 指令数增加、解码开销降低、并发依赖链更少 | scoreboard + 内存队列 |
| **WAR** | **显式追踪**：同一组 SB 中的**另一个计数器在读完源操作数时递减**（而非写回时）。原因：「even though issue is in-order, the read-write of operands may occur out-of-order due to variable-latency instructions」 | ALU 侧靠硬件顺序保证；**VMEM 侧用 `VM_VSRC` 计数器**（等"内存指令已读完 VGPR 源"即可放行后续写） | 第二块 scoreboard（in-flight consumer 计数） |
| **WAW** | 与 RAW **共用**"写回时递减"的计数器 | 靠顺序发射 + 早释放计数器 | 与 RAW 同一块 scoreboard |
| **内存依赖** | SB0–SB5 + `DEPBAR`（**注意：`vmcnt` 是 AMD/PTX 词汇，不是 NVIDIA SASS 词汇**） | `s_waitcnt` + `MEM_ORDERED` 位 | L1/SMEM/全局队列 |
| **内存可见 WAR**（unbuffered store 的源寄存器） | **Read dependency barrier**（Volta，3 bit 索引）：store 期间其源寄存器不得被改写 | `VM_VSRC` | 未建模 |
| **控制流 / barrier** | B registers + wait barrier mask（6 bit） | `s_barrier` | — |
| **跨 warp 切换** | `Yield=0` → 换 warp，**+1 cycle** 且 reuse flags 失效 | 「single-cycle context switching between warps with **zero overhead**」 | — |

##### 5.2.2 硬件 scoreboard 的代价（NVIDIA 论文 §7.5 实测）——**为什么 OSF 不建 scoreboard**

| 方案 | 面积 | 性能 | 精度 |
|------|------|------|------|
| **软件-硬件协同**（Stall counter + Dependence counters） | **41 bit/warp = 0.09% RF** | 基准 | **MAPE 13.98%** |
| **硬件 scoreboard**（两块：WAW/RAW + WAR） | 332 entries/warp（255 regular + 63 uniform + 7 predicate + 7 uniform predicate）、63 consumers/entry → 2324 bit/warp → 全 SM **111,552 bit = 5.32% RF** | **0.97×（更慢）** | MAPE **14.87%** |

⇒ **面积 59×、性能略差、精度略差** ⇒ **不建 scoreboard**（与 SYNTHESIS C2「数据冒险与端口争用必须分层」一致，也与本文档 §8.1「`HazardTracker` 保持不变（数据冒险与端口争用分层）」一致）。

##### 5.2.3 OSF 的最终选择

| 依赖 | **OSF 处置** | 与谁对齐 |
|------|------------|---------|
| RAW（定长 ALU） | **编译器 Stall counter**（编译期已知延迟）——**不建硬件 scoreboard** | NVIDIA |
| RAW（可变延迟） | Dependence counter（SB）/ `s_waitcnt` | NVIDIA / AMD |
| **WAR** | **per-warp WAR 计数器，读源时释放**（C-5） | **NVIDIA**（v0.5 改） |
| WAW | 与 RAW 共用"写回时释放"计数器 | NVIDIA |
| 内存依赖 | SB + `DEPBAR`（NVIDIA 侧）/ `s_waitcnt`（CDNA 侧）；CppTLM 已有 `kHardwareCounter`（vmcnt/lgkmcnt/expcnt） | 两者 |
| 内存可见 WAR | Read dependency barrier（store 的源寄存器在 store 完成前不得被改写） | NVIDIA（Volta） |
| 控制流 / barrier | 现有 B registers + barrier mask | NVIDIA |
| **端口争用 / bank 冲突** | **与数据冒险分层**：由 Allocate 级端口预约处理（§3 表"Allocate 保留"） | NVIDIA |

> **CppTLM 落地影响**（§8.2 P1/P2 需增补）：
> - `HazardTracker`（`include/tlm/gpu/sm/hazard_tracker.hh`）目前**只有 RAW（`kVirtualReg`）+ vmcnt（`kHardwareCounter`）**，**无 WAR / WAW** → 需新增 **WAR 计数器**（读源时释放）。
> - `WritebackUnit::enqueue()` 当前**全仓无调用点** ⇒ "按延迟占用 → 写回"这条时序链尚未生效；C-5 要求写回端**等待 WAR 计数器归零**⇒ 必须先把写回时序真正建模起来。
> - `LatencyClass` 目前是单一粗粒度枚举（`kFixed1Cycle/kFixed4Cycle/…`）⇒ 需能表达「**读窗 3 拍**」与「**FU 占用 `d`**」两个独立维度（§4.4.1b）。

---

## 6. 定量目标与预期收益

> ⚠ **以下为设计目标值，非实测**。所有基线取自 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) 引用的实测数据。

| 指标 | NVIDIA Ampere 基线 | OSF 目标 | 依据 |
|------|-------------------|---------|------|
| **IPC（连续 3 源序列，如 FFMA）** | **0.667**（warp-inst/cycle/sub-core） | **1.000**（**+50%**） | MCOS（`r`: 3→2）；§4.1.4b / §4.1.4c + 附录 §3 |
| **IPC（连续 2 源序列，如 FADD）** | **1.000** | 1.000（**+0%**，已触发射宽度上限） | §4.1.4b 结论 2 |
| RF 读次数（GEMM 内层，N 消费者） | N | **1** | MCOS |
| 读端口利用率（3 源指令密集，均衡分配） | 100%（已饱和） | **100%（不变）** | 瓶颈是读带宽，ERW 不增端口 |
| 读端口利用率（2 源指令密集） | 100%（已饱和） | **100%（不变）** | **v0.4 修正**：v0.3 的"2/3 ≈ 67% → 95%+"基于"窗口独占"错误前提（§4.2.1），**不可达** |
| RF 读带宽（窄值 kernel） | 1× | **0.25–0.5×**（**位宽**，非读次数） | WABR |
| 槽面积成本 | — | **≈ 0.023% RF 面积**（`producer_pc` 省略则 0.006%；含 `demand_miss` 仍 < 0.05%） | MCOS 增量位估算 |
| **WAR 依赖计数器成本** | — | **≈ 0.037% RF 面积**（12 bit/warp × 64 warp） | C-5；§5.2.2 对比硬件 scoreboard 的 5.32% |
| 冲突气泡（3 源同 bank 场景） | 2 拍/指令 | **0–1 拍/指令** | ERW（提前收集跨过 issue 边界） |
| 依赖链延迟 | 4 cycle | **4 cycle（不变）** | **明确不在范围内**（§4.4.1b：`d = 1`） |
| Execute 时机契约 | 编译期已知 | **编译期已知（不变）** | §5 |

#### 6.1 IPC 目标的**前提与达成条件**（v0.5：`W` 已裁决，不再是条件式）

> ✅ **`W = 2` 已裁决**（§3.1，开放项 O-1 关闭）。故上表 IPC 目标为**定值**，但**附带达成条件**（§4.1.4c）：

| `W` 口径 | 3 源序列基线 IPC | 3 源序列 MCOS 后 IPC | MCOS 的 IPC 收益 | 2 源序列 IPC | 状态 |
|---------|--------------|------------------|------------------|------------|------|
| **2**（**采纳**） | **0.667** | **1.000** | **+50%** | 1.000 | ✅ **v0.5 裁决** |
| 3 | 1.000 | 1.000 | 0% | 1.000 | ❌ 不采纳（需第 3 组 1024-bit 读写口，§10 已否决） |

> **三条并附条件的结论**：
> 1. **IPC = 1.000 的达成条件**（**不是自动达成**）：每条 3 源指令 ≥1 个操作数由 MCOS 供给（编译器复用意识 + `budget_hint` 正确）+ 剩余 2 源跨 bank（§4.1.4c）。**无复用机会的负载恒停在 0.667**（R14）。
> 2. **OSF 的适用边界 = 3 源密集负载**（FFMA / GEMM / 矩阵类）。2 源密集负载已同时打满发射宽度与读端口 → **全部机制在 IPC 维度收益为 0**。
> 3. **弹性折扣**：上游实测 CORF/CORF++ 的"读 −10%/−23% → IPC +4%/+9%"给出弹性 **≈ 0.4**。**实际目标应取模型值（弹性 1.0）与实测弹性（0.4）之间**，不应按线性外推承诺 +50%。

---

## 7. 与 NVIDIA / 学术先例的 Novelty 对照

> **新颖度口径声明**（v0.2 补，critic SHOULD_FIX 1）：下表"新颖度"一律**相对于「NVIDIA Ampere 实测的 read-once RFC」口径**评估。**若改用「US8639882B2 专利的 write-invalidate + 多指令并发缓存」口径，MCOS 的"多消费者"本身已是既有能力**（该专利摘要逐字：`operands may be cached and reused in subsequent instructions … allowing operands for two or more instructions to be cached concurrently`；权项 7 要求容量容纳两条已译码指令；权项 1 **未限定** storage element 数量与命中条件 → 容量/复用语义属**可调工程参数**）。
>
> **因此 OSF 相对该专利的真实增量是三件事**：① **有界计数**（`budget` 计数器，专利的 cache table 只有 valid/invalidate 两态）；② **编译器 hint 编码**（2 bit `budget_hint`，把复用次数纳入指令语义）；③ **硬件自适应预算分配**（FILL 时按持续需求信号分配，受 R-G1 门控）。这三件**都不在**该专利的权项范围内。

| 机制 | NVIDIA 现状 | 学术 / 专利先例 | **OSF 的差异** | 新颖度（相对 Ampere read-once 口径） |
|------|-------------|---------------|--------------|-------|
| 操作数收集 | Tesla–Kepler 有，Volta+ 无 | CORF/Accel-Sim 假设有（**已被实测否定**） | 延续 Ampere 口径（无 OC），不复活 OC | 低（跟随） |
| bank 仲裁 | Allocate 预约 | wavefront 仲裁（GPGPU-Sim） | 延续 | 低 |
| **复用缓存（多消费者）** | `.reuse` 1-bit，**read-once + 消费者可 re-arm**（Ampere 实测：消费者重置 `.reuse` 即重新武装槽，Listing 2 Ex.1 vs Ex.2） | **US8639882B2**：write-invalidate + **多指令并发缓存**（多消费者已是既有能力）；CORF：无复用缓存 | **有界计数 `budget`** + **编译器 `budget_hint`** + **硬件自适应预算分配**（FILL 时，相对专利口径的增量）；**代价**：不可表达"消费者各自 re-arm"（§4.1.2 推论） | **中高**（相对 Ampere read-once 口径）／**低**（相对专利 write-invalidate 口径） |
| 寄存器合并 | 无 | CORF（写端打包 + 读端合并，-23% 读） | 叠加 | 中（组合） |
| 窄读 | 无 | CORF packing 间接支持（**写端**） | **按需少读（读端粒度）** | 中 |
| 弹性窗口 | 已有（定长 3 拍窗口 + **跨指令预约共享**的端口；v0.4 修正：非"每指令独占"） | 无 | **放宽窗口的时序约束**（允许提前收集）+ 保 I2（`Execute = issue + 3` 不变） | **中**（v0.3 评为"中高"，v0.4 下调：**稳态 IPC 收益为 0**，价值在气泡削减） |
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
4. **（v0.4 新增）读带宽供给 `W` 口径不做单方面假设**：本文档同时持有三个互斥口径（§3.1），**不擅自选定**——因为 §6 的 IPC 目标随 `W` 翻转。**实施前必须裁决**（O-1 / V9）；在此之前，所有 IPC 数字均标注其口径。

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

> ⚠ **`W` 的口径说明（v0.4，开放项 O-1）**：`W = bank_count × read_ports_per_bank` = **每 sub-core 每周期可供给的 warp 寄存器读数**（§3.1）。上表默认值给出 **`W = 2`**，但该值**与 Ampere 的 1 warp-FFMA/cycle/sub-core 峰值不自洽**（该峰值需 3 读/cycle）→ **实施前必须裁决 V9**，并同步修订本 config 的默认值。
>
> **本仓建模建议**：把 `W` 作为**显式建模参数**（`read_ports_per_bank` 可配到 2），使 TLM 能在 `W=2` 与 `W=3` 两种口径间切换做**敏感性对照**——这比先赌一个口径更稳妥，也直接支撑 §6.1 的条件式目标。

#### 8.3.1 三种"失效/生命周期"语义的区分（**v0.2 澄清，critic SHOULD_FIX 5**）

v0.1 用一个 `invalidation: read_once | on_write` 键混装了**两个正交的概念**，导致实现方无法判断该键的语义。v0.2 拆清：

| 概念 | 性质 | 是否可配置 | 取值 | 归属 |
|------|------|------------|------|------|
| **写回即失效**（write-invalidate） | **正确性前提**（C-3） | ❌ **不可关闭** | 恒为 on | 槽的 `valid` 在 RF 写入时必须清零 |
| **读一次即失效**（read-once） | **生命周期/驻留策略** | ✅ 可配置 | `eviction: read_once`（= `budget_max = 1`，Ampere 实测口径，默认） | 槽交付一次后即 DEAD |
| **多消费者预算**（budgeted） | **生命周期/驻留策略** | ✅ 可配置 | `eviction: budgeted` + `multi_consumer: true`（P3，OSF 口径） | 槽交付 `budget` 次后 DEAD |

**实现契约**：

- `write-invalidate` **始终生效**，与 `eviction` 取值**正交**——它保证"槽值 == RF 当前值"（§4.1.2 证明第 3 条），**任何 `eviction` 取值下都不可省略**；
- `eviction: read_once` ⇒ `budget_max = 1` ⇒ **R-G1 旁路自适应通道**（`demand_miss` 不维护）⇒ FILL 恒分配 budget=1 ⇒ MCOS 退化为 **read-once 生命周期**（§4.1.2 推论的**限定形式**：非"逐拍等价"——Ampere 的"任意读即失效"与"消费者 `.reuse` re-arm"两条语义未复现，见 R11）；
- `eviction: budgeted` + `multi_consumer: true` ⇒ 允许 `budget_max > 1`（由编译器 `budget_hint` 决定上界）⇒ R-G1 开放自适应预算通道；
- `multi_consumer: false` 时 **`budget_max` 恒为 1**，且自适应预算通道**静态旁路**（R-G3，`demand_miss` 不维护）。

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
| R1 | **MCOS 槽驻留变长 → 跨 warp 替换变频繁**，在"每 warp 读不同寄存器"的工作负载下反而更差 | 性能回退 | `budget_max` 硬上限（R-G2）+ `demand_miss ≥ 3` 才自适应 + **R-G3 显式 opt-in（默认关）**。**"最坏 = 不变差"仅在 `eviction: read_once`（默认）下成立**；`budgeted` 模式下**可能变差**，这是该模式的已知代价 |
| R1b | **驻留变长会放大跨 warp 切换的惩罚** | 性能回退 | Volta 论文 §2.1 实测：切 warp → 所有 reuse flags 失效，**+1 cycle**。`budgeted` 模式下驻留期内的 warp 切换次数上升 → 该惩罚被放大 → **`budget_max` 上限需按实测调参**（列入 §9 开放问题 3 的一部分） |
| R2 | **ERW 遇分支需 flush slot buffer** | 分支密集 kernel 受损 | 显式开关 + 按 kernel 画像启用；flush 气泡可计入预算。**且 v0.2 已明确**：ERW 收益依赖"同 warp 连续发射"，跨 warp 交错（round-robin / CGGTY）下收益大幅缩水 → 需与编译器 warp 内排序协同 |
| R3 | **WABR 宽度提示与实际不符 → 读错数据** | **正确性事故** | **tag 为权威、提示仅为上界**；写回时记录实际宽度 |
| R3b | **WABR 前提不成立时零收益**（窄值已被符号扩展到 32 bit 容器） | 收益落空 | 编译期统计窄值占比；占比过低则不启用该机制 |
| R4 | **SOP 预测错误** | 性能回退 | tag 校验 + fallback；**永不提交未校验值** |
| R5 | **OSF 全部机制都无法改善依赖链延迟（P1）** | 期望落空 | §4.4 已明确声明；本提案的价值定位在**带宽 / 冲突 / 复用**，不是延迟 |
| R6 | **"多消费者"在真实编译器里难以静态给出 budget** | MCOS 收益打折 | 硬件自适应通道兜底；且 GEMM 等主流 kernel 的消费关系是静态的 |
| R7 | **与未来 NVIDIA 实际实现脱节** | 调研价值衰减 | 本提案是**建模参考**，不是"预测 NVIDIA 未来"的赌注；CppTLM 的价值在**口径正确**而非"押中未来" |
| R8 | **沉默的语义漂移**：`budget` 自适应若实现不当，可能让**已被改写的寄存器**的值被错误领取 | **正确性事故** | **写回即失效（C-3）是硬前提，不可关闭、不可配置**（与 `eviction` 正交，见 §8.3.1）；另需在实现期补一张真值表核对（critic 验证建议） |
| R9 | **"退化为现状"推论被误读** | 实施方按错误前提实现 | 推论的前提已显式化：`budget_max = 1` **且** R-G1 静态旁路自适应 **且** `multi_consumer = false`（默认）；三条缺一则**不成立**（§4.1.2 推论 + §4.1.3b 门控表）。**v0.4 追加**：推论本身已降级为"read-once 生命周期的子语义等价"，**不再是"逐拍等价"**（R11） |
| **R10** | ~~读带宽供给 `W` 口径未裁决~~ | — | ✅ **v0.5 关闭**：裁决 `W = 2`（§3.1.1 三条论据：面积 / RFC 存在性 / 峰值可达性分析）。`W=3` 不采纳（需第 3 组 1024-bit 读写口，§10 已否决） |
| **R11** | **显式偏离 Ampere 两条实测语义**（§4.1.2 推论对照表）：① "任意读请求打到同 `(bank, op_pos)` 即失效（无论命中与否）" OSF **未实现**；② "消费者重置 `.reuse` 即 re-arm" OSF **不可表达** | ① 只会**多命中**（更保守，不会错值）但与现状**行为不一致**；② 消费者数 N 运行时才确定时**无法复用** | ① 作为**有意的偏离**登记（保留槽更久 = 语义安全方向）；② 由 `budget_hint` 承载，**hint 少给→miss、多给→驻留变久**（均只是性能问题，见 §4.1.5 护栏）。**必须在实现期做行为差分测试**（§12 V11） |
| **R12** | **自适应预算是极限环而非稳态**（§4.1.3c 收敛性）：`budget` 在 1 ↔ `budget_max` 之间周期振荡 | 性能：平均 budget 介于两者之间，**低于**理论上限；不影响正确性 | 显式登记，避免实现方按"第 4 次进入稳态"实现；如需真稳态需加迟滞状态（额外面积）→ §12 V7 调参时一并评估 |
| **R13** | **WAR 语义需依赖计数器**（§5.1 C-5，v0.5 改）：per-warp WAR 计数器，**读源时释放**〔**仅 NV 建模后端**〕 | 面积 ≈ **0.037% RF**（12 bit/warp × 64 warp）；**写者可能被读者阻塞**（与 NVIDIA 实测同构） | 与 §4.1.6 的槽面积成本**分开记账**；写回端需实现"等 WAR 计数器归零"（依赖 §12 V13 的写回时序建模） |
| **R14** | **`W = 2` 下 IPC = 1.000 不是自动达成**（§4.1.4c）：必须有复用机会 + `budget_hint` 正确 + 剩余源跨 bank | **无复用机会的负载恒停在 IPC 0.667**（如寄存器压力极大的标量代码） | 硬件无法弥补——**编译器是唯一能创造复用机会的主体**（I3）。故 MCOS 的 `budget_hint` 与编译器寄存器分配必须协同设计；§8.2 P3 的 profiling 须专门统计"3 源指令的复用命中率" |

### 开放问题（需评审裁决）

1. **`producer_pc` 是否必要**？占 16 bit × 6 槽 × 4 sub-core ≈ 384 bit/SM。省略可把槽面积成本从 **0.023% 降到 0.006%**。**建议省略**（调试可用独立 trace 机制）。
2. **MCOS 与 NVIDIA `.reuse` 的关系**：是把 `.reuse` 升级为 2-bit `budget_hint`，还是**新增独立字段**？后者会撞 128 字节上限（余量 0；可回收 8B padding，但属跨仓契约变更）→ **建议升级复用现有位**。
3. **ERW 是否值得做 + `budget_max` 上限取值**：ERW 收益依赖"同 warp 连续发射"（跨 warp 交错下大幅缩水，见 §4.2.4），需先有基线 profiling 才能判断；`budget_max` 的上限（4 / 16）也需按 R1b 的实测调参 → **建议 P3 阶段先做 profiling 再决策**。**v0.4 追加**：ERW 的**稳态 IPC 收益为 0**（§4.2.3），其价值只剩**气泡削减** → profiling 应专门测"bank 偏斜场景的气泡数"。
4. **`eviction` 默认值**：`read_once`（= 实测口径，默认，已在 §8.3 定为 `read_once`）vs `budgeted`（= OSF 口径）。**建议默认 `read_once`**（对齐真实硬件，且保证"退化为 read-once 生命周期"成立）；`budgeted` 作 opt-in 对照模式。
5. **`multi_consumer` 的门控粒度**：是全局 config 开关（本提案 v0.3 的做法），还是**按编译器的 `budget_hint` 逐指令生效**（`hint ≥ 2` 即自动允许，无需全局开关）？后者更细粒度但实现更复杂 → **待裁决**。
6. **`demand_miss` 是否需要区分寄存器**？v0.4 的信号统计"该 op_pos 上**取数失败**的次数"，**不区分是不是同一个寄存器**（区分需额外存 `last_tag`，18 bit × 3 op_pos × 64 warp ≈ 3.4 Kbit/SM）。不加 `last_tag` 时信号会偏乐观（安全但可能浪费槽位）；加则更准但面积上升 → **待裁决**。

---

### v0.4 新增开放项（IPC / 时序专项）

7. ~~**【O-1】读带宽供给 `W` 的口径**~~ → ✅ **v0.5 关闭：裁决 `W = 2`**（§3.1.1）。三条论据：① 面积（第 3 组 1024-bit 读写口极贵，CORF §1）；② **RFC 的存在性证据**（RFC 关掉 → CUTLASS sgemm 0.79×、35.9% 静态指令走 RFC、Ampere §7.4 端口敏感性差 44% ⇒ 读带宽就是紧约束）；③ **峰值可达性分析**（`W=2` + 复用 ⇒ 峰值可达；"不自洽"的提法作废）。
8. ~~**【O-2】ALU 流水线深度 `d`**~~ → ✅ **v0.5 关闭：`d = 1`**（§4.4.1b）。依据：Ampere FU 为**全 warp 宽 → 1 拍占用**（论文 §5.1.1 原文）；定长指令依赖延迟**实测 4**（论文 §4，且经 Stall counter 语义验证）；读窗 **3**（§5.3）。**"5/6/7" 是 6 条指令序列的 elapsed（Listing 1），不是 issue→result 延迟** ⇒ 上游 SYNTHESIS 与两处 overview 的表述系误读，**已回写标注**。
9. ~~**【O-3】WAR 语义的成本取舍**~~ → ✅ **v0.5 关闭：采用 NVIDIA 的 per-warp WAR 依赖计数器（读源时释放）**（§5.1 C-5 / §5.2）。面积从 v0.4 方案的 ~1.2% RF 降到 **~0.037% RF**（30×），且与真实硬件一致；不建硬件 scoreboard（其代价：5.32% RF 面积、更慢、精度略差，§5.2.2）。

---

## 10. 被否决的备选方案

| 方案 | 否决理由 |
|------|---------|
| **加 RF 读端口（2/bank）** | **面积代价极高**（CORF §1：「the cost of a port is extremely high when considering the width of a warp register」——warp 寄存器 1024 bit 宽）；且与真实 NVIDIA 口径脱节（实测就是 1 读口）。⚠ **不作为依据的**：Table 6 的 APE 恶化（那是建模精度指标，含义是"该学术模型刻画不了多端口"；且 2 读口在性能上 MaxFlops 1.44×、Cutlass 1.11×，与 Ideal 行同值）。**v0.4 追加**：开放项 O-1（`W` 口径）的裁决**不应**通过本行达成——`W` 只能被"认定"或被"建模为参数"，不能靠加端口硬凑 |
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
| `d` | **ALU 流水线深度**（本提案取 1；开放项 O-2 待裁决） |
| `dispatch(i)` | 调度器把指令 i 送上分配级的那一拍 |
| **`issue(i)`** | **指令 i 离开 Allocate、端口预约成功的那一拍**（本文档一切时序公式的坐标原点，§5.0） |
| **`W`** | **每 sub-core 每周期可供给的 warp 寄存器读数** = bank 数 × 每 bank 读口数（§3.1，开放项 O-1） |
| `r` | 每条指令实际需要的 RF 读数 = 源操作数 − 被 MCOS 命中的数 |
| `max_b` | 一条指令的源操作数中落在**同一 bank** 的最大个数（= 气泡 + 1） |
| `max_b_avg` | 跨指令平均后单 bank 的最大槽位负载 |
| **`IPC`** | 每周期成功分配的 warp 指令数；稳态上界 `min(I_issue, W/r, 1/max_b_avg)`（§4.1.4b） |
| `demand_miss` | per-(warp, op_pos) 的**取数失败计数**（2 bit），自适应预算的输入信号（§4.1.3c，v0.4 由 `demand_streak` 重定义） |
| `ERW` | Elastic Read Window，弹性读窗口 + 提前收集 |
| `MCOS` | Multi-Consumer Operand Slot，多消费者操作数槽 |
| `WABR` | Width-Adaptive Bank Read，宽度自适应 bank 读 |
| `SOP` | Speculative Operand Provisioning，推测供给 |
| `CVF` | （显式化）值前递 |
| `I1/I2/I3` | 三条不变式（见 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §3） |
| `P1–P4` | 四条遗留问题（见 [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §4） |
| `C-1 ~ C-4` | MCOS 槽状态机规范条款（§4.1.1b） |
| `R-G1 ~ R-G3` | MCOS 门控规则（§4.1.3b） |
| `O-1 ~ O-3` | v0.4 新增开放项（§9 开放问题 7–9：读带宽口径 / ALU 深度 / WAR 成本） |

## 附录 B：关键证据索引

| 主张 | 证据 |
|------|------|
| 现代 NVIDIA 无 OC | arXiv:2503.20481 §5.3 原文 |
| 定长 3 周期窗口 + 2 源指令空转 | 同上 §5.3 |
| **气泡 = `max_b − 1`**（跨 bank 无气泡 / FMUL 同 bank 1 拍 / FFMA 三源同 bank 2 拍）→ **稳态 IPC = `1/max_b`** | 同上 §5.3（IP C 模型的**自洽性验证**，见配套附录 §3.2） |
| **读带宽口径 `W = 2`**（2 bank × 1 读口/sub-core） | 同上 §5.3 + §7.4（RFC 关掉 → CUTLASS sgemm 0.79×；35.9% 静态指令走 RFC；端口敏感性 MaxFlops 差 44%）→ **v0.5 裁决 `W = 2`**（§3.1.1） |
| **定长指令依赖延迟 = 4**（实测 + Stall counter 语义验证） | arXiv:2503.20481 §4：「an addition whose latency is four cycles … encodes a four in the Stall counter」；「the hardware does not check for RAW hazards」 |
| **「5/6/7」= 6 条指令序列的 elapsed，不是 issue→result 延迟** | arXiv:2503.20481 §3 + Listing 1 原文：「five cycles (**the minimum since each sub-core can issue one instruction per cycle**)」；「**two consecutive instructions can have from 0 to 2 cycles of bubbles in between**」 |
| **FU 占用 = 1 cycle（全 warp 宽）/ 2 cycles（半 warp 宽）** | arXiv:2503.20481 §5.1.1：「This latch is occupied for two cycles if the width of the execution unit is just half warp, and for **one cycle if its width is a full warp**」 |
| **WAR 用「读源时释放」的依赖计数器** | arXiv:2503.20481 §4：「the counter is decreased **after the instruction reads its source operands**」；「Clearing WAR dependencies after reading the source operands is an important optimization … may happen hundreds of cycles later」 |
| **控制位 vs scoreboard 的成本**（41 bit/warp = 0.09% RF vs 5.32% RF；0.97× 更慢；MAPE 13.98% vs 14.87%） | arXiv:2503.20481 §7.5 |
| **SASS 固定延迟分档**（Volta: FFMA 4 / IMAD 5 / half 6 / FP64 8 / POPC 10 / MUFU 14；Pascal: 6/8/12/14） | arXiv:1804.06826 Table 4.1（实测） |
| **AMD 不需软件介入处理 ALU 数据冒险；RDNA3/3.5 加 DELAY_ALU；内存依赖用 waitcnt** | arXiv:2503.20481 §4（引 AMD ISA 文档） |
| **AMD MFMA 延迟随 shape/dtype 变**（16×16×16 FP16 = 32 cycle；32×32×8 = 64） | ISPASS 2024, *Characterizing AMD Matrix Cores*（MI250X 实测） |
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
| **读→IPC 弹性 ≈ 0.4**（CORF：读 −10% → IPC +4%；CORF++：读 −23% → IPC +9%） | ASPLOS'19 CORF Table 1（**用于给 §6 的 IPC 目标打折**，§4.1.4b） |
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
| **v0.4** | 2026-10-28 | **IPC / 时序专项复审**（build agent 自主复审，非 critic 档） | **4 个 BLOCKER 修正 + 6 个 SHOULD_FIX + 4 个 NIT**；**未发起第 3 轮 critic**（评审预算 2/2 已用满） | 见 §11.4 闭合证据表；**新增配套分析附录** [`34-sm-operand-supply-ipc-timing-analysis.md`](./34-sm-operand-supply-ipc-timing-analysis.md) |
| **v0.5** | 2026-10-28 | **开放项裁决轮**（build agent，承接用户决策 + 一手原文核查） | **O-1 关闭（`W = 2`）/ O-2 关闭（`d = 1`）/ O-3 关闭（WAR 用依赖计数器）**；**更正上游「5/6/7」误读**；**v0.4 的 C-5 方案被推翻并替换** | 见 §11.5 闭合证据表 |

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

### v0.3 → v0.4 的 IPC / 时序专项复审闭合证据

> **复审性质**：**build agent 自主专项复审**（非 critic 档）。**未发起第 3 轮 critic**（评审预算 2/2 已用满，per build agent 评审预算规则）。本轮发现**全部在本版内修正或显式登记为开放项**，未留悬空缺陷。
> **配套分析文档**：[`34-sm-operand-supply-ipc-timing-analysis.md`](./34-sm-operand-supply-ipc-timing-analysis.md)（IPC 模型推导 + cycle 坐标时序图 + 敏感性分析 + 可复算脚本）。

| # | 级别 | 问题 | v0.4 闭合位置 |
|---|------|------|-------------|
| **B1** | BLOCKER | **"budget_max=1 精确退化为 NVIDIA 现状（逐拍等价）"不成立**——Ampere 的两条实测语义被丢弃：①"任意读请求到达同 `(bank, op_pos)` 即失效（无论是否命中）"；②"消费者重置 `.reuse` 即 re-arm"（P3 的真正机制） | **§4.1.2 推论降级**为"**read-once 生命周期的子语义等价**"，删"逐拍等价"；**新增两行对照表**（逐条列出行为差异）+ **能力替换分析**（收益：复用决策从"每消费者 1 bit"压缩为"每生产者 2 bit `budget_hint`"；代价：hint 必须精确）；**§8.3.1 / §9 R9 / §7 表格**同步；**§9 新增 R11** 登记两条显式偏离 |
| **B2** | BLOCKER | **`demand_streak` 自适应通道是死代码**：① 定义（消费者取数失败）≠ 实现（FILL 计数）；② C-3 的"先 INVALIDATE 后 FILL" + INVALIDATE 清零 ⇒ **FILL 必然读到 0** ⇒ `budget` 恒为 1；③ 且这恰好发生在目标负载（生产者反复写同一寄存器，如 GEMM） | **§4.1.3c 信号重定义**：`demand_streak` → **`demand_miss`**（计"消费者取数失败"；命中衰减 / 未命中递增；**FILL 与 INVALIDATE 均不改它**）；**伪代码三段重写**；**收敛性改述**为**受控极限环**（v0.3 的"第 4 次进入稳态"不成立）→ **§9 新增 R12**；§4.1.3a 差异表**扩为 v0.1–v0.4 四列** |
| **B3** | BLOCKER | **缺 IPC 目标**：§6 无 IPC 行；"读↓"从未换算成 IPC → 设计目标不可验收 | **新增 §4.1.4b**（IPC 上界公式 + 3 源/2 源对比表 + 三条结论）；**§6 新增 IPC 两行 + §6.1 条件性小节**（`W` 敏感性 + 适用边界 + 弹性折扣）；**§0 TL;DR 新增 IPC 结论块** |
| **B4** | BLOCKER | **读带宽供给 `W` 未钉死**：三个互斥口径（硬件表 `W=2` / v0.3 ERW 图 `W=1` / 峰值反推 `W≥3`）；ERW 收益建立在"窗口独占"前提上，与本文档硬件口径 + 实测气泡数据不自洽 | **新增 §3.1**（`W` 显式定义 + 三口径表 + 不自洽论证）；**§4.2.1 前提重写**（端口是"跨指令预约共享"非独占，附实测证据）；**§4.2.2 图重画**（按 bank 分列）；**§4.2.3 收益表重写**（"33% 浪费"删除，改为"稳态已 100% 饱和，ERW 的 IPC 收益 = 0，价值在气泡削减"）；**§6 / §9 R10 / 开放项 O-1** 同步 |
| **S1** | SHOULD_FIX | §4.2.2 的 ERW 图自相矛盾：单宽流水同拍出 2 值（`i 的第3源` 与 `i+1 的第1源` 同在 t2）；隐含 `W=1` 与硬件口径冲突，按图实现会**减半**读带宽 | **删除 v0.3 图**，替换为按 bank 分列的槽位占用图（§4.2.2） |
| **S2** | SHOULD_FIX | `INVALIDATE` 伪代码缺 bank 维度（`slot[op_pos]` 无 bank 索引）→ 6 槽中清哪 3 个无定义 | **§4.1.3c 伪代码补 `bank = bank_of(reg)`**（`bank(reg) = reg_index % N`，SYNTHESIS C3 硬件口径）+ 明确遍历该 bank 的 3 个 op_pos |
| **S3** | SHOULD_FIX | "issue" 一词双义（调度发射 vs 离开 Allocate）→ 时序坐标原点不确定 | **新增 §5.0 术语与坐标定义表**（`dispatch(i)` / `issue(i)` / `L` / `d` / 各事件拍位）；**明确"气泡推迟的是后续指令的 `dispatch`"** |
| **S4** | SHOULD_FIX | WAR/读写同拍取值顺序未定义（消费者的 3 拍读窗口可能跨越生产者的写回拍） | **新增 §5.1**（规范条款 **C-5 读在 `issue` 拍锁存** / **C-6 MCOS 命中优先** / **C-7 写回不阻塞在飞读**）+ 面积代价（≈1.2% RF 面积）+ 替代方案 → **§9 开放问题 O-3 / R13** | **⚠ v0.5 已改：§5.1 C-5 改为「per-warp WAR 依赖计数器（读源时释放）」，面积 ≈1.2% → ≈0.037% RF（见 §11.5）**
| **S5** | SHOULD_FIX | 门控表 `budget_hint=0` 行标"等价于 NVIDIA 现状 = 是"——hint=0 是**完全关闭复用**，比现状更保守 | **§4.1.3b 门控表修正**（该行改为"否（比现状更保守）"；`hint=1` 行加"仅在子语义下"限定） |
| **S6** | SHOULD_FIX | **ALU 流水线深度未给出** → P1 的 4-cycle 依赖延迟与 SYNTHESIS 的 5/6/7 cycle 无法调和 | **新增 §4.4.1b**（`d = 1` 显式化 + 推导链 + 与上游 1 拍差的显式登记 → **开放项 O-2**） |
| **N1** | NIT | 同一浪费量 **25%（§0 ERW 行）vs 33%（§4.2.3）** 不一致；且两者口径均不成立 | §0 ERW 行改为"第三拍空转（读窗口占用率 2/3）"；§4.2.3 删除"33% 读带宽浪费"表述；§1 P2 行重写 |
| **N2** | NIT | §4.1.4 "MCOS（自适应）\| 1 + (自适应增长)" 不是可验收数字 | §4.1.4 表格改为"**1 次**（`budget` 在 1 ↔ N 间振荡，见 §4.1.3c）" |
| **N3** | NIT | 悬空引用：根 `AGENTS.md`、`docs/architecture/README.md:17-21`（本仓两文件均不存在） | 头部改指 `docs/architecture/INDEX.md` + `docs/research/AGENTS.md`（两者均存在） |
| **N4** | NIT | §4.1.6 面积账未显式列 tag 的 18 bit | **§4.1.6 补依据说明**：Ampere RFC 条目已必须存 `warp_id + reg_id`（命中条件逐位比较），`op_pos` 由索引隐含 → **tag 是存量结构、非增量**；净增 = `width+producer_pc+budget−valid` |
| **V2** | — | `sizeof(InstrDescriptor)` 是否真 == 128 | ✅ **已闭合**（2026-10-28 编译实测：`sizeof = 128`、`reserved_hdr@4`、`reserved_mem@100`、各 4B → 8B padding 确认、`CtrlBits = 4 B` → `reuse_mask(3b)+budget_hint(2b)+width_hint(2b)` 共 7 bit **塞得下**） |

### v0.4 → v0.5 的开放项裁决闭合证据

> **裁决轮性质**：用户给出决策倾向（`W = 2`）+ 要求补充调研（ALU 深度、依赖处理），build agent 完成**一手原文核查**后裁决并回写。**未发起第 3 轮 critic**（评审预算 2/2 已用满）。

| # | 开放项 | 裁决 | 论据（均为一手来源） | 回写位置 |
|---|--------|------|-------------------|---------|
| **O-1** | 读带宽供给 `W` 的口径 | **`W = 2`** | ① **面积**：第 3 组 1024-bit 读写口极贵（CORF §1）；② **RFC 存在性证据**：RFC 关掉 → CUTLASS sgemm 0.79×、35.9% 静态指令走 RFC、Ampere §7.4 端口敏感性 MaxFlops 差 44% ⇒ 读带宽就是紧约束；③ **峰值可达性分析**：`W=2` + 复用 ⇒ 峰值可达 | §3.1 重写（新增 §3.1.1 三论据 + §3.1.2 连带结论）；§4.1.4c 新增达成条件；§6 / §6.1；§9 R10 关闭 + **R14 新增** |
| **O-2** | ALU 流水线深度 `d` | **`d = 1`** | ① Ampere FU 为**全 warp 宽 → 1 拍占用**（论文 §5.1.1 原文）；② 定长指令依赖延迟**实测 4**（§4，且经 Stall counter 语义验证）；③ 读窗 **3**（§5.3）⇒ 1+3 = 4 自洽 | §4.4.1b 重写（含 Volta/Pascal Table 4.1 延迟分档表 + 「不同指令不同长度但**非可变深度**」结论 + 合理深度 4 拍的四条论据）；§9 O-2 关闭 |
| **O-3** | WAR 语义的成本取舍 | **采用 NVIDIA 的 per-warp WAR 依赖计数器（读源时释放）** | 论文 §4 原文：「the counter is decreased **after the instruction reads its source operands**」；早释放是**实测确认的重要优化**；控制位方案 41 bit/warp = 0.09% RF vs 硬件 scoreboard 5.32% RF（§7.5） | §5.1 **重写**（C-5 从「issue 拍锁存值（≈1.2% RF）」改为「WAR 计数器（≈0.037% RF）」，C-8 新增面积条款）；**新增 §5.2**（NVIDIA / AMD / 学术口径 × RAW / WAR / WAW / 内存 / 控制五类依赖对照表 + scoreboard 代价 + OSF 最终选择）；§9 R13 改写 + O-3 关闭 |
| **上游更正** | SYNTHESIS / 两处 overview 的「issue 侧气泡：0/1/2 冲突 → **5/6/7 cycle**」 | **该表述系对来源的误读**，已回写标注 | 论文 §3 + Listing 1 原文：5/6/7 是**6 条指令序列的 elapsed**（5 = 每 sub-core 每拍发 1 条的下界；6/7 = 冲突多出 1/2 拍**气泡**），**不是**单条指令的 issue→result 延迟 | `docs/research/SM/CudaCore/SYNTHESIS.md` §1 表 + `CudaCore/overview.md` + `SM/overview.md`（三处已标注） |
| **推论** | v0.4 §4.4.1b 的「上游 5/6/7 隐含 `d = 2` ⇒ 与实测差 1 拍」 | **该推论作废**（基于同一误读） | 同上 | §4.4.1b ② 已重写为「真身」说明 |

> **连带更正**：v0.4 §5.1 的 C-5「源值在 `issue` 拍锁存」（≈1.2% RF 面积 + 「编译器是否已保证无 WAR」的待裁决）**被本轮推翻**——真实硬件用**依赖计数器**，面积低 30× 且行为已被实测确认。**这同时消除了 v0.4 的 R13 与 O-3。**

### 未采纳 / 超出 critic 范围

- critic NIT（`overview.md` §3.7 / 阅读路径把"设计提案"与解析并列）——随 B1 迁移自然消解。
- critic 未审：`sm_bundles_tlm.hh:40` 的 HSK-9 size constraint 原文未在权威 spec 中检索到（沿用"未核实"标注）。
- **v0.4 未采纳项**：**"给 OSF 加 RF 读端口以提高 `W`"** —— §10 已否决（面积论据 + 口径论据）。v0.4 的 O-1 裁决**不应**通过加端口达成，只能在"承认 `W=3` 并修订硬件表"与"`W=2` 且放弃 1 warp-FFMA/cycle 峰值"之间二选一（或由评审认定 `W` 为**建模口径参数**而非硬件断言）。

---

## 12. Backlog（评审预算用尽后转入的待验证项）

> **评审预算**: 2/2 轮已用满（per build agent 评审预算规则），**不再发起第 3 轮 critic 评审**。以下为第 2 轮 critic 提出的**验证建议**、v0.4 IPC/时序专项复审新增项、以及本文**未自行执行**的核对项，转入实施/验证阶段处理。

| # | 待验证项 | 类型 | 建议动作 | 归属 |
|---|---------|------|---------|------|
| **V1** | **MCOS 状态机真值表核对**：`budget==0` 时 hit 是否 deliver、槽置 EMPTY 的精确时机、`multi_consumer=false` 是否同时禁用自适应预算通道 | 静态核对 | ⚠️ **v0.4 前移至"文档定稿前"**——v0.4 的 B2（自适应死代码）正是本项会抓到的问题类型。实现 P2 前由 build 补一张真值表，逐条比对 §4.1.1b / §4.1.3b / §8.3.1 | build（**定稿前** + P2 实施前） |
| ~~V2~~ | ~~`sizeof(InstrDescriptor)` 是否真 == 128、余量是否真为 0~~ | 编译期实测 | ✅ **已闭合（2026-10-28）**：`sizeof = 128`、`reserved_hdr@4` / `reserved_mem@100`（各 4B → 8B padding）、`CtrlBits = 4 B` | **完成** |
| V3 | **`openspec list --json` 实测确认无 active change 涉及 SM 操作数供给** | 仓库状态 | 本文头部标"未核实"；本提案**不创建** openspec change，但实施时需另起 | build（实施时） |
| V4 | **HSK-9 的 bundle size constraint 原文** | 契约 | `sm_bundles_tlm.hh:40` 注释称"per HSK-9 spec size constraint"，但**未在权威 spec**（`docs/superpowers/specs/2027-02-09-hsk-9-icompute-api-v1-sm-rewrite.md`）中检索到该原文（标注"未核实"） | 跨仓（HSK 流程） |
| V5 | **`demand_miss` 是否需要 `last_tag` 区分寄存器** | 开放问题 6 | 加 `last_tag`（18 bit × 3 op_pos × 64 warp ≈ 3.4 Kbit/SM）可提升信号精度；不加则信号偏乐观但**安全** | 评审裁决 |
| V6 | **ERW 的基线 profiling** | 性能数据 | §9 开放问题 3：ERW 的**稳态 IPC 收益为 0**（v0.4 修正）→ profiling 应**专测"bank 偏斜场景的气泡数"**，而非"整体读带宽利用率" | P3 前 |
| V7 | **`budget_max` 上限（4 / 16）实测调参** | 性能数据 | R1b：驻留变长会放大跨 warp 切换的 +1 cycle 惩罚；**并评估 R12 的极限环是否需要加迟滞** | P3 前 |
| V8 | **WABR 窄值占比统计** | 编译期数据 | R3b：若窄值已被符号扩展到 32 bit 容器，WABR 零收益 | P3 前 |
| ~~**V9**~~ | ~~读带宽供给 `W` 的口径裁决~~（开放项 O-1 / 风险 R10） | 架构裁决 | ✅ **v0.5 已裁决 `W = 2`**（§3.1.1 三论据）；连带新增 §4.1.4c「IPC = 1.000 的达成条件」与 **R14**；`W` 改为 CppTLM 显式可配参数（§8.3） | **完成** |
| ~~**V10**~~ | ~~ALU 流水线深度 `d` 的裁决~~（开放项 O-2） | 架构裁决 | ✅ **v0.5 已裁决 `d = 1`**（§4.4.1b）；**并更正上游「5/6/7」误读**（SYNTHESIS §1 + 两处 overview 已回写标注） | **完成** |
| **V11** | **OSF 与 Ampere RFC 的行为差分测试**（风险 R11） | 验证 | 针对"任意读即失效"与"消费者 `.reuse` re-arm"两条**有意偏离**，构造差分用例（miss-then-match 序列、producer→N consumer 链），确认 OSF 只在**性能**维度偏离、**值语义**恒等 | build / verifier |
| ~~**V12**~~ | ~~WAR 定序规则的成本复核~~（开放项 O-3 / 风险 R13） | 面积 | ✅ **v0.5 已裁决：采用 per-warp WAR 依赖计数器（读源时释放）**，面积 ≈ 0.037% RF（v0.4 的值锁存方案 ≈ 1.2% RF，**降低 30×**）；**新增 §5.2 五类依赖机制对照** | **完成** |
| **V13** | **写回时序建模 + WAR 计数器落地**〔**仅 NV 建模后端**；新 ISA 后端不实现 WAR 计数器，见 40 号 S-DEP-6〕 | 实现 | CppTLM 现状：`WritebackUnit::enqueue()` **全仓无调用点** ⇒ 「按延迟占用 → 写回」尚未生效；`HazardTracker` **无 WAR / WAW**。C-5 要求写回端「等 WAR 计数器归零」⇒ 必须先把写回时序真正建模起来，并为 WAR 计数器补状态与接口 | build（P2 实施前） |
| **V14** | **3 源指令的复用命中率统计** | 编译期数据 | R14：`W = 2` 下 IPC 1.000 **依赖复用机会存在**。须统计真实 kernel 中「3 源指令至少 1 个操作数可被复用」的比例；若普遍 < 1/3，则 MCOS 的 IPC 收益假设不成立，须重新评估 | build（P3 前） |

---

*本提案基于 2026-10-27 一手调研材料（3 件 NVIDIA 专利 PDF + 3 篇论文 PDF + 本机 GPGPU-Sim 4.2.0 源码 + CppTLM 源码实测）撰写，并于 2026-10-28 完成 **v0.4 IPC / 时序专项复审**（配套分析文档：[`34-sm-operand-supply-ipc-timing-analysis.md`](./34-sm-operand-supply-ipc-timing-analysis.md)）。**非 NVIDIA 官方设计；未经验证；未经 Oracle/ADR 评审**。所有引号内英文为逐字引用。硅片侧真源在 ArchForge 仓（不在 CppTLM），本提案应作为**跨仓输入**同步过去。*
