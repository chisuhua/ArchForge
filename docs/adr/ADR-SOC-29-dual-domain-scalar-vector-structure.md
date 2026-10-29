# ADR-SOC-29: 标量/向量双域结构与跨域规则（独立 SGPR/SALU + VGPR/VALU）

> **状态**: 📋 Proposed（**待签批**；v1.1 → v1.2 = 回应 critic 复审：`VP[8]` → `VP[2]`，面积口径修正）
> **日期**: 2026-10-29
> **Owner**: ArchForge Team
> **影响**: 自研 ISA 的执行域结构、寄存器文件、条件码、编译器 uniformity 分析责任
> **类别**: ISA 执行域 / 寄存器架构
> **实施**: OpenSpec change（待建）—— B-0 / B-5
> **关联**: [`38-new-isa-dual-domain-structure.md`](../architecture/38-new-isa-dual-domain-structure.md)（本 ADR 的完整机理剖析与证据）· [`40-new-isa-spec-skeleton.md`](../architecture/40-new-isa-spec-skeleton.md) §1 / §2 / §6（规范条款）· [`33-sm-operand-supply-design-target.md`](../architecture/33-sm-operand-supply-design-target.md)（**向量域** OSF 结论）· [`ADR-SOC-26`](./ADR-SOC-26-self-authored-gpu-isa-as-sole-isa.md)（父决策）
> **取代**: 无
> **偏离声明**: **不继承** CDNA 的「VCC 物理住在 SGPR 文件内」（见 §2 D5）

---

## 1. 背景

CDNA 把执行单元分成**标量域**（`S_*` / SOP1/SOP2/SOPC/SOPK/SOPP，操作 SGPR）与**向量域**（`V_*` / VOP1/VOP2/VOP3/VOPC/VOP3P，操作 VGPR）。其分域的**根本原因不是性能等级，而是一条可寻址性约束**：

> 「**The SALU cannot use VGPRs or LDS.**」（CDNA3 ISA §5）

⇒ 标量单元只能操作**跨 lane 恒定**（uniform）的值 ⇒ 编译器必须做 uniformity 分析，否则整条链被迫搬到向量域。

同时 CDNA 的跨域代价**不对称**：VALU 读 SGPR **合法且廉价**；SGPR ← VGPR **ISA 层非法**（LLVM `SIFixSGPRCopies.cpp` 原文：「Copies from VGPR to SGPR registers are illegal」）。

## 2. 决策

### D1 —— 双域物理分离

| 域 | 文件 | 数量 | 条件码 | 单元 |
|---|---|---|---|---|
| **标量** | **SGPR** | **128 = 124 可分配 + 4 保留**（`EXEC` / `STATUS` / `M0` / `SCRATCH_BASE`） | **SCC**（1 bit） | **SALU** |
| **向量** | **VGPR** | **256**（另设 **256 AccVGPR**，v2 预留） | **VP[2]**（独立谓词文件，**3-bit 索引字段保留**） | **VALU** |

### D2 —— 跨域规则（**规范条款**）

| # | 规则 |
|:---:|---|
| **X-D1** | `SALU` 的源**只能**是 SGPR 或立即数；**不得寻址** VGPR / `AccVGPR` / `VP` / LDS |
| **X-D2** | `VALU` 的源**可以**是 VGPR / SGPR / 立即数；读 SGPR **不额外占发射槽** |
| **X-D3** | **`SGPR ← VGPR` 非法。** 必须经 `V_READFIRSTLANE_B32`（计 1 个 VALU 发射槽 + 其延迟 + 一条 `stall`/`wait`） |
| **X-D4** | **每指令 SGPR 源 ≤ 2**（读端口约束）。⚠ **该端口数是本 ISA 的微架构设定值**（不是从 CDNA 或 33 号的 `W=2` 推得 —— 33 号的 `W = 2` 是**向量域**结论，不覆盖 SGPR 读口）⇒ 实现可调整，但调整后须同步更新 X-D4 与 40 号 S-REG-3 |
| **X-D5** | `VP` 只能由向量比较类写入；`SALU` 不得读写 `VP` ⇒ **无跨域谓词写冲突** |

