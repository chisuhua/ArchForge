# 新 ISA 编译器后端方案：以 PTX-EMU 子集为约束的 PTX → 自研 ISA

> **版本**: v1.1 DRAFT — 2026-10-28（**v1.1 = 回应 Oracle 评审**：§5 "fork 是最短路径"**降级为假设** + 新增开放项 B-6（fork 与"新 target + 移植 4 pass"的工作量对照）；§6 元数据表与控制块宽度同步（36 号 Q-10/Q-11：向量 21 / 标量 16 bit，**取消 WAR 槽 id**）；§3.1 补"内存序与谓词的 golden 不走 PTX-EMU"）
> **状态**: 🟡 **设计方案**（**非当前实现**；未经 Oracle/ADR 评审；**开放项需评审裁决**）
> **Owner**: CppTLM Team
> **文档分类**: 第 1 层 · 编译器后端方案
> **关联裁决**: [`37-new-isa-design-charter.md`](./37-new-isa-design-charter.md)（Q-8 取代关系；§4「编译器硬依赖」）/ [`36-new-isa-dependence-layer-design.md`](./36-new-isa-dependence-layer-design.md)（依赖层规范）
> **上游依据**:
> - **PTX-EMU 项目**（`/workspace/main/PTX-EMU/`）：语法（`src/grammar/ptx*.g4`）、IR（`include/ptx_ir/ptx_op.def`）、执行器（`src/ptxsim/instructions/*.cpp`）——**一手源码核查**
> - **PTX ISA 9.4 规范** / **NVVM IR 13.4 规范**（NVIDIA 公开）
> - **LLVM AMDGPU 后端源码**（`SIRegisterInfo.td` / `SIInstrInfo.cpp` / `SIFixSGPRCopies.cpp` / `SIInsertWaitcnts.cpp` / `GCNRegBankReassign.cpp` / `AMDGPUTargetMachine.cpp`）
> - GPUOCelot（PTX 动态编译框架，已停维）、GPGPU-Sim `src/cuda-sim/ptx.y`（PTX 前端参考）、MGPUSim（GCN3 专用，**不消费 PTX**）
> **规范落地**: 编译器必须产出的元数据已在 [`40-new-isa-spec-skeleton.md`](./40-new-isa-spec-skeleton.md) §4 定稿（控制块 21/16 bit 逐字段）。
> **关联 OpenSpec changes**: 无
> **定位说明**:
> - **本文是 [`37-…`](./37-new-isa-design-charter.md) §4「编译器硬依赖」的具体化**，也是 §7 的 **C-3** 待办。
> - **ISA 侧的标量/向量双域结构**见 [`38-new-isa-dual-domain-structure.md`](./38-new-isa-dual-domain-structure.md)；**依赖层规范**见 36 号。

---

## 0. TL;DR

> **结论**：**PTX-EMU 支持的 PTX 子集不能直接当编译器前端** —— 它是"**解释器需要什么**"，不是"**编译器需要什么**"，有 **10 个硬缺口**（最致命的：**ALU 不可谓词化**、`shfl/vote` **连语法都过不了**）。
> **推荐路线**：**编译器前端用 LLVM IR**（拿到 Clang / Triton 生态 + 谓词 + 向量 + shuffle 全套能力）；**PTX-EMU 转为"功能黄金模型"（golden model）**，用差分测试验证新 ISA 的功能等价。**PTX 兼容前端作为独立的第二入口**，按需再加。

| # | 结论 | 章节 |
|---|------|------|
| **①** | **PTX-EMU 子集的 10 个硬缺口**（其中 3 个会让编译器**根本无法生成**合法代码） | §1.2 |
| **②** | **三条路线对比**：PTX 直译 / LLVM 前端 + 自研后端 / fork AMDGPU target | §2 |
| **③** | **推荐分层**：LLVM IR 前端（编译器）+ PTX-EMU（golden model）+ PTX 兼容前端（可选第二入口） | §3 |
| **④** | **LLVM AMDGPU 后端已有 6 个 pass 直接对应我们的依赖层需求**（可直接借鉴，不必从零写） | §5 |
| **⑤** | **编译器必须产出的元数据 = 36 号 §4.5.1 控制块全表**（**向量 21 bit / 标量 16 bit**，含 `budget`，不限于 E-1..E-4）——这就是"编译器硬依赖"的精确形式 | §6 |

---

## 1. 硬约束：PTX-EMU 实际支持的 PTX 子集

### 1.1 解码器的四层结构（**必须区分，否则会高估能力**）

