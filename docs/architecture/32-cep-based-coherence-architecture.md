# 32. CEP 对齐的一致性架构 — dGPU SoC + NSA 多卡互联 在 Coherence Exploration Platform 下的重设计

> **类别**: SoC Architecture > 子系统架构 (L7 Coherence) + 跨仓架构对齐
> **状态**: 📋 Draft v0.1 (2026-10-21 · CppTLM CEP 提问单答复轮)
> **日期**: 2026-10-21 · **作者**: ArchForge (coherence owner)
> **上游提问单**: [`docs/roadmap/cep-interface-alignment.md`](../roadmap/cep-interface-alignment.md) (CppTLM CEP DRI 提出, 6 问 + P0-1~P0-5)
> **关联决策**: [`ADR-SOC-25-cep-aligned-coherence-architecture.md`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md)
> **关联既有架构**:
> - [`09-coherence-protocol.md`](./09-coherence-protocol.md) (L7 Coherence · 本文的 SoC 侧重构对象)
> - [`25-nsa-hardware.md`](./25-nsa-hardware.md) §4 Hardware Directory (本文的 NSA 侧重构对象)
> - [`30-nsa-comprehensive-supplement.md`](./30-nsa-comprehensive-supplement.md) §2 跨节点一致性模型
> - [`08-noc-interconnect.md`](./08-noc-interconnect.md) §4.3 Virtual Channel
> - [`22-nsa-fabric-address-spec.md`](./22-nsa-fabric-address-spec.md) §0.5 Normative Glossary
> **关联上游契约** (CppTLM 仓, 只读引用):
> - `docs/architecture/07-coherence-exploration-platform.md` (CEP 6 层 + canonical 10 流)
> - `docs/adr/ADR-CEP-{00,02,04,05,07A,12,13,15,17}.md`
> - `include/tlm/cep/protocol_instance.schema.json` (协议实例声明 schema)

---

## 0. 阅读引导

