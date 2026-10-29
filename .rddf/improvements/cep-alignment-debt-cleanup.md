---
name: cep-alignment-debt-cleanup
priority: P1
phase: phase-1
category: arch-design
type: debt
状态: pending
主题: CEP 对齐债务清理与规约追认
依赖: ADR-SOC-25, ADR-CEP-04, ADR-CEP-12
来源: "CppTLM 跨仓请求（队列 #9 `cpptlm-cep-mesif-adapter` 的 R-1 阻塞处置）"
生成时间: 2026-10-29
---

# cep-alignment-debt-cleanup — CEP 对齐的债务清理与规约追认

> **载体说明**：本提案取代原 ArchForge 架构文档 `docs/architecture/41-cep-alignment-debt-cleanup-proposal.md`（2026-10-29 移除）。「提案文档」不是可跟踪工作项 —— 债务清单归入 rdd-workflow 改进提案后，才进入 `improvement → openspec change → 归档` 的可追踪链路（有 owner / tasks / AC / 归档记录），跨仓债才可见。
> **本提案只登记债务、判定与验收面**，不预设实现 —— 具体 diff 由后续 openspec change 的 `design.md` / `tasks.md` 落定。
> **本提案是债务台账的唯一载体**：41 号已删除，台账不得再随该文档一起丢失。

**优先级**: P1（阻塞 CppTLM 队列 #9 `cpptlm-cep-mesif-adapter`；R-1 未落地 ⇒ D-FABRIC 域无法建模、NSA Stage 2/3 阻塞）
**类型**: debt（债务清理）
**主题**: CEP 对齐债务清理与规约追认

## 架构依据

**决策链**（本仓 + 跨仓）

| 层 | 依据 | 关键内容 |
|----|------|---------|
| 本仓 | `docs/adr/ADR-SOC-25-cep-aligned-coherence-architecture.md` | CEP 框架下的一致性架构决策（Accepted）；`:91-100` 权威 6→4 投影表（MOESI） |
| 跨仓 | CppTLM `ADR-CEP-04 §13` | **R-1 裁决**：新增第 6 种 SharerTracker 实现 `HierarchicalDirectory` + `AggregationAt::HIERARCHICAL`；**`caps` 仍 4 维**（层级深度是实现参数，不是能力属性）；否决「扩 caps 为 5 维」与「`TreeManager` 降级近似」 |
| 跨仓 | CppTLM `ADR-CEP-12 §13` | **权威迁移**：按 2026-10-29 用户裁决，`mesif` 的声明权威**由 ArchForge 迁到 CppTLM 仓**（`protocol_instances.json` 顶层 `authority_migrations[]`，台账 Entry #96）；`:13.2` 明确「跨仓追认是 ArchForge 侧的动作」，本仓无权闭环 |
| 跨仓 | CppTLM `include/tlm/cep/protocol_instances.json` | `mesif` 声明 = `HierarchicalDirectory` + `SYSTEM/EXACT/GLOBAL/HIERARCHICAL`；`authority_migrations[mesif].archforge_snapshot` = `32 号 §6.2:519-523`（2026-10-29 读取） |
| 跨仓 | CppTLM `include/tlm/cep/sharer_tracker.hh:141,172,205-206` | `AggregationAt::HIERARCHICAL = 4` · `TrackerImpl::HierarchicalDirectory = 5` · caps = `{SYSTEM, EXACT, GLOBAL, HIERARCHICAL}` |
| 跨仓 | CppTLM openspec change `cpptlm-cep-mesif-state-spec` | 规约层 change（Phase 0~5 **全部未开始**）：产出 5 态 × 6 事件转换表 + 5→4 投影表 + 逐格 `basis`；载体 `include/tlm/cep/mesif_state_spec.hh`（**尚未存在**） |

**债务台账 D1~D7**（2026-10-29 对本仓当前文件逐条核验，**7 项全部原样存在**，无一项已被回写）