| 层 | 位置 | 数量 | 含义 |
|---|------|------|------|
| **L1** 词法 token | `src/grammar/ptxLexer.g4:294-385` | **94** | 能被切成 token 的助记符 |
| **L2** 语法规则 | `src/grammar/ptxInstructions.g4` | **63** | 有文法规则 |
| **L3** IR statement type | `include/ptx_ir/ptx_op.def` | **106** | 有 X-macro 条目（真正进 IR） |
| **L4** **真实 handler** | `src/ptxsim/instructions/*.cpp` | **47** | **真的被执行** |

> **⇒ 只有 L4 的 47 条是可信的功能基线。**

### 1.2 十个硬缺口（**按对编译器的影响排序**）

| # | 缺口 | 事实 | 对编译器的影响 |
|---|------|------|--------------|
| **G-1** | **ALU 不可谓词化** | `predicate?` 只出现在 `bra/brx/call/ret/exit/trap/brk/brkpt/bar`（`ptxInstructions.g4:51-89,315`）；**算术/访存指令的文法里没有 `@%p` 前缀** | 🔴 **`@%p add.s32` 是 ANTLR 解析错误** ⇒ 编译器**无法生成任何谓词 ALU** ⇒ 必须把谓词降成分支（性能灾难）或**扩展 PTX-EMU 子集** |
| **G-2** | **warp shuffle / vote 连语法都过不了** | token 是裸 `shfl`/`vote`，文法 `shflInst: SHFL shuffleMode PRED?`（`:366`）中间**没有 DOT** ⇒ `shfl.sync.down.b32` 解析失败 | 🔴 编译器**无法生成任何 warp 内数据搬移** ⇒ 归约 / 转置 / 蝶形交换类 kernel 不可编译 |
| **G-3** | **`.v2/.v4` 的 ALU 语义未定义** | 只有 `ld/st/mov` 有 v2/v4 路径（`memory.cpp:26-72,95-137`）；ALU 的 `vectorSpec?` 文法允许，但 handler 一律按标量处理（`getBytes` 只看类型不看 v2/v4） | 🔴 编译器**不能生成向量 ALU**（语义错） |
| **G-4** | **`.sat` 在 `add/sub` 被忽略；`.ftz` 全库未实现；舍入只在 `cvt`** | `arithmetic.cpp:394-432` 只查 `Q_CC`；`Q_FTZ` 只在 cvt 出现 | 🟡 编译器不能依赖这些修饰符的语义（要么避开，要么扩展） |
| **G-5** | **特殊寄存器只有 9 个** | 只有 `%tid/%ctaid/%ntid/%nctaid` 的 `.x/.y/.z`（`register_access_layer.cpp:18-41`）；`%laneid`/`%clock`/`%clock64`/`%lanemask_*`/`%pm0-7`/`%sp` **抛异常** | 🟡 编译器不能生成依赖 laneid / clock / lanemask 的代码 |
| **G-6** | **无内存序模型** | `.volatile/.relaxed/.acquire/.release/.acq_rel/.strong` 与 `.cta/.gpu/.gl/.sys/.cluster` 只进 qualifier 列表，**无语义**；`membar`/`fence` 是 no-op（`instruction_handlers.cpp:128-151` 明说 "no-op in single-threaded SC model"） | 🟡 编译器不能依赖内存序；但**我们的新 ISA 需要内存序**（36 号 E-11）⇒ golden model 在这块**不可信** |
| **G-7** | **无 `%ur` 统一寄存器、无 `.b1`、无 `.f16x2`、`.b128` 宽度退化为 4B** | `ptx_op.def` / `typeSpecifier` 无这些；`Q2bytes` 只含 1/2/4/8（`qualifier_utils.cpp:14-47`） | 🟡 编译器不能生成打包类型 / 位谓词 |
| **G-8** | **`call` 只有 printf 生效** | `call.cpp:40-45` 仅特判 `printf/vprintf/_printf`；普通 `call` 静默无动作；`call.uni` 语法有但无 IR 条目 | 🟡 编译器不能生成函数调用 |
| **G-9** | **`cp.async` / video-SIMD 9 条 / `madc` 被静默丢弃** | `ptx_visitor.cpp:538` 的 `VISITOR_IMPL_CP_ASYNC_INSTR` 为空；`videoSimdInst` 无任何 `S_*` | 🟡 编译器不能生成这些 |
| **G-10** | **`wmma.*` 已移除；`tcgen05.*` 多数子指令抛 `UnsupportedInstructionException`** | `src/ptxsim/instructions/AGENTS.md:48`；`tcgen05.cpp:363,369,…` 共 12 处抛出 | 🟡 矩阵路径几乎不可用 |

### 1.3 可直接依赖的「安全子集」（**编译器白名单**）