| 想了解 | 读 |
|--------|-----|
| **对提问单的审阅结论**（含 3 处事实错误） | [§2](#2-对提问单的审阅结论8-项发现) |
| **ArchForge 最大的架构缺口**（两套互不承认的一致性架构） | [§3](#3-根本问题诊断archforge-有两套互不承认的一致性架构) |
| **CEP 分层 ↔ ArchForge 构件映射表** | [§4](#4-目标模型cep-6-层--archforge-构件映射) |
| **一致性域重划**（3 域） | [§5](#5-一致性域重划3-域) |
| **协议实例声明**（可直接喂给 CEP schema） | [§6](#6-协议实例声明) |
| **P0-3 映射表**（ArchForge 类型 → canonical 10 流） | [§7](#7-p0-3-映射表archforge-类型--canonical-10-流) |
| **6 问的正式答复** | [§10](#10-6-问答复正式) |
| **对 CEP 框架的需求**（R-1 ~ R-13） | [§11](#11-对-cep-框架的需求r-1--r-13含-r-5--r-5--r-6-修订) |

---

## 1. 结论摘要

### 1.1 一句话

**ArchForge 的一致性架构从「自建 MOESI/GPU 协议栈」改为「CEP 框架下的协议语义规约 + 一致性域声明」** ——
SoC 内的 MOESI/GPU 6×6 与 NSA 侧的 Hardware Directory **不是两套东西**, 而是同一套 CEP 模型下的
「一个协议插件（两个实例）+ 一个分级 Sharer Tracker + 三个一致性域」。

### 1.2 七条核心结论

| # | 结论 | 依据 |
|---|------|------|
| **C1** | **ArchForge 当前有 6 态 MOESI/GPU 6×6（SoC 内, snoop 型）与 MESIF 分级目录（跨卡, directory 型）两套互不承认的一致性架构**；CEP 正是把二者收敛到同一模型的框架 | §3 |
| **C2** | 提问单 §3-Q3 的前提（「直连 CacheTLM **已实现**」）**不成立** —— 代码里没有 `register_cache_callback`, `cache_tlm.hh` 中 `snoop`/`coherence` 标识符出现 **0 次** | §2-F1/F2 |
| **C3** | 提问单 §2 把大量「设计文档级」类型写成「已实现」；`CoherenceProtocol` / `CoherenceBridge` 在 CppTLM 仓 **grep 0 命中** | §2-F1 |
| **C4** | 提问单 §3-Q4 的前提（「ArchForge 侧当前没有 VC/ordering 概念」）**不成立** —— `noc_bundles_tlm.hh:38` 已有 `vc_id` 0-3（与 CEP schema 同域）, NSA 已占 VC1=Atomic / VC2=Remote Query | §2-F5 |
| **C5** | ArchForge `CoherenceDomain` 同时承担「本地 cache line 状态」与「全局 sharer 跟踪」两职 —— 这正是 CEP 的 Stub Cache / Sharer Tracker 边界所禁止的 | [§8.1](#81-coherencedomain--拆分) |
| **C6** | `CoherenceProtocol::translate(probe, from, to)` 是**双协议感知**接口，与 CEP ADR-CEP-13 决策 3（桥接靠「一致性模型翻译 + proxy-cache」，两侧插件各自处理自己的请求）**不兼容** | [§10 Q2](#q2-coherenceprotocol-抽象基类的归属仓) |
| **C7** | ArchForge 的 `E + Write → M`（`state_transition[2][1]=3`）是**静默升级**，在跨域组合下会破坏全局 SWMR —— 直接命中 CEP `ADR-CEP-05 §10` 已经写下的「重新评估 (β) 独立接口方案」触发条件 | [§11 R-2](#r-2-perm-需要可静默升级判别位) |

### 1.3 6 问速览

| 问 | 结论 | 一句话理由 |
|----|:----:|-----------|
| **Q1** 6 态 `CoherenceState` 归属层 | **A**（下沉到协议插件） | 6 态是 MOESI/AMD 家族的**协议内编码**；`O`/`T` 无 4 值 `perm` 投影；CEP `INV-CEP-05-IC1` 分层正确 |
| **Q2** `CoherenceProtocol` 抽象基类归属仓 | **B**（下沉为 CppTLM 侧 ProtocolEngine 插件接口）**+ 3 项强制修订** | 「协议逻辑住 Plugin、能力以数据声明」是 CEP 的立论基础；但 `translate()` 必须移出、请求语义须带 consistency label、基类须更名 |
| **Q3** `snoop_callback` 耦合路径 | **A**（改走 adapter）—— **且无可改之物** | 直连从未实现；`CacheTLM` 当前天然满足 `INV-CEP-15-IC3`；正确动作是**不建成这样** |
| **Q4** VC / ordering 权威方 | **B**（ArchForge 侧承载）**+ 拆分** | `vc_id` 0-3 命名空间已存在且与 CEP 同域；但**协议→VC 绑定表**归协议实例声明 |
| **Q4**（复核修订） | **B** + **per-network 矩阵** | VC 分配是 **per-network** 的（片上 Compute NoC vs 卡间 UALink 是**两张表**）；`vc_binding` / `ordering_assumption` 加 **network 维度** → **R-5' / R-5'' / R-6'**（[复核回执 N-1/N-2](../roadmap/cep-interface-alignment-review-2026-10-21.md)） |
| **Q5** 协议族边界权威方 | **A**（边界由 CppTLM 侧定义）**+ ArchForge 给出实例拆分口径** | ArchForge 贡献 2 个协议实例（`moesi_gpu` / `mesif`）+ 1 个 SharerTracker 选型，而非 1 个 |
| **Q6** 跨域权限词表 | **A**（接受 4 值）**+ 投影表 + 1 项 schema 请求** | 6→4 投影无歧义；唯一缺口是「静默升级」不可表达 → R-2 |

---

## 2. 对提问单的审阅结论（8 项发现）

> 审阅对象: [`docs/roadmap/cep-interface-alignment.md`](../roadmap/cep-interface-alignment.md) v0.1 (2026-10-21)
> 方法: 提问单 §2 的每条断言逐条回查 CppTLM 仓代码 + ArchForge 仓文档，产出「文档断言 / 代码实证 / 判定」三列。

### F1 [严重·事实错误] §2 表把「设计文档级」的类型写成了「已实现」

提问单 §2「两侧接口面现状」表的 **ArchForge 侧 12 行**中，9 行把 ArchForge 文档里的**设计**当成了 CppTLM 仓里的**实现**。

| 提问单 §2 断言 | CppTLM 仓代码实证 | 判定 |
|----------------|------------------|------|
| `enum class Protocol { MESI, MOESI }` (coherence-domain.md:68) | `include/core/coherence_domain.hh:25-28` —— **已带 `[[deprecated]]`**，文件顶部注明「协议泄漏」 | **冲突已在 CppTLM 侧消解**（ADR-CEP-07A 决策 1） |
| `enum class CoherenceState { I,S,E,M,O,T }` (coherence-protocol.md:112) | 仓内仅 `include/ext/error_context_ext.hh:20` 的**调试观测型**枚举（`INVALID/SHARED/EXCLUSIVE/MODIFIED/OWNED/TRANSIENT`） | 无协议层 6 态枚举 |
| `enum class SnoopType` / `SnoopResp` (coherence-protocol.md:117/125) | 全仓 **grep 0 命中** | 仅文档级 |
| `class CoherenceProtocol` 抽象基类 (coherence-protocol.md:133) | `include/core/coherence_protocol.hh` **不存在**；`grep -rn CoherenceProtocol include/ src/` → **0 命中** | **未实现**（与 09 §10.1「（待新建）」自洽） |
| `class CoherenceDomain`（已实现）(coherence-domain.md:70) | `include/core/coherence_domain.hh:30` 存在但**已 `[[deprecated]]`**，且是**纯配置层**（`coherence-domain.md:106`「不执行业务逻辑——它只承载配置数据」） | 「已实现」成立，但**无 snoop 成员** |
| `class DomainRegistry` (coherence-domain.md:94) | `include/core/coherence_domain.hh:55` 存在 | 同上 |
| `class CoherenceBridge`（8 端口）(coherence-bridge.md:135) | `grep -rln CoherenceBridge include/ src/` → **0 命中** | 仅文档级 |
| `register_cache_callback(CacheTLM*)` (09:250) | 全仓 **grep 0 命中** | **未实现** |
| `cache_tlm_integration = "snoop_callback"` (09 §11) | CppTLM 侧无此配置项 | 仅文档级 |

> **影响**：提问单 §3-Q3 与 §4-P0-4 建立在这条错误事实上（详见 F2）；C-2 判据「PR 含 P0-1~P0-5 的结论（逐项可追溯到 ArchForge 文档行）」中的「ArchForge 侧」实为**本仓文档行**，
> 而非 CppTLM 仓的行 —— 两侧 file:line 混排，容易被机器检查误判。

### F2 [严重·结论反转] Q3 的前提不成立，答案从「要不要改路径」变成「不要建成这样」

提问单 §3-Q3 原文：

> 「但直连是**已实现**的（`include/core/coherence_domain.hh` 已有 snoop 相关成员），所以这需要你们确认**是否愿意改路径**。」

**实证**：
- `include/core/coherence_domain.hh` 的 8 个方法（`set_protocol` / `set_members` / `set_snoop_fanout` / `is_member` / `get_snoop_targets` / `lookup_home_node` / `register_bridge` / `has_bridge_to` / `get_bridge` / `tick`）**没有一条是 snoop 回调**；
- `grep -c "snoop\|coherence" include/tlm/cache_tlm.hh` → **0**。

**结论**：
1. **没有任何直连路径需要迁移** → Q3 答 A 的**迁移成本为零**；
2. `CacheTLM` 当前**天然满足** `INV-CEP-15-IC3`（源码不得出现 `snoop`/`coherence`/`MESI`/`MOESI`/`directory` 标识符）；
3. 正确动作不是「改路径」，而是**在 ArchForge 侧把 `snoop_callback` 这条设计从文档中撤下**（见 [§8.3](#83-撤下-snoop_callback-这条设计)）。

### F3 [中·仓内自相矛盾] ArchForge 自身对 `SnoopFilter` 有两套结构

| 出处 | 结构 |
|------|------|
| `09-coherence-protocol.md:311-323` | `SnoopEntry { uint64_t addr; std::vector<uint16_t> sharers; State shared_state; }` |
| `docs/microarchitecture/snoop_filter.md:106-146` | `SnoopFilterTLM` 抽象基类（3 个派生：`SnoopFilterCacheTLM` / `SnoopFilterInvalidatorTLM` / …）+ `FilterEntry { uint64_t addr; std::bitset<16> sharers; CoherenceState state; uint64_t lru_counter; }` + `get_snoop_targets() / update_sharer() / invalidate() / get_table_size()` |

提问单 §2 只引了 09 的版本，**漏掉了微架构文档的版本**。两者语义不同（`vector<sharers>` vs `bitset<16>` + LRU + 替换策略）。
**处置**：以 `snoop_filter.md` 为准（它更接近 CEP 的 `SparseSnoopFilter` 语义），09 §7.2 的 `SnoopEntry` 归并进去。
**这一条不解决，P0 结论无法落到可实施的结构。**

### F4 [严重·范围遗漏] 提问单只覆盖「SoC 内 coherence」，漏掉了 ArchForge 已有的第二套一致性架构

ArchForge 里还有一套**目录式跨卡一致性**，从未与 SoC 侧的 MOESI/GPU 对账：

| 构件 | 位置 | 性质 |
|------|------|------|
| Hardware Directory 三级结构（L1 per-GPC 64KB / L2 per-GPU 1MB / L3 per-Compute-Tray 4MB） | `25-nsa-hardware.md §4.1` | **Sharer Tracker**（CEP 语汇） |
| Directory Entry（Tag 16b / **State 12b MESIF 编码 M-E-S-I-F** / Sharer List 长度 4b / Owner Bitmap 32b per-GPC） | `25-nsa-hardware.md §4.2` | 协议状态 + sharer 集合 |
| Remote Query Packet（**UALink VC2**） | `25-nsa-hardware.md §4.3` | 目录式远端查询 + 定向 snoop |
| Remote Atomic Unit（**UALink VC1**，含 `[24] Acquire/Release semantics (Coherence)` 位） | `25-nsa-hardware.md §3.1/§3.2` | 远端原子 |
| 跨节点一致性模型（单 GPU **TSO** / 同 Tray **RC** / 跨 Tray **弱 RC** / 跨 DC **最弱**） | `30-nsa-comprehensive-supplement.md §2.1/§2.3` | **按 fabric scope 分级**的一致性标签 |
| NSA Switch Coherency Engine | `28-cxl-3-fabric.md §1.2.4` | 跨域 Ordering Point |

> **这才是最大的架构缺口**：ArchForge 有两套一致性架构（一套 snoop 型、一套 directory 型），
> 而 CEP 恰好是把二者收敛到同一模型的框架 —— 也是 CEP 最能对本仓产生价值的地方。
> 提问单对此**一字未提**。

### F5 [中·前提错误] Q4 的前提「ArchForge 侧当前没有 VC/ordering 概念（这是缺失，不是冲突）」不成立

| 实证 | 位置 |
|------|------|
| NoC 4 VC 分配 + 「4 VC 足以避免请求-响应协议死锁」 | `08-noc-interconnect.md:205-212` |
| `ch_uint<8> vc_id; // 虚拟通道 ID (0-3)` | `include/bundles/noc_bundles_tlm.hh:38` |
| 消息类别 `CATEGORY_REQUEST=0 / CATEGORY_RESPONSE=1 / CATEGORY_CREDIT=2` | `include/bundles/noc_bundles_tlm.hh:60-62` |
| NSA 已占用 **VC1 = Atomic**、**VC2 = Remote Query** | `25-nsa-hardware.md §3.1` / `§4.3` |
| HRT Entry 含 `VC_ID(4 bits)` | `22-nsa-fabric-address-spec.md §0.5.1 #5` |

**关键**：CEP schema 的 `vc_binding` 值域是 `0..3`（`protocol_instance.schema.json:129`），与 CppTLM 的 `vc_id` 0-3 **完全同域**。
→ Q4 应答 **B**，且**命名空间已经存在**，CEP 应**引用**而非**定义**。

### F6 [中·计数口径] 「21 份 ADR / 66 条 invariant」两处口径需校准

- 提问单 §1.3 写「21 份 ADR + 66 条守门 invariant」，§7 材料表写「21 份 ADR + 66 条 invariant」；
- CEP `07 号 §4` 自身写的是「**67 编号位 / 66 实际定义**」，并列 15 组 invariant（`07:254-271`），且 `INV-CEP-04-IC4` 是**唯一跳空位**。

→ 表述应为「**21 份 ADR / 67 编号位 / 66 条实际定义（IC4 跳空）**」。不影响结论，但跨仓文档应统一。

### F7 [中·答复表不完备] §5 答复表无法覆盖 P0-1~P0-5，C-2 判据将无法验收

6 问 ≠ 5 个 P0 冲突。逐项对应关系：

| P0 | 对应问 | 状态 |
|----|--------|------|
| P0-1 6 态枚举归属 | Q1 | 覆盖 |
| P0-2 `enum class Protocol` 仍是配置入口 | **无对应问** | **已消解**（`coherence_domain.hh` 已 deprecated；F1） |
| P0-3 4 类 Bundle ↔ canonical 10 流 无映射 | **无对应问** | 需独立交付 → [§7](#7-p0-3-映射表archforge-类型--canonical-10-流) |
| P0-4 `snoop_callback` 直连 | Q3 | 覆盖 |
| P0-5 `CoherenceProtocol` 归属 | Q2 | 覆盖 |

→ **建议 §5 答复表增列 P0-1~P0-5 的逐项结论行**，否则 C-2「逐项可追溯」不可验收。

### F8 [严重·治理阻塞] C-1 放行判据与 ArchForge 仓性质冲突，会造成**永久阻塞**

C-1 要求：「ArchForge 侧存在**已合入**的 coherence 接口 **PR**（有 commit hash）」。

**事实**：ArchForge 是**纯设计仓** —— `git log` 全部为 `docs(...)` 提交（`901cf19` / `10f5e11` / `a5a1226` / `5b553d2` / `f80c536` / `5d3bba2` / `fbda279`），**无 `src/`、无 `include/`**。
→ ArchForge **结构上无法**产出「接口 PR」，C-1 因此**永远无法闭合**，CEP 的 M2 准入门会**永久阻塞**。

**建议**（需与 CppTLM 侧协商）：把 C-1 从「接口 PR」改为「**接口规约 PR**（design-spec PR）」，
即以本文档 + `ADR-SOC-25` 为 C-1 的交付形态；实现型 PR 归 CppTLM 仓（CEP 侧 `ADR-CEP-00 §2 决策 1` 已把全部 C++ 实现归 CppTLM）。
**这是本次答复必须先解决的前置项**，否则后续 6 问结论再好也解不开阻塞。

---

## 3. 根本问题诊断：ArchForge 有两套互不承认的一致性架构

### 3.1 现状对照

```
┌─ 体系 A：SoC 内一致性（snoop 型） ────────────────────────────┐
│  协议: MOESI/GPU 6 态 I/S/E/M/O/T × 6 事件                    │
│  目录: 无中心目录（snoop 广播）                                 │
│  载体: CoherenceDomain(状态表 + snoop) + CoherenceBridge(8 端口)│
│        + SnoopFilter + CoherentXBar(每端口 domain_id)         │
│  范围: CPU 域 ↔ GPU 域（APU 内 / APU+dGPU）                     │
│  文档: 09-coherence-protocol.md + microarchitecture/coherence-*│
│  状态: 全部「规划」——CppTLM 侧 grep 0 命中                     │
└───────────────────────────────────────────────────────────────┘
                              ✗ 从未对账 ✗
┌─ 体系 B：NSA 跨卡一致性（directory 型） ───────────────────────┐
│  协议: MESIF 变体 M/E/S/I/F（选型开放问题 #4）                  │
│  目录: 三级 Hardware Directory（L1 GPC / L2 GPU / L3 Tray）      │
│  载体: Remote Query(VC2) + Remote Atomic(VC1) + Switch CE      │
│  范围: 跨 GPU / 跨 Compute Tray / 跨 Fabric                     │
│  文档: 25-nsa-hardware.md §4 + 30-nsa §2 + 28-cxl-3-fabric.md │
│  状态: Draft v0.1（2026-09-19），OpenSpec 未创建                  │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 三个具体的冲突点

| 冲突 | 体系 A | 体系 B | 后果 |
|------|--------|--------|------|
| **状态词表** | 6 态 `I/S/E/M/O/T` | 5 态 `M/E/S/I/F` | 同一 cache line 在跨卡路径上状态语义未定义 |
| **查找机制** | snoop 广播（`SnoopFilter` 过滤） | 目录查询（Owner Bitmap + Sharer List） | 跨卡路径走哪条？未定义 |
| **一致性模型** | 未声明（隐含 SC） | RC / 弱 RC，按 fabric scope 分级 | CPU(SC) + GPU(RC) 组合的公理未验证 |

### 3.3 CEP 提供的收敛方式

CEP 的 6 层模型（`07 号 §2.1-2.2`）恰好把两套体系放进**同一个框架的不同位置**：

| CEP 层 | 体系 A 落点 | 体系 B 落点 |
|--------|------------|------------|
| Coherence Interface（canonical 10 流） | `CoherenceBridge` / `CoherentXBar` | `Remote Query` / `Remote Atomic` |
| Protocol Engine（插件） | `MOESI/GPU 6×6` | `MESIF` |
| Directory & Ordering Plane | `SnoopFilter` | Hardware Directory L1/L2/L3 |
| Fabric & Transport Plane | NoC / Crossbar | UALink / PCIe-over-UALink / NSA Switch / CXL Fabric |

→ **体系 A 与体系 B 的差异被压缩为「用哪个协议插件 + 用哪个 Sharer Tracker」两个可配置项**，
而不是两套并列的代码路径。这正是 CEP 存在的意义（`07 号 §1.1`）。

---

## 4. 目标模型：CEP 6 层 ↔ ArchForge 构件映射

> **映射原则**（per `INV-CEP-07A-IC2` 协议泄漏通用禁令）：协议无关的层**不得**出现协议标识符；
> 协议标识符**只允许**出现在 Protocol Engine 插件内部与 capability schema 的数据值中。

| ArchForge 现有构件 | 位置 | CEP 目标层 | 协议无关? | 处置 |
|--------------------|------|------------|:----------:|------|
| NSA Fabric Address / HRT / RCT / Capability | 22 / 21-tee-udd / 27 | **Fabric & Transport** | ✅ | 保留；Capability 须与 `perm` **正交**（R-12） |
| Compute NoC / UALink / PCIe-over-UALink / NSA Switch / CXL Fabric | 08 / 21-fabric-switch / 28 | **Fabric & Transport** | ✅ | 保留；补 network 命名空间 + 每网络 `vc_count`（R-5'） |
| Hardware Directory L1/L2/L3 | 25 §4 | **Directory & Ordering**（SharerTracker） | ✅ | **需第 6 种 SharerTracker 实现**（R-1） |
| `SnoopFilter`（`snoop_filter.md`） | microarch | **Directory & Ordering**（`SparseSnoopFilter`） | ✅ | 归并 09 §7.2 的 `SnoopEntry`（F3） |
| `CoherenceBridge`（8 端口） | microarch | **Coherence Interface** + 跨域判据 | ✅ | 降级：不再是「懂两个协议」的转换器（R-9） |
| `CoherentXBar`（每端口 `domain_id`） | microarch | **Coherence Interface** 多端口挂载 | ✅ | 去掉 `domain_id` 概念，改用「一致性域」标签 |
| `CoherenceDomain`（状态表 + snoop） | microarch | **拆分为 Stub Cache Core + Sharer Tracker** | ✅ | 见 [§8.1](#81-coherencedomain--拆分) |
| MOESI/GPU 6×6 | 09 §3 | **Protocol Engine** 插件 `moesi_gpu` | ❌ | 状态机下沉插件；文档保留为语义规约 |
| MESIF 5 态 | 25 §4.2 | **Protocol Engine** 插件 `mesif` | ❌ | 收敛开放问题 #4（[§6.2](#62-备选实例mesif收敛-nsa-开放问题-4)） |
| `CacheTLM`（L1/L2 性能模型） | CppTLM | **Stub Cache Core**（协议无关）或 Stage 4+ adapter | ✅ | 协议相关语义**不进入** CacheTLM（R-11） |
| Remote Atomic Unit | 25 §3 | **Protocol Engine** 的 atomic 意图 + capability 强制 | ❌ | `atomic.intent_field` 承载（R-4） |
| Capability Token（128b） | 27 | **叠加在 perm 之上的独立正交层** | — | schema 需显式正交声明（R-12） |

---

## 5. 一致性域重划（3 域）

> **域的定义**（per CEP `ADR-CEP-13` 决策 1）：一致性域 = **一个 Ordering Point 生效 + 一套自己的 `ppo` 生效**的范围。
> 域间**不共享** `ppo`；跨域关系进全局内存序。

| 域 | 覆盖范围 | 一致性模型 | Ordering Point | 声明依据 |
|----|---------|-----------|---------------|---------|
| **D-CPU** | CPU 核 + CPU LLC | **SC** | 本地 LLC 目录 | `30-nsa §2.3` Rule 1-2 |
| **D-GPU** | 单 GPU 的 SM/L1/L2/TCC + VRAM | **RC**（read: RC-data, write: RC-release） | GPU 侧 L2 Directory | `30-nsa §2.1`（推荐 RC）+ `30-nsa §2.3` Rule 2 |
| **D-FABRIC** | 跨 Compute Tray / 跨 Fabric | **弱 RC** | NSA Switch Coherency Engine + L3 Directory | `30-nsa §2.3` Rule 3-4 |

### 5.1 跨域桥接的粒度（per `INV-CEP-13-IC3`）

> 跨域桥接的并发粒度**由对端协议是否允许提前 ack 决定**，不由框架固定。

| 跨域边 | 对端协议 | 粒度 | 说明 |
|--------|---------|------|------|
| D-CPU ↔ D-GPU | `moesi_gpu` | **保守**（全部串行） | `moesi_gpu` 的写 ack 语义需在插件规约中明确声明；若允许「写 ack 提前」则可转激进 |
| D-GPU ↔ D-FABRIC | `moesi_gpu` + Remote Atomic | **激进**（同地址串行，跨地址可并发） | Remote Atomic 由 NSA Switch **锁定目标 cache line**（`25-nsa §3.4`），属「不允许提前完成」 |

### 5.2 跨域写传播的触发（per `INV-CEP-13-IC2`，域可见写判据）

> 请求 `r` 是**域可见写** ⟺ (a) 终态 `s1` 允许 store 命中且**无需外部通信**（可能转到 `s2`）**且** (b) `s1`/`s2` 接受导致**数据值响应**的转发请求。

**对本仓的直接后果**：`moesi_gpu` 的 `state_transition[2][1] = 3`（**E + Write → M**）满足判据 (a)（E 态本地写命中无需外部通信），
因此它**是一个域可见写** → 跨 D-GPU / D-FABRIC 边界时**必须触发跨域传播**。
但 CEP 的 4 值 `perm` 无法表达「这是静默升级」→ **R-2**。

---

## 6. 协议实例声明

> 格式严格对齐 `CppTLM/include/tlm/cep/protocol_instance.schema.json`（13 个顶层属性 / 7 个字段组，per `INV-CEP-12-IC1`）。
> `status` 一律填 `planned` —— **CEP 侧只有 `implemented` 才计入 adapter 实例数**（`INV-CEP-12-IC3`）。
> 两份声明均已通过 **JSON Schema 校验**（2026-10-21 实测）。
> ⚠️ `protocol_version` 的取值受 `INV-CEP-11-IC1` 约束：**必须**落在 `ADR-CEP-11 §3` 锁定表内，否则装配期 fail ——
> `moesi-gpu-1.0` / `mesif-1.0` **当前不在该表内**，需 CEP 侧增补（**R-13**）。

### 6.0 VC 分配权威矩阵（per-network）+ 消息类词表

> **本节是 VC 分配的唯一权威**（per 复核回执 [N-1 裁决](../roadmap/cep-interface-alignment-review-2026-10-21.md)）。
> `08-noc-interconnect.md §4.3`（片上 Compute NoC）与 `25-nsa-hardware.md §3.1/§4.3`（卡间 UALink）
> **分属不同 fabric**，是本矩阵的**两行**，不是两套互斥答案。

#### 6.0.1 消息类词表（CEP 规范消息类，**6 类**）

| # | 消息类 | canonical 流 | 方向 | 语义 |
|---|--------|------------|------|------|
| 1 | `request` | 流 1 | node → center | 缓存行请求（读 / 唯一化 / 写回 / 驱逐） |
| 2 | `response` | 流 2 | center → node | 请求完成 + data + perm + error |
| 3 | `snoop` | 流 3 | center → node | snoop 查询 / 失效 / clean / forward |
| 4 | `snoop_resp` | 流 4 | node → center | snoop 响应：hit + state + dirty + data + txn_id |
| 5 | `atomic` | 流 1 的**独立属性** | node → center | 原子意图（CEN-Ib11） |
| 6 | `query` | 流 8 | node ↔ center | 地址归属 / sharer 查询 |

**明确排除**（不进 `vc_binding` 词表）：

| 被排除项 | 排除理由 |
|---------|---------|
| **`CATEGORY_CREDIT`** | **流控类别**，非一致性消息类（`noc_bundles_tlm.hh:62` 注释即「Credit 信号专用类别」）；credit 随所在 VC 的流一起走，**不单独占槽** |
| **`forward_data`（流 6）** | **不单列** —— 它是 `snoop` 槽（Forward 槽）的**承载实例**；对 stub 不可显式为接口（CEN-Ib6 不可分辨性） |
| **`snoop_completion_ack`（流 10）** | **不单列** —— 它是 `snoop_resp` 槽（Reply 槽）的**承载实例**（CEN-Ib10：配对 `snoop_resp` 不配对 `completion`） |

> **为什么 `snoop_resp` 是一等消息类**：`CEN-Ib3`（snoop 必有 snoop_resp）+ `CEN-Ib4`（须含 `txn_id`）+ `CEN-Ib10`（ack 配对它）
> 三条 invariant 都以它为对象；且它承担**协议插件内瞬态态收敛**职责（`INV-CEP-05-IC1` 的 `T` 态由它终结）。
> 漏列它 → 协议侧无法声明「snoop 应答走哪个 VC」。

#### 6.0.2 per-network VC 分配矩阵（权威）

| 网络 | VC0 | VC1 | VC2 | VC3 | 出处 |
|------|-----|-----|-----|-----|------|
| **`compute_noc`**（片上 Mesh） | `request` | `response` | `snoop` + `forward_data` | `snoop_resp` + `snoop_completion_ack` | `08-noc-interconnect.md §4.3` 的 Request/Response/Forward/Reply **四槽划分保持不变**，仅补 6 类词表映射 |
| **`ualink_fabric`**（卡间 UALink） | `request`（+ 非一致性的 Fault Request 共槽，`25-nsa:336`） | `atomic`（`25-nsa:392`） | `query`（`25-nsa:567`） | `response` + `snoop_resp` + `forward_data` | VC0~VC2 原样保留，**VC3 本次补齐** |

**槽位语义的两层归属**（避免混淆）：

| 层 | 内容 | 归属 |
|----|------|------|
| **fabric config**（拓扑配置层） | 每个网络每个 VC 槽**承载什么**（可含非一致性流量，如 UALink VC0 的 Fault Request） | 网络侧 |
| **`vc_binding`**（协议实例声明） | 本协议实例的**一致性消息类** → `vc_id` 绑定（逐网络） | 协议侧 |

#### 6.0.3 死锁自由性论证（per `ADR-CEP-09` 装配期判据）

| 网络 | 通道依赖边 | 环 |
|------|-----------|:--:|
| `compute_noc` | VC0→VC1, VC0→VC2, VC0→VC3, VC1→VC3, VC3→VC2 | **无环** ✅ |
| `ualink_fabric` | VC0→VC3, VC1→VC3, VC2→VC3 | **无环** ✅ |

**两条支撑规则（缺一即成环，必须写进协议语义规约）**：

| # | 规则 | 破了会怎样 |
|---|------|-----------|
| **VC-R1** | **请求向与响应向必须异槽**（VC0 ↔ VC1/VC3） | 请求-响应互等 → 经典请求-响应死锁 |
| **VC-R2** | **`snoop_resp` 不携带数据；数据一律走 `forward_data`** | `snoop_resp`(VC3) 依赖 `forward_data`(VC2) 而 `forward_data` 又依赖 `snoop_resp` → **VC2↔VC3 成环** |

> **VC-R2 正是 `08 §4.3` 原有 Forward / Reply 双槽设计的用意**（Reply = 纯状态应答，Forward = 数据通道）——
> 本次只是把它**显式化为协议规约**，而非新增设计。

> ⚠️ 上述论证由 ArchForge 侧给出**分配表 + 依赖边**；最终判定归 CEP `ADR-CEP-09` 的机器校验（ArchForge 侧不背书）。

### 6.1 实例 1：`moesi_gpu`

```json
{
  "id": "moesi_gpu",
  "family": "industrial",
  "adapter": "MoesiGpuAdapter",
  "status": "planned",
  "protocol_version": "moesi-gpu-1.0",
  "flow_support": {
    "request": true,          "completion": true,
    "snoop": true,            "snoop_resp": true,
    "writeback": true,        "forward_data": true,
    "back_invalidate": true,  "address_resolve": true,
    "barrier": true,          "snoop_completion_ack": true
  },
  "perm": ["NONE", "READ", "UNIQUE", "WRITEBACK"],
  "atomic": { "supported": false },
  "consistency_labels": {
    "read": "RC-data",
    "write": "RC-release"
  },
  "ordering_assumption": {
    "compute_noc": {
      "0": "unordered",
      "1": "p2p_ordered",
      "2": "unordered",
      "3": "p2p_ordered"
    },
    "ualink_fabric": {
      "0": "unordered",
      "1": "unordered",
      "2": "unordered",
      "3": "p2p_ordered"
    }
  },
  "vc_binding": {
    "compute_noc": {
      "request": 0, "response": 1,
      "snoop": 2, "snoop_resp": 3
    },
    "ualink_fabric": {
      "request": 0, "atomic": 1, "query": 2,
      "response": 3, "snoop_resp": 3
    }
  },
  "sharer_tracker": {
    "impl": "SparseSnoopFilter",
    "caps": {
      "scope": "SYSTEM",
      "completeness": "CONSERVATIVE",
      "authority": "GLOBAL",
      "aggregation_at": "HOME"
    }
  },
  "combination_capabilities": {
    "concurrent": true, "hierarchical": true, "heterogeneous": true
  }
}
```

**声明要点**

| 字段 | 取值依据 |
|------|---------|
| `family = "industrial"` | MOESI/AMD 家族源自工业界（`07 §5.1.1`）；**注**：gem5 Ruby 族已有 `MOESI_AMD_Base` + `GPU_VIPER`（`07 §5.1.2`），语义重叠 → 需在 §6.3 澄清「同语义不同实现」 |
| `perm` 4 值 | 与 `CEN-Ib11` 的 4 值锁一致；投影表见 [§7.2](#72-6-态--4-值-projection-表答复-q6-a) |
| `atomic.supported = false` | `moesi_gpu` 6 事件中无原子语义；原子由 Remote Atomic 路径承担（见 §6.2 的 `mesif` / NSA 侧） |
| `consistency_labels` = RC | `30-nsa §2.1` 选型推荐（GPU 侧）+ `30-nsa §2.3` Rule 2 |
| `vc_binding` | **逐网络**矩阵，见 [§6.0.2](#602-per-network-vc-分配矩阵权威)；`compute_noc` 行取自 `08 §4.3` 的四槽划分（Request/Response/Forward/Reply），`ualink_fabric` 行取自 `25-nsa` 已占的 VC0/VC1/VC2 + 本次补齐的 VC3 |
| `ordering_assumption` | **逐网络 × 逐 VC**（per `ADR-CEP-12` 决策 5「排序是 **VC 的静态属性**」）；响应类槽（VC1/VC3）取 `p2p_ordered`，请求向槽取 `unordered` |
| `sharer_tracker.impl = SparseSnoopFilter` | SoC 内为 snoop 型（`SnoopFilter`，`snoop_filter.md`），保守过滤（宁多探不漏探），与 `07 §5.2` 的 `SparseSnoopFilter` 语义对齐 |

> **VC 死锁自由性**：见 [§6.0.3](#603-死锁自由性论证per-adr-cep-09-装配期判据)（两张网络均无环 + 两条支撑规则 VC-R1 / VC-R2）。
> **但该论证须由 CEP `ADR-CEP-09` 的装配期判据机器校验**（ArchForge 侧只提供分配表，不背书）。
> **另一处待修**：`noc_bundles_tlm.hh:60-62` 目前只有 `CATEGORY_REQUEST/RESPONSE/CREDIT` 三类，
> 而一致性消息类需 **6 类**（`request` / `response` / `snoop` / `snoop_resp` / `atomic` / `query`，见 [§6.0.1](#601-消息类词表cep-规范消息类6-类)）→ 见 **R-6'**。
> **`CATEGORY_CREDIT` 明确排除**在消息类词表之外（流控类别，非一致性语义）。

### 6.2 备选实例：`mesif`（收敛 NSA 开放问题 #4）

`25-nsa-hardware.md §7` 开放问题 #4「Hardware Directory 一致性协议：MESIF vs MOESI vs MESI？选型待讨论」
在 CEP 框架下的收敛方式：**不做单选，做可实例化的 A/B**。

```json
{
  "id": "mesif",
  "family": "industrial",
  "adapter": "MesifAdapter",
  "status": "planned",
  "protocol_version": "mesif-1.0",
  "flow_support": { "request": true, "completion": true, "snoop": true, "snoop_resp": true,
                    "writeback": true, "forward_data": true, "back_invalidate": true,
                    "address_resolve": true, "barrier": true, "snoop_completion_ack": true },
  "perm": ["NONE", "READ", "UNIQUE", "WRITEBACK"],
  "atomic": { "supported": true, "intent_field": "consistency_intent" },
  "consistency_labels": { "read": "RC-acquire", "write": "RC-release" },
  "ordering_assumption": {
    "compute_noc": {
      "0": "unordered",
      "1": "p2p_ordered",
      "2": "unordered",
      "3": "p2p_ordered"
    },
    "ualink_fabric": {
      "0": "unordered",
      "1": "unordered",
      "2": "unordered",
      "3": "p2p_ordered"
    }
  },
  "vc_binding": {
    "compute_noc": {
      "request": 0, "response": 1,
      "snoop": 2, "snoop_resp": 3
    },
    "ualink_fabric": {
      "request": 0, "atomic": 1, "query": 2,
      "response": 3, "snoop_resp": 3
    }
  },
  "sharer_tracker": {
    "impl": "SparseSnoopFilter",
    "caps": { "scope": "SYSTEM", "completeness": "CONSERVATIVE",
              "authority": "GLOBAL", "aggregation_at": "HOME" }
  },
  "combination_capabilities": { "concurrent": true, "hierarchical": true, "heterogeneous": true }
}
```

**与 `moesi_gpu` 的差异**（正是 CEP 值得做的 A/B 对比）：
1. `F`（Forward）态 → `perm` 投影为 `WRITEBACK`（Owner 转移时清空 Forward，`25 §4.2`）；
2. `atomic.supported = true` + `intent_field = "consistency_intent"` → 承载 NSA Remote Atomic 的 `[24] Acquire/Release` 位（**R-4**）；
3. `consistency_labels` 用 `RC-acquire` / `RC-release`（显式 acquire 读），而 `moesi_gpu` 用 `RC-data`（数据值响应）；
4. 目录形态不同（Owner Bitmap + Sharer List vs 保守 snoop filter）→ 见 [§9.1](#91-hardware-directory--sharertracker)。

> **为何 `mesif` 不声明 `nsa_switch` 网络**：NSA Switch Coherency Engine 是 **D-FABRIC 域的 Ordering Point**
> （见 [§9.4](#94-nsa-switch-双角色--ordering-point)），但 **NSA Switch 本身当前不是「承载一致性消息的 fabric」** ——
> 本仓未给出它的 VC 分配（`25-nsa` / `28-cxl-3-fabric` 均无 VC 占用记录）。
> 按 §6.0.2 的纪律「**每个网络必须同时出现在 `ordering_assumption` 与 `vc_binding` 中**」，
> 未有 VC 分配的网络**不进矩阵**。待 NSA Switch 成为承载网络时，须先补其 VC 行，再进矩阵。

### 6.3 族边界声明（答复 Q5）

| ArchForge 贡献 | 类别 | CEP 计数口径 |
|----------------|------|-------------|
| `moesi_gpu` | 协议实例（`family = industrial`） | +1 adapter 实例（`status=planned`，**不计入** `implemented` 计数） |
| `mesif` | 协议实例（`family = industrial`） | +1 adapter 实例（planned） |
| NSA 三级 Hardware Directory | **SharerTracker 选型**（非协议实例） | 不计 adapter；计 SharerTracker 实现（**R-1** 需新增第 6 实现） |
| `moesi_gpu` 与 Ruby `MOESI_AMD_Base` / `GPU_VIPER` 的关系 | **同语义不同实现** | 依 `07 §5.1.4`「同一协议语义的不同实现，adapter 按 §5.1.1/§5.1.2 计，**不重复计数**」→ 两边各计各的，**不合并** |

---

## 7. P0-3 映射表：ArchForge 类型 → canonical 10 流

> **状态**：本表即提问单 §4-P0-3 所要求的「纯映射表」，**不依赖 §3 的 6 问**，可先行交付。

### 7.1 逐类型映射

| ArchForge 侧类型 / 事件 | 位置 | → canonical 流 | 折叠 / 约束 |
|------------------------|------|----------------|------------|
| `CacheReqBundle`（Read） | `cache_bundles_tlm.hh:38` | 流 1 `request` | `perm = READ`；`is_write=false` → `perm` |
| `CacheReqBundle`（Write） | 同上 | 流 1 `request` | `perm = UNIQUE`（非 `WRITEBACK`） |
| `CacheReqBundle.is_write`（bool） | 同上 | **→ `perm` 投影** | ⚠️ bool 表达力不足：无法表达「静默 E→M 升级」→ **R-2** |
| `CacheReqBundle` 分片字段（`parent_id`/`fragment_id`/`fragment_total`） | 同上 | 保留在 Bundle 层，**不进 Coherence Interface** | 流控/分片属传输层，不属一致性语义 |
| `CacheRespBundle` | `cache_bundles_tlm.hh:85` | 流 2 `completion` | `data` + `perm` + `error_code`；`is_hit` → `perm != NONE` |
| `SnoopProbe` | `coherence-protocol.md:177` | 流 3 `snoop` | `type` 4 值 ↔ CEP snoop type 4 值（见 7.3） |
| `SnoopRespBundle` | `coherence-protocol.md:186` | 流 4 `snoop_resp` | `hit` + `state` + `dirty` + `data` + `txn_id`（CEN-Ib4） |
| `SnoopRespBundle`（ack 语义） | 同上 | 流 10 `snoop_completion_ack` | **配对 `snoop_resp`，不配对 `completion`**（CEN-Ib10） |
| `CoherenceMsg`（`msg_type` 协议特异） | `coherence-protocol.md:194` | **无对应 → 解散** | `msg_type` = 协议专属字段泄漏进共享抽象（`07 §5.4`「不做」项） |
| `SnoopProbe.source_protocol` / `target_protocol` | 同上 | **无对应 → 删除** | 协议标识符泄漏（`INV-CEP-07A-IC2`） |
| `SnoopRespBundle.source_protocol` | 同上 | **无对应 → 删除** | 同上 |
| 事件 `Read` | `09 §3.2` | 流 1 `request` | |
| 事件 `Write` | 同上 | 流 1 `request` | |
| 事件 `Invalidate`（中心 → 节点） | 同上 | 流 7 `back_invalidate` | 反向失效；CXL 3.0 BISnp 亦走此流 |
| 事件 `Invalidate`（节点 ← 中心 snoop 触发） | 同上 | 流 3 `snoop`（type = invalidate） | 与流 7 的区别 = **方向** |
| 事件 `InvalidateAck` | 同上 | 流 10 `snoop_completion_ack` | |
| 事件 `Flush` | 同上 | 流 5 `writeback` | `addr + data + dirty`；clean writeback 不带 data（INV-SC5） |
| 事件 `FlushAck` | 同上 | 流 10 `snoop_completion_ack` | |
| NSA Remote Query（目录远端查询） | `25 §4.3` | 流 8 `address_resolve` + 流 3 `snoop`（定向） | 目录查完再定向 snoop；`address_resolve` 在 ProtocolEngine 内终结（CEN-Ib8） |
| NSA Remote Atomic | `25 §3.1` | 流 1 `request` + `atomic.intent_field` | CEN-Ib11：atomic 是 request 的独立属性，**不新增 perm 值** |
| NSA Switch Coherency Engine | `28 §1.2.4` | 流 9 `barrier` 的一种实现 | 不带 `group_id` / `participant_count` / `epoch_id`（CEN-Ib9） |
| 远端取数（peer cache 提供数据） | — | 流 6 `forward_data` | 对 stub 透明、不可分辨（CEN-Ib6） |

### 7.2 6 态 → 4 值 projection 表（答复 Q6-A）

| 6 态 `CoherenceState` | 语义 | → CEP `perm` | 备注 |
|-----------------------|------|--------------|------|
| `I` (Invalid) | 无副本 | `NONE` | |
| `S` (Shared) | 多副本共享读 | `READ` | |
| `E` (Exclusive) | 单副本独占读，干净 | `UNIQUE` | 可静默升级到 `M` → **R-2** |
| `M` (Modified) | 单副本独占写，脏 | `WRITEBACK` | |
| `O` (Owned) | 单副本持有脏数据 + 其他可只读 | `WRITEBACK` | 与 `M` 在 4 值下**不可分辨** ⚠️ |
| `T` (Transient) | 瞬态，等待 snoop 响应 | **无投影** | 协议私有态，住插件内部（`INV-CEP-05-IC1`） |

**两个必须显式声明的语义损失**：
1. **`O` 与 `M` 在 4 值下合并** → 「有其他 sharer 吗」这一信息在跨域接口上**丢失**。
   → 对策：跨域桥接依赖 Sharer Tracker 回答「谁持有」，而非依赖 `perm` 本身（CEP 的分层正好支持这一点）。
2. **`T` 无投影** → 瞬态态**必须**留在插件内部；跨域接口上不得出现「等待 snoop 响应」这种中间态。
   → 这是 `INV-CEP-05-IC1` 的直接推论，ArchForge 侧 09 §3.3 的 `T` 态描述须相应改写。

### 7.3 `SnoopType` 4 值 ↔ CEP snoop 流

| ArchForge `SnoopType` | 语义 | CEP 流 3 的 `snoop` type | 对应状态动作 |
|----------------------|------|------------------------|------------|
| `INVALIDATE` | 强制置 I | invalidate | `→ I` |
| `DOWNGRADE_TO_S` | 强制 M/E → S | downgrade | `M→O→S` / `E→S` |
| `READ_SHARED` | 请求共享副本 | shared-read | `→ S` |
| `READ_EXCLUSIVE` | 请求独占 | exclusive-read | `→ E`（无 sharer）或 `→ M`（有 sharer，须先 invalidate） |

> CEP 流 3 的 `snoop` type 集合在 `ADR-CEP-05` 的折叠表（`07 §3.2`）中未逐值列举，
> 上表为 ArchForge 侧建议值；**若 CEP 侧 type 词表不同，需在 Stage 1 前对齐**（R-7）。

---

## 8. dGPU SoC 侧的逐构件重设计

### 8.1 `CoherenceDomain` → 拆分

**现状问题**：`09 §5.1` 给 `CoherenceDomain` 的职责是「维护 cache line 状态表（per address）+ 响应 snoop 请求 + 触发 cache line 状态转换」——
这**同时**做了两件在 CEP 里必须分开的事：

| 职责 | CEP 归属 | 理由 |
|------|----------|------|
| 缓存行的**本地**状态（I/S/E/M） | **Stub Cache Core**（每个 L1/L2 一份） | 每个 stub cache 持有**自己**的行状态；`INV-CEP-05-IC1` 只暴露稳定态 |
| 缓存行的**全局**状态（谁持有） | **Sharer Tracker**（Directory & Ordering Plane） | 目录平面负责 sharer 跟踪（`07 §2.2`） |

**拆分后的对应**：

```
现状（1 个构件干 2 职）              目标（CEP 分层）
┌────────────────────────┐          ┌──────────────────────────┐
│ CoherenceDomain        │          │ Stub Cache Core (per L1/L2)│  ← 本地行状态
│  ├ per-address 状态表  │   ═══>   │  · 行状态 I/S/E/M        │
│  ├ 响应 snoop          │          │  · MSHR / 驱逐 / 写回     │
│  └ 触发状态转换        │          └──────────────────────────┘
│                        │          ┌──────────────────────────┐
│                        │   ═══>   │ Sharer Tracker            │  ← 全局 sharer 集
│                        │          │  · (SparseSnoopFilter)    │
└────────────────────────┘          └──────────────────────────┘
```

**附带处置**：
- 「CoherenceDomain」这个**名字**在 CEP 语境下已被占用（指**一致性域**，per `ADR-CEP-13` 决策 1）→ ArchForge 侧**停止使用该命名**（R-10）；
- CppTLM 的 `coherence_domain.hh` 已 deprecated 且 `coherence_domains` JSON 字段须保留 4 个 config 依赖（`INV-CEP-07A-IC3`）→ 消费在 **Stage 2**。

### 8.2 `CoherenceBridge` → 从「协议转换器」降级为「两插件的组合」

**现状**：`coherence-bridge.md §2.3` 的 `protocol_converter_` 持有 `protocol_a_` + `protocol_b_` 两份 `CoherenceProtocol`，
并调用 `translate(req, from, to)`。

**问题**：这是一个**同时懂两个协议**的组件。CEP 的 `ADR-CEP-13` 决策 3 给的桥接机制是：
> ① **一致性模型翻译**（在目标域找出「SC 等价的访问序列」）+ ② **proxy-cache**（在桥接点内嵌一个目标域协议状态机实例，由它发起目标域的请求）

→ **不需要**任何「双协议感知」的转换器；桥接点只需**内嵌一个目标域的协议插件实例**。

**目标结构**：

```
┌───────────────┐        canonical 10 流        ┌───────────────┐
│ ProtocolEngine│ ◄───────────────────────────► │ ProtocolEngine│
│  (moesi_gpu   │                                │  (moesi_gpu   │
│   或 SC 侧插件)│                                │   另一实例)    │
└───────┬───────┘                                └───────┬───────┘
        │                                              │
        └────────── Coherence Interface (10 流) ────────┘
                          │
                   ┌──────┴───────┐
                   │ proxy-cache  │  ← 内嵌目标域插件实例
                   │ + 标签映射    │     (ADR-CEP-13 决策 3 机制②)
                   └──────────────┘
```

**「协议转换」在新模型中的位置**：`translate(from, to)` **从基类移除**；
跨域语义的映射由**一致性标签映射表**承担（`consistency_labels` 的 `read`/`write`/`request_level` 三元组之间的映射），
这是一个**数据表**，不是代码 —— 这也正是 CEP 把「能力/前提」做成数据声明的立论。

### 8.3 撤下 `snoop_callback` 这条设计

**动作**（在 ArchForge 侧文档层面）：

| 位置 | 现状 | 目标 |
|------|------|------|
| `09 §5.2` `register_cache_callback(CacheTLM*)` | 目标 API | **删除**；改为「Stub Cache Core 的 snoop 入口（协议无关）」 |
| `09 §5.3` 「Phase 7.C: snoop callback → CacheTLM 集成」 | 实施计划 | **改写**为「Phase 7.C: Stub Cache Core 接入 Coherence Interface」 |
| `09 §11` `"cache_tlm_integration": "snoop_callback"` | 配置项 | **删除**；若需保留则取值改为 `"cep_stub_adapter"` / `"none"` |
| `09 §10.3` 「CacheTLM protocol-aware：`on_snoop` callback」 | MVP 简化路径 | **改写**为「Stub Cache Core 承接协议侧 snoop；CacheTLM 保持协议无关」 |

**理由**（三条独立支撑）：
1. `CacheTLM` 源码中 `snoop`/`coherence` 标识符 **0 次** —— 现在改是**零成本**（F2）；
2. `INV-CEP-15-IC3` 明文「`CacheTLM` 不得实现 canonical 10 流的任何一条」；
3. `ADR-CEP-15` 决策 4 定的 adapter 方向是 **`CacheTLM → Coherence Interface`（单向下投影）**，
   而 snoop 是**反方向**（中心 → cache）—— 方向都搞反了。

### 8.4 `CoherentXBar` → 去掉 `domain_id`

`09 §8.1` 的 `CoherentXBar` 每端口带 `domain_id`。在 CEP 模型里：
- 「域」不是端口属性，而是**一组 (Ordering Point, ppo) 的范围**（`ADR-CEP-13` 决策 1）；
- 端口上的应是**协议无关的**挂载点。

→ `CoherentXBar` 在 CEP 下的对应物是 **Coherence Interface 的多端口挂载**（canonical 10 流 × N 端口），
`domain_id` 降为**配置期的标签**（用于决定某个端口的请求路由到哪个 ProtocolEngine 实例 / 哪个 Sharer Tracker）。

### 8.5 6×6 状态机的归属

`09 §3.3` 的 `uint8_t state_transition[6][6]` **表本身不变**，但归属改为：

| 变化项 | 现状 | 目标 |
|--------|------|------|
| 存放位置 | ArchForge 文档（待新建 `include/core/coherence_protocol.hh`） | **Protocol Engine 插件内部**（`MoesiGpuAdapter`） |
| 语义规约 | ArchForge 文档 | **保留在 ArchForge**（作为协议语义规约，per `07 §1.4`「5 个具体协议的语义建模设计文档 → ArchForge 真源 2」） |
| `CoherenceState` 枚举 | 顶层类型（`coherence-protocol.md:112`） | 插件私有；顶层只留 4 值 `perm` 投影 |
| `CoherenceState`（debug 型） | — | `include/ext/error_context_ext.hh:20` 保留，但**降级为观测投影**，注明「非协议状态」 |

---

## 9. NSA 多卡侧的逐构件重设计

### 9.1 Hardware Directory → SharerTracker

| NSA 构件 | `25-nsa-hardware.md` | CEP 目标 |
|-----------|---------------------|----------|
| L1 Directory（per-GPC, 64KB, 8192 entries） | §4.1 | SharerTracker 的**一级**（`scope` 视角） |
| L2 Directory（per-GPU, 1MB, 131K entries） | §4.1 | 二级 |
| L3 Directory（per-Compute-Tray, 4MB, 524K entries） | §4.1 | 三级（仅 NSA Phase 3） |
| Directory Entry 64b（Tag 16b / State 12b / SharerLen 4b / OwnerBitmap 32b） | §4.2 | SharerTracker 的**条目格式**（CEP 不约束条目格式，只约束 `caps`） |
| Remote Query Packet（UALink VC2） | §4.3 | 流 8 `address_resolve` + 流 3 定向 `snoop` |
| MESIF 状态（M/E/S/I/F） | §4.2 | Protocol Engine 插件 `mesif` 的私有状态 |

**关键缺口**（**R-1**）：CEP 现有 5 种 SharerTracker 实现（`ADR-CEP-04 §2`）**全部是单级**：

| 实现 | scope | completeness | authority | aggregation_at |
|------|-------|--------------|-----------|----------------|
| `FullMapDirectory` | SYSTEM | EXACT | GLOBAL | HOME |
| `SparseSnoopFilter` | SYSTEM | CONSERVATIVE | GLOBAL | HOME |
| `DcohSymmetric` | LOCAL_MEMORY_REGION | CONSERVATIVE | LOCAL_HINT | REQUESTER 或 HOME |
| `TreeManager` | SUBTREE | EXACT | LOCAL | TREE_PARENT |
| `BroadcastNull` | NONE | EXACT (degenerate) | NONE | NONE |

NSA 需要的是：`scope = SYSTEM` + `completeness = EXACT` + `authority = GLOBAL` + **`aggregation_at` = 三级（L1 GPC / L2 GPU / L3 Tray）**。
现有枚举里**没有**能表达「多级聚合」的值（`HOME` 是单点，`TREE_PARENT` 是单父）。

→ **建议**：新增第 6 种实现 `HierarchicalDirectory`，其 `caps.aggregation_at` 需要一个新枚举值（如 `HIERARCHICAL`），
或把 `caps` 从 4 维扩为 5 维（加 `hierarchy_depth`）。**这是 R-1 的具体形态。**

### 9.2 Remote Atomic → `atomic` 意图 + capability 强制

| NSA 侧 | CEP 侧 |
|--------|--------|
| Remote Atomic Packet（UALink VC1，`25 §3.2`） | 流 1 `request` + `atomic.intent_field`（CEN-Ib11） |
| `[24] Acquire/Release semantics (Coherence)` 位 | `atomic.consistency_intent` → **R-4** |
| `[23:16] Tenant ID` + Capability Token 校验 | **与 `perm` 正交**的安全层 → **R-12** |
| 「Capability 校验**先于** Atomic Op 启动」（`30 §2.2`） | 与 CEP 分层一致（capability 属 Fabric/控制面，不属一致性语义） |
| 跨 Compute Tray 时「NSA Switch 必须**锁定**目标 cache line」 | 落在 SharerTracker 的 `aggregation_at = HOME`（L3）+ 协议插件的独占获取 |

### 9.3 跨节点一致性模型 → `consistency_labels` 的 scope 分级

`30-nsa §2.3` 的 Rule 1-4 是**按 fabric scope 分级**的：

| Scope | 模型 | CEP 表达 |
|-------|------|----------|
| 单 GPU（Fabric ID = 0） | 强 TSO | `consistency_labels` 的一档 |
| 同 Compute Tray 跨 GPU | RC | 另一档 |
| 跨 Compute Tray | 弱 RC | 又一档 |
| 跨数据中心 | 最弱（RDMA-like） | 最后一档 |

**现有 schema 表达不了**：CEP 的 `consistency_labels`（`protocol_instance.schema.json:98-118`）是
**per-protocol-instance 的单一标签集**（`read` / `write` / `request_level`），**没有 scope 维度**。

→ **R-3**：`consistency_labels` 需支持按 scope 分档，或允许一个协议实例声明多个 scope 变体
（后者在 schema 上是「一个实例 → 多条声明」，与 `INV-CEP-12-IC3` 的计数口径需一并厘清）。

### 9.4 NSA Switch 双角色 → Ordering Point

`28-cxl-3-fabric.md §1.2.2` 的 Fabric Manager 层次（Tier1/2/3）与 `§1.2.4` 的跨 Fabric Coherency Engine，
在 CEP 模型里就是 **D-FABRIC 域的 Ordering Point**（`ADR-CEP-13` 决策 1）：

| NSA 构件 | CEP 角色 |
|---------|---------|
| NSA Switch Coherency Engine | D-FABRIC 域的 Ordering Point（跨域串行化点） |
| L3 Directory（per-Compute-Tray） | D-FABRIC 域内 SharerTracker 的聚合点 |
| CXL Fabric Manager Tier 1/2/3 | **不在 CEP 范围**（属控制面，非一致性语义） |

---

## 10. 6 问答复（正式）

> 本节内容同步填入 [`docs/roadmap/cep-interface-alignment.md`](../roadmap/cep-interface-alignment.md) §5 答复表。

### Q1. 6 态 `CoherenceState` 的归属层

**结论：A —— 状态枚举下沉到协议插件。**

**理由**：`I/S/E/M/O/T` 是 MOESI/AMD 家族的**协议内编码**，不是一致性语义本身；
CEP 的 `INV-CEP-05-IC1`（协议瞬态态与协议私有态住插件内）是正确的分层。
`O`（Owned）与 `T`（Transient）在 4 值 `perm` 下无投影（见 §7.2），恰恰说明它们**不是跨域接口的类型**。

**落点与改动范围**：
- `docs/architecture/09-coherence-protocol.md:242`（`CoherenceDomain::State` 嵌套枚举）→ 删除该嵌套枚举；
- `docs/microarchitecture/coherence-protocol.md:112`（`CoherenceState` 枚举）→ 标注「协议插件私有」；
- `docs/microarchitecture/coherence-protocol.md:73-83`（6 状态表）→ **保留**，但标题改为「MOESI/GPU 协议语义规约（插件内部）」；
- `CppTLM/include/ext/error_context_ext.hh:20`（debug 型 `CoherenceState`）→ 保留，标注「调试观测投影，非协议状态」。

### Q2. `CoherenceProtocol` 抽象基类的归属仓

**结论：B —— 下沉为 CppTLM 侧 ProtocolEngine 插件接口，附 3 项强制修订。**

**理由**：「协议逻辑住 Plugin、能力以数据声明」是 CEP 的立论基础（`07 §1.4` gem5 Ruby 类比）。
若基类留在 ArchForge，CEP 侧就只剩一份声明 schema 而**没有可插拔的逻辑接口**，「可插拔协议」落空。

**3 项强制修订**（缺一则无法落地）：

| # | 修订 | 理由 |
|---|------|------|
| **Q2-a** | **`translate(probe, from, to)` 必须从插件接口移除** | 双协议感知接口与 `ADR-CEP-13` 决策 3（桥接靠「一致性模型翻译 + proxy-cache」）不兼容；桥接只需内嵌目标域插件实例（[§8.2](#82-coherencebridge--从协议转换器降级为两插件的组合)） |
| **Q2-b** | **请求语义须携带一致性标签，不得用 `bool is_write, bool is_read`** | CEP 的 `consistency_labels.request_level` 就是为此存在（`ADR-CEP-17` 决策 7 / HeteroGen §VII-B：目录无法区分 read vs acquire → 请求改名） |
| **Q2-c** | **基类更名为 `ProtocolEngine`；`can_coexist(a, b)` 降为插件内部工具** | `can_coexist` 是「状态对合法性」检查，属协议私有状态机；且基类名不应含「Coherence」——CEP 的分层里协议无关的层不得出现协议标识符（`INV-CEP-07A-IC2`） |

**落点与改动范围**：
- `docs/architecture/09-coherence-protocol.md:399`（「（待新建）`include/core/coherence_protocol.hh`」）→ **取消该新建计划**，改为「协议语义规约交付 CppTLM，由 CEP 侧实现为 `MoesiGpuAdapter`」；
- `docs/microarchitecture/coherence-protocol.md:133-155`（5 个纯虚）→ 拆为「插件接口（CEP 侧，3 项修订后）」+「MOESI/GPU 插件实现（规约）」两节；
- `docs/microarchitecture/coherence-bridge.md:49/81/121`（`protocol_a_`/`protocol_b_` 两份协议指针）→ 改为「proxy-cache 内嵌实例」。

### Q3. `snoop_callback` 的耦合路径

**结论：A —— 改走 adapter。**（并澄清：**当前没有任何直连需要改**）

**理由**（三条独立支撑）：
1. `register_cache_callback` 在 CppTLM 仓 **grep 0 命中**；`cache_tlm.hh` 中 `snoop`/`coherence` 标识符 **0 次**
   → **零迁移成本**，`INV-CEP-15-IC3` 当前**已满足**（F2）；
2. 直连意味着 CacheTLM 侧出现 snoop 语义，正是 `INV-CEP-15-IC3` 要防的形态；
3. `ADR-CEP-15` 决策 4 定的 adapter 方向是 `CacheTLM → Coherence Interface`（**单向下投影**），
   而 snoop 是反方向 —— 方向本就搞反。

**落点与改动范围**（ArchForge 侧文档层，5 处）：
- `docs/architecture/09-coherence-protocol.md:250`（`register_cache_callback`）→ 删除；
- `docs/architecture/09-coherence-protocol.md:256`（§5.3 「Phase 7.C snoop callback → CacheTLM 集成」）→ 改写；
- `docs/architecture/09-coherence-protocol.md:430`（§10.3「CacheTLM protocol-aware：`on_snoop` callback」）→ 改写；
- `docs/architecture/09-coherence-protocol.md:459`（§11 `"cache_tlm_integration": "snoop_callback"`）→ 删除或改取值；
- `docs/microarchitecture/coherence-protocol.md:32`（「协议无关 Bundle（`SnoopProbe` / `SnoopResp` / `CoherenceMsg`）」）→ 拆解（见 §7.1）。

**并追加一条**：ArchForge 侧应**明确声明** dGPU SoC 的一致性缓存模型走哪条路线（R-11）：
**(a)** 直接用 CEP `Stub Cache Core`（推荐，与 `07 §1.1` 定位一致，且 `register_cache_callback` 永不实现）；
**(b)** `CacheTLM` + adapter（`ADR-CEP-15` 决策 4，归 Stage 4+，Stage 1~3 不承诺）。

### Q4. VC / ordering 假设的权威方

**结论：B —— ArchForge 侧承载 `vc_id` 命名空间与网络排序属性；协议→VC 绑定表归协议实例声明。**（原问题把两件事混为一谈，拆分如下）

> 🔶 **复核修订（2026-10-21，per [复核回执 N-1/N-2](../roadmap/cep-interface-alignment-review-2026-10-21.md)）**：
> ① 本问前提「ArchForge 侧当前没有 VC/ordering 概念」**不成立** —— `include/bundles/noc_bundles_tlm.hh:38` 已有 `vc_id` 0-3，与 CEP schema 同域；
> ② **VC 分配是 per-network 的**（片上 Compute NoC vs 卡间 UALink 是**两张表**，不是两套互斥答案）；
> ③ **`vc_binding` 必须带 network 维度**（选项 A），且 `ordering_assumption` 须同步升为 per-(network, vc_id)；
> ④ 消息类词表定为 **6 类**（`request` / `response` / `snoop` / `snoop_resp` / `atomic` / `query`），`CATEGORY_CREDIT` 排除。

| 子项 | 权威方 | 依据 |
|------|--------|------|
| `vc_id` **命名空间**（0-3） | **ArchForge / CppTLM NoC Bundle 层**（已存在） | `noc_bundles_tlm.hh:38`（`ch_uint<8> vc_id`，0-3）+ `08-noc-interconnect.md:205-212`；**与 CEP schema 的 0..3 完全同域** |
| **网络清单 + 每网络 `vc_count`** | **ArchForge 侧**（fabric config 输入） | `22-nsa §0.5` Glossary 扩 network 维度（**R-5'**） |
| 各网络各 VC 的**排序属性** | **ArchForge 侧声明**（逐网络 × 逐 VC） | `08 §4.1` XY 路由死锁避免；`ADR-CEP-12` 决策 5「排序是 **VC 的静态属性**」 |
| **消息类 → `vc_id`**（逐网络） | **协议实例声明**（CEP 侧 schema 承载） | 绑定是协议属性；且死锁论证的图节点必须是 **(network, vc_id)** |
| 死锁自由性**论证** | **CEP 侧**（`ADR-CEP-09` 装配期判据） | `07 §2.2`「VC 分配（首要用途 = 死锁自由性论证载体）」 |

**落点与改动范围**：
- `docs/architecture/08-noc-interconnect.md:205-212` → 标注 `network = compute_noc` + 补 6 类词表映射 + 指向 §6.0.2 权威矩阵；
- `docs/architecture/25-nsa-hardware.md §3.1/§4.3` → 标注 `network = ualink_fabric` + 补 VC3 = `response` + 指向权威矩阵；
- `docs/architecture/22-nsa-fabric-address-spec.md §0.5`（Normative Glossary）→ **扩一维：network 命名空间**（R-5'）；
- `docs/architecture/32-cep-based-coherence-architecture.md §6.0` → **新增 per-network 权威矩阵**（§6.4 → schema delta）。

### Q5. 协议族边界的权威方

**结论：A —— 边界由 CppTLM 侧定义并回写 ArchForge 文档；ArchForge 侧给出实例拆分口径。**

**ArchForge 侧实例拆分口径**（答复 CEP 的「`moesi_gpu` 算 1 个实例还是多个」）：

| 项 | 口径 |
|----|------|
| `moesi_gpu` | **1 个协议实例**。MOESI/GPU 与 MESI 不拆（`MESI` 是 `moesi_gpu` 的**退化配置**，不构成独立实例 —— 与 `07 §5.1.1` 把 CXL 2.0/3.0 记作「同一 adapter 的两种模式但 2 个实例」的**因实施阶段而异**不同：ArchForge 无此分期压力） |
| `mesif` | **1 个协议实例**（与 `moesi_gpu` 并列，构成 A/B 对比） |
| NSA 三级 Hardware Directory | **不是协议实例**，是 SharerTracker 选型 → 不计 adapter |
| `moesi_gpu` vs Ruby `MOESI_AMD_Base` / `GPU_VIPER` | **同语义、不同实现** → 依 `07 §5.1.4`「不重复计数」，两边各计各的，**不合并** |

### 6.4 提议的 schema delta（per 复核回执 N-2 裁决 · 选项 A）

> **本节是给 CEP 侧的直接可执行 patch**。在 CEP 侧合入前，§6.1 / §6.2 的声明按**现行 schema 校验会 fail（预期）** ——
> 本仓**不做**「迁就现行 schema 的降级写法」，因为那会把 N-2 的语义漂移重新引入。

#### 6.4.1 delta

```diff
  "ordering_assumption": {
-   "description": "逐网络的排序假设(per ADR-CEP-12 决策 5):key 必须能解析到唯一 vc_id;排序是 VC 的静态属性,flit 不带 ordering 字段",
-   "type": "object",
-   "minProperties": 1,
-   "additionalProperties": { "enum": ["p2p_ordered", "unordered"] }
+   "description": "逐网络 × 逐 VC 的排序假设(per ADR-CEP-12 决策 5 + 复核 N-2 裁决):key = network,值 = { vc_id: ordering };排序是 VC 的静态属性,flit 不带 ordering 字段",
+   "type": "object",
+   "minProperties": 1,
+   "additionalProperties": {
+     "type": "object",
+     "minProperties": 1,
+     "additionalProperties": { "enum": ["p2p_ordered", "unordered"] }
+   }
  },
  "vc_binding": {
-   "description": "消息类 → vc_id 的映射(per ProtoGen 局限 L4:VC 绑定不由协议生成器负责);不自动生成",
-   "type": "object",
-   "minProperties": 1,
-   "additionalProperties": { "type": "integer", "minimum": 0, "maximum": 3 }
+   "description": "逐网络的消息类 → vc_id 映射(per 复核 N-2 裁决选项 A:VC 分配是 per-network 的,死锁自由论证的图节点必须是 (network, vc_id));消息类词表 = 6 类 {request,response,snoop,snoop_resp,atomic,query};不自动生成",
+   "type": "object",
+   "minProperties": 1,
+   "additionalProperties": {
+     "type": "object",
+     "minProperties": 1,
+     "additionalProperties": { "type": "integer", "minimum": 0, "maximum": 3 }
+   }
  }
```

#### 6.4.2 `INV-CEP-12-IC2` 的可实现化（提议修订）

```
对每个 network n ∈ ordering_assumption ∪ vc_binding:
  ① ordering_assumption[n] 的每个 vc_id v ∈ vc_binding[n].values()
  ② vc_binding[n].values() 中每个 vc_id v < fabric_config.networks[n].vc_count
  ③ vc_binding[n] 的每个消息类 m ∈ {request,response,snoop,snoop_resp,atomic,query}
否则 → 装配期 fail（沿用 ADR-CEP-12 决策 3 的「不静默降级」处置）
```

> **① 消除了现行扁平形式的歧义**：现行 `ordering_assumption` 的 key 既可是 `vc_id` 又可是 `named_network`（`ADR-CEP-12` 决策 5），
> 扁平形态下 `"0"` 指哪个网络的 VC0 **无法判定**；嵌套形态下该歧义消失。
>
> **② 需要 fabric config 提供**：`networks: { <name>: { vc_count: <int> } }` —— 即 R-5' 的交付物。

#### 6.4.3 三面分工（终态）

| 面 | 归属 | 内容 | 本仓交付物 |
|----|------|------|-----------|
| 网络命名空间 + 每网络 `vc_count` | **fabric config** | 网络清单 + 槽位数 | **R-5'** |
| 消息类 → `vc_id`（逐网络） | **协议实例声明** `vc_binding` | §6.0.2 矩阵 | ✅ 已交付 |
| 排序假设（逐网络 × 逐 VC） | **协议实例声明** `ordering_assumption` | §6.1 / §6.2 | ✅ 已交付 |

**落点与改动范围**：
- `docs/architecture/09-coherence-protocol.md:444`（`"protocol": "moesi_gpu"`）→ 保留，但补注「协议实例 id，per CEP `protocol_instance.schema.json`」；
- `docs/architecture/25-nsa-hardware.md §4.4`（开放问题 #4）→ 收敛为「MESIF 作为 `mesif` 实例，与 `moesi_gpu` 并列做 A/B」（[§6.2](#62-备选实例mesif收敛-nsa-开放问题-4)）；
- `docs/architecture/25-nsa-hardware.md §7`（开放问题表）→ #4 标注「已由 `ADR-SOC-25` 收敛」。

### Q6. 跨域接口是否接受 CEP 的 4 值权限词表

**结论：A —— 接受 4 值作跨域词表**，并交付 6→4 投影表（[§7.2](#72-6-态--4-值-projection-表答复-q6-a)）。

**理由**：
1. 4 值是 CEP 已冻结的口径（`CEN-Ib11`），不新增 ATOMIC 值；
2. 6→4 投影**无歧义**（除 `O`/`M` 合并与 `T` 无投影两点，已显式说明）；
3. `O`/`M` 合并导致的信息损失**由 Sharer Tracker 补偿**（CEP 分层的既定做法），不构成额外成本。

**并附 1 项 schema 请求**：`perm` 需能表达「可静默升级」（**R-2**）——
`moesi_gpu` 的 `E + Write → M` 是静默升级，在跨域组合下是「域可见写」（`ADR-CEP-13` 决策 3 判据 (a)），
4 值 `perm` 无法区分「静默升级」与「显式请求升级」。

**落点与改动范围**：
- `docs/architecture/09-coherence-protocol.md:242`（`CoherenceDomain::State`）→ 删除；
- `docs/architecture/09-coherence-protocol.md §6.2`（跨域流程）→ 补「跨域接口只传 4 值 `perm`」；
- `docs/microarchitecture/coherence-protocol.md:73-83`（6 状态表）→ 补投影表；
- `docs/microarchitecture/coherence-bridge.md §2.2`（8 端口表）→ 端口承载的 Bundle 类型按 §7.1 重述。

---

## 11. 对 CEP 框架的需求（R-1 ~ R-13，含 R-5' / R-5'' / R-6' 修订）

> 下列需求由 ArchForge 侧的 NSA 硬件目录 / 跨节点一致性模型 / NoC VC 体系提出，
> 均带本仓实证锚点。**优先级 P0 = 阻塞 CEP Stage 1 / 或阻塞 ArchForge 自身后续设计**。

### R-1. SharerTracker 需要「分级目录」第 6 种实现

| 项 | 内容 |
|----|------|
| **需求** | `ADR-CEP-04 §2` 的 5 种实现需新增第 6 种（或放宽 `caps` 维度），以表达 `scope=SYSTEM` + `completeness=EXACT` + `authority=GLOBAL` + **多级 `aggregation_at`**（L1 per-GPC / L2 per-GPU / L3 per-Compute-Tray） |
| **实证** | `docs/architecture/25-nsa-hardware.md §4.1`（三级目录 + 各自容量/时延）、`§4.2`（Directory Entry 64b） |
| **现状** | 5 实现的 `aggregation_at` 枚举仅 `HOME` / `REQUESTER` / `TREE_PARENT` / `NONE` —— **无「多级」表达** |
| **建议落点** | `ADR-CEP-04 §2` 表 + `protocol_instance.schema.json` 的 `sharer_tracker.impl` 枚举与 `caps.aggregation_at` 枚举 |
| **优先级** | **P1**（不解决则 D-FABRIC 域在 CEP 内无法表达） |

### R-2. `perm` 需要「可静默升级」判别位

| 项 | 内容 |
|----|------|
| **需求** | `perm` 需能区分「静默 E→M 升级」与「显式请求升级」；或新增独立的 `perm_upgrade` 字段 |
| **实证** | `docs/architecture/09-coherence-protocol.md:151`（`state_transition[2][1] = 3`，E + Write → M）；`docs/architecture/30-nsa-comprehensive-supplement.md §2.1`（GPU 侧 RC）；`ADR-CEP-13` 决策 3 判据 (a) |
| **现状** | `protocol_instance.schema.json:77-83` 的 `perm` 是**纯枚举数组**；`ADR-CEP-05 §10`（`:223-225`）**已写明**「若组合协议需要区分静默/显式升级 → 重新评估 (β) 独立接口方案」—— **本需求命中该已写下的触发条件** |
| **建议落点** | `protocol_instance.schema.json` 的 `perm`（改为对象数组 `[{value, silent_upgrade_to}]`）或新增顶层字段；`ADR-CEP-05 §10` 判据升级为「已触发」 |
| **优先级** | **P0**（直接命中 ADR-CEP-05 已写下的触发条件；且不解决则 D-CPU↔D-GPU 跨域正确性无法论证） |

### R-3. `consistency_labels` 需要支持「按 fabric scope 分级」

| 项 | 内容 |
|----|------|
| **需求** | `consistency_labels` 需能表达「同一协议实例在不同 fabric scope 上有不同一致性标签」（TSO / RC / 弱 RC / 最弱） |
| **实证** | `docs/architecture/30-nsa-comprehensive-supplement.md §2.3` Rule 1-4 |
| **现状** | `protocol_instance.schema.json:98-118` 是 per-instance 的**单一**标签集（`read` / `write` / `request_level`），无 scope 维度 |
| **建议落点** | `consistency_labels` 增 scope 键；或允许「一个协议实例 → 多条 scope 变体声明」（后者需同步厘清 `INV-CEP-12-IC3` 的计数口径） |
| **优先级** | **P1** |

### R-4. `atomic` 需要承载一致性语义标签

| 项 | 内容 |
|----|------|
| **需求** | `atomic` 从 `{supported: bool, intent_field: string}` 扩为 `{supported, intent_field, intents: [...]}`，取值含 `relaxed` / `acquire` / `release` / `acq_rel` / `seq_cst` |
| **实证** | `docs/architecture/25-nsa-hardware.md §3.2`（Remote Atomic Packet `[24] Acquire/Release semantics (Coherence)` 位）；`docs/architecture/30-nsa-comprehensive-supplement.md §2.2`（原子性作用域 4 级） |
| **现状** | `protocol_instance.schema.json:84-97` 的 `atomic` 无语义标签；`CEN-Ib11` 只规定「atomic 是 request 的独立属性」，不规定属性内容 |
| **建议落点** | `protocol_instance.schema.json` 的 `atomic`；`ADR-CEP-02` 的 `CEN-Ib11` 补充「intent 取值域」 |
| **优先级** | **P1** |

### R-5'. fabric config 需提供**网络命名空间 + 每网络 `vc_count`**（R-5 升级）

> 🔶 **复核修订（per [N-2 裁决](../roadmap/cep-interface-alignment-review-2026-10-21.md)）**：R-5 的交付物从「网络名单」升级为
> 「**网络命名空间 + 每网络 VC 槽位数**」，因为 `vc_binding` / `ordering_assumption` 改为逐网络后，**槽位上界**必须由 fabric config 给出。

| 项 | 内容 |
|----|------|
| **需求** | fabric config 提供 `networks: { <network_name>: { vc_count: <int> } }`；`vc_count` 是该网络 VC 槽位总数（本仓两个网络均为 4） |
| **实证** | `docs/architecture/08-noc-interconnect.md:45`（片上 NoC）+ `25-nsa-hardware.md:336/392/567`（UALink 已占 VC0/VC1/VC2）+ `22-nsa-fabric-address-spec.md §0.5`（Glossary 15 术语，**尚无 network 维度**） |
| **现状** | `protocol_instance.schema.json:119-130` 的两个字段均为扁平 map；`INV-CEP-12-IC2` 的「named_network → 唯一 vc_id」解析面**在声明内不存在**（flat 形态下 `"0"` 指哪个网络无法判定） |
| **建议落点** | **ArchForge 侧**扩 `22-nsa §0.5` 为「15 术语 + **network 命名空间**」清单（含每网络 `vc_count` 与槽位语义）；CEP 侧 fabric config 消费 |
| **优先级** | **P0**（`vc_binding` 逐网络化的直接前提；C-4 双向映射依赖此项） |

### R-5''. `ordering_assumption` 需从 per-network 单值升为 per-(network, vc_id)

> 🔶 **复核修订（per [N-2 裁决](../roadmap/cep-interface-alignment-review-2026-10-21.md)）**：
> `ADR-CEP-12` 决策 5 的**理由**是「排序是 **VC 的静态属性**」，其**依据**（`.pcc` 的 `Network { Ordered fwd; Unordered resp; Unordered req; }`）
> 说明**不同网络、不同 VC 可以有不同序**。现行 per-network 单值**无法表达「同一网络内 VC0 有序、VC1 无序」**。

| 项 | 内容 |
|----|------|
| **需求** | `ordering_assumption` 改为 `{ <network>: { <vc_id>: "p2p_ordered" \| "unordered" } }`（与 `vc_binding` 同 key space） |
| **实证** | `ADR-CEP-12:118-124`（决策 5 理由 + 依据） |
| **现状** | `protocol_instance.schema.json:119-124` 为 per-network 单值 |
| **建议落点** | `protocol_instance.schema.json` + `ADR-CEP-12` 决策 5 修订（与 **R-6'** 同一批 schema delta） |
| **优先级** | **P0**（与 R-6' 捆绑；否则两个 map 的 key space 不一致） |

### R-6'. 消息类词表定为 **6 类** + `vc_binding` / `ordering_assumption` 加 network 维度（schema 修订）

> 🔶 **复核修订（per [N-2 / N-3 裁决](../roadmap/cep-interface-alignment-review-2026-10-21.md)）**：
> 原 R-6 只要求「词表 5 类 + NoC Bundle 类别扩展」，现升级为「**词表 6 类** + **schema 逐网络化**」。

| 项 | 内容 |
|----|------|
| **需求 A（词表）** | CEP 规范消息类词表 = **6 类**：`request` / `response` / `snoop` / `snoop_resp` / `atomic` / `query`。**明确排除** `CATEGORY_CREDIT`（流控类别）、`forward_data`（流 6）与 `snoop_completion_ack`（流 10）—— 后两者是已有槽位的**承载实例**，不单列 |
| **需求 B（schema）** | `vc_binding` 与 `ordering_assumption` 加 **network 维度**（选项 A），delta 见 [§6.4.1](#641-delta) |
| **实证 A** | `07 号 §3.1:174`（流 4 = `snoop_resp`）+ `CEN-Ib3` / `CEN-Ib4` / `CEN-Ib10`（三条 invariant 均以它为对象）+ `CppTLM/include/bundles/noc_bundles_tlm.hh:62`（`CATEGORY_CREDIT` 注释即「Credit 信号专用类别」） |
| **实证 B** | `ADR-CEP-12:118-124`（决策 5）+ `:84-85`（决策 6）；`protocol_instance.schema.json:119-130` |
| **现状** | 词表口径不一致（`32 号 §6.1` 声明用了 6 类，而原 R-6 只写 5 类）；schema 两字段均扁平 |
| **建议落点** | `protocol_instance.schema.json`（两个字段的 `additionalProperties` 各嵌一层）+ `ADR-CEP-12` 决策 5 / 决策 6 修订 + `INV-CEP-12-IC2` 按 §6.4.2 重写 |
| **CppTLM 侧附带项** | `noc_bundles_tlm.hh:60-62` 的 `CATEGORY_*` 需从 3 类扩到覆盖 6 类一致性消息类（**注**：`CATEGORY_*` 是 **flit 类别**（链路层），与 `vc_binding` 的**消息类**（一致性层）是两个正交维度 —— 建议 CEP 侧明确二者关系，避免又一次「词表混层」） |
| **优先级** | **P0**（N-2 的直接落点；不修订则 C-4 不可机器验收） |

### R-7. CEP 侧需文档化「目录式远端查询」的流组合规范

| 项 | 内容 |
|----|------|
| **需求** | 「目录查 sharer → 定向 snoop」在 CEP 里是 **流 8 + 流 3 的组合**，而非新流；需在 CEP 侧给出规范表述与 `flow_support` 的填法 |
| **实证** | `docs/architecture/25-nsa-hardware.md §4.3`（Remote Query Packet = 目录查询 + 定向 snoop） |
| **现状** | `07 §3.1` 定义了 10 条流但未给「组合用法」；`07 §3.2` 的折叠表覆盖的是 stub 视角 |
| **建议落点** | `ADR-CEP-02` 或 `07 号 §3.1` 增「典型流组合」小节 |
| **优先级** | **P2** |

### R-8. `family` 口径需澄清 `moesi_gpu` 与 Ruby 族的关系

| 项 | 内容 |
|----|------|
| **需求** | 明确 ArchForge `moesi_gpu` 与 gem5 Ruby `MOESI_AMD_Base` / `GPU_VIPER` 是「同语义不同实现」，两边各计各的 adapter |
| **实证** | `07 §5.1.2`（Ruby 族 8 实例含 `MOESI_AMD_Base` / `GPU_VIPER`）；`07 §5.1.4`（不重复计数口径） |
| **现状** | `protocol_instance.schema.json:30-33` 的 `family` 枚举 = `industrial` / `ruby-slicc` / `academic`；ArchForge 侧填 `industrial` |
| **建议落点** | `07 号 §5.1.1` 增补一行「ArchForge `moesi_gpu`（与 Ruby `MOESI_AMD_Base`/`GPU_VIPER` 同语义）」 |
| **优先级** | **P2** |

### R-9. CEP 需明确「无 `translate(from, to)` 接口」

| 项 | 内容 |
|----|------|
| **需求** | CEP 侧显式声明：协议插件接口**不含**双协议转换方法；跨域桥接 = 「一致性模型翻译 + proxy-cache」 |
| **实证** | `docs/microarchitecture/coherence-protocol.md:149-151`（`translate(probe, from, to)`）；`docs/microarchitecture/coherence-bridge.md:49/81`（两份协议指针） |
| **现状** | `ADR-CEP-13` 决策 3 已给出机制，但**未禁止**插件接口里出现 `translate`；若不澄清，CEP Stage 1 的插件接口形状会被 ArchForge 的接口绑架 |
| **建议落点** | `ADR-CEP-12`（插件能力映射）+ `ADR-CEP-13` 决策 3 增「负向约束」 |
| **优先级** | **P0**（影响 Stage 1 插件接口定稿） |

### R-10. `CoherenceDomain` 弃用后的「域」概念需与 CEP 对齐

| 项 | 内容 |
|----|------|
| **需求** | ArchForge 侧停用「CoherenceDomain」作为模块名（该名在 CEP 指**一致性域**）；并在 CEP Stage 2 消费 `coherence_domains` JSON 字段 |
| **实证** | `include/core/coherence_domain.hh:30`（已 `[[deprecated]]`）；`INV-CEP-07A-IC3`（4 个 config 依赖 `coherence_domains` 字段，Stage 2 消费，Stage 0~1 标 `not-consumed`）；`ADR-CEP-13` 决策 1（一致性域定义） |
| **现状** | 两处同名不同义：ArchForge 的「域」= per-cache 状态容器；CEP 的「域」= Ordering Point + ppo 的范围 |
| **建议落点** | ArchForge 侧文档全面改用「Stub Cache Core」+「Sharer Tracker」+「一致性域」三个词；`ADR-CEP-13` 明确 `coherence_domains` JSON 的消费语义 |
| **优先级** | **P1** |

### R-11. 「真实缓存 + CEP 协议」的路线需在 Stage 1 前定案

| 项 | 内容 |
|----|------|
| **需求** | 明确 dGPU SoC 的一致性缓存模型走 (a) CEP `Stub Cache Core` 还是 (b) `CacheTLM` + adapter；并据此裁定 `register_cache_callback` 是否**永不复现** |
| **实证** | `ADR-CEP-15` 决策 4（adapter 路径归 Stage 4+，Stage 1~3 不承诺）；`docs/architecture/09-coherence-protocol.md:250/256/430/459`（4 处 snoop callback 设计） |
| **现状** | `ADR-CEP-15` 决策 4 的 adapter 方向是 `CacheTLM → Coherence Interface`（单向下投影），**snoop 是反方向** → 走 (b) 时 snoop 无处安放 |
| **建议落点** | **ArchForge 侧** `ADR-SOC-25` 采纳 (a)；CEP 侧在 `ADR-CEP-15` 补一句「若走 (a)，`CacheTLM` 侧无需任何 snoop 入口」 |
| **优先级** | **P0**（直接决定 ArchForge Phase 7.C 是否还写 `snoop_callback`） |

### R-12. `perm` 与 Capability 的正交性需在 schema 中显式

| 项 | 内容 |
|----|------|
| **需求** | 显式声明 `perm` **不承载**安全 / 租户语义；或新增与 `perm` 正交的 `capability` 字段组 |
| **实证** | `docs/architecture/22-nsa-fabric-address-spec.md §0.5.1 #10`（Capability Token 128 bits）；`docs/architecture/25-nsa-hardware.md §3.2`（`[23:16] Tenant ID`）；`docs/architecture/27-nsa-capability.md` |
| **现状** | CEP `perm` 4 值只表达一致性权限；若把 capability 混进同一枚举，会重演 `07 §5.4`「协议专属字段泄漏进共享抽象」的错误 |
| **建议落点** | `protocol_instance.schema.json` 的 `perm` 描述字段 + `ADR-CEP-12` 说明「capability 属 Fabric / 控制面层，不在协议实例声明内」 |
| **优先级** | **P1** |

### R-13. `ADR-CEP-11 §3` 版本锁定表需收录 ArchForge 贡献的两个协议实例

| 项 | 内容 |
|----|------|
| **需求** | `ADR-CEP-11 §3` 的规范版本锁定表（**唯一真源**）需增 2 行：<br>`moesi_gpu` → `moesi-gpu-1.0`（MOESI/GPU 6 态 I/S/E/M/O/T × 6 事件；AMD MOESI + GPU 扩展）<br>`mesif` → `mesif-1.0`（MESIF 变体 M/E/S/I/F；单 Owner + Forward） |
| **实证** | 本仓 `docs/architecture/09-coherence-protocol.md §3`（6 态 6 事件表）+ `docs/architecture/25-nsa-hardware.md §4.2`（MESIF 状态编码） |
| **现状** | `INV-CEP-11-IC1`：「每个协议实例的 `protocol_version` **必须**落在 §3 锁定表内；表外取值 = **装配期 fail**（不得静默降级）」。当前锁定表只有 CHI / CXL 2.0 / CXL 3.0 / TileLink-C / NVLink / UALink 六族，**不含** `moesi_gpu` / `mesif` → §6.1 / §6.2 的声明**当前必然装配期 fail** |
| **附带约束** | `ADR-CEP-11 §3` 的使用规则第 2 条：「表中**不含**任何未列入 §5.1 的协议族」→ 需 CEP 侧同步把这两个实例纳入 `07 号 §5.1` 的协议族清单（或明确豁免该规则） |
| **schema 附带发现** | `protocol_version` 的 pattern `^[a-z0-9]+(-[a-z0-9.]+)*$` **不接受** `1.0.0` 形式（首段不能含 `.`）→ 本仓实例用 `moesi-gpu-1.0` / `mesif-1.0` 形式 |
| **建议落点** | `ADR-CEP-11 §3` 锁定表 + `07 号 §5.1` 协议族清单 |
| **优先级** | **P0**（不解决则 §6 的协议实例声明无法通过装配期校验，C-4 判据不可机器验收） |

---

## 12. ArchForge 侧交付物清单

> 面向 C-1/C-2/C-3 放行判据（**判据 C-1 需按 F-8 协商改为「接口规约 PR」**）。

| # | 交付物 | 形态 | 对应判据 | 状态 |
|---|--------|------|---------|------|
| D-1 | 6 问书面结论 | 本仓文档 §10 + roadmap §5 答复表 | C-3 | ✅ 本文完成 |
| D-2 | P0-1 ~ P0-5 逐项结论 | roadmap §4 增列结论列 | C-2 | ✅ 本文完成 |
| D-3 | 4 类 Bundle ↔ canonical 10 流 映射表 | 本仓文档 §7 | C-2 / P0-3 | ✅ 本文完成 |
| D-4 | 6→4 投影表 + 语义损失说明 | 本仓文档 §7.2 | C-2 / Q6 | ✅ 本文完成 |
| D-5 | 协议实例声明（`moesi_gpu` / `mesif`） | 本仓文档 §6（JSON） | C-4 | ✅ 本文完成 |
| D-6 | 一致性域声明（3 域 + 桥接粒度 + 域可见写判据） | 本仓文档 §5 | C-2 | ✅ 本文完成 |
| D-7 | **per-network** VC 分配矩阵（每网络 4 VC × 6 消息类）+ network 命名空间 + `vc_count` | 本仓文档 §6.0.2 + `22-nsa §0.5` 扩展 | C-4 / R-5' / R-5'' / R-6' | ✅ 矩阵已交付（§6.0.2）；network 清单待补 |
| D-8 | 架构决策记录 | [`ADR-SOC-25`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md) | C-1 | ✅ 已出 |
| D-9 | `09-coherence-protocol.md` 的文档层返工（8 处） | 文档修订 | C-2 | 🔶 待执行 |
| D-10 | R-1 ~ R-13 需求单 | 本仓文档 §11 | — | ✅ 本文完成 |

---

## 13. 风险与缓解

| # | 风险 | 等级 | 缓解 |
|---|------|:----:|------|
| **RK-1** | **放行判据 C-1 结构上不可闭合**（ArchForge 无代码仓，产不出「接口 PR」） | 🔴 高 | **优先与 CppTLM 侧协商**把 C-1 改为「接口规约 PR」（F8）；这是本轮唯一的**治理级**阻塞，优先于一切技术结论 |
| **RK-2** | R-2（`perm` 静默升级）不被 CEP 采纳 → D-CPU↔D-GPU 跨域正确性无法论证 | 🟡 中 | ArchForge 侧按 `ADR-CEP-13` 决策 3 判据**自行论证**并写入 D-6 声明；CEP 侧缺席时以「声明 + 实验证伪」模式兜底（per `ADR-CEP-06 §3` `verification_mode`） |
| **RK-3** | R-1（分级目录）不被采纳 → D-FABRIC 域无法建模，NSA Stage 2/3 阻塞 | 🟡 中 | 降级方案：先用 `TreeManager`（scope=SUBTREE）近似三级目录，把「多级聚合」作为 ArchForge 侧扩展标签承载 |
| **RK-4** | 提问单 §2 的实现状态误判导致 CEP 侧按「已实现」排期 → 双方预期错位 | 🟡 中 | 本文档 §2 的「文档断言 / 代码实证 / 判定」三列表可作为后续所有跨仓断言的**取证模板** |
| **RK-5** | 文档返工（D-9）触碰 8 处 09 号引用 → 与其他文档的引用一致性破裂 | 🟢 低 | 返工时同步更新 `docs/microarchitecture/coherence-*.md` 与 `docs/architecture/INDEX.md`；改完跑一次全仓 `file:line` 引用检查 |
| **RK-6** | 5 阶段 NSA 路线（`29-nsa-evolution-roadmap.md`）与 CEP Stage 1~3 路线**并行推进但不同步** | 🟡 中 | 在 `29-nsa-evolution-roadmap.md §3 交付物清单` 中标注各阶段对 CEP Stage 的依赖点（R-1/R-4 落在 NSA Stage 2） |

---

## 14. 维护记录

| 日期 | 版本 | 作者 | 修订 |
|------|------|------|------|
| 2026-10-21 | v0.1 | ArchForge (coherence owner) | 首版：CEP 提问单审阅（8 项发现）+ 体系 A/B 收敛诊断 + CEP 分层映射 + 3 域重划 + 2 个协议实例声明 + P0-3 映射表 + 6 问答复 + R-1~R-12 需求单 |

**下次更新**：待 CppTLM 侧对 R-1 ~ R-13 逐条答复后升 v0.2（补「CEP 侧回执」列）