| # | 债务 | 现状证据 | 阻塞面 |
|---|------|---------|--------|
| **D1** | R-1 未被采纳 | `32 号:738` 仍写「现有枚举里**没有**能表达『多级聚合』的值」；`:740-741` 仍是「**建议**」语气；`:1157` RK-3 仍记「R-1（分级目录）不被采纳 → D-FABRIC 域无法建模，NSA Stage 2/3 阻塞」，其缓解措施「先用 `TreeManager` 近似」正是 CppTLM 已**否决**的方案 | 阻塞 R-1 落地 |
| **D2** | `mesif` 声明与三级目录不自洽 | `32 号:519-523` 声明 `"impl": "SparseSnoopFilter"` + `SYSTEM/CONSERVATIVE/GLOBAL/HOME`；同文件 `:718-725`（三级目录 L1 GPC / L2 GPU / L3 Tray）与 `:737`（`aggregation_at` = 三级）自陈冲突 | 声明本身不可信 |
| **D3** | `SparseSnoopFilter` 已被 `moesi_gpu` 占用 | `docs/microarchitecture/snoop_filter.md:45-47`「本模块**就是** CEP 声明中的 `SparseSnoopFilter` 实现，无需另立选型」；`32 号:445` `moesi_gpu` 已声明该实现 | 语义冲突（不只是「不自洽」） |
| **D4** | MESIF 状态机规约缺失 | 全仓 `state_transition` / `状态转换表` / `转换表` 命中 36 条**全部**属 MOESI / MOESI-GPU 6×6 或 LTSSM ⇒ **MESIF 转换表 0 命中**；MESIF 侧仅存 5 态词表（`25 号:598` · `32 号:213` · `32 号:725`） | 无判据可写 |
| **D5** | MESIF 5→4 `perm` 投影表缺失 | 唯一投影表是 MOESI 6→4（`32 号:582-591` · `ADR-SOC-25:91-100`）；MESIF 侧**仅 1 条**（`32 号:529` `F → WRITEBACK`），`M/E/S/I` 四态投影全缺 | 投影无依据 |
| **D6** | 开放问题编号跨文件不一致 | **canonical = #4**（`25 号:724` 是该题在本文件的真实编号；`ADR-SOC-25:240,283,315` + `32 号:200,248,479,943` 共 7 处一致引用 #4）；`25 号:611` 写 #9 = **同文件内真误引**（本文件 #9 是「L3 Directory 跨 Compute Tray 时延」，`:729`）；`22 号:538`(#9) / `23 号:583`(#8) 是同一语义题被复制进各自独立的开放问题表 | 交叉引用易指错 |
| **D7** | `32 号 §7.2` 语义损失分析不适用于 MESIF | `32 号:593-597` 两条损失全是 MOESI 态（`O`/`M` 合并、`T` 无投影）；MESIF 的 `M`/`F → WRITEBACK` 合并损失**零出现** | 语义损失登记缺项 |

**权威归属裁决**：本提案采纳 **方案 A（追认）** —— ArchForge 侧保留 `mesif` 声明作为**镜像**，口径对齐 CppTLM 仓。依据：`ADR-CEP-12 §13` 的用户裁决已把权威迁到 CppTLM 仓，并**否决**了「等 ArchForge 撤回或修正」（选项 C）；且 `§13.2` 正面收益之一即「`mesif` 的声明可在本仓演进 ⇒ R-1 落地不再被跨仓阻塞」。

## 范围

**In Scope**

1. `docs/architecture/32-cep-based-coherence-architecture.md` —— §6.2 声明块（`:519-523`）、§7.2 投影与语义损失（`:582-597`）、§9.1 R-1 措辞（`:737-741`）、§13 RK-3（`:1157`），以及新增 MESIF 转换表小节（§7 之后）
2. `docs/architecture/25-nsa-hardware.md` —— §4.4 选型措辞（`:611`）+ §7 开放问题编号引用（`:724`）
3. `docs/architecture/22-nsa-fabric-address-spec.md`（`:538`）/ `docs/architecture/23-dist-scale-up-topology.md`（`:583`）—— 同义题补显式交叉引用
4. `docs/adr/ADR-SOC-25-cep-aligned-coherence-architecture.md` —— 追加式 Status Update 段（「`mesif` 声明权威的分叉与归位」）
5. MESIF 规约（5 态 × 6 事件转换表 + 5→4 投影表）的**追认与回填** —— 规约本体由 CppTLM 侧 change `cpptlm-cep-mesif-state-spec` 产出
6. 跨仓动作登记 —— CppTLM 侧 `authority_migrations[mesif]` 的降级/删除；CppTLM change `tasks.md` 任务 4.2 的 ArchForge 引用改指本提案
7. 原 41 号文档的移除 + `docs/architecture/INDEX.md` 计数与分组同步