| 类别 | 指令 | 附注 |
|------|------|------|
| 整数 ALU | `add sub mul mad fma min max neg abs div rem`（32/64-bit 整型） | `addc/subc` 仅 `.cc` 侧完整 |
| 位运算 | `and or xor not shl shr bfe popc clz` | ⚠ **不要用 `shf` / `lop3`**（空实现） |
| 比较/选择 | `setp` + `selp` | ⚠ **不要用 `set` / `slct` / `cnot`** |
| 转换 | `cvt`（含 `.sat` + 5 种舍入）、`mov` | `cvta` **仅指针拷贝**，空间转换未实现 |
| 访存 | `ld` / `st` 标量与 `.v2/.v4`（GLOBAL/SHARED/LOCAL/CONST/PARAM） | `.v2/.v4` **仅 ld/st/mov** 有效 |
| 原子 | `atom`（9 op + cas） | ⚠ 有符号 `min/max` 语义**错**（用 `uint64_t` 比较，`atomic.cpp:135-140`） |
| 控制流 | `bra`（可带 `@%p`）+ `ret` + `bar.sync` + `bar.warp.sync` + `activemask` | ⚠ **不要生成 `call`（除 printf）、不要生成 ALU 谓词、不要生成 `shfl`/`vote`** |
| 类型 | `.u8/.u16/.u32/.u64/.s8/.s16/.s32/.s64/.f16/.f32/.f64/.bf16/.b8/.b16/.b32/.b64/.pred` | 向量仅 `.v2/.v4` 且**只用于 ld/st/mov** |

### 1.4 执行模型（golden model 的语义基准）

| 项 | 值 | 出处 |
|---|-----|------|
| 层次 | `GPUContext → SMContext → CTAContext → WarpContext(32 lanes) → ThreadContext` | `README.md:25` |
| warp 宽度 | **32** | `include/ptxsim/warp_context.h:53` |
| 执行粒度 | warp 调度、**逐 lane 串行执行**同一条指令 | `warp_context_dispatch.cpp:22-120` |
| PC | **per-thread PC**（`WarpState::threads[i].pc`） | 同上 |
| 发散 | `bra` 用 taken/not_taken mask 压 SIMT 栈；汇合点由 **CFG post-dominator** 计算 | `warp_context.cpp:15-54` / `cfg_builder.cpp` |
| 寄存器 | per-(warp,lane) 字节数组；谓词 = per-lane 1 字节（**非位掩码**） | `register_bank_manager.cpp:21` |
| 内存 | global = 宿主指针直当 GPU 地址；shared = CTA 级；local = per-thread | `memory_interface.h` |
| 原子 | 全局 `AtomicMutex` 串行化（**非真硬件原子**） | `atomic.cpp` |

> ⚠ **⇒ 黄金模型的三个已知偏差**（差分测试必须排除）：
> 1. **原子用互斥锁串行** ⇒ 无原子性/顺序性语义 ⇒ **内存序测试不可信**（G-6）。
> 2. **逐 lane 串行** ⇒ 无 SIMT 硬件的锁步/掩码语义 ⇒ **发散与谓词的等价性可测，时序不可测**。
> 3. **`.b1` 是 1 字节非位** ⇒ 位谓词压缩相关测试不可信（G-7）。

---

## 2. 三条路线比较

### 2.1 现实核查：**谁真的吃 PTX？**

| 项目 | 定位 | 是否可用作本项目的前端 |
|------|------|---------------------|
| **GPUOCelot** | 仓库自述「A dynamic compilation framework for PTX」⇒ PTX → LLVM IR → JIT 到 x86/GPU | **唯一被广泛引用的 PTX→异构 ISA 先例**，但**已停维十余年** |
| **GPGPU-Sim** `src/cuda-sim/` | 完整 PTX 词法/语法/IR + **解释执行**（`ptx.l`/`ptx.y`/`ptx_ir.cc`） | **"PTX 前端长什么样"的最好教材**，但**不做代码生成** |
| **MGPUSim** | README：「It models GPUs that run the AMD GCN3 instruction sets」「only AMD GCN3-based GPU simulation is stable」 | ❌ **不消费 PTX**（走 GCN3 汇编） |
| **gem5 AMDGPU** | GCN3 / ISA 级 | ❌ 同上 |
| **NVIDIA 的 `libnvvm`** | 官方 API 公开，但**二进制分发、无源码**；作用是 `NVVM IR → PTX`（「The linked IR program is compiled to PTX.」） | ❌ **帮不了你离开 NVIDIA** |
| **`ptxas`** | **闭源、无规范、无源码** | ❌ 不可用 |

> ⚠ **纠正一个常见说法**：「NVVM 是开源的」**不准确**。开源的是 LLVM 的 **NVPTX 后端**（LLVM IR → PTX，**方向相反**）与 Clang 的 CUDA 前端；**NVVM IR 只是"公开规范的 LLVM IR 方言"**，其实现（libnvvm）闭源。
> ⇒ **PTX ISA 9.4 规范是公开的**（可自行实现 PTX 解析器），**NVVM IR 13.4 规范也是公开的**（LLVM bitcode 子集，`llvm-dis` 可读）。