> **X-D1 / X-D3 的违反是编译期非法**（汇编器必须拒绝），不是运行时未定义行为。

### D3 —— 动机排序（**硬件第一，编译器收益第二且有条件**）

| 层级 | 理由 | 强度 |
|:---:|---|:---:|
| **第一（硬件）** | SALU 若可寻址 VGPR，就必须带 **warp 宽读口** ⇒ 标量单元退化为**第二条向量通路**（面积与读带宽双重浪费） | **决定性** |
| **第二（编译器，条件化）** | **若**走 39 号路线 (c) fork AMDGPU，则 `UniformityAnalysis` / `moveToVALU` / `SIFixSGPRCopies` / `legalizeOperandsSMRD` 可移植 | **取决于路线** |

> ⚠ **条件必须写明**： uniformity 证明的负担**不是"照抄约束才引入的"** —— 只要标量单元不可寻址 VGPR，证明责任就存在，与编译器是否自研无关。

### D4 —— 域分离的收益边界（**标量域不需要 OSF 的带宽理由**）

33 号的全部量化结论（`W = 2` / IPC / MCOS / ERW / WABR）**都是向量域结论**：

| 维度 | 向量域 | 标量域 |
|---|---|---|
| 主流源数 | 3 源 | **1–2 源** |
| 读需求 vs 供给 | 3 读/指令 vs **2** 读/拍 ⇒ **带宽受限**（IPC 0.667） | 2 读/指令 vs 2 读/拍 ⇒ **恰好打满**，无缺口 |
| 结论 | OSF（MCOS/ERW/WABR）**有带宽动机** | **MCOS 的带宽动机不成立**；**ERW 的价值场景反而主要在标量域**（1–2 源流） |

⇒ **标量域 v1 不做 MCOS**（38 号 I-2），但**依赖层必须双域齐全**。

### D5 —— 偏离 CDNA：**VCC 迁出 SGPR**

**不继承** CDNA 的「VCC 物理住在 SGPR 文件内」，改用**独立谓词文件 `VP[2]`**（每项 32-bit 逐 lane 掩码，per-warp 64 bit）。

> **⚠ v1.2 修正（critic 复审）**：v1.1 曾写 `VP[8]`（256 bit/warp）并按「256 / 2,097,152」估算为 **0.012% RF** —— **该估算漏乘 48 warp 基数**。按 36 号 §4.2.2 的统一口径（`bit/warp × 48 warp ÷ 2,097,152 bit`）：
> - `VP[8]` = 256 bit/warp ⇒ **0.586% RF** = **整个依赖层（0.121%）的 4.8 倍** ⇒ **不可接受**；
> - `VP[2]` = 64 bit/warp ⇒ **0.146% RF**。
> **⇒ 决定改为 `VP[2]`**：v1 的规范只用到 `VP[0]`（谓词执行）与 `VP[1]`（比较链的第二个目标）⇒ `VP[2..7]` 在 v1 是**死状态**。
> **⇒ 编码不需改动**：`VP` 索引字段仍为 **3 bit**（40 号 §2.1）⇒ v2 扩展 `VP[2..7]` **无需改编码**，只需把架构状态从 2 个扩到 8 个（+0.44% RF，届时按实测需要决定）。

| 理由 | 说明 |
|---|---|
| ① | CDNA 的这个设计让「**每指令 SGPR 源数量有硬上限**」成为架构约束 —— 一个**寄存器文件的偶然耦合**被升级成架构约束 |
| ② | 它制造了一个**编译器必须插 wait 的 hazard**（CDNA 原文警告："The user/compiler must prevent a scalar-ALU write to the SGPR holding VCC"） |
| ③ | 独立谓词文件（256 bit/warp）比这两条代价都便宜 |

⇒ **X-D4 的论证基础因此从"寄存器文件耦合"改为"读端口数"**。

### D6 —— 保留集与字段宽度的取舍