**Out Scope**

1. **不**在 ArchForge 侧推导 MESIF 规约本体（30 格逐格 `basis`、`mesif_state_spec.hh`）⇒ 权威已迁到 CppTLM 仓，ArchForge 只做**追认 + 回填**
2. **不**改 `docs/microarchitecture/snoop_filter.md:45-47` 的「本模块**就是** `SparseSnoopFilter` 实现」表述 —— 该实现归属 `moesi_gpu`（`32 号:445`）仍成立，冲突只出在 `mesif` 侧重复声明
3. **不**改 MOESI / `moesi_gpu` / `chi_rnf` 的既有 `perm` 投影与转换表（零回归要求）
4. **不**新增 SharerTracker 实现、**不**扩 `caps` 维度（仍 4 维）
5. **不**在本提案内直接落笔本仓文档改动 —— 改动落在后续 openspec change 的 `design.md` / `tasks.md`
6. **不**替代 CppTLM 侧的规约 change —— 本提案只登记跨仓依赖与追认面

## Why

1. **7 项债务全部原样存在**（2026-10-29 逐条核验）：2 项直接阻塞 `mesif` 落地（声明不自洽 + 规约缺失），1 项是权威归属必须显式处置的分叉，其余 4 项是文档一致性问题。
2. **漂移对守门不可见**：`ADR-CEP-12 §13.2` 负面项 ① 明确 —— `mesif` 登记进 `authority_migrations[]` 后，跨仓镜像闸 ⑥ 对迁移名单**不适用** ⇒ 两端声明分叉只能靠人工发现，不会被自动拦住。
3. **「提案文档」不是工作项**：41 号以架构文档形态承载债务清单 ⇒ 无 owner、无 tasks、无 AC、无归档记录 ⇒ 跨仓债不可见、债龄不可计。
4. **不处置的后果**：分叉永久持续，D-FABRIC 域阻塞不解，NSA Stage 2/3 无法推进。

## What Changes

按处置顺序（先权威归属 → 再声明与选型 → 再文档一致性 → 最后规约追认）：

1. **权威归属（A 追认）** —— `ADR-SOC-25` 追加 Status Update 段，登记「`mesif` 声明权威迁到 CppTLM 仓」的分叉与归位：ArchForge 侧保留 `mesif` 声明作为**镜像**，口径对齐 CppTLM 仓 `protocol_instances.json`。
2. **`32 号 §6.2` 声明对齐**（`:519-523`）：

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