### 2.2 三条路线

| 路线 | 做法 | 优点 | 代价 | 适用 |
|------|------|------|------|------|
| **(a) PTX → 自研 ISA 直译** | 自写 PTX 解析 + SSA 构造 + 指令选择 + 调度 + 寄存器分配 | 完全可控；能直接吃 CUDA fatbin 里的 PTX | **要自建 SSA / RA / 调度 / legalization 全部**；PTX 每版新增指令（9.4 已含 tcgen05/wgmma）；**无上游测试集** | **仅当"必须跑现成 CUDA fatbin"**（ZLUDA 场景） |
| **(b) LLVM IR 前端 + 自研 LLVM 后端** | 用 Clang/LLVM 的 NVPTX 前端产出 LLVM IR/NVVM IR → 自研 TableGen target | 白拿 Clang / Triton / Julia / OpenMP offload；NVVM IR 就是 LLVM bitcode 子集；TableGen + MC + 调度框架齐全 | 要写完整 target（TargetMachine / TargetLowering / ISelLowering / InstrInfo / RegisterInfo / MC / ELF writer / kernel ABI），**人年量级** | ✅ **推荐默认** |
| **(c) fork / 扩展 AMDGPU target** | fork LLVM AMDGPU，替换指令集与寄存器模型 | CDNA 那套 SALU/VALU/EXEC/SCC/VMEM/waitcnt/MFMA **已实现**；`SIInsertWaitcnts` / `SIFixSGPRCopies` / `moveToVALU` / `GCNRegBankReassign` **都是现成参考实现**；Apache-2.0 with LLVM exceptions | 要拆掉大量 AMD 专有假设（HSA ELF、kernel descriptor、occupancy 模型、flat scratch、XNACK）；AMDGPU 是 LLVM 里**最复杂的 target 之一** | ✅ **若新 ISA 就是 CDNA-like（标量+向量分离、wave64、EXEC/SCC）⇒ 最短路径** |

### 2.3 推荐

> **⇒ (b) + (c) 组合**：
> - **从 (c) 起步**：fork AMDGPU target 的 **TableGen 描述 + 关键 pass**（`SIRegisterInfo.td` / `SIInstrFormats.td` / `SOPInstructions.td` / `VOP*Instructions.td` / `SIInstrInfo.cpp` 的 `copyPhysReg`+`moveToVALU` / `SIFixSGPRCopies.cpp` / `SIInsertWaitcnts.cpp` / `GCNRegBankReassign.cpp`）——**这些正是我们双域结构与依赖层需要的参考实现**。
> - **前端用 (b) 的 LLVM IR**：顺带拿到 Clang / Triton 生态。
> - **(a) 作为独立第二入口**（若将来要 CUDA fatbin 兼容），**不作为主编译器**。

> ⚠ **但本项目的特殊约束改变了优先级**：新 ISA 的**依赖层是编译器驱动的**（36 号）⇒ **编译器不是"配套工具"，而是 ISA 的一部分**。⇒ **必须先有可用的编译器骨架（方案 B 的 pass 集），才能验证 ISA 规范**（37 号 C-3）。

---

## 3. 推荐方案：三层分工

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ①  编译器前端（LLVM IR / NVVM IR）                                          │
│     Clang CUDA → NVVM IR (LLVM bitcode 子集)  →  自研后端                   │
│     ⚠ 本项目自有 ISA 的**前端契约**见 §6（编译器必须产出的元数据）             │
├────────────────────────────────────────────────────────────────────────────┤
│ ②  自研 LLVM 后端（fork AMDGPU 起步）                                       │
│     TableGen 描述（SOP*/VOP* 风格）+ 6 个关键 pass（§5）                    │
│     产出：新 ISA 的目标码 + **依赖控制块（向量 21 / 标量 16 bit，36 号 §4.5.1）** │
├────────────────────────────────────────────────────────────────────────────┤
│ ③  PTX-EMU（功能黄金模型 / golden model）                                    │
│     同一份 PTX → ① 产出新 ISA 码 → 本仓 SM 模拟器执行                      │
│                              ↘  PTX → ③ 逐 lane 解释执行                     │
│     ⇒ 差分测试：功能等价性（不是时序）                                       │
│     ⚠ 已知偏差见 §1.4（原子无序 / 逐 lane / 谓词非位）                       │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 PTX-EMU 作为 golden model 的三种用法

