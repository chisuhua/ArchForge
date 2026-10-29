# ADR-SOC-26: 自研 GPGPU ISA 为本仓唯一 ISA（取代 CDNA 路线）

> **状态**: 📋 Proposed（**待签批**；签批后方可作为 40 号规范骨架的冻结前置，见 37 号 C-1 / C-7）
> **日期**: 2026-10-29
> **Owner**: ArchForge Team
> **影响**: dGPU SoC v1.0 GPU 算力侧的 ISA 路线；取代 ADR-SOC-15 的 Phase C
> **类别**: ISA 战略 / 取代决策
> **实施**: OpenSpec change（待建）—— B-0..B-5（per [`39-new-isa-compiler-backend.md`](../architecture/39-new-isa-compiler-backend.md) §7）
> **关联**: [`37-new-isa-design-charter.md`](../architecture/37-new-isa-design-charter.md)（Q-8 裁决总纲）· [`40-new-isa-spec-skeleton.md`](../architecture/40-new-isa-spec-skeleton.md)（B-0 规范骨架）· [`ADR-SOC-15`](./ADR-SOC-15-cdna-real-isa-roadmap.md)（Phase C 被本 ADR 取代）· [`ADR-SOC-16`](./ADR-SOC-16-sm-microarchitecture.md)（接缝处置）
> **父决策**: 无（本 ADR 是 ADR-SOC-27..31 的父）
> **取代**: ADR-SOC-15 **Phase C**（CDNA 引擎接入）；**不取代** ADR-SOC-15 的阶段 A（`InstrDescriptor` 契约中立化）/ 阶段 B（内存 Seam）

---

## 1. 背景

本仓此前的 ISA 路线是「**以 CDNA3 真实物理 ISA 为演进目标**」：ADR-SOC-15 分四阶段推进，Phase C 接入 CDNA 引擎，随后用 12 号校准基线与 NVIDIA/AMD 实测对齐。

推进过程中出现三个**不可绕开的事实**，使「对标 CDNA」这条路线的前提不再成立：

| # | 事实 | 出处 |
|---|------|------|
| **F-1** | **OSF 的带宽缺口在 `W = 2` 下是真实的**：3 源流 IPC = 0.667；而用硬件 scoreboard 兜底依赖追踪的代价是 **5.32% RF** | 33 号 §5.2.2 / 34 号 §3 |
| **F-2** | **依赖管理的"正确性由谁保证"在现有 ISA 上是模糊的**：CDNA 的 `s_waitcnt` + 类型化硬件计数器要求编译器与硬件**互相猜时序模型**；而把 `D_c` / `L_w` 变成架构可查表后，依赖成为**编译期可算、可机械检查**的不变式 | 36 号 §3.2 / §4.1 |
| **F-3** | **仿真宿主无法忠实复现 CDNA 的隐藏时序** ⇒「与 CDNA 校准」这件事本身**不可验收** | 35 号 §8（CppTLM 现状：`enqueue()` 无调用点、`HazardTracker` 只有 RAW + vmcnt） |

⇒ **结论**：继续走 CDNA 路线意味着**同时承担 F-1 的面积代价、F-2 的正确性模糊、以及 F-3 的不可验收**。这三条**都不是实现力度问题，而是路线选择问题**。

## 2. 决策

### D1 —— 唯一 ISA

**自研 GPGPU ISA 是本仓 GPGPU 的唯一 ISA。** 实现目标只有它一个。

### D2 —— 参考 ISA 降级

PTX / CDNA3 / SASS **降级为研究与参考**，用途限定为三项：**行为基线**（结果正确性对照）、**延迟分档**（架构延迟常量来源）、**先例**（机制参考）。**不作为实现目标**，其编码与机制**不被复制**。

### D3 —— 取代 ADR-SOC-15 Phase C

ADR-SOC-15 的 **Phase C（CDNA 引擎接入）被本 ADR 取代**。
**保留**：阶段 A（`InstrDescriptor` 契约中立化 —— 它是 timing 宿主的前置，与 ISA 无关）、阶段 B（内存 Seam —— 同上）。

### D4 —— ADR-SOC-16 的接缝处置

ADR-SOC-16（SM 微架构重构，✅ Accepted）的启动前提写明「CDNA Real ISA 集成（ADR-SOC-15）启动后」，且其 12 子模块含 `MatrixCore = CDNA MFMA 子集（per 13 号）` ⇒ **Q-8 动摇了它的前提与一个子模块的内容来源**。处置原则：

