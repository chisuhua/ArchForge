# ADR-SOC-25: 一致性架构改采 CEP 框架对齐（协议插件化 + 能力声明 + 域重划）

> **状态**: 📋 Proposed — 2026-10-21
> **日期**: 2026-10-21
> **Owner**: ArchForge Team (coherence owner)
> **影响**: L7 Coherence 子系统架构（09 号）+ NSA 跨卡一致性（25/30 号）+ 跨仓协作（CppTLM CEP）
> **类别**: SoC 架构 / 一致性协议 / 跨仓治理
> **关联文档**:
> - [`docs/architecture/32-cep-based-coherence-architecture.md`](../architecture/32-cep-based-coherence-architecture.md) **详细设计（本文的展开）**
> - [`docs/architecture/09-coherence-protocol.md`](../architecture/09-coherence-protocol.md) L7 Coherence（本文的返工对象）
> - [`docs/architecture/25-nsa-hardware.md`](../architecture/25-nsa-hardware.md) §4 Hardware Directory
> - [`docs/architecture/30-nsa-comprehensive-supplement.md`](../architecture/30-nsa-comprehensive-supplement.md) §2 跨节点一致性模型
> - [`docs/roadmap/cep-interface-alignment.md`](../roadmap/cep-interface-alignment.md) **上游提问单 + 本 ADR 的答复载体**
> - **关联 ADR**: ADR-SOC-01（一致性协议分步走策略，**本文部分修订其 Phase 7.C 表述**）、ADR-SOC-22 / 23 / 24（NSA 系列）
> **跨仓依据**（CppTLM 仓，只读引用）:
> - `docs/architecture/07-coherence-exploration-platform.md`（CEP 6 层 + canonical 10 流 + 66 条 invariant）
> - `docs/adr/ADR-CEP-{00,02,04,05,07A,12,13,15,17}.md`
> - `include/tlm/cep/protocol_instance.schema.json`（协议实例声明 schema，13 属性 / 7 字段组）

---

## 1. Context (背景)

### 1.1 触发事件

2026-10-21，CppTLM 仓的 CEP（Coherence Exploration Platform）DRI 向本仓提出
[`docs/roadmap/cep-interface-alignment.md`](../roadmap/cep-interface-alignment.md)，
列出 6 个需本仓裁决的接口问题 + 5 项 P0 冲突，并声明：

> **ArchForge 协议接口 PR 未合入前，CppTLM 对应 OpenSpec change 不得从 Proposed Draft 转 Proposed**
> （per `ADR-CEP-00 §2` 决策 3）

本 ADR 是对该提问单的**正式答复**，同时是对本仓一致性架构的**重构决策**。

### 1.2 根本问题：本仓有两套互不承认的一致性架构

| 体系 | 协议 | 查找机制 | 载体 | 文档 |
|------|------|---------|------|------|
| **A：SoC 内** | MOESI/GPU 6 态 `I/S/E/M/O/T` × 6 事件 | snoop 广播 | `CoherenceDomain` + `CoherenceBridge` + `SnoopFilter` + `CoherentXBar` | `09-coherence-protocol.md` |
| **B：NSA 跨卡** | MESIF 变体 `M/E/S/I/F` | 三级目录查询 | Hardware Directory L1/L2/L3 + Remote Query(VC2) + Remote Atomic(VC1) | `25-nsa-hardware.md §4` |

两者的**状态词表**（6 态 vs 5 态）、**查找机制**（广播 vs 目录）、**一致性模型**（未声明 vs 按 fabric scope 分级的 RC）
全部冲突，且**从未对账**。这是本仓一致性问题里最大的架构缺口 —— 而提问单对此**一字未提**。

### 1.3 实现状态的取证结论（与提问单的断言有出入）

逐条回查 CppTLM 仓代码后确认：

| 提问单 §2 断言 | 代码实证 | 判定 |
|----------------|---------|------|
| `class CoherenceProtocol` 抽象基类 | `include/core/coherence_protocol.hh` **不存在**；`grep -rn CoherenceProtocol include/ src/` → **0 命中** | 未实现 |
| `class CoherenceBridge`（8 端口） | `grep -rln CoherenceBridge include/ src/` → **0 命中** | 未实现 |
| `register_cache_callback(CacheTLM*)` | 全仓 **0 命中** | 未实现 |
| `CacheTLM` 含 snoop 语义 | `grep -c "snoop\|coherence" include/tlm/cache_tlm.hh` → **0** | **天然满足 `INV-CEP-15-IC3`** |
| `enum class Protocol { MESI, MOESI }` | `include/core/coherence_domain.hh:25-28` —— **已 `[[deprecated]]`** | 冲突已在 CppTLM 侧消解 |
| `enum class SnoopType` / `SnoopResp` | 全仓 **0 命中** | 仅文档级 |

