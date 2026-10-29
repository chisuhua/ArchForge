# SM 依赖管理架构方案：五类依赖的统一框架与双后端

> **版本**: v1.2 DRAFT — 2026-10-29（v1.0 初版；**v1.1 = 回应 critic 复审：WAR 槽方案补「仅 NV 建模后端」适用范围** —— §1.2 判据表 / §3.2 L1 状态表 / §4.2 WAR 槽设计 / §6 控制位落位 / §7.3 flush 语义（**新 ISA 后端的 WAR 由 40 号 S-DEP-6 的 gap-`stall` 机制覆盖，不设 WAR 槽**）；版本号与 §9 的「命名更正（v1.1）」对齐）
> **状态**: 🟡 **架构方案**（派生自 [`33-sm-operand-supply-design-target.md`](./33-sm-operand-supply-design-target.md) v0.5；**非当前实现**；未经 Oracle/ADR 评审）
> **Owner**: CppTLM Team
> **文档分类**: 第 1 层 · 架构方案（SM 依赖管理层）
> **上游依据**:
> - [`33-sm-operand-supply-design-target.md`](./33-sm-operand-supply-design-target.md) v0.5 §5（依赖处理机制对比 + WAR 规范条款 C-5~C-8）
> - [`arXiv2503.20481` 解析](../research/SM/CudaCore/arXiv2503.20481_现代NVIDIA核心无操作数收集器_解析.md) §4 / §6b / §7.5（NVIDIA 依赖管理：Stall counter / Dependence counters / WAR 早释放 / scoreboard 代价）
> - [`arXiv1804.06826` 解析](../research/SM/CudaCore/arXiv1804.06826_Volta微基准_寄存器复用与bank冲突_解析.md)（Volta Table 4.1 延迟分档 + 控制位字段宽度）
> - [`gpgpu-sim_操作数收集器实现剖析`](../research/SM/CudaCore/gpgpu-sim_操作数收集器实现剖析.md)（学术口径：scoreboard 与 OC 互不引用）
> - [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) C2（数据冒险与端口争用必须分层）
> - CppTLM 源码实测（`hazard_tracker.hh` / `writeback.hh` / `sm_bundles_tlm.hh` / `instruction_descriptor.hh`）
> **关联 OpenSpec changes**: 无（本文未实施；33 号文档的实施另起 change）
> **定位说明**:
> - **⚠ 视角区分**：本文是「**如何忠实建模现有硬件**」的依赖方案（NVIDIA / CDNA / 学术三口径对比）。若目标是「**设计新 ISA**」，请看 [`36-new-isa-dependence-layer-design.md`](./36-new-isa-dependence-layer-design.md)——该文用本文的机理剖析作为输入，给出**候选架构比较与推荐**，并指出两者在「不变式 D-1」处分叉。
> - **本文回答"正确性由谁保证、什么时候保证"**，33 号文档回答"机制长什么样、收益多少"。两者必须同步维护。
> - **本文不引入新的性能机制**：MCOS / ERW / WABR / SOP 的定义在 33 号文档；本文只定义它们**如何与依赖管理层共存**。

---

## 0. TL;DR

> **一句话**：**五类依赖不该"混用厂商机制"，而该"一个统一框架 + 按 ISA 家族选后端"**——因为决定用不用硬件的，是**依赖的解除时刻是否编译期可知**，而不是它属于哪一类。

| # | 结论 | 章节 |
|---|------|------|
| **①** | **唯一判据**：依赖需要硬件介入 ⟺ **解除时刻编译期不可知**。定长 RAW/WAR/WAW → 编译器 + 少量计数器；可变延迟（内存/SFU）→ 硬件计数器 | §1.2 / §3 |
| **②** | **四层分离**：L1 依赖层 / L2 资源层（端口、bank、FU —— **不是依赖**）/ L3 内存序层 / L4 控制层。**跨层不合并**是 OSF 的扩展不变式 | §2 |
| **③** | **混合的正确位置 = 后端，不是依赖类型**。NV/PTX 后端（Stall counter + SB0-5 + DEPBAR）与 CDNA 后端（TLB scoreboard + vmcnt/lgkmcnt/expcnt + s_waitcnt）并存；**学术口径只作建模对照/回归校验，不作实现目标** | §3 |
| **④** | **WAR 用「读源时释放」的计数器**：读者 issue 时递增、**读完源时递减**；写者等归零。面积 ≈ **12 bit/warp**，比"值锁存"方案低 30× | §4.2 |
| **⑤** | **控制位预算 24 bit/指令**〔**NV 建模后端**（6 槽 ⇒ mask 6 bit）；新 ISA 后端为 **21/16 bit**，见 §6 注〕：`CtrlBits::reserved_ctrl0/1` 只有 16 bit → **差 8 bit**；解法是取 `InstrDescriptor::reserved_hdr` 的 **1 字节**（**不改变 128 字节布局**） | §6 |
| **⑥** | **MCOS 的复用提示是"fail-safe"的**：提示错 ⇒ 命中/未命中变化 ⇒ **性能问题**，**不可能产生错误值**（tag 精确匹配 + C-3 写回失效兜底） | §7.2 |

---

## 1. 范围与判据

### 1.1 先分清"依赖"与"争用"（本仓最重要的分层不变式）

> SYNTHESIS C2：「**数据冒险与端口争用必须分层**」；NVIDIA 论文的 issue 阶段**只检查"资源保证可用"，不检查 RF 读端口**（端口检查在 Allocate 级）；GPGPU-Sim 的 Scoreboard 与 OC **互不引用**。

| | **依赖（hazard）** | **争用（contention）** |
|---|------------------|-------------------|
| 语义 | "这个值**什么时候**可以被消费" | "这个**资源**什么时候归我" |
| 表现 | 指令**不能发射**（warp 不 ready） | 指令**在 Allocate 滞留**，向上游**压气泡** |
| 延迟 | **变**（指令自身的完成时间） | **不变**（定长契约保 I2） |
| 层次 | **L1 依赖层** | **L2 资源层** |
| 归属 | HazardTracker / 依赖计数器 | **独立的端口仲裁器**（33 号文档 §3 表的 Allocate） |

> ⚠ **混层的两个典型错误**：
> 1. 把 bank 冲突塞进 RAW 逻辑 → 冲突被误算成"数据冒险延迟"，破坏 I2（定长契约）且污染依赖层面积账。
> 2. 把 WAR 塞进资源层 → 写者被"资源不够"阻塞，编译器无法推理，模型不可预测。

### 1.2 唯一判据：**解除时刻是否编译期可知**

```
依赖需要硬件介入  ⟺  解除时刻在编译期不可知
```