| 部分 | 处置 |
|---|---|
| **12 子模块的 timing 宿主结构**（Fetch/Decode/Issue/ScalarALU/VectorALU/SIMTLane/LsuGlobal/LsuLDS/RegFileUnit/WritebackUnit/HazardTracker + 8 Bundle + `IComputeDevice` 15 方法） | ✅ **保留**（ISA 中立） |
| **CDNA 特定内容**（MFMA 子集、CDNA 延迟类、CDNA 指令编码） | ⚠️ **降级为参考实现**，随新 ISA 前端替换 |

### D5 —— 既有文档的连带处置

| 文档 | 处置 |
|---|---|
| [`13-cdna-emu-selector.md`](../architecture/13-cdna-emu-selector.md) | **作废**（选型对象不存在了） |
| [`11-cdna-real-isa-integration.md`](../architecture/11-cdna-real-isa-integration.md) | **范式保留、收敛为单一前端**（`isa_type` 多值 → 单值 + 回放模式） |
| [`12-cdna-calibration-baseline.md`](../architecture/12-cdna-calibration-baseline.md) | **方法论保留**，**对标对象**由 CDNA 改为 NVIDIA/AMD 实测延迟表 |
| ADR-SOC-13 | **不涉及**（它是 AXI Stream Adapter / AXI4Mapper，与 CDNA-EMU 无关；被作废的是架构文档 13 号） |
| **ADR-SOC-09**（双 vendor 战略） | ⚠️ **语义降级**：从「支持双 vendor ISA」改为「**双 vendor 实测数据作行为基线**」（SoC 硬件建模目标不变）；其 **L6 的 CDNA 内核路径随 ADR-SOC-15 Phase C 一并取代** |
| **33 号 §8.2**（落地路径 P1/P2/P3） | **术语调整**：「Ampere 口径基线」→「**行为基线（新 ISA）**」；V13 的 WAR 计数器条款已加〔仅 NV 建模后端〕限定 |

### D6 —— 决策的边界

本 ADR **只决定"走哪条 ISA 路线"**。D2–D5 是该路线的**代偿义务**（参考 ISA 降级 / 取代 / 接缝 / 连带处置），不构成独立决策点。具体的依赖层机制、双域结构、编码格式、执行模型分别由 **ADR-SOC-27..31** 决定，**不得**在本 ADR 内展开。

### D7 —— 签批顺序（**消除表面循环**）

```
ADR-SOC-26 签批  ──►  ADR-SOC-27..31 签批  ──►  B-0 落地 40 号  ──►  40 号冻结
     │                      │                      │
     └─ 解除 40 §0.2 前置④     └─ B-0 门禁 = 本 ADR 签批   └─ 需 40 §0.2 全部满足
```
⇒ **40 号 §0.2 的冻结前置第 4 项只要求 ADR-SOC-26 签发**；27..31 的签批是**40 号 B-0 阶段的门禁**，不与 40 号的冻结构成循环。

## 3. 选项对比

| # | 选项 | 结论 | 理由 |
|---|------|:----:|------|
| **1** | **继续 CDNA 路线**（ADR-SOC-15 全量执行） | ❌ 否决 | 承担 F-1（5.32% RF scoreboard）+ F-2（时序互相猜）+ F-3（校准不可验收）三条；且 CDNA **无 operand reuse cache**（四份手册全文检索仅 1 处命中）⇒ OSF 的核心资产无处安放 |
| **2** | **多前端并存**（CDNA + 新 ISA 并行） | ❌ 否决 | 依赖控制位布局、延迟类、指令编码**三套并存** ⇒ 仿真宿主要同时维护三套时序模型；ADR-SOC-15 阶段 A 的「契约中立化」正是为多前端付出的一致性成本，本仓规模承受不起。**量化**：三套并存意味着依赖控制位有 **26 / 21 / 16 bit 三种宽度**、延迟类有 **NVIDIA 41 bit + CDNA 4 计数器 + 新 ISA 21 bit 三套语义**，而 `InstrDescriptor` 只有 **128 字节**且 `CtrlBits` 仅 4 字节 ⇒ 三套控制位无法在同一描述符中共存 |
| **3** | **NVIDIA 路线**（照搬 SASS 语义 + 自研 ISA） | ❌ 否决 | 语义基线最完整，但 NVIDIA 机制**正确性全押编译器**（stall counter 设错 ⇒ 程序结果错误），且无 `D-1` 这类可机械检查的不变式；本仓要的是**不变式 + 架构保证**，不是照搬 |
| **4** | **自研 ISA 为唯一 ISA，参考 ISA 仅作研究**（**本 ADR**） | ✅ **采纳** | 唯一能同时满足三条事实的选项：面积可控（依赖层 0.121% RF）、正确性可静态检查（不变式 + A-1/A-2 架构保证）、**验收标准自洽**（对标"功能正确 + 延迟表一致"，而非"逐周期复刻 CDNA"） |
| **5** | 暂不决策，继续做 CDNA 校准再定 | ❌ 否决 | 校准本身**不可验收**（F-3）⇒ 继续投入不产生决策所需的证据 |