| 用法 | 做法 | 价值 |
|------|------|------|
| **G-a. 差分验证** | 同一 PTX：PTX-EMU 解释执行 vs 新 ISA 模拟器执行 → 比对寄存器/内存终态 | **功能等价性**（ISA 语义正确性） |
| **G-b. 覆盖率母本** | 用 PTX-EMU 的 handler 集合（47 条真实 + 10 个缺口）生成**ISA 规范的一致性测试向量** | 把"缺口"变成"待覆盖清单" |
| **G-c. 编译器正确性回归** | PTX-EMU 的执行结果作为**期望输出**，检查编译器后端产出的码在新 ISA 上是否等价 | **编译器正确性**（含谓词降级、槽分配、stall count 的正确性） |

> ⚠ **G-c 有两个致命限制**（**v1.1 补第二条**）：
> ① 由于 G-1（ALU 不可谓词化），**PTX-EMU 无法执行带谓词的 ALU** ⇒ 谓词相关路径**无法用 PTX-EMU 做 golden**；
> ② 由于 G-6（无内存序模型，`membar`/`fence` 是 no-op），**内存序不可用 PTX-EMU 做 golden** —— 而新 ISA 有 `mem.fence`（36 号 E-11）⇒ **这块写成错的也没有差分测试能抓到**。
> ⇒ **必须自建"谓词版 + 内存序版" golden**（或直接用 LLVM IR 层的解释器 / `ExecutionEngine`）。
> ⇒ **这直接支撑"编译器前端用 LLVM IR 而非 PTX"的建议**：LLVM IR 层有完整的谓词/向量/shuffle 语义可做 golden。
> ⚠ **⇒ 规范级后果**：新 ISA 的**内存序语义必须由自有测试套件验证**，不得声明"由 PTX-EMU 差分覆盖"（写进 40 号 §5）。

---

## 4. 若坚持用 PTX 作为前端：必须先补的扩展

| # | 缺口 | 需要的扩展 | 工作量 |
|---|------|-----------|-------|
| **1** | **G-1 ALU 谓词化** | 文法加 `predicate?` 到算术/访存规则；IR 加 predicated 标志；handler 实现掩码执行 | 🟡 中（文法 + IR + 执行三处） |
| **2** | **G-2 `shfl`/`vote` 语法** | token 与文法补 `.sync`（或文法接受裸 token） | 🟢 小 |
| **3** | **G-3 `.v2/.v4` ALU** | handler 按 vector 宽度逐元素执行 | 🟡 中 |
| **4** | **G-4 修饰符语义** | `.sat`/`.ftz`/舍入 在 ALU 上落地 | 🟡 中 |
| **5** | **G-5 特殊寄存器** | 至少补 `%laneid`（**warp 内语义必需**） | 🟢 小 |
| **6** | **G-6 内存序** | 需要真正的内存模型（**工作量大**） | 🔴 大 |
| **7** | **G-7 类型** | `%ur` / `.b1` / `.f16x2` / `.b128` | 🟡 中 |

> **⇒ 若走 PTX 前端路线，前 5 项是"必须先做"的阻塞项**，合计约 1–2 人月；第 6 项（内存序）是独立的大工程。
> **⇒ 这就是"编译器前端用 LLVM IR"的核心理由**：**LLVM IR 全部这些能力都是现成的**。

---

## 5. LLVM AMDGPU 后端中**可直接借鉴**的 6 个 pass

> 这些不是"参考"，是**我们要自己写的东西的现成实现**（新 ISA 的双域结构与依赖层都需要）。

| # | pass / 机制 | 解决我们的什么问题 | 出处 |
|---|-------------|-----------------|------|
| **P-1** | **`AMDGPUAnnotateUniformValues` + `UniformityAnalysis`** | **SALU 不可寻址 VGPR** ⇒ 编译器必须证明 uniform 才能留在标量域（38 号 X-D1 / §2.2） | `SIISelLowering.cpp:31`（`#include "llvm/Analysis/UniformityAnalysis.h"`）；`isUniformLoad` `:2533` |
| **P-2** | **`SIInstrInfo::moveToVALU()`** | 发散值回退到向量域 | `SIInstrInfo.cpp:8341` |
| **P-3** | **`SIFixSGPRCopies`** | **SGPR ← VGPR 非法**的合法化（38 号 X-D3） | `SIFixSGPRCopies.cpp:10`（注释原文） |
| **P-4** | **`legalizeOperandsSMRD`** | 标量共享内存地址落在 VGPR 时插 `v_readfirstlane` | `SIInstrInfo.cpp:7331` |
| **P-5** | **`GCNRegBankReassign`** | **寄存器 bank 冲突重分配**（33 号的 bank 布局是核心，编译器侧必须配套） | `GCNRegBankReassign.cpp`（gfx10+：VGPR 4 bank 轮转 / SGPR 8 bank 成对） |
| **P-6** | **`SIInsertWaitcnts`** | **内存序等待点的插入**（对应 36 号 E-10 `dep.wait` / E-11 `mem.fence`） | `llvm/lib/Target/AMDGPU/SIInsertWaitcnts.cpp` |