| 依赖 | 解除时刻 | 编译期可知 | 机制归属 |
|------|---------|-----------|---------|
| RAW（定长 ALU） | `issue(consumer) ≥ issue(producer) + latency` | ✅ **可知**（latency 是 ISA 常量） | **编译器**（Stall counter / scoreboard 静态等待） |
| WAW | 前一次写回完成 | ✅ 可知 | 同 RAW |
| **WAR** | **读者取走源值的那一拍** | ❌ **不可知**（读者何时真正读到是运行时） | **硬件计数器**（读源时释放）〔**NV 建模后端**；新 ISA 后端改用 gap 内 `stall`，见 40 号 S-DEP-6〕 |
| RAW（可变延迟：内存 / SFU） | 访存完成 | ❌ 不可知 | **硬件计数器**（SB / vmcnt） |
| 控制 / 同步 | 到达 barrier | ✅ 静态 | **控制单元**（mask / B register） |

> **这条判据解释了 NVIDIA 的全部设计选择**：
> - 定长 ALU 依赖 → 硬件**不检查 RAW**（「the hardware does not check for RAW hazards, and simply relies on these compiler-set counters」）→ 省掉 scoreboard 的 5.32% RF 面积。
> - WAR 与可变延迟依赖 → 硬件**必须**有计数器（一个 6-bit 计数器 + 3-bit id + 6-bit mask 就够）。〔**NV 建模后端**〕**新 ISA 后端不适用**：其 WAR 由编译期可算的 **gap 内 `stall`** 表达（36 号 §4.1.6 / 40 号 S-DEP-6），不需要硬件计数器。

### 1.3 五类依赖的定义（本方案覆盖范围）

| # | 依赖 | 定义（对本 warp 的寄存器流） | 典型触发者 |
|---|------|--------------------------|-----------|
| 1 | **RAW**（真依赖） | 读 R 的指令在写 R 的指令之后 | FFMA 读累加器 → 下一条 FFMA 写它 |
| 2 | **WAR**（反依赖） | 写 R 的指令在读 R 的指令之后 | 长延迟读之后紧跟覆盖同一寄存器的写 |
| 3 | **WAW**（输出依赖） | 两次写同一寄存器 | 同一条指令被重定址产生两次写 |
| 4 | **内存依赖** | 访存序（load/atomic/store 的可见性顺序） | LDG → 用其结果的指令；STG → 后续读 |
| 5 | **控制 / 同步** | 分支收敛、barrier、exec mask 依赖 | `s_barrier` / `bar.sync` / 分支汇合 |

> **不覆盖**：跨 warp 的数据依赖（通过 shared memory / atomics 表达 → 归入 #4）、跨 CTA 同步（归入 #5）、指令 cache 一致性（非本层）。

---

## 2. 四层分离架构

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ L4 控制层：分支收敛 / barrier / exec mask                                     │
│    状态：B registers（≥16/warp）、barrier mask（6b）、read/write barrier idx    │
│    放行判据：warp 到达 barrier 前不可 issue                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ L3 内存序层：访存可见性顺序                                                    │
│    NV 后端：SB0-5（可变延迟依赖的载体）+ DEPBAR.LE                            │
│    CDNA 后端：vmcnt / vscnt / lgkmcnt / expcnt + s_waitcnt                    │
│    放行判据：计数器归零 / 显式 waitcnt 触发                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ L1 依赖层：寄存器 RAW / WAR / WAW  ★ 本方案主体                                │
│    状态：per-warp stall_cnt + SB[6] + WAR 槽 〔NV 建模后端；新 ISA 后端无 WAR 槽〕 │
│    放行判据：stall_cnt == 0 ∧ ∀ sb ∈ wait_mask: SB[sb] == 0                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ L2 资源层：RF 读/写端口、bank 槽位、FU 输入 latch、issue 槽位                │
│    状态：端口预约表（Allocate 级）                                             │
│    ⚠ 与 L1 **完全分离**：争用表现为 Allocate 滞留 + issue 侧气泡，**不改变延迟** │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 跨层不合并的三条硬规则

| # | 规则 | 违反后果 |
|---|------|---------|
| **R-1** | L2 资源冲突**不得**写入 L1 依赖状态 | 破坏 I2（定长契约）+ 依赖层面积失控 |
| **R-2** | L1 的依赖计数**不得**用于推断"值已就绪"以外的任何事 | 编译器与硬件的推理模型分叉，无法验证 |
| **R-3** | L3 内存序**不得**复用 L1 的寄存器级槽位 | 内存请求的在飞数（几十）与寄存器依赖数（个位）规模不同，混用会导致假阻塞 |

> **R-1/R-3 的实证支撑**：NVIDIA 的 scoreboard 与 operand collector **互不引用**（GPGPU-Sim 同构）；NVIDIA 论文把 scoreboard 与软件依赖管理**分开评估**（面积 5.32% vs 0.09%）。

### 2.2 L2 资源层在 OSF 中的位置（与 33 号文档的衔接）

| L2 资源 | 状态 | 冲突表现 | 归属 |
|---------|------|---------|------|
| RF 读端口（2 bank × 1×1024-bit） | 端口预约表 | 指令滞留 Allocate → **issue 侧气泡** | **Allocate 级**（33 号文档 §3） |
| RF 写端口（2 bank × 1×1024-bit） | 结果队列 | **不延迟**（队列吸收） | Result queue |
| bank 槽位（读槽/指令） | `max_b` 分布 | 同上（气泡 = `max_b − 1`） | Allocate + 编译器分配 |
| FU 输入 latch | 每 FU 1 拍（full warp 宽） | **不阻塞 issue**（issue 只检查"资源保证可用"） | 调度器 |
| issue 槽位 | 指令缓冲 | 调度器换 warp | Issue 级 |

---

## 3. 统一框架 + 双后端（回答"是否混合"）

> **📄 若目标是设计新 ISA**：本文 §3 的机理剖析（可提炼的 4 条机制 / 不可照搬的 3 条约束）是 [`36-…`](./36-new-isa-dependence-layer-design.md) §3 的直接输入；本文 §5.2.3 的"OSF 最终选择"是**建模保真**口径下的答案，**不是**新 ISA 的推荐答案（后者见 36 号 §4）。
### 3.1 为什么不是"按依赖类型混用厂商机制"