> 即：提问单 §3-Q3 所述「直连是**已实现**的……需要你们确认是否愿意改路径」**前提不成立**。
> 详见 [`32-cep-based-coherence-architecture.md §2`](../architecture/32-cep-based-coherence-architecture.md#2-对提问单的审阅结论8-项发现)。

### 1.4 治理级阻塞

放行判据 **C-1** 要求「ArchForge 侧存在**已合入**的 coherence 接口 **PR**」。
本仓是**纯设计仓**（`git log` 全为 `docs(...)` 提交，无 `src/`、无 `include/`），
**结构上无法**产出「接口 PR」→ C-1 永远无法闭合 → CEP 的 M2 准入门**永久阻塞**。

---

## 2. Decision (决策)

### D1. 一致性架构改采 CEP 框架对齐：ArchForge 从「协议实现方」转为「协议语义规约 + 一致性域声明方」

**决策**：本仓的一致性架构**不再自建协议栈**，改为在 **CppTLM CEP（Coherence Exploration Platform）** 框架下
以「**协议语义规约 + 能力声明 + 一致性域声明**」的形式交付；全部 C++ 实现归 CppTLM 仓
（per `ADR-CEP-00 §2` 决策 1 的代码归口）。

**理由**：
1. CEP 的分层（协议逻辑住 Plugin、能力以数据声明）**正好**把体系 A 与体系 B 的差异压缩为
   「用哪个协议插件 + 用哪个 Sharer Tracker」两个可配置项（详见 `32 号 §3.3`）—— 这是本仓自己造不出的一致性收敛；
2. gem5 Ruby 类比已被采纳（`07 号 §1.4`）：可插拔协议探索**必须**是框架能力，不能是某个 SoC 的私有扩展；
3. 本仓**没有代码仓**，实现类承诺本就不可持续。

**边界**：本 ADR **不**否决任何已有 NSA 设计 —— 它改变的是**归属与表达**：
体系 A/B 的语义规约、域划分、目录形态、VC 绑定**全部保留**，只是改用 CEP 术语与 CEP 声明面承载。

### D2. 6 态 `CoherenceState` 下沉到协议插件；顶层只保留 4 值 `perm` 投影

**决策**：`I/S/E/M/O/T` 降为 **MOESI/GPU 协议插件的私有状态机**；跨域接口只承载 CEP 的 4 值 `perm`
（`NONE` / `READ` / `UNIQUE` / `WRITEBACK`）。

**6 → 4 投影表**（权威版，见 `32 号 §7.2`）：

| 6 态 | → `perm` | 备注 |
|------|-----------|------|
| `I` | `NONE` | |
| `S` | `READ` | |
| `E` | `UNIQUE` | **可静默升级到 `M`** → 触发 R-2 |
| `M` | `WRITEBACK` | |
| `O` | `WRITEBACK` | 与 `M` 合并 → 信息损失由 Sharer Tracker 补偿 |
| `T` | **无投影** | 协议私有态（`INV-CEP-05-IC1`） |

**理由**：`O`/`T` 在 4 值下无投影，正说明它们**不是跨域接口的类型**；CEP 的 `INV-CEP-05-IC1` 分层正确。

### D3. `CoherenceProtocol` 抽象基类下沉为 CppTLM 侧 ProtocolEngine 插件接口（附 3 项强制修订）

**决策**：采纳提问单 Q2-B，但**必须**同时满足：

| # | 修订 | 理由 |
|---|------|------|
| **D3-a** | **`translate(probe, from, to)` 从插件接口移除** | 双协议感知接口与 `ADR-CEP-13` 决策 3（桥接靠「一致性模型翻译 + proxy-cache」，两侧插件各自处理自己的请求）不兼容 |
| **D3-b** | **请求语义携带一致性标签，不得用 `bool is_write, bool is_read`** | `consistency_labels.request_level` 正是为此存在（HeteroGen §VII-B：目录无法区分 read vs acquire → 请求改名） |
| **D3-c** | **基类更名为 `ProtocolEngine`；`can_coexist(a,b)` 降为插件内部工具** | 协议无关层不得出现协议标识符（`INV-CEP-07A-IC2`）；`can_coexist` 属协议私有状态机 |

**连带**：ArchForge `09 §10.1` 的「（待新建）`include/core/coherence_protocol.hh`」计划**取消**；
`09` 的 6×6 转换表**保留为协议语义规约**，交付 CppTLM 实现为 `MoesiGpuAdapter`。

### D4. 撤下 `snoop_callback` 设计；dGPU SoC 一致性缓存模型改用 CEP `Stub Cache Core`

**决策**：
1. 撤下 `register_cache_callback(CacheTLM*)` 与 `cache_tlm_integration = "snoop_callback"`（共 5 处文档位置）；
2. dGPU SoC 的一致性缓存模型走路线 **(a)**：直接用 CEP `Stub Cache Core`；
   路线 (b)（`CacheTLM` + adapter）归 **Stage 4+**，且 `CacheTLM` 侧**永不**实现 snoop。

**理由**：
1. 零迁移成本 —— `CacheTLM` 当前 `snoop`/`coherence` 标识符 **0 次**，`INV-CEP-15-IC3` **已满足**；
2. `ADR-CEP-15` 决策 4 的 adapter 方向是 `CacheTLM → Coherence Interface`（**单向下投影**），
   而 snoop 是**反方向** —— 方向本就搞反；
3. 路线 (a) 与 CEP 的框架定位（`07 §1.1`）一致，且使 `09 §5.3`「Phase 7.C snoop callback → CacheTLM 集成」不再成立。

**连带修订**：ADR-SOC-01 §3 实施表中「7.C `CacheTLM` 引入 `CoherenceState` 标签 + 6×6 state transition switch 表」
改为「**Stub Cache Core** 承接 6×6 状态机；`CacheTLM` 保持协议无关」。

### D5. `CoherenceDomain` 拆分为 Stub Cache Core + Sharer Tracker；停用「CoherenceDomain」作为模块名

**决策**：

| 现有职责 | 归属 |
|---------|------|
| 缓存行的**本地**状态（I/S/E/M） | **Stub Cache Core**（每 L1/L2 一份） |
| 缓存行的**全局**状态（谁持有） | **Sharer Tracker**（Directory & Ordering Plane） |

**并停用「CoherenceDomain」作为模块名** —— 该名在 CEP 语境下已被占用（指**一致性域**，
per `ADR-CEP-13` 决策 1：一致性域 = 一个 Ordering Point 生效 + 一套自己的 `ppo` 生效的范围）。

**理由**：`09 §5.1` 给 `CoherenceDomain` 的职责（状态表 + 响应 snoop + 触发状态转换）
**同时**做了两件在 CEP 里必须分开的事 —— 这正是 `INV-CEP-05-IC1`（stub 只暴露稳定态）
与 `07 §2.2`（目录平面负责 sharer 跟踪）的边界所禁止的。

**连带**：`CoherentXBar` 的每端口 `domain_id` 降为**配置期标签**（决定端口请求路由到哪个插件实例 / 哪个 Sharer Tracker）。

### D6. 一致性域重划为 3 域

**决策**：

| 域 | 范围 | 一致性模型 | Ordering Point |
|----|------|-----------|---------------|
| **D-CPU** | CPU 核 + CPU LLC | SC | 本地 LLC 目录 |
| **D-GPU** | 单 GPU 的 SM/L1/L2/TCC + VRAM | RC | GPU 侧 L2 Directory |
| **D-FABRIC** | 跨 Compute Tray / 跨 Fabric | 弱 RC | NSA Switch Coherency Engine + L3 Directory |

**跨域桥接粒度**（per `INV-CEP-13-IC3`，由对端协议是否允许提前 ack 决定）：
- D-CPU ↔ D-GPU：**保守**（全部串行），待 `moesi_gpu` 插件规约明确写 ack 语义后可转激进；
- D-GPU ↔ D-FABRIC：**激进**（同地址串行，跨地址可并发）—— Remote Atomic 由 NSA Switch 锁定目标 cache line。

**理由**：`30-nsa §2.3` Rule 1-4 已给出按 fabric scope 分级的模型；CEP 的 `ADR-CEP-13` 决策 2 的
**复合一致性公理** `acyclic(ppo_com ∪ rfe ∪ fr ∪ ws)` 提供了跨异构域组合的正确性判据 ——
这正是「CPU(SC) + GPU(RC)」组合所缺的。

### D7. 跨域接口采用 CEP 4 值 `perm` 词表

**决策**：跨域接口只传 4 值 `perm`；`O`/`M` 合并的信息损失**由 Sharer Tracker 补偿**（而非依赖 `perm` 表达）。

**并向 CEP 提出 R-2**：`perm` 需能表达「可静默升级」——
`moesi_gpu` 的 `state_transition[2][1] = 3`（E + Write → M）满足 `ADR-CEP-13` 决策 3 的
「域可见写」判据 (a)（终态允许 store 命中且无需外部通信），因此**跨域时必须触发传播**，
而 4 值 `perm` 无法区分「静默升级」与「显式请求升级」。

> 该需求**命中 CEP `ADR-CEP-05 §10`（`:223-225`）已写下的触发条件**：
> 「若组合协议需要区分静默 E→M 升级与显式请求升级，则 Stub 的 4 值 `perm` 表达力不足 → 重新评估 (β) 独立接口方案」。

### D8. `vc_id` 命名空间与网络排序属性由本仓承载；协议→VC 绑定表归协议实例声明

**决策**（对提问单 Q4 的**拆分**答复）：

| 子项 | 权威方 | 依据 |
|------|--------|------|
| `vc_id` 命名空间（0-3） | **本仓 / CppTLM NoC Bundle 层**（已存在） | `noc_bundles_tlm.hh:38` + `08-noc-interconnect.md:205-212`；与 CEP schema 的 0..3 **同域** |
| 各网络的排序属性 | **本仓声明**（逐网络） | `08 §4.1`；NSA Switch PBR |
| 消息类 → `vc_id` 绑定表 | **协议实例声明**（CEP schema 承载） | 绑定是协议属性 |
| 死锁自由性论证 | **CEP 侧**（`ADR-CEP-09`） | `07 §2.2` |

**4 VC × 5 消息类分配（草案）**：`VC0 = request/snoop`、`VC1 = atomic`、`VC2 = query`、`VC3 = response/snoop_resp`。
NSA 已占 VC1=Atomic、VC2=Remote Query（`25 §3.1/§4.3`），本分配与之相容。

### D9. 协议实例拆分口径：2 个协议实例 + 1 个 SharerTracker 选型

**决策**：

| 项 | 口径 |
|----|------|
| `moesi_gpu` | 1 个协议实例（`family = industrial`）；MESI 是其退化配置，不独立计 |
| `mesif` | 1 个协议实例（`family = industrial`），与 `moesi_gpu` 并列做 A/B 对比 |
| NSA 三级 Hardware Directory | **不是协议实例**，是 SharerTracker 选型 → 不计 adapter |
| `moesi_gpu` vs Ruby `MOESI_AMD_Base`/`GPU_VIPER` | **同语义不同实现** → 依 `07 §5.1.4`「不重复计数」，两边各计各的 |

**连带**：收敛 `25-nsa §4.4` + `§7` 开放问题 #4（MESIF vs MOESI vs MESI）
→ **不做单选，做可实例化的 A/B**（这正是 CEP 的存在价值）。

### D10. 向 CppTLM CEP 提出 R-1 ~ R-13 需求单

**决策**：本仓向 CEP 提交 13 项需求（`32 号 §11`），其中 **P0 级 5 项**：

| # | 需求 | 阻塞什么 |
|---|------|---------|
| **R-2** | `perm` 加「可静默升级」判别位 | D-CPU↔D-GPU 跨域正确性论证；命中 `ADR-CEP-05 §10` 已写下的触发条件 |
| **R-6** | 消息类词表 `{request,response,snoop,atomic,query}` + NoC Bundle 类别扩展 | 放行判据 C-4（机器可验收的双向映射） |
| **R-9** | 显式声明「插件接口不含 `translate(from,to)`」 | CEP Stage 1 插件接口定稿 |
| **R-11** | 「真实缓存 + CEP 协议」路线在 Stage 1 前定案 | 本仓 Phase 7.C 是否还写 `snoop_callback` |
| **R-13** | `ADR-CEP-11 §3` 版本锁定表增 2 行（`moesi-gpu-1.0` / `mesif-1.0`） | `INV-CEP-11-IC1`：表外取值 = **装配期 fail** → 本仓 `32 号 §6` 的协议实例声明当前必然 fail,C-4 不可机器验收 |

**P1 级 8 项**：R-1（分级目录第 6 实现）、R-3（`consistency_labels` scope 分级）、R-4（`atomic` 语义标签）、
R-5（network 命名空间清单）、R-7（目录式远端查询的流组合规范）、R-8（`family` 口径）、
R-10（`CoherenceDomain` 弃用后的域概念对齐）、R-12（`perm` 与 Capability 的正交性）。

### D11. 请求把放行判据 C-1 从「接口 PR」改为「接口规约 PR」

**决策**：向 CppTLM 侧提出协商请求 —— C-1 改为「ArchForge 侧存在**已合入的接口规约文档**」
（形态 = 本 ADR + `32 号`文档 + roadmap 答复表），实现型 PR 归 CppTLM 仓。

**理由**：本仓无代码仓，C-1 在现行措辞下**永远无法闭合**，CEP M2 准入门将**永久阻塞**
（per `ADR-CEP-00 §2` 决策 3）。**这是本轮唯一的治理级阻塞，优先于一切技术结论。**

---

## 3. 影响面

### 3.1 本仓文档返工清单（9 份）

| 文档 | 改动 | 依据 |
|------|------|------|
| `architecture/09-coherence-protocol.md` | 8 处：`:112` `CoherenceState` 标注、`:242` 删嵌套枚举、`:250` 删 `register_cache_callback`、`:256` §5.3 改写、`:399` 取消新建计划、`:430` §10.3 改写、`:444` §11 协议字段补注、`:459` 删 `snoop_callback` 配置 | D2/D3/D4 |
| `architecture/09-coherence-protocol.md` §6.2 / §7.2 | 跨域流程补 4 值 `perm`；`SnoopEntry` 归并入 `snoop_filter.md` 版本 | D2/D7 |
| `microarchitecture/coherence-protocol.md` | `:73-83` 6 状态表 → 标注「插件内部规约」+ 补投影表；`:112` 标注；`:133-155` 5 个纯虚 → 拆分「插件接口 / 插件实现」；`:32` Bundle 类型按 §7.1 重述；`:149-151` 删 `translate` | D2/D3 |
| `microarchitecture/coherence-domain.md` | `:68` `enum class Protocol` 标注已 deprecated；`:70-101` API 改为 Stub Cache Core + Sharer Tracker 拆分 | D5 |
| `microarchitecture/coherence-bridge.md` | `:49/81/121` 双协议指针 → proxy-cache 内嵌实例；`§2.2` 端口 Bundle 按 §7.1 重述 | D3-a/D7 |
| `microarchitecture/snoop_filter.md` | 明确为 CEP `SparseSnoopFilter` 选型；补 `caps` 声明 | D5 |
| `architecture/25-nsa-hardware.md` | `§4.4` 收敛为 MESIF/mesif 实例；`§4.1` 映射到 SharerTracker；`§7` 开放问题 #4 关闭 | D9 |
| `architecture/08-noc-interconnect.md` | `:205-212` 补「本仓是 `vc_id` 命名空间权威方」 | D8 |
| `architecture/22-nsa-fabric-address-spec.md` | `§0.5` Glossary 扩一维：network 命名空间 | D8 / R-5 |

### 3.2 对 NSA 演进路线的影响

`29-nsa-evolution-roadmap.md §3` 交付物清单中：
- **NSA Stage 2**（硬件加速，2027-2028）依赖 **R-1**（分级目录）与 **R-4**（atomic 语义标签）；
- **NSA Stage 3**（CXL 3.0 完整）依赖 **R-3**（scope 分级标签）与 **R-12**（capability 正交）。

### 3.3 对 CppTLM 侧的影响（预期）

| 项 | 影响 |
|----|------|
| `ADR-CEP-00 §2` 决策 3 准入门 | 判据 C-1 措辞待协商（D11） |
| `ADR-CEP-05` 插件接口 | 受 D3-a/b/c 三项修订影响 → 需在 Stage 1 前定稿 |
| `ADR-CEP-04 §2` | 需增第 6 种 SharerTracker 实现（R-1） |
| `protocol_instance.schema.json` | 需改 `perm`（R-2）、`atomic`（R-4）、`consistency_labels`（R-3）、`sharer_tracker.impl`/`caps`（R-1）、`perm` 与 capability 正交声明（R-12） |
| `ADR-CEP-12` | 需增「插件接口不含 `translate`」负向约束（R-9） |
| `ADR-CEP-15` | 需补「若走 Stub Cache Core 路线，`CacheTLM` 侧无需任何 snoop 入口」（R-11） |

---

## 4. Consequences (后果)

### 4.1 正面

| # | 后果 |
|---|------|
| **+1** | **体系 A 与体系 B 首次对账** —— 差异被压缩为 2 个可配置项，而非两套并列代码路径 |
| **+2** | 本仓 6 问全部有结论 → **解除 CEP M2 准入门的技术阻塞**（治理阻塞另议，见 D11） |
| **+3** | `CoherenceDomain` 的双重职责消除 → `09 §5.1` / `§7.1` 的长期语义混乱收敛 |
| **+4** | NSA 开放问题 #4（一致性协议选型）从「待讨论」变为「可 A/B 实验」 |
| **+5** | 本仓从「协议栈维护者」转为「协议语义 + 域声明维护者」→ 职责边界清晰，与本仓**无代码仓**的事实一致 |
| **+6** | `snoop_callback` 零迁移成本撤下 → `CacheTLM` 天然满足 `INV-CEP-15-IC3`，无回归风险 |

### 4.2 负面 / 代价

| # | 代价 | 缓解 |
|---|------|------|
| **−1** | 本仓失去对一致性实现细节的直接控制 —— 依赖 CppTLM 侧按规约实现 | 规约文档须**足够精确**（6×6 转换表 + 投影表 + 域声明 + VC 表，详见 `32 号 §12` 交付物清单） |
| **−2** | R-1 ~ R-4 / R-12 若不被 CEP 采纳 → 部分域无法在 CEP 内建模 | 降级方案（`32 号 §13` RK-3）：先用 `TreeManager` 近似三级目录；跨域正确性走「声明 + 实验证伪」模式（per `ADR-CEP-06 §3`） |
| **−3** | 9 份文档返工 → 引用一致性风险 | 返工后跑全仓 `file:line` 引用检查（`32 号 §13` RK-5） |
| **−4** | D11 若协商失败 → CEP 准入门继续阻塞 | 作为**治理级**议题单独跟进，优先级高于技术收敛 |

### 4.3 被本 ADR 取代 / 修订的既有决策

| 既有决策 | 处置 |
|---------|------|
| **ADR-SOC-01** §2 决策「Phase 7.C：将 `CacheTLM` 升级为 protocol-aware……`CoherenceDomain` 与 `CacheTLM` 通过 snoop callback 集成」 | **修订** → 改为「Stub Cache Core 承接协议侧 snoop；`CacheTLM` 保持协议无关」（D4）。ADR-SOC-01 主体保留（分步走策略、write-through 起步、6×6 表），以 Status Update 追加 |
| **ADR-SOC-01** §3 实施表「7.C `CacheTLM` 引入 `CoherenceState` 标签 + 6×6 switch 表」 | **修订** → 6×6 表移入协议插件 |
| `09 §5.1` `CoherenceDomain` 职责 | **取代** → 拆分为 Stub Cache Core + Sharer Tracker（D5） |
| `25 §4.4` 一致性协议选型开放问题 | **收敛** → `mesif` 与 `moesi_gpu` 并列 A/B（D9） |

---

## 5. Verification (验收)

| # | 验收项 | 方法 |
|---|--------|------|
| V-1 | 6 问各有书面结论且落点可追溯 | roadmap `cep-interface-alignment.md §5` 答复表填满 |
| V-2 | P0-1 ~ P0-5 逐项有结论 | roadmap `cep-interface-alignment.md §4` 增列结论列 |
| V-3 | P0-3 映射表存在且逐类型可追 | `32 号 §7.1` |
| V-4 | 6→4 投影表存在且标注两处语义损失 | `32 号 §7.2` |
| V-5 | 协议实例声明可被 CEP schema 校验 | `32 号 §6.1/§6.2` 的 JSON → `protocol_instance.schema.json` 校验通过 |
| V-6 | 3 域声明含桥接粒度 + 域可见写判据 | `32 号 §5` |
| V-7 | 9 份文档返工完成且无悬空引用 | 返工 diff + 全仓 `file:line` 检查 |
| V-8 | R-1 ~ R-12 需求单送达并有 CEP 侧回执 | CEP 侧 reply（本 ADR 升 Accepted 的前置） |

---

## 6. Status Update

| 日期 | 版本 | 修订 |
|------|------|------|
| 2026-10-21 | v0.1 | 首版：对齐 CppTLM CEP 提问单（6 问）+ 体系 A/B 收敛诊断 + 11 项决策 + 9 份文档返工清单 + R-1~R-12 需求单 + 8 项验收 |

---

**关联 OpenSpec change**: 待创建（`openspec/changes/2026-10-21-archforge-cep-alignment/`）
**下次更新**: 待 CEP 侧对 R-1 ~ R-12 逐条答复后升 v1.0（Accepted / Rejected 逐条）