3. **`32 号 §9.1` R-1 状态更新**（`:737-741`）—— 从「现有枚举里没有能表达多级聚合的值」改为「**已由 CppTLM `ADR-CEP-04 §13` 裁决并落地**：新增第 6 种实现 `HierarchicalDirectory` + `AggregationAt::HIERARCHICAL`；**未**扩 `caps` 维度（层级深度是实现参数，不是能力属性）」。
4. **`32 号 §13` RK-3 更新**（`:1157`）—— 「R-1 不被采纳 ⇒ D-FABRIC 域无法建模」的缓解措施「先用 `TreeManager` 近似」已被 CppTLM 否决 ⇒ 随 R-1 落地改写。
5. **`25 号 §4.4` 选型收敛**（`:611`）—— 「⚠ 选型待讨论 (per §7 开放问题 #9)」→「**选型已定**：MESIF（单 Owner + Forward 简化）；**规约待补**：状态机转换表与 5→4 投影表由 CppTLM 侧按 `cpptlm-cep-mesif-state-spec` 产出后追认回填」。
6. **D6 编号统一为 #4** —— `25 号:611` 的 `#9` → `#4`（**同文件内真误引**）；`22 号:538`(#9) / `23 号:583`(#8) 保留本文件内合法编号，但补显式交叉引用「同 `25 号 §7 #4`」以消除歧义。
7. **`32 号 §7.2` 补 MESIF 投影与语义损失** —— 追加 MESIF 5→4 投影表（`I→NONE` / `S→READ` / `E→UNIQUE` / `M→WRITEBACK` / `F→WRITEBACK`，每条带依据锚点）与 MESIF 侧合并损失声明：

   > MESIF 的 `M`（Modified，脏独占）与 `F`（Forward，单 Owner + 多 Sharer）**同投影** `WRITEBACK` ⇒「是否还有其他 sharer」在 4 值接口上**不可分辨**。
   > ⚠️ 措辞必须与 MOESI 的 `O`/`M` 合并**区分**：该损失**可由 Sharer Tracker 补偿**（`mesif` 的 `sharer_tracker = HierarchicalDirectory`，caps `EXACT` + `GLOBAL` ⇒ 目录**能**回答「谁持有」）；而 CHI RN-F 的同类合并（`SD`/`UD`）在 RN 侧**不可补偿**（RN 不维护 sharer set）。

8. **MESIF 规约追认与回填** —— CppTLM 侧 change `cpptlm-cep-mesif-state-spec` 落地后，把 5 态 × 6 事件转换表（30 格，每格带 `basis` 锚点）回填进 `32 号`（§7 之后新增小节），并在 `25 号 §4.2` 补目录条目状态编码的依据。追认**仅覆盖依据强度 ②/③ 档**（① 档一手原文无需追认）。
9. **跨仓动作登记** —— ① CppTLM 侧 `protocol_instances.json` 的 `authority_migrations[mesif]` 条目在追认完成后**应降级/删除**（该降级动作未机器化，需 CppTLM 人工裁决 + 台账 entry ⇒ 本仓无权闭环，登记为跨仓待办）；② CppTLM `openspec/changes/cpptlm-cep-mesif-state-spec/tasks.md` 任务 4.2 指向的 ArchForge 载体（已删除的 41 号）改指本改进提案。
10. **41 号文档移除 + 索引同步** —— 删除 `docs/architecture/41-cep-alignment-debt-cleanup-proposal.md`；`docs/architecture/INDEX.md` 总数 54 → 53、G 组 2 → 1、维护记录追加 v3.11。

## 追认输入（2026-10-29，CppTLM 侧已产出）

CppTLM 侧的**规约层** change `cpptlm-cep-mesif-state-spec` 已完成 Phase 1~3，**逐格追认的输入已就位** ⇒ 本提案的 **AC-7**（`32 号` 回填 MESIF 5 态 × 6 事件转换表 + 5→4 投影表）**具备回填条件**。

| 产物 | 位置（CppTLM 仓） | 内容 |
|------|------------------|------|
| **规范性载体** | `include/tlm/cep/mesif_state_spec.hh` | 30 格转换表 + 5 格投影表，**每格**带 `basis{kind, pending, ref, note}`；`kind ∈ {Primary, Structural, Derived, Analogical}` |
| **逐格追认清单** | `docs/implementation/2026-10-29-cep-mesif-state-spec-recognition-checklist.md` | **由载体直接生成** ⇒ 与载体零漂移（机器判据 `MS-06` 逐格核对） |
| **推导口径** | `openspec/changes/cpptlm-cep-mesif-state-spec/design.md`（`D-ε.1` ~ `D-ε.11`） | 建模约定 C1~C6 · 依据强度分级 · 偏离清单 · 2 项语义损失 · 秩的精确口径 |

**追认刻度（机器可查）**：待追认 **31 / 35** 格；一手原文 **4 / 35** 格（转换表 3 + 投影表 1）。第 ① 档（一手原文）**无需追认**，仅需确认未被推翻；**第 ②/③ 档（推导 / 类比）需逐格确认或纠正**。

**与本提案 D4 / D5 / D7 的对应**：

| 本提案债务 | CppTLM 侧的对应产出 | 追认动作 |
|------------|-------------------|----------|
| **D4** MESIF 状态机规约缺失 | 30 格转换表（`basis` 逐格带锚点） | 逐格确认或纠正（重点：`F` 行的 5 格 + 4 条相对 CHI 的**偏离**） |
| **D5** MESIF 5→4 投影表缺失 | 5 格投影表（`F→WRITEBACK` 是一手原文，其余 4 态为 MOESI 6→4 表的**状态同义迁移**） | 确认 4 态投影 + 确认 `F` 的原文仍成立 |
| **D7** MESIF 侧语义损失未登记 | 2 项登记：`F`/`M` 同投影 `WRITEBACK`（**可由 Sharer Tracker 补偿** —— `mesif` 的 `sharer_tracker = HierarchicalDirectory`，caps `EXACT` + `GLOBAL`）＋ 次生的 `F → E` **秩回落** | 确认措辞与 MOESI 的 `O`/`M` 损失**可区分**（本仓 `chi_rnf` 的同类合并是**不可补偿**的 —— 措辞不得混用） |

**偏离清单（追认优先级最高，8 条）**：`I+SnpShared`（CHI `→SC` vs 本表 `→I`）· `E+SnpShared`（CHI `→SC` vs 本表 **`→F`**，MESIF Forward 语义）· `S+RdUnique`（CHI `→SC` vs 本表 `→E`，MESIF 目录语义）· `F` 行的 5 格（**CHI 无对应态**）。

⚠️ **口径边界**：CppTLM 侧的判据锁**完备性 / 可审计性 / 待追认标记 / 内部自洽**，**不**锁推导值的**语义正确性** ⇒ 未追认的值**带着 `pending` 标记**留在规约里，**不**被固化为「既定事实」⇒ **投影表回填前不得据此写实现层判据**。

## Acceptance

- [ ] **AC-1** `32 号 §6.2` 的 `mesif.sharer_tracker` == `{impl: HierarchicalDirectory, caps: SYSTEM/EXACT/GLOBAL/HIERARCHICAL}`；`mesif` 声明块内 `SparseSnoopFilter` / `CONSERVATIVE` / `"aggregation_at": "HOME"` **零命中**
- [ ] **AC-2** `32 号 §9.1` 不再出现「现有枚举里没有能表达多级聚合的值」；R-1 表述为「已由 `ADR-CEP-04 §13` 裁决并落地」；`32 号 §13` RK-3 不再写「R-1 不被采纳 ⇒ D-FABRIC 域无法建模」，且**不以 `TreeManager` 近似为缓解**
- [ ] **AC-3** `ADR-SOC-25` 含追加式 Status Update 段，登记「`mesif` 声明权威迁到 CppTLM 仓（`authority_migrations[]`，台账 Entry #96）」的分叉与归位（追认方案 A），且**未改动** §1~§N 既有正文
- [ ] **AC-4** `25 号 §4.4` 不再写「选型待讨论」；表述为「选型已定：MESIF」；`25 号 §4.1` 三级目录 + §4.2 目录条目与 `32 号 §9.1` 口径一致
- [ ] **AC-5** 开放问题 canonical = #4：`25 号:611` 的 `#9` 已改为 `#4`；`22 号:538` / `23 号:583` 保留本文件内合法编号但补「同 `25 号 §7 #4`」交叉引用；全仓无「MESIF 选型题 = #8 / #9」的残留引用
- [ ] **AC-6** `32 号 §7.2` 含 MESIF 5→4 投影表（5 条：`I→NONE` / `S→READ` / `E→UNIQUE` / `M→WRITEBACK` / `F→WRITEBACK`），每条带依据锚点；语义损失小节含 MESIF `M`/`F` 合并损失，且措辞与 MOESI `O`/`M` 损失**可区分**（含「可由 Sharer Tracker 补偿」限定）
- [ ] **AC-7** `32 号` 含 MESIF 5 态 × 6 事件转换表（30 格）且每格带 `basis` 锚点；追认状态（第 ①/②/③ 档）可查
- [ ] **AC-8** 零回归：`moesi_gpu` / `chi_rnf` 的既有 `perm` 投影与 `moesi_gpu` 的 `SparseSnoopFilter` 声明（`32 号:445`）**未被改动**；`docs/microarchitecture/snoop_filter.md:45-47` 未被改动
- [ ] **AC-9** `docs/architecture/41-cep-alignment-debt-cleanup-proposal.md` 已删除；`docs/architecture/INDEX.md` 总数 = 53（与 `ls docs/architecture/*.md | grep -v INDEX | wc -l` 实测一致）、G 组 = 1 份、维护记录含 v3.11 行
- [ ] **AC-10** 跨仓引用无悬空：CppTLM `openspec/changes/cpptlm-cep-mesif-state-spec/tasks.md` 任务 4.2 的 ArchForge 侧指向改为本改进提案（或等价新载体）；两仓均无指向已删除 41 号的引用
- [ ] **AC-11** CppTLM 侧 `authority_migrations[mesif]` 的**降级/删除**动作已登记为跨仓待办（含所需台账 entry 锚）⇒ 明确标注「本仓不可闭环」
- [ ] **AC-12** 锚点可复核：改动触及 `32 号` §6.2 / §7.2 / §9.1 / §11 / §13 的行号 ⇒ 提交附**锚点位移对照表**（旧行号 → 新行号）

## Capabilities

- **跨仓声明单一权威 + 镜像口径**：ArchForge 侧 `mesif` 声明与 CppTLM 侧权威口径一致，`mesif` 不再重复声明 `SparseSnoopFilter` ⇒ 消除 D3 的语义冲突
- **规约可判据化**：MESIF 5 态 × 6 事件转换表 + 5→4 投影表落进 ArchForge 设计文档，每格带依据锚点 ⇒ 可写判据、可逐格追认、可审计
- **语义损失显式登记**：MESIF `M`/`F` 合并损失与其补偿路径（Sharer Tracker **可**补偿 vs RN 侧**不可**补偿）措辞可区分，不再被 MOESI 口径覆盖
- **债务可跟踪**：7 项债务从「架构文档里的登记条目」升级为 rdd-workflow 工作项（有 owner / tasks / AC / 归档链路），跨仓债可见、债龄可计
- **编号一致性**：开放问题 canonical 编号（#4）与跨文件同义题交叉引用收敛，交叉引用不再指错

## Impact

- **对 `32 号`**：§6.2 声明块改写（行数不变）+ §7.2 新增投影表与语义损失 + §9.1 措辞 + §13 RK-3 + §7 之后新增转换表小节 ⇒ **§9.1 / §11 / §13 行号整体下移**，须附锚点位移对照表
- **对 `25 号`**：§4.4 选型措辞 + §7 开放问题引用编号改写（`#9` → `#4`）⇒ 影响「NSA Hardware Directory 跨 Fabric 一致性」题的收敛状态记录
- **对 `ADR-SOC-25`**：追加式 Status Update 段（不改既有正文，per ADR 不可变 + Status Update 先例）
- **对 CppTLM**：追认完成后两端 `mesif` 声明一致 ⇒ 跨仓镜像闸 ⑥ 对 `mesif` 可恢复逐字段镜像；`authority_migrations[mesif]` **应降级/删除**（跨仓动作，本仓无权闭环）
- **不改动**：`docs/microarchitecture/snoop_filter.md`（归属 `moesi_gpu` 仍成立）、MOESI / `moesi_gpu` / `chi_rnf` 的既有投影
- **风险**：① 权威迁移与声明镜像并存 ⇒ 若 CppTLM 侧不降级迁移登记，两端分叉将持续（已登记为跨仓待办 + 已知残留）；② 转换表 30 格中第 ②/③ 档依据是**推导 / 类比** ⇒ 追认可纠正 ⇒ 投影表回填前**不得**据此写实现判据；③ 41 号移除后债务台账仅存于本提案 ⇒ 本提案是唯一载体，不得再删