| 候选做法 | 问题 |
|---------|------|
| **A. 按依赖类型分配厂商**（如 RAW 用 NV、内存用 AMD） | ① 同一 warp 内出现两套不兼容的"等待"语义，编译器无法统一推理；② AMD 的 `s_waitcnt` 是**显式指令**（占 issue 槽），NV 的 DEPBAR 是**控制位**（不占）——混用会改变指令流；③ 面积账无法统一核算 |
| **B. 按 ISA 家族分后端** ✅ | 同一 SM 模型要同时承载 PTX/NV 与 CDNA 两种**硬件行为口径**（原前提见 [`11-cdna-real-isa-integration.md`](./11-cdna-real-isa-integration.md)；**v1.1 该前提已被 ADR-SOC-26 移除**，见下方口径说明）；两个 ISA 的**依赖语义本就不同**（NV 编译器负责 ALU 依赖，AMD 硬件负责），后端化是**对硬件事实的建模**，不是拼凑 |

> **结论：依赖类型决定"要不要硬件"（§1.2 判据），ISA 家族决定"硬件长什么样"（后端）。两者正交。**

> **⚠ v1.1 口径澄清（critic 复审追加）：双后端在 ADR-SOC-26 之后还剩什么。**
> ADR-SOC-26 D1 已定「**自研 ISA 是本仓 GPGPU 的唯一 ISA**」，D2 否决的是「**作为 ISA 实现路径**的三套时序模型并存」（量化理由：三套控制位宽度 26/21/16 bit 与三套延迟类语义无法共存于同一 `InstrDescriptor`）。
> **⇒ 因此本文的「双后端」须按层级重读**：
> | 层级 | ADR-26 之后的地位 |
> |---|---|
> | **作为 ISA 实现路径**（解码 + 执行 NVIDIA/CDNA 指令） | ❌ **已取消** —— `isa_type` 收敛为「单值 + 回放模式」（37 号 §5 第 6 条） |
> | **作为硬件行为口径**（NVIDIA/AMD 的依赖语义，用于**校准对拍**） | ✅ **保留** —— 本文的 NV / CDNA 后端是**对照口径**，由 **trace-replay 校准**消费（37 号 §3.4 / 12 号校准基线），**不占用 `isa_type`，也不产生第三条实现路径** |
>
> **⇒ 与 ADR-26 D2 的关系**：D2 否决的是「实现路径并存」，本文保留的是「**校准口径并存**」⇒ **层级不同，不矛盾**。
> **⇒ 消费方归属（v1.2 裁决，归 37 号 §5 第 10 条）**：**本文的 NV / CDNA 建模后端 = 「trace-replay 校准专用」** —— 由 **37 号 §3.4 的回放通道 + 12 号校准基线**消费；**不占用 `isa_type`，不产生第二条 ISA 实现路径**。
> ⇒ **落地后果**：33 号 §12 **V13（WAR 计数器落地）只在回放 NVIDIA 轨迹做行为对拍时需要**；33 号 §8.2 **P1/P2/P3 的产物是「行为口径」而非「前端实现路径」**。
> ⇒ **本仓当前不承诺实现 NV/CDNA 建模后端**（无 OpenSpec change 指向它）—— 它是**校准对照口径**，由 12 号按需驱动。

### 3.2 框架与后端