| 项 | 决定 | 代价 |
|---|---|---|
| SGPR 物理数 | **128**（RDNA 式恒定分配；免去 16-dword 动态粒度复杂度） | 比 CDNA 的 102 多 26×4 = 104 bit/warp（可忽略） |
| 索引字段 | **7 bit**（SGPR）/ **8 bit**（VGPR） | **放弃 CDNA 的内联常量块**（`SGPR[128..255]`）⇒ **所有标量常量走立即数字段** ⇒ `SOPK` 占比上升 ⇒ 64-bit 形态占比上升 |
| 备选（否决） | 8-bit 字段 + 内联常量块 | 标量 48-bit 形态预算 `11 + 3×8 + 16 = 51 > 48` ⇒ 吃掉全部标量编码收益 |

## 3. 选项对比

| # | 选项 | 结论 | 理由 |
|---|------|:----:|------|
| **1** | **单一统一域**（一套寄存器 + 一套 ALU） | ❌ 否决 | uniform 值被迫占用向量寄存器 ⇒ 向量域压力上升；且无法借鉴 CDNA 的成熟编译器机制（uniformity 分析 + moveToVALU） |
| **2** | **双域，完全照抄 CDNA**（含 VCC-in-SGPR + `s_waitcnt` 式的条件码语义） | ❌ 否决 | 继承了两条不必要的耦合（X-D4 的原始依据 + SALU-write-VCC hazard），代价 256 bit/warp 的独立谓词文件即可消除 |
| **3** | **双域 + VCC 迁出 SGPR（本 ADR）** | ✅ **采纳** | 保留双域的**全部收益**（物理分离 + 独立压力集 + 编译器 uniformity 机制），去掉两条偶然耦合；`VP[2]` 成本 **0.146% RF**（3-bit 索引字段保留 ⇒ v2 可无改编码扩到 8 个） |
| **4** | **双域但允许 SALU 读 VGPR** | ❌ 否决 | SALU 退化为第二条向量通路（需 warp 宽读口）⇒ 它的存在意义（省一个发射槽）消失 |

## 4. 后果

### 4.1 正面

- **uniform 值不挤占向量寄存器** ⇒ 向量域压力独立可调；
- **编译器获得现成的机制同构**：fork 路线下可移植 4 个 AMDGPU pass（uniformity 分析 / moveToVALU / SGPR copy 修复 / SMEM 合法化）；
- **条件码语义互不干扰**（SCC 与 VP 分离）；
- **X-D3 的跨域代价被显式计价**（1 个 VALU 发射槽 + 延迟 + wait）⇒ 编译器有明确的优化目标（把"从向量域取回标量"尽量推到最后）。

### 4.2 负面

- **编译器必须做 uniformity 分析** ⇒ 标量域的正确性依赖编译器证明；
- **放弃内联常量块** ⇒ 标量常量全走立即数字段 ⇒ `SOPK`（64-bit 形态）占比可能达 30–50% ⇒ **"标量域多数 48-bit"目前是待测假设**；
- **双域意味着两套寄存器分配与两套压力模型** ⇒ 编译器复杂度上升；
- **标量域参数无外部来源**（AMD 不公开 SALU 吞吐 / SMEM 延迟）⇒ 必须自研微基准（40 号 T-1）。

### 4.3 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| **uniformity 分析不可靠** ⇒ 标量域结果错误 | 高 | X-D1/X-D3 做成**编译期非法**（汇编器拒绝）⇒ 错误在编译期暴露，不在运行时 |
| 标量域 `SOPK` 占比过高 ⇒ 标量流平均长度接近 56 bit | 中 | B-2 后对代表性 kernel 统计（40 号 §8 T-1 / 38 号 §3.3） |
| 标量域 `L_w` 实测 < 4 | 中 | 40 号 S-DEP-0：实现插延迟对齐到声明值，或同步收紧该类 `D_c` |
| `VP[2]` 在 v1.1 的比较链场景下不够用 | 低 | 3-bit 索引字段已保留 ⇒ v1.1 扩到 `VP[4]`（+0.146% RF）**无需改编码** |