**另需参考**：`AMDGPUTargetMachine.cpp` 的 **pass 顺序**（pre-ISel：`AMDGPUUnifyDivergentExitNodes → FixIrreducible → UnifyLoopExits → StructurizeCFG → AnnotateUniformValues → SIAnnotateControlFlow` → ISel → `SIFixSGPRCopies → SILowerI1Copies → SIFoldOperands → SILoadStoreOptimizer → SIShrinkInstructions` → 后期 `SIInsertWaitcnts / SIOptimizeExecMasking`）。

> **⇒ 这 6 个 pass 恰好覆盖新 ISA 双域结构（38 号）在编译器侧的**结构类**需求。但**依赖管理层不在其中** —— 见下。

#### 5.1 迁移率核查：`SIInsertWaitcnts` 到底能搬多少（**v1.1 新增**）

> ⚠ **v1.0 写"fork 不是可选项，而是最短路径"。Oracle 评审指出该结论未做对照就下了** ⇒ **v1.1 降级为假设**，并给出核查：

| 维度 | AMD `SIInsertWaitcnts` | 新 ISA（36 号） | 可迁移性 |
|---|---|---|:---:|
| 等待机制 | `s_waitcnt` + **vmcnt/lgkmcnt/expcnt 三个类型化 FIFO 计数器** | **SB[8] 槽 + `wait_mask` 并集等待** | ❌ 语义不同 |
| 槽分配 | **不存在**（计数器按类型自动推进，无需着色） | **A-2 槽分配**是独立算法（依赖图 + 域政策） | ❌ 无对应物 |
| stall count | **不存在**（ALU 冒险由硬件兜底） | **A-1 延迟填充**是核心算法 | ❌ **LLVM 全仓无先例**（ptxas 闭源） |
| 精确计数 | 等待"计数 ≤ N"（精确值） | 等待"mask 指定槽全归零"（**并集，无数值**） | ❌ 语义更粗 |
| 遍历骨架 | 跨 BB 跟踪在飞访存、join 点合并求最小等待 | **同构** | ✅ **20–30%** |

> **⇒ 结论**：`SIInsertWaitcnts` 的可迁移部分是**遍历骨架**，**算法本体（计数器算术）不可移植**。同理 `GCNRegBankReassign` 针对 gfx10+ 的 4-bank/8-bank 模型，而 33 号的 2-bank 来自 **NVIDIA 实测口径** ⇒ 只能参照结构。
> **⇒ 于是 fork 的真实价值收窄为三件事**：① **TableGen 的 SOP/VOP 格式类与编码描述**；② 寄存器类 / 压力集 / MC / ELF 工具链基础设施；③ P-1..P-4 四个**结构类** pass（uniformity / moveToVALU / SGPR copy 修复 / SMEM 合法化）。
> **⇒ 而代价是实打实的**：AMDGPU 是 LLVM 最重的 target 之一，拆 HSA ELF / kernarg ABI / occupancy 模型 / XNACK / flat scratch 的成本可观。
> **⇒ 因此「新 target + 选择性移植 P-1..P-4」是必须认真对照的路线**（见 §8 开放项 **B-6**），**"最短路径"在对照完成前只是假设**。

---

## 6. 编译器必须产出的元数据（**= 36 号 E-1..E-4；"编译器硬依赖"的精确形式**）

| 字段 | 向量域 | 标量域 | 编译器如何计算 | 出错后果 |
|------|:---:|:---:|---|---|
| **stall count**（E-1） | 4 | 4 | `生产者延迟 − 生产者与首个消费者之间的指令数`（36 号 E-14 查询表提供延迟）；**并承担 late-addr 类的 WAR 保护**（36 号 Q-11） | 🔴 **程序结果错误** |
| **dep slot id + wait mask**（E-2） | 3 + 8 | 3 + 8 | 为可变延迟生产者分配槽；消费者填 mask（**mask 只覆盖 SB[8]**） | 🔴 读到陈旧值 / 假阻塞 |
| ~~WAR slot id~~ | **0** | **0** | **v1.1 删除**：36 号 Q-11 证明 WAR 可用 **gap 内** `stall` 表达（`d + Σ ≥ 8`，`D_mem − L_w,min = 7 ≤ 15`）⇒ **不需要专用槽、不需要编码位** | — |
| **reuse flags + budget hint**（E-3） | 3 + 2 | **0** | **哪些源操作数可复用** + **会被消费几次**（仅 VGPR/MCOS 语义） | 🟡 **仅性能**（36 号 A-1/A-2 兜底）✅ |
| **width hint**（E-3） | **0（opcode 变体）** | **0** | 由窄值算术的 **opcode 变体**承载（36 号 Q-10） | 🟡 仅性能 |
| **late-addr 标注**（36 号 Q-9） | **0（opcode 变体）** | — | 地址依赖能否在 `D_mem = 4` 内就绪 | 🟡 性能（地址链 kernel） |
| **yield**（E-4） | 1 | 1 | 建议调度器换 warp | 🟡 性能 |
| **合计** | **21** | **16** | 与 36 号 §4.5.1 / Q-10 一致 | — |