```
                    ┌───────────── DependenceManager（SM 内，每 warp 状态）─────────────┐
                    │  DependenceState { stall_cnt:4b, SB[6]:6b, war_slots, yield }     │
                    │  统一接口：ready(warp, instr) / on_issue() / on_read_done() /      │
                    │            on_writeback() / on_barrier()                         │
                    └───────────────┬───────────────────────────┬──────────────────────┘
                                    │                           │
             ┌──────────────────────▼──────────┐   ┌────────────▼──────────────────┐
             │ **NV / PTX 后端**（实测口径）     │   │ **CDNA 后端**（文档口径）       │
             │ · Stall counter（定长 RAW/WAW）   │   │ · TLB scoreboard（ALU 冒险）  │
             │ · SB0-5（可变延迟 RAW/WAW + WAR） │   │ · vmcnt / vscnt / lgkmcnt /   │
             │ · WAR 槽（读源时释放）            │   │   expcnt                       │
             │ · DEPBAR.LE SBx, n              │   │ · s_waitcnt（显式等待指令）    │
             │ · Yield（跨 warp 切换 +1 cycle） │   │ · DELAY_ALU（RDNA 3/3.5+）     │
             │ · Read/Write barrier index      │   │ · MEM_ORDERED 位               │
             └─────────────────────────────────┘   └───────────────────────────────┘
                                    │                           │
             ┌──────────────────────▼───────────────────────────▼──────────────────────┐
             │ **学术口径后端**（GPGPU-Sim / Accel-Sim scoreboard）                        │
             │  ⚠ **仅用于建模对照与回归校验**，不作实现目标（OC 假设已被实测否定）          │
             └────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 三后端的统一抽象

| 抽象动作 | 语义 | NV 后端 | CDNA 后端 | 学术后端 |
|---------|------|---------|-----------|---------|
| `on_issue(w, instr)` | 指令发射：递增它声明的依赖槽 | 递增 SB / 递增 WAR 槽 | 递增 TLB scoreboard 计数 | 置 pending write |
| `on_read_done(w, reg)` | **读完源操作数**（WAR 释放点） | 递减 WAR 槽 | （顺序发射，ALU WAR 由硬件保证） | — |
| `on_writeback(w, instr)` | 结果写回 RF | 递减 SB（RAW/WAW） | 释放 scoreboard 条目 | 清除 pending write |
| `ready(w, instr)` | 该 warp 能否发射 | `stall_cnt == 0 ∧ ∀sb∈mask: SB[sb]==0` | TLB 无冲突 ∧ waitcnt 满足 | scoreboard 无冲突 |
| `on_barrier(w)` | 到达同步点 | 置 barrier mask 位 | `s_barrier` 等待 | — |

> **统一抽象的价值**：CppTLM 只需实现**一套** `DependenceManager` 接口 + **两套**后端策略（NV / CDNA），并让 `model` config 键选择（对齐 33 号文档 §8.3 的 `sm.operand_supply.model` 风格）。

---

## 4. 五类依赖的完整方案

### 4.1 RAW（真依赖）

#### 4.1.1 定长 ALU 的 RAW —— 纯编译器责任

| 项 | 内容 |
|---|---|
| **判据** | 解除时刻 `issue(producer) + latency` **编译期已知** ⇒ **硬件零参与** |
| **编译器责任** | 在消费者指令上设置 **Stall counter** = `生产者延迟 − 生产者与首个消费者之间的指令数`；`latency` 取 §4.1.2 的分档表 |
| **硬件责任** | 每拍 `stall_cnt--`；`stall_cnt > 0` ⇒ 该 warp **不可发射**（调度器换 warp，CGGTY） |
| **状态** | per-warp `stall_cnt` **4 bit**（0–15） |
| **时序** | 消费者在 `issue(producer) + latency` 那一拍变为 ready |
| **相邻指令的坑** | 依赖计数器的递增发生在**发射的下一拍** ⇒ 若消费者紧跟生产者，编译器必须把 Stall counter 设为 **≥ 2**（论文原文：「if the consumer is the next instruction, the producer has to set the Stall counter to 2」） |
| **与 OSF 交互** | MCOS 命中**不改变**该延迟（值仍须在 `issue+3` 前就绪）；ERW 让值**提前到达**⇒ 消费者可以**提前 ready**（提前量受 L=3 窗口约束） |
| **失败模式** | Stall counter 设错 ⇒ **程序结果错误**（论文已实测验证：「the result of the program is incorrect」）⇒ **必须做差分测试** |

#### 4.1.2 延迟分档表（编译期常量的取值来源）

| 架构 | 指令类 | 延迟 (cycle) |
|------|--------|------------|
| **Pascal** | FADD/FMUL/**FFMA**/LOP3/IADD/MOV/SEL/… | **6** |
| | DADD/DMUL/DFMA | 8 |
| | FSET/DSET/DSETP/ISETP/FSETP | 12 |
| | POPC/FLO/MUFU/F2F/F2I/I2F/I2I | 14 |
| **Volta** | IADD3/SHF/LOP3/SEL/MOV/FADD/**FFMA**/FMUL/ISETP/FSET/FSETP | **4** |
| | IMAD/FMNMX/DSET/DSETP | 5 |
| | HADD2/HMUL2/HFMA2 | 6 |
| | DADD/DMUL/DFMA | 8 |
| | POPC | 10 |
| | FLO/BREV/MUFU | 14 |

> **本仓建模取值**（33 号文档 §4.4.1b 裁决 `d = 1`）：`LatencyClass` 应能表达「**读窗 3 拍**」与「**FU 占用 `d`**」两个独立维度，而非当前的粗粒度单一枚举。

#### 4.1.3 可变延迟（内存 / SFU）的 RAW —— 硬件计数器

| 项 | 内容 |
|---|---|
| **判据** | 解除时刻 = 访存完成 ⇒ **不可知** ⇒ 需硬件 |
| **编译器责任** | 为生产者分配一个 **SB 槽 id**（3 bit，6 选 1）；消费者在 **wait mask**（6 bit）中置该 id |
| **硬件责任** | 生产者**发射后一拍**递增 `SB[x]`（6 bit，饱和于 63）；生产者在**写回时**递减；消费者发射前检查 `∀sb∈mask: SB[sb]==0` |
| **并行性** | 多个生产者可共用一个 SB 槽（"the same Dependence counter can be used by all these producers without losing any parallelism"） |
| **槽位耗尽** | >6 个不同可变延迟生产者 ⇒ 编译器必须「合并到同一槽」或「重排」 |
| **失败模式** | mask 漏置 ⇒ 读到陈旧值；mask 多置 ⇒ 假阻塞 |

### 4.2 WAR（反依赖）—— **本方案的关键设计**

> **⚠ 适用范围（v1.1，critic 复审追加）**：**本节的 WAR 槽机制只属于「NVIDIA 行为基线建模后端」**（本仓对标 NVIDIA 的实现路径，33 号 C-5 / C-8 / V13 依赖它）。
> **新 ISA 前端配置下不适用** —— 新 ISA 的 WAR 由 [`40-new-isa-spec-skeleton.md`](./40-new-isa-spec-skeleton.md) §4.5 **S-DEP-6** 覆盖：**不设 WAR 计数器 / WAR 槽**，改由 gap 内 `stall` 表达（36 号 §4.1.6 推导）。
> **⇒ 本节是「建模口径」，不是「新 ISA 的依赖层规范」。**

#### 4.2.1 问题

写者 W 写寄存器 R；读者 Q 也要读 R。若 W 的写发生在 Q 取走 R 之前 ⇒ Q 读到**新值**而非它应得的**旧值** ⇒ 程序序错误。

**WAR 的解除时刻是"读者何时真正取走源值"——运行时才知道 ⇒ 必须硬件参与。**

#### 4.2.2 机制：**读源时释放**的计数器（NVIDIA 实测口径）

> 论文原文：「For **WAR hazards**, the mechanism is similar, with the only difference being that **the counter is decreased after the instruction reads its source operands**, instead of decreasing the counter at write-back.」
> 「**Clearing WAR dependencies after reading the source operands is an important optimization**, since source operands are sometimes read much earlier than the result is produced, especially for memory instructions.」

| 项 | 内容 |
|---|---|
| **编译器责任** | 为"会被 WAR 影响的寄存器"分配一个 **WAR 槽 id**（可复用 SB 槽空间）；读者在发射时声明"我正在读这些寄存器" |
| **硬件责任（读者侧）** | 读者**发射后一拍**递增 WAR 槽计数；**读完源操作数时递减** |
| **硬件责任（写者侧）** | 写者发射前检查该 WAR 槽为 0（**否则不放行**）⇒ 写者被阻塞，读者不被阻塞 |
| **状态** | per-warp WAR 槽 **6 bit × 2 = 12 bit**（可与 SB 槽合并，共享 6 个槽） |
| **面积** | **12 bit/warp（独立占用，Q-M1 裁决"分开"）× 48 warp = 576 bit/SM ≈ 0.027% RF**（以 48 warp 计；64 warp 则 0.037%）。**Q-M1 分开的理由**：WAR 与 RAW/WAW 的**释放事件不同**（读完源 vs 写回），合并会让一个槽承载两种释放时刻 |
| **与 OSF 交互（优势）** | MCOS 命中时**不占 bank 读槽**、且**值在 `issue` 拍即交付** ⇒ WAR 槽**提前一拍释放** ⇒ 写者更早解阻。**这是 MCOS 在依赖层面的额外收益**（33 号文档 §5.1 C-6） |
| **失败模式** | 槽分配错误 ⇒ 写者提前写 ⇒ **读到陈旧值**（正确性事故）⇒ 需差分测试（§12 V13） |

> **为什么"写者被阻塞、读者不被阻塞"是对的**：WAR 的危险在"写早于读" ⇒ 必须阻塞**写者**。若反过来阻塞读者（v0.4 的值锁存思路是让读者读到旧值、写者自由写），则写者会**覆盖**掉读者尚未取走的值 —— 除非额外保留一份旧值副本（即那 1.2% 面积的来源）。**两种方案都正确，但计数器方案便宜 30×。**

> ⚠ **代价（诚实标注）**：写者可能被读者阻塞——若读者自身被前面的依赖卡住，其源读迟迟不发生，写者要一直等。**NVIDIA 真实硬件就是这个行为**，且由编译器排程规避（把长延迟读排到独立序列）。OSF 采纳同一取舍。

#### 4.2.3 内存可见 WAR（unbuffered store）

store 的**源寄存器**在 store 完成前不得被改写 ⇒ 需一个"读屏障"级别的保护。NVIDIA 的做法：**Read dependency barrier**（3 bit 索引）+ Write dependency barrier（3 bit 索引）。OSF：归入 L4 控制层。

### 4.3 WAW（输出依赖）

| 项 | 内容 |
|---|---|
| **判据** | 解除时刻 = 前一次写回完成 ⇒ **与 RAW 同构** ⇒ **共用同一计数器** |
| **机制** | 生产者发射后一拍**递增** SB 槽；**写回时递减**；后续消费者等该槽归零 ⇒ 保证"读到的是最后一次写的值" |
| **与 OSF 交互** | MCOS 的 **INVALIDATE（C-3）** 保证槽值恒等于 RF 当前值 ⇒ **WAW 不会污染 MCOS 槽**（写回时先清所有 op_pos 槽，再 FILL 新值） |
| **失败模式** | 两次写同寄存器未串行 ⇒ 后写的值被先读到 |

> **关键性质**：WAW 与 RAW 共用槽 ⇒ **不额外增加面积**。

### 4.4 内存依赖

| 项 | NV / PTX 后端 | CDNA 后端 |
|---|---------------|------------|
| **载体** | SB0-5（与寄存器依赖共享槽空间）+ `DEPBAR.LE SBx, n` | `vmcnt`（load）/ `vscnt`（store，gfx10+）/ `lgkmcnt`（LDS+SMEM）/ `expcnt`（export）；**每 wavefront 3–4 个** |
| **等待方式** | **控制位**（wait mask）⇒ **不占 issue 槽** | **显式 `s_waitcnt` 指令** ⇒ 占 issue 槽，但解码开销低 |
| **并行链上限** | 6 个 SB ⇒ 6 条并发可变延迟依赖链 | 3–4 条（每计数器专用于特定指令类型） |
| **AMD 的 ALU 依赖** | — | **硬件 scoreboard（TLB）**，**不需要软件/编译器介入**；RDNA 3/3.5 另加 `DELAY_ALU` 缓解依赖停顿 |
| **实测延迟**（Ampere，单线程） | `LDG.32` regular：**WAR 11 / RAW-WAW 32**；`LDG.128`：**11 / 38**；`LDS.32` regular：**9 / 24**；`STG.32` regular：**WAR 14** | — |

> **口径差异必须在文档中显式标注**：NV 的"内存依赖"是 **SB 计数器 + DEPBAR**；`vmcnt` 是 **AMD/PTX 词汇**，不是 NVIDIA SASS 词汇（33 号文档 v0.4 曾把二者混列，v0.5 已更正）。
>
> **实测延迟表的一个要点**：load 的 **WAR 释放（11 拍）远早于 RAW/WAW 可用（32 拍）** ⇒ "读者何时能取走源"远早于"值何时可用" ⇒ **WAR 早释放的价值在内存路径上最大**（论文原文同义）。

### 4.5 控制依赖与同步

| 项 | 内容 |
|---|---|
| **判据** | 静态 ⇒ 编译器可完全推理 |
| **NV 机制** | **B registers**（每 warp ≥16，控制流重收敛）+ **barrier mask（6 bit）** + **Read/Write dependency barrier index（各 3 bit）**；`DEPBAR.LE` 亦可等控制位 |
| **CDNA 机制** | `s_barrier` / `s_waitcnt` / `vscnt` / `MEM_ORDERED` 位 |
| **硬件责任** | warp 到达 barrier 前**不可发射**；分支汇合点的活跃 mask 维护 |
| **与 OSF 交互** | **ERW 的分支 flush**（33 号文档 §4.2.4）**必须与控制层协同**：分支解析后 flush slot buffer ⇒ 需一个"分支已解析"事件从 L4 传到 L1/L2 |
| **失败模式** | 分支 flush 与 WAR 槽交互 ⇒ flush 后未释放的 WAR 槽会造成**假阻塞**（见 §7.3） |

---

## 5. 统一的放行判据与时序

### 5.1 放行判据（warp readiness）

```
warp_ready(w) =  ( stall_cnt[w] == 0 )                      // L1 定长 RAW/WAW（编译器给的）
              ∧  ∀ sb ∈ wait_mask[w] : SB[w][sb] == 0        // L1 可变延迟 RAW/WAW + WAR 槽
              ∧  warp 未停在 barrier                          // L4 控制
              ∧  常量 cache 已命中（否则 4 拍后换 warp）        // 前端
              ∧  执行单元输入 latch 可用（"资源保证可用"）       // L2（**不含 RF 端口**）
              ─────────────────────────────────────────────────────────────
              ⚠ RF 读端口可用性【不在此判据内】⇒ 由 Allocate 级处理（33 号文档 §3）