## 4. 后果

### 4.1 正面

- **验收标准自洽**：不再以"逐周期复刻他人硬件"为验收依据，改为「**功能等价 + 架构延迟表一致**」，这在仿真宿主上**可判定**；
- **依赖层面积可控**：0.121% RF（53 bit/warp），相对学术全 scoreboard（5.32%）是 **1/44**；
- **正确性责任可分配**：A-1/A-2 把"值身份"交回硬件（tag 校验），只把"时序"留给编译器 ⇒ **编译器提示错降级为性能问题**；
- **OSF 有了落地载体**：操作数供给层（MCOS 槽 + 复用提示）是新 ISA 的**自有资产**，而非 NVIDIA 机制的复刻。

### 4.2 负面

- **生态成本最高**：拿不到 CUDA 生态现成的前端与库（39 号结论：PTX-EMU 的子集是"解释器需要什么"，**不能直接当编译器前端**，G-1/G-2/G-3 三个致命缺口）；
- **失去 NVIDIA/AMD 的"现成正确答案"**：延迟类、`L_w`、`D_c` 全须自测（AMD 不公开 SALU 吞吐与 SMEM 延迟）；
- **连带文档修订面大**：ADR-SOC-15 状态、11/12/13 号文档、ADR-SOC-16 接缝均须同步；
- **编译器是 ISA 的一部分**，不是配套工具 ⇒ **ISA 规范冻结必须等编译器骨架可运行**（B-3 是正确性论证的闭合点）。

### 4.3 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| **编译器始终做不出来** ⇒ ISA 的正确性论证无法闭合 | 高 | B-2 先做汇编器 + A-1/A-4（可独立于 LLVM）；B-3 是硬门禁 |
| v2 特性（矩阵类 / 多谓词 / 标量 MCOS）撑破 v1 编码 | 中 | 40 号 §3.5 `EXT` 扩展机制 + §8 **T-10**（v2 启动前必须裁决 `fmt` 是否还留得住） |
| **标量域延迟参数无来源**（AMD 不公开） | 中 | 40 号 T-1（B-2 前必须自测）；`L_w` 固定声明 4（S-DEP-0），不依赖实测 |
| 生态缺口导致上层应用无法迁移 | 中 | 39 号 §3 的三层分工：LLVM IR 前端保住 Clang/Triton 生态，PTX 兼容前端作为可选第二入口（B-2） |

## 5. 实施

| 阶段 | 内容 | 产出 | 门禁 |
|---|---|---|---|
| **B-0** | ISA 规范冻结（架构状态 / 编码 / 依赖层契约） | [`40-new-isa-spec-skeleton.md`](../architecture/40-new-isa-spec-skeleton.md) | 本 ADR 签批 + ADR-SOC-27..31 签批 |
| **B-1** | ISA 模拟器骨架 + PTX-EMU 差分框架 | 差分测试流水线 | 首个 PTX 用例端到端通过 |
| **B-2** | 汇编器 + A-1（延迟填充）+ A-4（late-addr 判定） | 能产出正确 `stall` 的汇编器 | 单指令级差分 100% 通过 |
| **B-3** | A-2（槽分配） | 依赖槽 id + mask | 多指令序列差分通过（**正确性论证闭合点**） |
| **B-4** | A-3（复用/宽度提示）+ MCOS 硬件模型 | OSF 可建模 | IPC 模型与 34 号预测吻合 |
| **B-5** | fork LLVM AMDGPU target（路线 c，**需先做 B-6 对照**） | 自有 LLVM 后端 | Clang/Triton 端到端可跑 |

## 6. Verification（**前瞻判据，尚未验证**）