> ⚠ **v1.1 更正**：v1.0 的表沿用 36 号的 26 bit 口径（含 `WAR slot id 3` 与独立的 `late-addr 1`），且把 `width_hint` 当成控制位。**该表已作废** —— 现表与 36 号 v1.3 的 Q-10/Q-11 逐字段对齐。

**⇒ 编译器必须实现的算法（4 个）**：

| 算法 | 输入 | 输出 | 难度 |
|------|------|------|:----:|
| **A-1 延迟填充** | 指令序列 + E-14 查询表 | 每条指令的 stall count | 🟢 易 |
| **A-2 槽分配** | 依赖图 | SB 槽 id + wait mask（**无 WAR 槽**：36 号 Q-11 / 40 号 S-DEP-6） | 🟡 中（**域标记约束**：38 号 I-4） |
| **A-3 复用/宽度提示** | 数据流 + 复用分析 | reuse flags + budget hint + width hint | 🟡 中 |
| **A-4 late-addr 判定** | 地址依赖分析 | late-addr 位 | 🟢 易 |

> **⇒ 与 37 号 §4 的"方案 B（汇编器 + 依赖元数据 pass）"完全对应**：A-1..A-4 就是那个 pass 集的**最小内容**。
> **⇒ 且 A-2 是唯一有真正难度的**（依赖图着色 + 域约束 + 槽耗尽处理）。

---

## 7. 路线图与门禁（**37 号 C-3 的细化**）

| 阶段 | 内容 | 产出 | 门禁 |
|------|------|------|------|
| **B-0** | **ISA 规范冻结**：E-1..E-14 的编码布局 + E-14 查询表 + 38 号双域规则 | ISA 规范文档 | **阻塞后续全部** |
| **B-1** | **ISA 模拟器骨架**（可执行新 ISA 码）+ **PTX-EMU 差分框架**（G-a） | 差分测试流水线 | 首个 PTX 用例端到端通过 |
| **B-2** | **汇编器 + A-1/A-4 pass**（延迟填充 + late-addr） | 能产出正确 stall count 的汇编器 | **单指令级差分 100% 通过** |
| **B-3** | **A-2 槽分配 pass** | 依赖槽 id + mask | 多指令序列差分通过（**这是 36 号正确性论证的闭合点**） |
| **B-4** | **A-3 复用/宽度提示 pass** + **MCOS 硬件模型**（33 号） | OSF 可建模 | IPC 模型与 34 号预测吻合 |
| **B-5** | **fork AMDGPU target**（路线 c）→ 替换为自有指令集 | 自有 LLVM 后端 | Clang/Triton 端到端可跑 |

> **建议顺序**：**B-0 → B-1 → B-2 → B-3 →（并行）B-5 → B-4**。
> **B-3 是关键门禁**——它通过，36 号的"编译器驱动依赖层"才真正可信。
> **B-5 可延后**：B-1..B-4 用一个**手写汇编器**就够；LLVM 后端是"生态接入"，不是"正确性前提"。

---

## 8. 开放问题

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| **B-1** | **前端契约**：LLVM IR（NVVM IR）还是自建 IR？ | 决定 B-2..B-5 的工作量 | **LLVM IR**（拿生态 + 谓词/向量/shuffle 全套） |
| **B-2** | **PTX 兼容前端是否做**（路线 a） | CUDA fatbin 兼容性 | **v1 不做**；若做，作为**独立第二入口**，不污染主编译器 |
| **B-3** | **PTX-EMU 的扩展投入**（§4 的 7 项） | 是否扩 PTX-EMU 以补齐 golden model | **只补 G-2/G-5/G-7（低成本）**；G-1/G-3/G-6 改用 LLVM IR 层做 golden |
| **B-4** | **wave 宽度**：PTX-EMU 是 32，CDNA 是 64 | **语义映射**（最容易埋雷处） | **先定 32**（与 PTX-EMU 对齐，便于差分）；CDNA 的 64 留 v2 |
| **B-5** | **是否 fork LLVM**（许可 Apache-2.0 with LLVM exceptions） | 法务 + 维护 | fork 合法；若长期维护需评估上游同步成本 |
| **B-6** | **路线 (c) fork AMDGPU vs 「新 target + 移植 P-1..P-4」的工作量对照**（**v1.1 新增**，§5.1） | B-5 的启动决策 | **必须在 B-5 启动前完成对照**；对照口径：① 双域寄存器类+编码描述的可复用行数；② 需拆除的 AMD 专有假设清单（HSA ELF / kernarg ABI / occupancy / XNACK / flat scratch）逐项工时；③ 上游同步成本 |