```

> **这一行是本方案与 NVIDIA 论文的接口点**：issue 阶段**不检查** RF 读端口（论文实测：「the issue scheduler is unaware of whether the evaluated instructions have enough ports」）；端口争用变成 **Allocate 滞留 + issue 侧气泡**，**不改变延迟**。

### 5.2 cycle 坐标：一条 FFMA 依赖链 + WAR 交互

```
        t+0    t+1    t+2    t+3    t+4    t+5    t+6    t+7    t+8
        ├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────▶
I0 发射 │ I0   │      │      │      │      │      │      │      │
I0 读源 │ ██   │ ██   │ ██   │      │      │      │      │      │
I0 Exec │      │      │      │ 进入 │      │      │      │      │
I0 结果 │      │      │      │      │ 结果 │      │      │      │
I0 写回 │      │      │      │      │ 写   │      │      │      │
        │      │      │      │      │ ↑SB[x] 递减（RAW/WAW 释放）
I1 发射 │      │      │      │      │ I1   │      │      │      │  ← Stall counter 到 0
I1 读源 │      │      │      │      │      │ ██   │ ██   │ ██   │
I1 Exec │      │      │      │      │      │      │      │ 进入 │
        │  ↑ WAR 槽递增（读者 I1 声明正在读 R）        ↑ WAR 槽递减（读完源）