## 5. 实施

| 阶段 | 内容 | 门禁 |
|---|---|---|
| **B-0** | 规范落地：40 号 §1.2（架构状态清单）、§2（寄存器 + 保留集）、§6（X-D1..X-D5） | 本 ADR 签批 |
| **B-5** | fork LLVM target：移植 uniformity 分析 / moveToVALU / SGPR copy 修复 | Clang/Triton 端到端可跑（**且须先完成 39 号 B-6 对照**） |
| 验证期 | 自研标量域微基准（测 `L_w` / `D_c`） | 40 号 T-1 关闭 |

## 6. Verification（**前瞻判据，尚未验证**）

> **判据归属**：**[本仓]** = 本仓（ArchForge，纯文档）即可关闭；**[CppTLM]** = 涉及模拟器 / 汇编器 / 差分测试 / 微基准，**在 CppTLM 仓执行**，本仓只登记关闭证据。
> 本 ADR 的划分：**本仓** = V3、V4、V7；**CppTLM** = V1、V2、V5、V6。

- [ ] **V1**〔CppTLM〕：**汇编器拒绝非法跨域形式**（`@%p` 式标量谓词、SALU 寻址 VGPR、SGPR←VGPR 直写） — 验证手段：三个专项负例用例全部被拒绝并给出明确诊断；责任人：build
- [ ] **V2**〔CppTLM〕：**VALU 读 SGPR 不额外占发射槽** — 验证手段：对比"读 SGPR vs 读 VGPR"的发射口占用计数；责任人：verifier
- [ ] **V3**〔本仓〕：**SGPR 保留集恰为 4 个且可分配 124 个** — 验证手段：分配器上限测试 + 40 号 §2.2 逐项核对；责任人：verifier
- [ ] **V4**〔本仓〕：**`VP[2]` 与 SGPR 无耦合**（SALU 写 `VP` 被拒绝；无 SALU-write-VCC hazard） — 验证手段：专项用例 + 40 号 S-PRED-1 核对；责任人：verifier
- [ ] **V5**〔CppTLM〕：**标量域 `L_w` / `D_c` 有自测来源**（不是"参照 CDNA"） — 验证手段：微基准报告归档；40 号 T-1 关闭；责任人：验证
- [ ] **V6**〔CppTLM〕：**标量流 48/64-bit 形态占比已统计** — 验证手段：B-2 汇编器对代表性 kernel 的统计报告；责任人：build
- [ ] **V7**〔本仓〕：**33 号的向量域结论未被误用到标量域** — 验证手段：33 号 §0「向量域」限定仍在 + 38 号 §5 结论一致；责任人：文档 owner

## 7. 参考

- [`38-new-isa-dual-domain-structure.md`](../architecture/38-new-isa-dual-domain-structure.md)（§2 CDNA 机理剖析 / §2.8 可借鉴 6 条与不可照搬 3 条 / §3.1 保留集 / §3.1.1b VCC 迁出 / §3.1.1c 内联常量块取舍 / §4 域适配）
- [`40-new-isa-spec-skeleton.md`](../architecture/40-new-isa-spec-skeleton.md) §1.2 / §2 / §6
- [`33-sm-operand-supply-design-target.md`](../architecture/33-sm-operand-supply-design-target.md) §0（向量域限定）
- AMD CDNA1/2/3 Shader ISA 手册 §5（「The SALU cannot use VGPRs or LDS」；「Vector ALU instructions can take up to three arguments, which can come from VGPRs, SGPRs, or literal constants」；VCC-in-SGPR 原文）
- LLVM `SIFixSGPRCopies.cpp:10`（「Copies from VGPR to SGPR registers are illegal」）/ `SIInstrInfo.cpp:8341`（`moveToVALU`）/ `SIISelLowering.cpp:31`（uniformity 分析）
- [`ADR-SOC-30`](./ADR-SOC-30-isa-encoding-48-64-variable-length.md)（编码格式的独立决策）

---

## Status Update

（暂无更新）