---

## 附录 A：术语

| 术语 | 含义 |
|------|------|
| **golden model** | 逐 lane 解释执行的功能参考实现（此处 = PTX-EMU） |
| **差分测试** | 同一输入在两套实现上执行，比对终态 |
| **谓词化（predication）** | 指令级掩码执行（`@%p`），而非分支 |
| **uniformity 分析** | 证明某值跨 lane 恒定的编译期分析 |
| **legalization** | 把非法/低层形式转成合法形式（如 SGPR←VGPR） |
| `A-1..A-4` | 编译器必须实现的 4 个算法（§6） |
| `G-1..G-10` | PTX-EMU 子集的 10 个硬缺口（§1.2） |
| `B-0..B-5` | 编译器后端路线图阶段（§7） |

---

## 附录 B：证据索引

| 主张 | 证据 |
|------|------|
| **PTX-EMU 解码器四层：94 token / 63 文法 / 106 IR / 47 handler** | `src/grammar/ptxLexer.g4:294-385`、`ptxInstructions.g4`、`include/ptx_ir/ptx_op.def:15-195`、`src/ptxsim/instructions/*.cpp` |
| **ALU 不可谓词化** | `ptxInstructions.g4:51-89,315`（`predicate?` 只在控制流） |
| **`shfl`/`vote` 语法缺 DOT** | `ptxInstructions.g4:365-366` |
| **`.v2/.v4` ALU 未实现** | `src/ptxsim/instructions/memory.cpp` 有 v2/v4；ALU 的 `getBytes` 不看 vector 宽度 |
| **修饰符/特殊寄存器/内存序缺口** | `arithmetic.cpp:394-432`、`cvt_strategy.cpp:82-93`、`register_access_layer.cpp:18-41`、`instruction_handlers.cpp:86-158` |
| **`call` 仅 printf** | `src/ptxsim/instructions/call.cpp:40-45` |
| **`cp.async` / video-SIMD / `madc` 静默丢弃** | `src/ptx_parser/ptx_visitor.cpp:538`、`ptx_op.def` |
| **执行模型：32 lanes / 逐 lane 串行 / per-thread PC / CFG post-dominator 汇合** | `include/ptxsim/warp_context.h:53`、`src/ptxsim/core/warp_context_dispatch.cpp:22-120`、`warp_context.cpp:15-54` |
| **PTX ISA 9.4 公开**；**NVVM IR 13.4 是 LLVM bitcode 子集** | NVIDIA PTX ISA 9.4 / NVVM IR 13.4 规范 |
| **libnvvm 是 `NVVM IR → PTX` 的生产者，闭源** | NVIDIA libNVVM API v4 文档原文 |
| **PTXAS 闭源、无规范** | 无公开来源（本文档为否定性结论） |
| **GPUOCelot 是 PTX 动态编译框架、已停维** | `gtcasl/gpuocelot` 仓库描述 + 历史 |
| **GPGPU-Sim 有 PTX 词法/语法/IR 但只解释执行** | `src/cuda-sim/ptx.l` / `ptx.y` / `ptx_ir.cc` |
| **MGPUSim 只跑 GCN3，不消费 PTX** | `sarchlab/mgpusim` README 原文 |
| **AMDGPU 的 6 个关键 pass** | `SIISelLowering.cpp:31`、`SIInstrInfo.cpp:8341,7331`、`SIFixSGPRCopies.cpp:10`、`GCNRegBankReassign.cpp`、`SIInsertWaitcnts.cpp`、`AMDGPUTargetMachine.cpp:1717-1807` |
| **LLVM 新 target 所需最小集** | LLVM 官方文档《Writing an LLVM Backend》《CodeGenerator》 |
| **36 号的依赖控制块（向量 21 / 标量 16 bit）** | [`36-…`](./36-new-isa-dependence-layer-design.md) §4.5.1 |

---

*本方案基于 2026-10-28 对 PTX-EMU 源码、AMD CDNA ISA 手册、LLVM AMDGPU 后端源码与 NVIDIA 公开规范的一手核查撰写。**未经验证；未经 Oracle/ADR 评审**。所有引号内英文为逐字引用。*