> 以下为**实施期必须逐条验证**的目标。**当前全部为待验证（pending）** —— 任何 `[x]` 都是过度承诺。
>
> **判据归属**：**[本仓]** = 本仓（ArchForge，纯文档）即可关闭；**[CppTLM]** = 涉及模拟器 / 汇编器 / 差分测试 / 微基准，**在 CppTLM 仓执行**，本仓只登记关闭证据。
> 本 ADR 的划分：**本仓** = V1、V2、V3、V4、V5、V6、V7a、V7b；**CppTLM** = V7、V8。

- [ ] **V1**〔本仓〕：**本 ADR 已签批**，且 ADR-SOC-27..31 已签批 — 验证手段：ADR-INDEX 状态更新为 ✅ Accepted；责任人：架构评审
- [ ] **V2**〔本仓〕：**ADR-SOC-15 已记录 Phase C 被取代**（阶段 A/B 保留）— 验证手段：**语义判据** = ADR-SOC-15 的 Status Update 中出现「Phase C 被 ADR-SOC-26 取代」且明确列出保留的阶段 A/B；责任人：架构评审
- [ ] **V3**〔本仓〕：**11 / 12 / 13 号文档的连带处置已执行** — 验证手段：**语义判据** = 13 号头部出现「作废」；11 号正文不再以 CDNA 为前端实现路径；12 号的对标对象表述已改为 NVIDIA/AMD 实测延迟表；责任人：文档 owner
- [ ] **V4**〔本仓〕：**ADR-SOC-16 接缝已处置** — 验证手段：**语义判据** = ADR-SOC-16 的 Status Update 同时写明「12 子模块保留」与「CDNA 特定内容降级为参考实现」；责任人：架构评审
- [ ] **V5**〔本仓〕：**不存在第二条 ISA 实现路径** — 验证手段：全仓 `grep -rn "isa_type" docs/architecture/` 只余「新 ISA 前端 + 回放模式」两类取值；责任人：build
- [ ] **V6**〔本仓〕：**参考 ISA 的使用边界被遵守**（只作行为基线 / 延迟分档 / 先例，不复制编码）— 验证手段：40 号规范正文中**无** PTX/CDNA/SASS 的编码字段；责任人：verifier
- [ ] **V7a**〔本仓〕：**ADR-SOC-09 已按 D5 降级** — 验证手段：ADR-SOC-09 的 Status Update 记录「语义降级为双 vendor 实测数据作行为基线」且 L6 的 CDNA 内核路径标注被本 ADR 取代；责任人：架构评审
- [ ] **V7b**〔本仓〕：**33 号 §8.2 术语已调整** — 验证手段：`grep -n "Ampere 口径基线" docs/architecture/33-*.md` 无命中；责任人：文档 owner
- [ ] **V7**〔CppTLM〕：**B-3 通过**（依赖正确性论证闭合）— 验证手段：多指令序列差分测试全绿；责任人：verifier
- [ ] **V8**〔CppTLM〕：**B-6 对照完成**（fork AMDGPU vs 新 target + 移植 4 pass 的工作量对照）— 验证手段：39 号 §8 B-6 从开放项转为已裁决；责任人：工具链 owner

**整体通过条件**：V1..V8 全部 `[x]`，且 B-0..B-3 已完成（B-4/B-5 可延后）。

## 7. 参考

- [`37-new-isa-design-charter.md`](../architecture/37-new-isa-design-charter.md)（Q-8 取代关系的裁决总纲、§5 连锁后果清单）
- [`40-new-isa-spec-skeleton.md`](../architecture/40-new-isa-spec-skeleton.md)（B-0 规范骨架）
- [`36-new-isa-dependence-layer-design.md`](../architecture/36-new-isa-dependence-layer-design.md)（依赖层：F-1/F-2 的证据）
- [`33-sm-operand-supply-design-target.md`](../architecture/33-sm-operand-supply-design-target.md) §5.2.2（scoreboard 5.32% RF 实测口径）
- [`35-sm-dependence-management-architecture.md`](../architecture/35-sm-dependence-management-architecture.md) §8（CppTLM 现状：F-3）
- [`ADR-SOC-15-cdna-real-isa-roadmap.md`](./ADR-SOC-15-cdna-real-isa-roadmap.md)（被本 ADR 取代 Phase C）
- [`ADR-SOC-16-sm-microarchitecture.md`](./ADR-SOC-16-sm-microarchitecture.md)（接缝处置对象）

---

## Status Update

（暂无更新）