I2 发射 │      │      │      │      │      │      │      │ I2   │  ← I2 写 R，须等 WAR 槽归零
```

### 5.3 五类依赖的"放行事件"汇总

| 依赖 | 递增事件 | 递减（释放）事件 | 等待方 | 判据归属 |
|------|---------|--------------|--------|---------|
| RAW（定长） | 无（编译器直接给 Stall counter） | Stall counter 每拍 −1 | 消费者 | L1 / 编译器 |
| RAW（可变） | 生产者**发射后一拍** | 生产者**写回** | 消费者 | L1 / SB 槽 |
| **WAR** | 读者**发射后一拍** | **读者读完源操作数** | **写者** | L1 / WAR 槽 |
| WAW | 生产者**发射后一拍** | 生产者**写回** | 后续写者 / 消费者 | L1 / SB 槽（与 RAW 共用） |
| 内存 | 访存发出 | 访存完成 | 消费者（NV: 控制位；AMD: 显式 waitcnt） | L3 |
| 控制 | 到达 barrier | 全部到达 | warp | L4 |

---

## 6. 控制位与状态面积预算

### 6.1 每指令控制位

| 字段 | 位宽 | 归属 | 备注 |
|------|------|------|------|
| `stall_cnt` | 4 | L1（定长 RAW/WAW） | 0–15；**延迟 >15 的指令无法用此机制编码** |
| `sb_id_raw` | 3 | L1（可变延迟 RAW/WAW） | SB0-5 |
| `sb_id_war` | 3 | L1（WAR） | 可与 `sb_id_raw` 复用同一槽 |
| `sb_wait_mask` | **6** | L1/L3 | 等哪些 SB 归零；**NVIDIA 实测 6 个依赖计数器 ⇒ 6 bit**（本文 §5.2.1 / 附录 A `SB[0..5]`）。⚠ **与新 ISA 的 8 bit 区分**：36 号 Q-2 的「8 槽 ⇒ 8 bit」是**新 ISA**的裁决，不适用于 NV 口径 |
| `yield` | 1 | 调度 | 跨 warp 切换 +1 cycle |
| `reuse_flags` | 3 | MCOS | 每 op_pos 1 bit（生产者填充槽） |
| `budget_hint` | 2 | MCOS | 0/1/≤4/≤16 |
| `width_hint` | 2 | WABR | 1024/512/256 bit |
| **合计** | **24** | | Q-5 采用隐式提示 ⇒ 不需要 operand-source 字段（省 6 bit）。**v1.2 修正**：v1.1 曾按 8-bit mask 算得 26 bit ⇒ 已回到 NVIDIA 实测的 **6 槽 / 6-bit mask ⇒ 24 bit** |

> ⚠ **超出 `CtrlBits` 现有余量**：`CtrlBits` 共 4 字节，其中 `reserved_ctrl0/1` = **16 bit** ⇒ **差 8 bit**。
> **解法（不动跨仓 bundle 布局）**：从 `InstrDescriptor::reserved_hdr`（4 B，位于 header 内，实测 offset 4）取 **1 字节** ⇒ 合计 **24 bit**（6 槽 mask 6 bit），**`sizeof(InstrDescriptor)` 仍为 128**（实测确认），剩余 3 B 仍可回收。
>
> **⚠ 后端口径（v1.1，critic 复审追加；v1.2 修正数字）**：**上述 24 bit 是「NVIDIA 建模后端」的控制位预算**（含 3 bit WAR 槽 id + 6 bit mask）。
> **新 ISA 前端配置下的控制块是 21 bit（向量）/ 16 bit（标量）**（36 号 §4.5.1 / Q-10 / Q-11）—— **不含 WAR 槽**（WAR 由 gap 内 `stall` 表达），**且标量域省掉 `reuse_flags`/`budget_hint`**。
> ⇒ **两者不冲突，但落位方案也不同**：NV 后端取 `reserved_hdr` 1 B 装 **24 bit**；新 ISA 后端只需 **21 bit** ⇒ **同一字节可容纳**，但**槽数（6 vs 8）、掩码宽度（6 vs 8）、WAR 处理（计数器 vs gap-stall）三者都不同** ⇒ 实现时**不得把两个后端的位定义混用**。
> **禁止**的做法：扩 `IssueToExecBundle` / `WritebackToRegFileBundle`（跨仓 HSK-9 size 约束，33 号文档 §8.4 已列）。

### 6.2 每 warp 状态

| 状态 | 位宽 | 归属 |
|------|------|------|
| `stall_cnt` | 4 | L1 |
| `SB[6]` | 6 × 6 = 36 | L1 / L3 |
| WAR 槽（可复用 SB 槽） | 0（共享）或 2 × 6 = 12 | L1 |
| B registers | ≥16 × ? | L4 |
| **小计（依赖相关）** | **40–52 bit/warp** | |

⇒ **48 warp/SM × 52 bit = 2496 bit/SM ≈ 0.119% RF**（论文口径基数；64 warp 则 3328 bit ≈ 0.16%）。与 NVIDIA 实测 41 bit/warp = 0.09%（同为 48 warp 基数）**同量级**。
> ⚠ **基数一致性**：论文的 5.32% 与 0.09% 均以 **48 warp/SM** 计（`2324 bit/warp × 48 = 111,552 bit = 5.32%` 可自校验）⇒ 本文一律用 48 warp 基数，避免与 64 warp 混比。

### 6.3 与"硬件 scoreboard"方案的对照（为何不建）

| 方案 | 面积 | 性能 | 精度 | 结论 |
|------|------|------|------|------|
| **本方案（编译器 + 计数器）** | 41 bit/warp = **0.09% RF** | 基准 | **MAPE 13.98%** | ✅ 采纳 |
| 硬件 scoreboard（两块：WAW/RAW + WAR） | 332 entries/warp → 2324 bit/warp → **5.32% RF** | **0.97×（更慢）** | 14.87% | ❌ 不采纳 |

---

## 7. 失败模式与安全性质

### 7.1 失败模式矩阵

| # | 失败模式 | 影响 | 检测 | 缓解 |
|---|---------|------|------|------|
| F-1 | **Stall counter 设错** | **程序结果错误** | 差分测试（必须） | 编译器单测：逐指令核对 latency 表 |
| F-2 | **WAR 槽漏置 / 错置** | 写者提前写 ⇒ **读到陈旧值** | 差分测试 | 编译器单测 + §12 V13 |
| F-3 | **SB wait mask 漏置** | 读到陈旧值 | 差分测试 | 同上 |
| F-4 | **SB 槽耗尽（>6 生产者）** | 假阻塞或被迫重排 | 静态计数（编译器可检） | 编译器合并槽 / 重排 |
| F-5 | **分支 flush 后 WAR 槽未释放** | 假阻塞（吞吐损失） | 定向用例 | flush 时**强制清零该 warp 的 WAR 槽** |
| F-6 | **端口冲突被误塞进依赖层** | 破坏 I2 + 面积失控 | 层次审计 | **R-1** 分层不变式 |
| F-7 | **MCOS 复用提示错** | **性能问题**（命中/未命中变化） | — | **tag 精确匹配 ⇒ 不可能产生错误值**（§7.2） |

### 7.2 MCOS 的 fail-safe 性质（重要）

| 提示错误的后果 | 是否产生错误值 | 原因 |
|--------------|:------------:|------|
| `reuse_flags` 少置 | ❌ 不产生 | 消费者 MISS → 走 RF 直读 → 值正确 |
| `reuse_flags` 多置 | ❌ 不产生 | 槽被填入**权威副本**；消费者的 tag 必须精确匹配才交付 |
| `budget_hint` 少给 | ❌ 不产生 | 预算耗尽 → 后续消费者 MISS → 走 RF |
| `budget_hint` 多给 | ❌ 不产生 | 槽多命中几次；**C-3 写回即失效**保证槽值恒等于 RF 当前值 |
| `width_hint` 与实际不符 | ❌ 不产生 | **tag 为权威、提示仅为上界**（33 号文档 R3） |

⇒ **MCOS 的复用/宽度提示是"性能提示"而非"正确性提示"** ⇒ 编译器提示错误**最坏是性能回退，绝不产生错误值**。这是 OSF 相对"编译器承担全部依赖正确性"（NV 的 Stall counter）的**显著安全优势**：**OSF 把一部分正确性责任从编译器手里移到了硬件 tag 校验上**。

> ⚠ **但 WAR / RAW 的提示仍是"正确性提示"**（F-1/F-2/F-3）——这部分的编译器责任**无法用硬件兜底**，必须靠差分测试。

### 7.3 分支 flush 与 WAR 槽的交互（实现注意项）

> **⚠ 适用范围（v1.1，critic 复审追加）**：本节讲的是 **WAR 槽**的 flush 语义 ⇒ **只适用于「NVIDIA 建模后端」**。
> **新 ISA 后端没有 WAR 槽**（WAR 由 gap 内 `stall` 表达）⇒ **本节的「强制清零」要求对新 ISA 不适用**；新 ISA 的对应问题是「**flush 后 gap 内累计的 `stall` 是否仍然有效**」——由于 `stall` 是**编译期常量**、与运行时是否执行无关 ⇒ **flush 丢弃指令不会产生悬挂计数**，该问题**自动消失**。


ERW 的分支 flush 会丢弃已预取但可能不执行的源值。**若被丢弃的指令已递增了 WAR 槽而其"读完源"事件永不发生 ⇒ 写者永久阻塞。**

⇒ **规范要求**：**分支 flush 时，必须把该 warp 所有 WAR 槽强制清零**（读者不再会读该源 ⇒ 其 WAR 声明作废）。**此条须写入 33 号文档 §5.2 / 本方案 §4.5 的实现契约。**

---

## 8. CppTLM 落地映射

### 8.1 现状与差距（源码实测）

| 组件 | 现状 | 缺什么 |
|------|------|--------|
| `HazardTracker`（`include/tlm/gpu/sm/hazard_tracker.hh`） | 只有 `vmcnt`（`kHardwareCounter`）+ `allocated_vregs_` 位图（`kVirtualReg` 的 RAW）；`tick()` 是 no-op | **无 WAR / WAW**；无 per-warp `stall_cnt` / SB 槽；**无"读完源"事件**（WAR 释放点无处触发） |
| `WritebackUnit`（`include/tlm/gpu/sm/writeback.hh`） | `enqueue(desc, finish_cycle)` + `tick(current_cycle)` | **`enqueue()` 全仓无调用点** ⇒ "按延迟占用 → 写回"这条时序链**尚未生效** ⇒ SB/WAR 的"写回时递减"事件**无触发源** |
| `ScalarALU::execute()` | 返回 cycles（1/4）但**无人消费**；结果在 execute 当拍直接写 RF | 延迟未参与时序；**无 in-flight 队列** ⇒ 无"写回拍"概念 ⇒ RAW/WAW 无法建模 |
| `InstrDescriptor::ctrl` | `CtrlBits` 4 B（`reserved_ctrl0/1` = 16 bit） | 依赖控制位需 **24 bit** ⇒ 需 1 B（从 `reserved_hdr` 取） |
| `LatencyClass` | 6 个粗粒度枚举（1/4/8/16/32/memory） | 需能表达「**读窗 3 拍**」+「**FU 占用 `d`**」两个独立维度 |
| `IssueUnitTLM` | round-robin 跨 warp | 需消费 `warp_ready(w)` 判据；`Yield` 语义（换 warp +1 cycle） |

### 8.2 建议的落地顺序（对齐 33 号文档 §8.2 的 P1/P2/P3）

| 阶段 | 内容 | 依赖 |
|------|------|------|
| **D0（前置）** | **把写回时序真正建起来**：让 `ScalarALU/VectorALU::execute()` 的 `cycles` **被消费** → `WritebackUnit::enqueue(desc, finish_cycle)` 有调用点 → 结果在 `finish_cycle` 才写 RF | 无 |
| **D1** | `DependenceManager` 抽象 + **NV 后端**：`stall_cnt`（4 bit）+ `SB[6]`（6 bit）；`HazardTracker` 增 `on_issue/on_read_done/on_writeback/ready` 接口 | D0 |
| **D2** | **WAR 槽** + "读完源"事件（由 RF 读窗口完成触发）；分支 flush 强制清零 | D1 |
| **D3** | **CDNA 后端**：TLB scoreboard（ALU 冒险）+ `vmcnt/lgkmcnt/expcnt` + `s_waitcnt` | D1 |
| **D4** | 控制位编码扩展（`reserved_hdr` 1 B）+ `LatencyClass` 拆分 | D1 |
| **D5** | 与 **MCOS** 联动：`CONSUME` 命中路径的 WAR 释放时刻 = `issue`（而非 `issue+2`） | D2 |

> **D0 是硬前置**：没有真实的写回拍，RAW/WAW/WAR 都无从建模——**这是当前实现与 OSF 依赖层之间的最大缺口**，且与 33 号文档 §12 V13 是同一件事。

### 8.3 接口草案

```cpp
// 依赖层统一接口（草案；不扩跨仓 bundle）
class DependenceManager {
public:
  // 发射时：登记本指令声明的依赖槽（RAW/WAW 递增、可变延迟生产者递增、WAR 读者递增）
  virtual void on_issue(uint32_t warp, const InstrDescriptor&) = 0;
  // 读完源操作数时：释放 WAR 槽（WAR 的唯一释放点）
  virtual void on_read_done(uint32_t warp, uint32_t reg_mask) = 0;
  // 写回时：释放 RAW/WAW 槽
  virtual void on_writeback(uint32_t warp, const InstrDescriptor&) = 0;
  // 放行判据（见 §5.1）
  virtual bool ready(uint32_t warp, const InstrDescriptor&) const = 0;
  // 分支 flush：强制清零该 warp 的 WAR 槽（§7.3）
  virtual void on_branch_flush(uint32_t warp) = 0;
};
```

---

## 9. 未决问题（**建模侧，编号 `Q-M*`**）

> **命名更正（v1.1）**：本文 v1.0 用 `D-1..D-4`，与 [36 号](./36-new-isa-dependence-layer-design.md) §4 的三条**不变式 D-1/D-2/D-3** 撞名。
> v1.1 起本文改用 **`Q-M1..Q-M4`**（M = Modeling）；**ISA 设计参数的编号 `Q-1..Q-9` 专属 36 号 §7**，两文档不共用编号，避免歧义。
> 唯一跨文档对应：**本文 `Q-M1` ≡ [36 号](./36-new-isa-dependence-layer-design.md) `Q-1`（WAR 槽是否分开）**。⚠ **v1.2 限定**：36 号 **Q-1 已被 Q-11 取代**（新 ISA 域取消 WAR 槽）⇒ **Q-M1 的裁决只适用于「NVIDIA 建模后端」**，新 ISA 域见 ADR-SOC-28。

| # | 问题 | 裁决 / 状态 | 影响 |
|---|------|-----------|------|
| **Q-M1** | WAR 槽与 SB 槽是否物理合并？（= 36 号 Q-1，**仅 NV 建模后端**；36 号 Q-1 已被 Q-11 取代） | ✅ **裁决：分开** | `WAR[2]×6 = 12 bit/warp` **独立占用**；面积见 §4.2 |
| **Q-M2** | CDNA 后端的 TLB scoreboard 深度 | ⏳ **仍未决**（无一手来源；"4/6/8-deep" 无法证实） | 仅影响 CDNA 后端建模精度，不阻塞 NV 后端 |
| **Q-M3** | AMD `s_waitcnt` 占 issue 槽是否显式建模 | ⏳ **仍未决** | 影响 CDNA 后端 IPC 精度 |
| **Q-M4** | 控制位落位：取 `reserved_hdr` 1 B，还是另开 SM 内部旁路 | ⏳ **仍未决**（跨仓 HSK 流程） | 位宽已更新为 **24 bit**（**NV 后端**：6 槽 ⇒ mask 6 bit）；**新 ISA 后端为 21/16 bit**（36 号 §4.5.1） |

> **新 ISA 相关的参数**（槽数 / 编码宽度 / `D_mem` / `L_w` / 显式-隐式提示）**不在本文范围**——它们是 ISA 设计决策，见 [36 号](./36-new-isa-dependence-layer-design.md) §7 的 **Q-2..Q-6（均已裁决）**。


## 附录 A：符号表

| 符号 | 含义 |
|------|------|
| `L1/L2/L3/L4` | 依赖层 / 资源层 / 内存序层 / 控制层 |
| `stall_cnt` | per-warp 定长 RAW/WAW 等待计数（4 bit） |
| `SB[0..5]` | per-warp 依赖槽（6 bit each）：可变延迟 RAW/WAW + WAR |
| `wait_mask` | per-instruction：等哪些 SB 归零（6 bit） |
| `WAR 槽` | 读者递增、**读完源时递减**的计数器 |
| `DEPBAR.LE` | NVIDIA：部分等待依赖槽的指令 |
| `vmcnt/vscnt/lgkmcnt/expcnt` | AMD：load/store/LDS/export 计数器 |
| `TLB` | AMD：处理 ALU 数据冒险的硬件 scoreboard |
| `warp_ready` | §5.1 的放行判据 |

---

## 附录 B：证据索引

| 主张 | 证据 |
|------|------|
| **硬件不检查 RAW，靠编译器 Stall counter；设错 ⇒ 程序结果错误** | arXiv:2503.20481 §4 原文 |
| **依赖计数器每 warp 6 个（6 bit，上限 63）；每指令 2 个 3-bit id + 6-bit mask** | 同上 §4 |
| **递增发生在发射的下一拍 ⇒ 相邻指令需 stall ≥ 2** | 同上 §4 原文 |
| **WAR：计数器在读完源时递减（而非写回时）** | 同上 §4 原文 |
| **WAR 早释放的价值：读者取走源可比写回早数百拍** | 同上 §4 原文 + Figure 2 例子 |
| **控制位 vs scoreboard：41 bit/warp (0.09%) vs 5.32% RF；0.97× 更慢；MAPE 13.98% vs 14.87%** | 同上 §7.5 |
| **scoreboard 需两块（WAW/RAW + WAR）；332 entries/warp** | 同上 §7.5 |
| **AMD：ALU 冒险无需软件介入；RDNA3/3.5 引入 DELAY_ALU；普通指令不能用控制位等计数器** | 同上 §4（引 AMD ISA 文档） |
| **AMD：每 wavefront 3–4 个专用计数器 + 显式 waitcnt** | 同上 §4 |
| **issue 阶段不检查 RF 读端口；端口检查在 Allocate** | 同上 §5.1.1 |
| **内存延迟（WAR vs RAW/WAW）：LDG.32 regular 11 / 32；LDS.32 regular 9 / 24；STG.32 regular 14** | 同上 Table 2 |
| **SASS 固定延迟分档（Volta 4/5/6/8/10/14；Pascal 6/8/12/14）** | arXiv:1804.06826 Table 4.1 |
| **Volta 控制位字段宽度**（reuse 4b / wait barrier mask 6b / read barrier idx 3b / write barrier idx 3b / yield 1b / stall 4b） | arXiv:1804.06826 §控制位 |
| **学术口径：scoreboard 与 OC 互不引用** | [`gpgpu-sim_操作数收集器实现剖析`](../research/SM/CudaCore/gpgpu-sim_操作数收集器实现剖析.md) |
| **数据冒险与端口争用必须分层（C2）** | [`SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) §7 |
| **CppTLM 现状（无 WAR/WAW；`enqueue()` 无调用点；`CtrlBits` 4 B）** | CppTLM 源码实测（`hazard_tracker.hh` / `writeback.hh` / `instruction_descriptor.hh`） |

---

*本方案基于 2026-10-28 对 [`33-sm-operand-supply-design-target.md`](./33-sm-operand-supply-design-target.md) v0.5 §5 的展开，配套上游调研见 [`docs/research/SM/CudaCore/`](../research/SM/CudaCore/overview.md)。**非 NVIDIA 官方设计；未经验证；未经 Oracle/ADR 评审**。所有引号内英文为逐字引用。*
