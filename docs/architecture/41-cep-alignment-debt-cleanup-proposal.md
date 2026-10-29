# 41-cep-alignment-debt-cleanup-proposal: CEP 对齐的债务清理与改进提案

> **类别**: SoC Architecture > 架构文档 · **来源**: **CppTLM 跨仓请求**(队列 #9 `cpptlm-cep-mesif-adapter` 的 R-1 阻塞处置 + 规约层立项)
> **日期**: 2026-10-29 · **提出方**: CppTLM CEP DRI · **答复方**: ArchForge coherence owner
> **状态**: 🟡 **待答复** —— 本提案**不要求 ArchForge 立即动手**,而是把 7 项**已定位**的债务与对齐动作**显式登记**,并给出**建议 diff** 与**逐格追认清单**
> **答复载体建议**: [`ADR-SOC-25-cep-aligned-coherence-architecture.md`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md)(决策) + 本文的 §3 建议 diff
> **关联 ArchForge 文档**: [32-cep-based-coherence-architecture.md](../architecture/32-cep-based-coherence-architecture.md)(§6.2 `mesif` 声明 / §9.1 三级目录 / §11 R-1~R-13 / §13 RK-3) ·
> [25-nsa-hardware.md](../architecture/25-nsa-hardware.md)(§4.1 三级目录 / §4.2 目录条目 / §4.4 **开放问题**) ·
> [09-coherence-protocol.md](../architecture/09-coherence-protocol.md)(§3.3 MOESI 6×6 对照) ·
> [snoop_filter.md](../microarchitecture/snoop_filter.md)(§SparseSnoopFilter 归属)
> **关联 CppTLM 文档**: `ADR-CEP-04 §13`(R-1 裁决)· `ADR-CEP-12 §13`(权威迁移)· `openspec/changes/cpptlm-cep-mesif-state-spec/`(规约层立项)

---

## 0. 一句话

CppTLM 侧已把 **R-1(SharerTracker 第 6 种实现)**裁决并落地,但 ArchForge 侧仍留有 **7 项未清理的债务** —— 其中 2 项直接**阻塞** `mesif` 的落地(声明不自洽 + 规约缺失),1 项是**权威归属**问题(必须显式选一条路),其余 4 项是文档一致性问题。⇒ 本提案把债务**逐条登记**并给出**建议 diff**,供 ArchForge owner 一次性处置。

---

## 1. 背景:为什么会产生这批债务

2026-10-28,CppTLM 完成队列 #8(`cpptlm-cep-chi-rnf-subset`)归档,队列 #9(`cpptlm-cep-mesif-adapter`)成为下一个待启动项。启动前的阻塞排查(**ArchForge 全仓检索,2026-10-29,零命中**)发现:

| # | 债务 | 位置 | CppTLM 侧影响 |
|---|------|------|--------------|
| **D1** | **R-1 未被采纳** ⇒ `32 号 §13` RK-3 记的「D-FABRIC 域无法建模 / NSA Stage 2~3 阻塞」仍在 | `32 号 §9.1:737-741` / `§13:1157` | 阻塞 `mesif` 的 SharerTracker 选型 |
| **D2** | **`mesif` 声明与三级目录不自洽** —— 声明 `impl=SparseSnoopFilter`(caps `SYSTEM/CONSERVATIVE/GLOBAL/HOME`),同文件 §9.1 却描述**三级目录** | `32 号 §6.2:519-523` vs `§9.1:716-741` | 阻塞(声明本身不可信) |
| **D3** | **`SparseSnoopFilter` 已被 `moesi_gpu` 占用** —— 「本模块**就是** CEP 声明中的 `SparseSnoopFilter` 实现」,且指向 `moesi_gpu` 的声明 | `snoop_filter.md:45-47` | `mesif` 复用它是**语义冲突**(不只是「不自洽」) |
| **D4** | **MESIF 状态机规约缺失** —— 只有 5 态词表 `M/E/S/I/F`,**无**转换表 / 事件表 | `25-nsa:598` / `32 号:213` / `32 号:725`;检索 `state_transition` / `状态转换表` **0 命中** | 阻塞(无判据可写) |
| **D5** | **MESIF 的 5→4 `perm` 投影表缺失** —— 唯一投影表是 MOESI 的 6→4;MESIF 侧仅 1 条(`F → WRITEBACK`) | `32 号 §7.2:582-597` / `32 号:529`;检索 `mesif.*projection` **0 命中** | 阻塞(投影无依据) |
| **D6** | **开放问题编号跨文件不一致** —— 同一问题被记为 **#4 / #8 / #9** | `ADR-SOC-25:240,283,315`(#4)· `32 号:200,248,479,943`(#4)· `22-nsa:538`(#9)· `23-dist:583`(#8)· `25-nsa:611`(#9) | 交叉引用易指错 |
| **D7** | **`§7.2` 的语义损失分析不适用于 MESIF** —— 该节分析的是 MOESI 的 `O`/`M` 合并;MESIF 的 `M`/`F` 同投影 `WRITEBACK` 的合并损失**未被显式声明** | `32 号 §7.2:593-596` | 语义损失登记缺项 |

---

## 2. CppTLM 侧已做的处置(供 ArchForge 追认)

| 债务 | CppTLM 处置 | 位置 |
|------|------------|------|
| **D1** | **R-1 已裁决并落地**:新增第 6 种 SharerTracker 实现 `HierarchicalDirectory`(caps `SYSTEM`/`EXACT`/`GLOBAL`/`HIERARCHICAL`)+ `AggregationAt` 新枚举值 `HIERARCHICAL`;`caps` **仍 4 属性**(层级深度是实现参数,不是能力属性)。**否决**「扩 caps 为 5 维」与「用 `TreeManager` 降级近似」 | `ADR-CEP-04 §13` + `include/tlm/cep/sharer_tracker.hh` + `protocol_instance.schema.json` |
| **D2** | `mesif` 的 `sharer_tracker` 已改本仓口径:`HierarchicalDirectory` + `SYSTEM/EXACT/GLOBAL/HIERARCHICAL` | `include/tlm/cep/protocol_instances.json` |
| **D3** | 同上(不再声明 `SparseSnoopFilter`) | 同上 |
| **D4 / D5** | 已立项**规约层** change `cpptlm-cep-mesif-state-spec`:按「**本地推导 + 逐格 `basis` + 待追认标记**」产出 5 态 × 6 事件转换表与 5→4 投影表(每一格都标注依据来源) | `openspec/changes/cpptlm-cep-mesif-state-spec/`(design `D-α` 推导口径表) |
| **D6 / D7** | 尚未处置(属 ArchForge 侧文档) | — |

---

## 3. 建议 diff(逐条;供 ArchForge owner 采纳或改写)

### 3.1 `32 号 §9.1` —— 把 R-1 从「缺口」改为「已被采纳」

**现状**(`32 号:737-741`):

> NSA 需要的是:`scope = SYSTEM` + `completeness = EXACT` + `authority = GLOBAL` + **`aggregation_at` = 三级(L1 GPC / L2 GPU / L3 Tray)**。
> 现有枚举里**没有**能表达「多级聚合」的值(`HOME` 是单点,`TREE_PARENT` 是单父)。
> → **建议**:新增第 6 种实现 `HierarchicalDirectory`,其 `caps.aggregation_at` 需要一个新枚举值(如 `HIERARCHICAL`),
> 或把 `caps` 从 4 维扩为 5 维(加 `hierarchy_depth`)。**这是 R-1 的具体形态。**

**建议**:改写为「**已由 CppTLM `ADR-CEP-04 §13` 裁决并落地**:新增第 6 种实现 `HierarchicalDirectory` + `AggregationAt::HIERARCHICAL`;**未**扩 `caps` 维度(层级深度是实现参数,不是能力属性)。详见 `41 号 §3.3`」。

### 3.2 `32 号 §6.2` —— `mesif` 声明的 `sharer_tracker` 与三级目录对齐

**建议 diff**:

```diff
   "sharer_tracker": {
-    "impl": "SparseSnoopFilter",
-    "caps": { "scope": "SYSTEM", "completeness": "CONSERVATIVE",
-              "authority": "GLOBAL", "aggregation_at": "HOME" }
+    "impl": "HierarchicalDirectory",
+    "caps": { "scope": "SYSTEM", "completeness": "EXACT",
+              "authority": "GLOBAL", "aggregation_at": "HIERARCHICAL" }
   },
```

> ⚠️ **理由**:`SparseSnoopFilter` 是**单级**且 `CONSERVATIVE`(`HOME` 聚合点),与 §9.1 的**三级目录**不符;且该实现**已被 `moesi_gpu` 占用**(`snoop_filter.md:45-47` 明说「本模块**就是** CEP 声明中的 `SparseSnoopFilter` 实现」)⇒ `mesif` 继续声明它是**语义冲突**。

### 3.3 权威归属 —— 必须**显式选一条路**(二选一,不能悬空)

CppTLM 侧已按用户裁决把 `mesif` 的**声明权威迁到本仓**(登记在 `protocol_instances.json` 的顶层 `authority_migrations[]`,带理由 + 台账锚 + 本仓快照锚,per `ADR-CEP-12 §13`)。⇒ **两端声明当前处于「分叉」状态**,ArchForge 侧须**显式处置**:

| 选项 | 动作 | 后果 |
|---|---|---|
| **A(追认)** | 把 `32 号 §6.2` 改成 §3.2 的 diff,并在 `ADR-SOC-25` 追加一段「`mesif` 声明权威的**分叉与归位**」 | 两端**一致**;CppTLM 侧的迁移登记降级为 `repo_owned`;**推荐** |
| **B(撤回)** | 从 `32 号 §6.2` 移除 `mesif` 声明(声明归 CppTLM 域) | 两端**一致**;但 `32 号 §6.3` 的 adapter 实例计数、§6.2 的 A/B 对比叙述需连带调整 |

> **不选**的后果:分叉**永久持续**且对 CppTLM 的 ⑥ 镜像闸**不可见**(迁移名单不参与逐字段比对)⇒ 漂移只能靠人工发现。

### 3.4 `25-nsa §4.4` —— 从「开放问题」收敛为「选型已定 + 规约待补」

**建议**:把 §4.4 的「⚠ 选型待讨论(per §7 开放问题 #9)」改为「**选型已定**:MESIF(单 Owner + Forward 简化);**规约待补**:状态机转换表与 5→4 投影表由 CppTLM 侧按 `41 号 §4` 的追认清单协助补齐」。

### 3.5 开放问题编号统一(**D6**)

**建议**:统一为 **#4**(该编号在 `ADR-SOC-25` 与 `32 号` 两处主要文档中一致),并修正 `22-nsa:538`(#9)与 `23-dist:583`(#8)与 `25-nsa:611`(#9)三处误引。

### 3.6 `32 号 §7.2` —— 补写 MESIF 侧的语义损失(**D7**)

**建议**:在该节追加一小节,声明 MESIF 的投影合并损失:

> MESIF 的 `M`(Modified,脏独占)与 `F`(Forward,单 Owner + 多 Sharer)**同投影** `WRITEBACK` ⇒「是否还有其他 sharer」在 4 值接口上**不可分辨**。
> ⚠️ 与 MOESI 的 `O`/`M` 合并**措辞必须区分**:该损失**可由 Sharer Tracker 补偿**(`mesif` 的 `sharer_tracker = HierarchicalDirectory`,caps `EXACT` + `GLOBAL` ⇒ 目录**能**回答「谁持有」);而 CHI RN-F 的同类合并(`SD`/`UD`)在 RN 侧**不可补偿**(RN 不维护 sharer set)。

---

## 4. 逐格追认清单(CppTLM 规约 → ArchForge 需确认项)

CppTLM 侧按「本地推导 + 逐格 `basis`」产出的 MESIF 规约,其**依据强度**分三档。ArchForge 侧只需对**第 2/3 档**逐格追认(第 1 档已是一手原文):

| 档 | 规约元素 | CppTLM 的依据 | ArchForge 需做的 |
|----|----------|--------------|----------------|
| **① 一手原文** | 5 态 `M/E/S/I/F` 的存在 | `25-nsa:598` / `32 号:213` / `32 号:725` | 无需追认(仅需**确认**未被推翻) |
| **① 一手原文** | `F` = 单 Owner + 多 Sharer | `25-nsa:599-600` | 无需追认 |
| **① 一手原文** | `F → WRITEBACK` 投影 | `32 号:529` | 无需追认 |
| **① 一手原文** | `F` 在 Owner 转移时清空 | `25-nsa:553` / `32 号:529` | 无需追认 |
| **① 一手原文** | 目录条目含 `State(12 bits, MESIF 编码)` | `25-nsa:539` | 无需追认 |
| **② 本仓推导** | `M/E/S/I` 的 4 值投影(`M→WRITEBACK` / `E→UNIQUE` / `S→READ` / `I→NONE`) | 同名态与 MOESI 同义 | **确认或纠正**(逐态) |
| **② 本仓推导** | 5 态 × 6 事件的转换表(30 格) | 以 MOESI 6×6(`09 号 §3.3`)为**结构模板**裁剪 | **逐格确认或纠正** |
| **③ 类比推导** | 「写只在独占态合法」(共享态上的写状态不变) | `25-nsa:552-554`(Owner 唯一性)+ 同型先例 IHI0050 §B4.1(CHI) | **确认或纠正** |

> 逐格 `basis` 与待追认标记的**可执行载体**在 CppTLM 侧 `include/tlm/cep/mesif_state_spec.hh`(规约层 change 的 Phase 2 产物)⇒ 追认进度**机器可查**。

---

## 5. 建议的处置顺序

1. **先答 §3.3(权威归属)** —— 二选一,决定后续动作的形态。
2. **再答 §3.2 + §3.4(声明与选型收敛)** —— 一并把 `mesif` 的 `sharer_tracker` 与 §9.1 对齐。
3. **再答 §3.5 + §3.6 + §3.1(文档一致性)** —— 编号统一、语义损失补写、R-1 状态更新。
4. **最后逐格追认 §4** —— 可与 CppTLM 侧规约 change **并行**推进(规约侧已标注待追认,不阻塞其落地)。

---

## 6. 维护记录

| 日期 | 版本 | 修订 |
|------|------|------|
| 2026-10-29 | v0.1 | 初版:登记 7 项债务(D1~D7)+ 5 组建议 diff + 逐格追认清单 + 处置顺序 |
