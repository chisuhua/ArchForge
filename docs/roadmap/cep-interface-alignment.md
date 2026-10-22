# cep-interface-alignment: CEP ↔ ArchForge coherence 接口对齐提问单

> **类别**: SoC Architecture > Roadmap · **来源**: **CppTLM 跨仓请求**(CEP 项目的 M2 跨仓准入门前置)
> **日期**: 2026-10-21 · **提出方**: CppTLM CEP DRI · **答复方**: ArchForge coherence owner
> **状态**: ✅ **已答复(6 问全部给出结论)** · 答复轮 2026-10-21 · **复核轮 2026-10-21(N-1~N-4 已裁决,见 [复核回执](./cep-interface-alignment-review-2026-10-21.md))**
> · **清单轮 2026-10-22(CppTLM「待回应清单」10 条已逐条答复,见 [答复回执](./cep-interface-alignment-response-2026-10-22.md))**
> **答复载体**: [`ADR-SOC-25-cep-aligned-coherence-architecture.md`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md)(决策)
> + [`32-cep-based-coherence-architecture.md`](../architecture/32-cep-based-coherence-architecture.md)(详细设计 + 审阅结论 + R-1~R-12 需求单)
> **关联 ArchForge 文档**: [09-coherence-protocol.md](../architecture/09-coherence-protocol.md) ·
> [ADR-SOC-01-coherence-protocol-strategy.md](../adr/ADR-SOC-01-coherence-protocol-strategy.md) ·
> [coherence-domain.md](../microarchitecture/coherence-domain.md) ·
> [coherence-protocol.md](../microarchitecture/coherence-protocol.md) ·
> [coherence-bridge.md](../microarchitecture/coherence-bridge.md) ·
> [snoop_filter.md](../microarchitecture/snoop_filter.md)
> **关联 CppTLM 文档**: 完整对齐清单(13 项 gap 矩阵 + PR 范围 + 5 条放行判据 + 32 个机器可读锚点)→
> `CppTLM/docs/implementation/2026-10-21-cep-archforge-interface-alignment.md`

---

## 0. 一句话

CppTLM 正在建 **CEP(Coherence Exploration Platform)** —— 一个**协议中立**的一致性互联仿真平台;
它需要一个「协议实例能力声明」的载体,而 **ArchForge 当前的 coherence 接口是 MOESI/GPU 单协议特化的**,
两者在**状态归属 / 协议标识入口 / CacheTLM 耦合路径 / 流口径 / 抽象基类归属**上有 5 处需要**你们裁决**的分歧。
本提问单列出这 6 个问题、每问的选项与影响 —— **请只给结论,实现由 ArchForge 侧自行安排**。

---

## 1. 背景(给不熟悉 CEP 的读者)

### 1.1 CEP 是什么

CEP = CppTLM 的**框架级**一致性互联探索平台(定位类比 gem5 Ruby 之于 gem5:用于**互相协议探索**,
而非某个具体协议的实现)。它有 3 条对 ArchForge 最关键的硬约束:

| # | 约束 | 出处 |
|---|------|------|
| **H-1** | **协议状态住 Protocol Engine 插件内**;缓存核心只暴露 **4 值稳定权限**(`NONE`/`READ`/`UNIQUE`/`WRITEBACK`) | `CppTLM/docs/adr/ADR-CEP-05-stub-cache-core-interface.md:170`(`INV-CEP-05-IC1`) |
| **H-2** | **协议标识符不得出现在与协议无关的层**(Stub Cache / 目录与排序平面 / 流量生成器 / 拓扑 Python 层) | `CppTLM/docs/adr/ADR-CEP-07A-06bis-artifact-disposition.md:99`(`INV-CEP-07A-IC2`) |
| **H-3** | **`CacheTLM` 不得实现 canonical 10 流**(它无协议知识);CEP 与 `CacheTLM` 之间**只允许经 adapter 交互** | `CppTLM/docs/adr/ADR-CEP-15-cachetlm-alignment.md:115`(`INV-CEP-15-IC3`) |

### 1.2 CEP 的「协议实例声明」长什么样

CEP 里每个协议实例(CHI RN-F / CXL 3.0 / TileLink-C / MOESI_hammer / …)有一份**数据形态**的
能力声明(`CppTLM/include/tlm/cep/protocol_instance.schema.json`,**7 个字段组 / 13 个顶层属性**):

| 字段组 | 内容 |
|--------|------|
| 身份状态 | `id` / `family`(来源族)/ `adapter` / `status`(计数口径)/ `protocol_version`(规范版本锁定) |
| 能力面 | `flow_support`(**canonical 10 流**矩阵)/ `perm`(**4 值**)/ `atomic` |
| 前提假设面 | `consistency_labels` / `ordering_assumption`(网络 → 排序假设)/ `vc_binding`(消息类 → `vc_id`) |
| Sharer Tracker | `impl`(5 实现可插拔)+ `caps` 4 维(scope/completeness/authority/aggregation_at) |
| 组合能力 | `concurrent` / `hierarchical` / `heterogeneous` |

> **关键性质**:声明是**数据**,协议逻辑在**插件**里 —— 这是 CEP 与 ArchForge 当前
> 「协议逻辑 = 顶层 C++ 抽象基类 `CoherenceProtocol`」的根本分歧(见 **Q2**)。

### 1.3 为什么现在问

CEP 的 Stage 0 契约层已在 CppTLM 仓完成并冻结(21 份 ADR + 66 条守门 invariant + schema + lint + 3 个工具)。
但 CppTLM 侧的**跨仓准入门**(`CppTLM/docs/adr/ADR-CEP-00-platform-charter-and-governance.md` §2 决策 3)规定:

> **ArchForge 协议接口 PR 未合入前,CppTLM 对应 OpenSpec change 不得从 Proposed Draft 转 Proposed。**

2026-10-21 的取证结论是:**ArchForge 侧不存在已合入的 coherence 接口 PR**
(仓内 coherence 相关产物目前**只有设计文档**,见 §2)。因此 CEP 的 umbrella change 目前**停留
Proposed Draft**。**解这个阻塞需要你们的 6 个结论**(§3)—— 这是本提问单的唯一目的。

---

## 2. 两侧接口面现状(摘要)

> ⚠️ **答复轮勘误(2026-10-21)**: 本表的 **ArchForge 侧**各行是**设计文档级**的规约,
> 其中 6 项在 CppTLM 仓**尚未实现或已废弃**。下表「答复轮状态」列给出逐条代码实证。
> 完整取证见 [`32-cep-based-coherence-architecture.md §2`](../architecture/32-cep-based-coherence-architecture.md#2-对提问单的审阅结论8-项发现)。

| ArchForge 侧 | 位置 | 答复轮状态(CppTLM 仓代码实证) | CEP 侧 | 位置 |
|-------------|------|-------------------------------|--------|------|
| `enum class Protocol { MESI, MOESI }` | `coherence-domain.md:68` | ⚠️ **已 `[[deprecated]]`**(`include/core/coherence_domain.hh:25-28`,per ADR-CEP-07A 决策 1) | `perm` 4 值锁 | `ADR-CEP-02:66` |
| `enum class CoherenceState { I,S,E,M,O,T }` | `coherence-protocol.md:112` | ⚠️ 协议层**未落地**;仅 `include/ext/error_context_ext.hh:20` 有 debug 观测型枚举 | 协议状态住插件内 | `ADR-CEP-05:170` |
| `enum class SnoopType { INVALIDATE, DOWNGRADE_TO_S, READ_SHARED, READ_EXCLUSIVE }` | `coherence-protocol.md:117` | ⚠️ **仅文档级**(全仓 grep 0 命中) | canonical 10 流 | `ADR-CEP-02:55` |
| `enum class SnoopResp { ACK, NACK, DATA, DATA_AND_ACK }` | `coherence-protocol.md:125` | ⚠️ **仅文档级** | — | — |
| `class CoherenceProtocol`(抽象基类,5 个纯虚) | `coherence-protocol.md:133` | ⚠️ **未实现**(`include/core/coherence_protocol.hh` 不存在,grep 0 命中) | ProtocolEngine **插件**接口 | `ADR-CEP-12:163` |
| `class CoherenceDomain`(已实现)+ `DomainRegistry` | `coherence-domain.md:70` / `:94` | ⚠️ 存在但**纯配置层** + **已 deprecated**(`coherence_domain.hh:30`/`:55`);**无 snoop 成员** | — | — |
| `class CoherenceBridge`(8 端口) | `coherence-bridge.md:135` | ⚠️ **未实现**(grep 0 命中) | canonical 10 流(不新增端口) | `07 号 §5.1` |
| `class SnoopFilter` + `SnoopEntry{addr,sharers,shared_state}` | `09-coherence-protocol.md:311` | ⚠️ 与本仓 `snoop_filter.md:141-146` 的 `FilterEntry{bitset<16> sharers, CoherenceState, lru}` **不一致** | `sharer_tracker` 5 实现 + caps 4 维 | `ADR-CEP-04 §2` |
| `CoherentXBar`(每端口 `domain_id`) | `09-coherence-protocol.md §8` | ⚠️ **仅文档级** | — | — |
| `register_cache_callback(CacheTLM*)` | `09-coherence-protocol.md:250` | ⚠️ **未实现**(grep 0 命中);`cache_tlm.hh` 中 `snoop`/`coherence` 标识符 **0 次** → **天然满足 `INV-CEP-15-IC3`** | 只允许经 **adapter** 交互 | `ADR-CEP-15:115` |
| 配置 `params.protocol = "moesi_gpu"` / `cache_tlm_integration = "snoop_callback"` | `09-coherence-protocol.md §11` | ⚠️ **仅文档级** | `family` / `status` / `protocol_version` | `ADR-CEP-12:163` |

> **对提问单 §3-Q3 的影响**: 该问原文称「直连是**已实现**的(`include/core/coherence_domain.hh` 已有 snoop 相关成员)」。
> **代码实证不成立** → 该问从「是否愿意改路径」变为「**不要建成这样**」,迁移成本为零。详见 §2 勘误与
> [`32 号 §2 F2`](../architecture/32-cep-based-coherence-architecture.md#f2-严重结论反转-q3-的前提不成立答案从要不要改路径变成不要建成这样)。
>
> **对提问单 §3-Q4 的影响**: 该问原文称「ArchForge 侧当前**没有** VC / ordering 概念(这是**缺失**,不是冲突)」。
> **代码实证不成立** —— `include/bundles/noc_bundles_tlm.hh:38` 已有 `vc_id`(0-3),与 CEP schema 同域;
> `08-noc-interconnect.md:205-212` 已有 4 VC 死锁避免;NSA 已占 VC1=Atomic / VC2=Remote Query。
> 该问的前提应改为「**已存在,只是未声明**」。

> 完整的 13 项 gap 矩阵(G1~G13,含两侧 file:line)见 CppTLM 侧的
> `docs/implementation/2026-10-21-cep-archforge-interface-alignment.md` §3。

---

## 3. 6 个问题(请给结论)

> 每问给:① **问什么** ② **为什么必须问你们**(CEP 侧约束 + file:line)③ **可选方案** ④ **影响面**。
> **建议答复形式**:在 §5 的答复表里填「结论 + 一句话理由 + 若选方案 B 则给出落点文件」。

### Q1. 6 态 `CoherenceState` 的**归属层**

> ✅ **答复:A —— 下沉到协议插件。**
> 6 态是 MOESI/AMD 家族的**协议内编码**;`O`/`T` 在 4 值 `perm` 下无投影,正说明它们不是跨域接口的类型。
> 顶层只保留 4 值 `perm` 投影(投影表见 [`32 号 §7.2`](../architecture/32-cep-based-coherence-architecture.md#72-6-态--4-值-projection-表答复-q6-a))。

**问**:协议状态枚举(`I,S,E,M,O,T`)应**下沉到协议插件内部**,还是**保留在 ArchForge 顶层**
(`coherence-protocol.md:112` 与 `09-coherence-protocol.md:242` 两处)?

**为什么问你们**:
- CEP 的 `INV-CEP-05-IC1`(`ADR-CEP-05:170`)要求**协议瞬态态(如 `T`)与协议私有状态一律住
  Protocol Engine 插件内,不泄漏到 Stub 的 4 值 `perm` 枚举**。
- 而 `CoherenceState` 当前是**顶层协议特化类型**,且 `O`(Owned)/`T`(Transient)**没有** 4 值 `perm` 的投影。
- 这不是「谁对谁错」,而是**分层归属**问题 —— 只有设计仓能定。

**可选方案**:

| | 方案 | 说明 |
|---|------|------|
| **A** | 状态枚举**下沉到协议插件** | 顶层只留「协议无关的 4 值 `perm` 投影」;`O`/`T` 留在插件内。CEP 侧**无需豁免** |
| **B** | **保留顶层** + 出显式豁免 | ArchForge 出 ADR 豁免 `INV-CEP-05-IC1` 在 ArchForge 侧不适用;CEP 侧记录该豁免 |

**影响面**:P0-1(其余 P0 项的前置)· Q6 也依赖本问的结论。

---

### Q2. `CoherenceProtocol` 抽象基类的**归属仓**

> ✅ **答复:B —— 下沉为 CppTLM 侧 ProtocolEngine 插件接口 + 3 项强制修订。**
> ① `translate(probe, from, to)` 从插件接口**移除**(双协议感知与 `ADR-CEP-13` 决策 3 不兼容);
> ② 请求语义**携带一致性标签**,不得用 `bool is_write/is_read`;
> ③ 基类更名 `ProtocolEngine`,`can_coexist` 降为插件内部工具。
> 连带:ArchForge `09 §10.1` 的「待新建 `include/core/coherence_protocol.hh`」**取消**;
> 6×6 转换表**保留为协议语义规约**,交付 CppTLM 实现为 `MoesiGpuAdapter`。

**问**:`class CoherenceProtocol`(`coherence-protocol.md:133`,5 个纯虚:
`handle_probe` / `handle_request` / `can_coexist` / `translate` / `get_protocol_name`)
应**留在 ArchForge**,还是**下沉为 CppTLM 侧的 ProtocolEngine 插件接口**?

**为什么问你们**:
- CEP 的分层是「**协议逻辑住 Plugin,能力以数据声明**」(`ADR-CEP-12:163` 定义声明面;
  `ADR-CEP-05:170` 定义逻辑面)。若 `CoherenceProtocol` 留在 ArchForge,则 CEP 侧只剩一个
  **声明 schema**,而**没有可插拔的逻辑接口** —— CEP 的「可插拔协议」就落空了。
- 反之若下沉,则 ArchForge 的 `09-coherence-protocol.md §10.1` 里标注为「待新建」的
  `include/core/coherence_protocol.hh` 需重新定位。

**可选方案**:

| | 方案 | 说明 |
|---|------|------|
| **A** | **留在 ArchForge** | CEP 侧插件通过**声明 + 外部进程/接口**消费;CEP 不定义 C++ 插件接口(降级为「声明驱动」而非「插件驱动」) |
| **B** | **下沉为 CppTLM 侧插件接口** | ArchForge 侧 `CoherenceProtocol` 演化为该接口的一个实现;协议状态随之下沉(与 Q1-A 天然一致) |

**影响面**:P0-5 · 决定 CEP Stage 1 的实现形态 · 与 Q1 强耦合(选 B 时建议同时选 Q1-A)。

---

### Q3. `snoop_callback` 的**耦合路径**

> ✅ **答复:A —— 改走 adapter;且当前无直连可改。**
> 代码实证:`register_cache_callback` 全仓 **grep 0 命中**;`include/tlm/cache_tlm.hh` 中 `snoop`/`coherence` 标识符 **0 次**
> → `INV-CEP-15-IC3` **当前已满足**,迁移成本为零。
> 正确动作是**撤下设计**(5 处文档位置),而非改路径。
> 并追加裁定:dGPU SoC 一致性缓存模型走 **CEP `Stub Cache Core`**(路线 a),`CacheTLM` 侧**永不**实现 snoop。

**问**:`register_cache_callback(CacheTLM*)`(`09-coherence-protocol.md:250`)与配置项
`cache_tlm_integration = "snoop_callback"`(`09 §11`)—— 这条**直连 CacheTLM** 的路径
**保留**,还是**改走 adapter**?

**为什么问你们**:
- CEP 的 `INV-CEP-15-IC3`(`ADR-CEP-15:115`):**`CacheTLM` 不得实现 canonical 10 流的任何一条**
  (它无协议知识);CEP 与 `CacheTLM` 之间**只允许通过 adapter 交互**。
- 直连 callback 意味着 CacheTLM 侧出现 snoop 语义 —— 正是该条 invariant 要防的形态。
- 但直连是**已实现**的(`include/core/coherence_domain.hh` 已有 snoop 相关成员),
  所以这需要你们确认**是否愿意改路径**,而非 CppTLM 单方要求。

**可选方案**:

| | 方案 | 说明 |
|---|------|------|
| **A** | **改走 adapter** | `CacheTLM` 只暴露协议无关接口;snoop 经 adapter 转发;`INV-CEP-15-IC3` 成立 |
| **B** | **保留直连** + 显式豁免 | ArchForge 出 ADR 豁免 `INV-CEP-15-IC3`;CEP 侧登记该豁免并把 CacheTLM 排除在 canonical 10 流实现者之外 |

**影响面**:P0-4 · 影响 ArchForge `09 §5.3` 的「Phase 7.C snoop callback → CacheTLM 集成」表述。

---

### Q4. VC / 排序假设的**权威方**

> ✅ **答复:B —— ArchForge 侧承载,并把「命名空间」与「绑定表」拆开。**
> 本问前提「ArchForge 侧当前没有 VC/ordering 概念」**不成立**:
> `include/bundles/noc_bundles_tlm.hh:38` 已有 `vc_id`(0-3),与 CEP schema 同域;
> `08-noc-interconnect.md:205-212` 已有 4 VC 死锁避免;NSA 已占 VC1=Atomic / VC2=Remote Query。
> 拆分:`vc_id` 命名空间 + 网络排序属性 → **ArchForge 侧**;消息类→`vc_id` 绑定表 → **CEP 协议实例声明**;
> 死锁自由性论证 → **CEP 侧**(`ADR-CEP-09`)。

**问**:`ordering_assumption`(网络 → `p2p_ordered`/`unordered`)与 `vc_binding`(消息类 → `vc_id` 0..3)
应**由 CppTLM 侧承载**,还是**由 ArchForge 侧承载**?

**为什么问你们**:
- 这两个字段是 CEP **协议实例声明**的一部分(`ADR-CEP-12:168`,`INV-CEP-12-IC2`:
  `named_network` key **必须**解析到唯一 `vc_id`,否则配置加载 fail)。
- 但 `vc_id` 的**命名空间**必须单点权威 —— 若两侧各自定义,则跨仓组合时无从对齐。
- ArchForge 侧当前**没有** VC / ordering 概念(这是**缺失**,不是冲突)——
  所以问题是:**未来会不会有?** 若不会有,则 CEP 侧独占该命名空间。

**可选方案**:

| | 方案 | 说明 |
|---|------|------|
| **A** | **ArchForge 侧不引入** VC/ordering | CEP 侧独占该命名空间;ArchForge 侧若将来需要,再走一次跨仓对齐 |
| **B** | **ArchForge 侧承载** | 需 ArchForge 侧提供 fabric 命名空间定义 + `vc_id` 分配规则;CEP 的 schema 引用而不定义 |

**影响面**:P1-1 · 与 Q6(权限词表)共同决定跨域接口的**共享词表边界**。

---

### Q5. 协议**族边界**的权威方

> ✅ **答复:A —— 边界由 CppTLM 侧定义并回写 ArchForge 文档;ArchForge 侧给出实例拆分口径。**
> 口径:`moesi_gpu` = **1 个协议实例**(MESI 是其退化配置,不独立计);
> `mesif` = **1 个协议实例**(与 `moesi_gpu` 并列做 A/B);
> NSA 三级 Hardware Directory = **SharerTracker 选型**(不计 adapter);
> `moesi_gpu` vs Ruby `MOESI_AMD_Base`/`GPU_VIPER` = **同语义不同实现**(依 `07 §5.1.4` 不重复计数)。
> 连带:收敛 `25-nsa-hardware.md §4.4` + `§7` 开放问题 #4 → **不做单选,做可实例化的 A/B**。

**问**:协议「族」的划分以哪一侧为准?ArchForge 侧的 MOESI/GPU 属 `industrial` 族,
Ruby-SLICC 族(`MESI_Two_Level` / `MOESI_hammer` / `GPU_VIPER` / …,共 8 实例)由 CppTLM 侧提供 ——
**两族的 adapter 边界在哪**?

**为什么问你们**:
- CEP 的口径是「**族 = 协议实例的来源集合**」,当前 **2 个来源族 = 14 个 adapter 实例**
  (`CppTLM/docs/architecture/07-coherence-exploration-platform.md:310`)。
- ArchForge 侧目前只有 **1 族(MOESI/GPU 6×6)**,而这 1 族在 CEP 里对应 `industrial` 族。
- 边界问题具体是:**ArchForge 的 `moesi_gpu` 在 CEP 侧算 1 个实例还是多个?**
  (CEP 的 `07 号 §5.1.1` 把 CXL 2.0 / 3.0 对称记作**同一 adapter 的两种模式但 2 个实例** ——
  ArchForge 的 MOESI/GPU 是否也该拆?)

**可选方案**:

| | 方案 | 说明 |
|---|------|------|
| **A** | ArchForge 侧 = `industrial` 族,**边界由 CppTLM 侧定义**并回写 ArchForge 文档 | 需 ArchForge 侧确认 `moesi_gpu` 的实例拆分口径 |
| **B** | **边界由 ArchForge 侧定义** | 需 ArchForge 侧给出「一个 adapter = 一个协议实例」的拆分规则,CppTLM 侧照搬 |

**影响面**:P1-4 · 影响 CEP 的「已实现 adapter 实例数」计数口径(`ADR-CEP-12` 决策 9)。

---

### Q6. 跨域接口是否接受 CEP 的 **4 值权限词表**

> ✅ **答复:A —— 接受 4 值作跨域词表 + 交付 6→4 投影表 + 1 项 schema 请求(R-2)。**
> 投影无歧义;`O`/`M` 合并的信息损失由 **Sharer Tracker** 补偿(CEP 分层既定做法),`T` 无投影(协议私有态)。
> **R-2**:`perm` 需加「可静默升级」判别位 —— `moesi_gpu` 的 `state_transition[2][1]=3`(E+Write→M)满足
> `ADR-CEP-13` 决策 3「域可见写」判据 **(a) ∧ (b)**(判据 (b) 已于 2026-10-22 补齐并**成立**,per [`答复回执 §1.1`](./cep-interface-alignment-response-2026-10-22.md)),
> 而 4 值 `perm` 无法区分静默/显式升级;
> **该需求命中 `ADR-CEP-05 §7`(α 失效判据 2)已写下的触发条件**。

**问**:跨域桥接两侧是否接受 CEP 的 `perm` **4 值**(`NONE`/`READ`/`UNIQUE`/`WRITEBACK`)
作为**跨域接口的稳定词表**,而非 6 态 `CoherenceState`?

**为什么问你们**:
- CEP 侧 `perm` 4 值是**已冻结**的口径(`ADR-CEP-02:66` 的 `CEN-Ib11`:
  「`perm` 枚举**维持 4 值锁**」),且**不新增** ATOMIC 值。
- ArchForge 侧是 6 态。**跨域**时若两侧用不同词表,需一张投影表;
  而 `O`/`T` **无投影**(瞬态态住插件内,见 Q1)。
- 这是**跨域接口**层面的选择,不是单域内部实现细节。

**可选方案**:

| | 方案 | 说明 |
|---|------|------|
| **A** | **接受 4 值**作跨域词表 | 需 ArchForge 侧产出 **6 态 → 4 值投影表**;`O`/`T` 显式说明「无投影」 |
| **B** | 跨域仍用 6 态 | CEP 侧在 adapter 边界做投影;需 ArchForge 侧说明 6 态在**跨域**时的语义稳定性 |

**影响面**:P1-3 · 与 Q4 共同构成跨域共享词表。

---

## 4. P0 冲突摘要(供快速定位)

> 完整 13 项见 CppTLM 侧清单 §3;此处只列**需要 ArchForge 侧直接改文档**的 5 项。
> **答复轮已逐项给出结论**,见末列。

| # | 冲突 | ArchForge 侧位置 | CEP 侧约束 | **答复结论** |
|---|------|----------------|----------|------------|
| **P0-1** | 6 态枚举归属 | `coherence-protocol.md:112`、`09:242` | `ADR-CEP-05:170` | ✅ **A 下沉到协议插件**;顶层只留 4 值 `perm` 投影(6→4 投影表见 `32 号 §7.2`) |
| **P0-2** | `enum class Protocol { MESI, MOESI }` 仍是**配置入口** | `coherence-domain.md:68` | `ADR-CEP-07A:99`(通用禁令) | ✅ **已消解** —— `include/core/coherence_domain.hh:25-28` 已 `[[deprecated]]`(per ADR-CEP-07A 决策 1);本仓侧只需停止把它写进新配置入口 |
| **P0-3** | **4 类 Bundle ↔ canonical 10 流** 无映射 | `coherence-bridge.md §2.2` | `ADR-CEP-02:55` | ✅ **已交付映射表** —— [`32 号 §7.1`](../architecture/32-cep-based-coherence-architecture.md#7-p0-3-映射表archforge-类型--canonical-10-流)(逐类型 20 行,含 `CoherenceMsg` 解散 / `source_protocol` 删除 / `Flush`→流5 / `Invalidate`→流7+流3 / NSA Remote Query→流8+流3 / Remote Atomic→流1+atomic) |
| **P0-4** | `snoop_callback` 直连 CacheTLM | `09:250`、`09 §11` | `ADR-CEP-15:115` | ✅ **A 改走 adapter** —— 且**无直连可改**(grep 0 命中);动作 = **撤下设计**(5 处文档位置),`CacheTLM` 天然满足 `INV-CEP-15-IC3` |
| **P0-5** | `CoherenceProtocol` 归属 | `coherence-protocol.md:133` | `ADR-CEP-12:163` | ✅ **B 下沉为 ProtocolEngine 插件接口** + **3 项强制修订**(`translate` 移除 / 请求带 consistency label / 基类更名 `ProtocolEngine`);`09 §10.1` 的「待新建 `coherence_protocol.hh`」**取消** |

**P0-3 不依赖 §3 的任何一问** —— 它是一份纯**映射表**。**答复轮已先行交付**,见上表末列与 `32 号 §7.1`。

---

## 5. 答复表(已填)

> **答复轮**: 2026-10-21 · **答复方**: ArchForge coherence owner
> **决策载体**: [`ADR-SOC-25-cep-aligned-coherence-architecture.md`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md)
> **详细依据**: [`32-cep-based-coherence-architecture.md`](../architecture/32-cep-based-coherence-architecture.md)

| # | 结论(A / B / 其他) | 一句话理由 | 若非 A,落点文件与改动范围 |
|---|-------------------|-----------|--------------------------|
| **Q1** 状态归属 | **A**(下沉到协议插件) | `I/S/E/M/O/T` 是 MOESI/AMD 家族的**协议内编码**;`O`/`T` 在 4 值 `perm` 下无投影,正说明它们**不是跨域接口的类型**(`INV-CEP-05-IC1` 分层正确) | — |
| **Q2** 抽象基类归属 | **B**(下沉为 CppTLM 侧 ProtocolEngine 插件接口)**+ 3 项强制修订** | 「协议逻辑住 Plugin、能力以数据声明」是 CEP 立论基础;若基类留在 ArchForge,CEP 侧只剩声明 schema 而无可插拔逻辑接口 | —(选 B);**但须同时**: ① `translate(probe,from,to)` 从插件接口**移除**(双协议感知与 `ADR-CEP-13` 决策 3 不兼容) ② 请求语义**携带一致性标签**,不得用 `bool is_write/is_read` ③ 基类更名 `ProtocolEngine`,`can_coexist` 降为插件内部工具。落点: `09:399`(取消新建计划)、`microarchitecture/coherence-protocol.md:133-155`、`microarchitecture/coherence-bridge.md:49/81/121` |
| **Q3** snoop callback 路径 | **A**(改走 adapter)—— **且无可改之物** | 直连**从未实现**(`register_cache_callback` grep 0 命中;`cache_tlm.hh` 的 `snoop`/`coherence` 标识符 **0 次**)→ `INV-CEP-15-IC3` **当前已满足**,正确动作是**撤下设计**而非改路径 | —(选 A);落点(5 处): `09:250`(删 `register_cache_callback`)、`09:256`(§5.3 改写)、`09:430`(§10.3 改写)、`09:459`(删 `snoop_callback` 配置项)、`microarchitecture/coherence-protocol.md:32`(Bundle 类型重述)。**并追加裁定**: dGPU SoC 一致性缓存模型走 **CEP `Stub Cache Core`**(路线 a),`CacheTLM` 侧**永不**实现 snoop → `register_cache_callback` **永不复现** |
| **Q4** VC / ordering 权威方 | **B**(ArchForge 侧承载)**+ 拆分** **+ per-network 矩阵**(复核修订) | `vc_id` 0-3 命名空间**已存在**且与 CEP schema 同域(`noc_bundles_tlm.hh:38`);但**VC 分配是 per-network 的** —— 片上 `compute_noc`(`08 §4.3`) 与卡间 `ualink_fabric`(`25-nsa` VC0/1/2 + 本次补齐 VC3)**是同一张矩阵的两行,不是两套互斥答案**;原扁平 `vc_binding` 造成语义漂移,已改为逐网络 | —(选 B);拆分口径: ① `vc_id` 命名空间 + **网络清单 + 每网络 `vc_count`** + 网络排序属性 → **ArchForge 侧**;② 消息类→`vc_id` 绑定表(**逐网络**)→ **CEP 协议实例声明**;③ 死锁自由性论证 → **CEP 侧**(`ADR-CEP-09`)。**连带 schema 修订**(选项 A:给 `vc_binding` / `ordering_assumption` 加 network 维度)→ **R-5' / R-5'' / R-6'**,delta 见 `32 号 §6.4`。落点: `08-noc-interconnect.md §4.3`(per-network 标注 + 6 类映射)、`25-nsa-hardware.md §4.3`(UALink 行 + VC3)、`22-nsa-fabric-address-spec.md §0.5`(Glossary 扩 network 维度)、`32 号 §6.0`(权威矩阵) |
| **Q5** 协议族边界权威方 | **A**(边界由 CppTLM 侧定义并回写 ArchForge 文档)**+ ArchForge 给出实例拆分口径** | ArchForge 贡献的不是 1 族 1 实例,而是 **2 个协议实例**(`moesi_gpu` / `mesif`)+ **1 个 SharerTracker 选型**(NSA 三级目录,不计 adapter) | —(选 A);ArchForge 侧实例拆分口径: `moesi_gpu` = **1 个实例**(MESI 是其退化配置,不独立计)、`mesif` = **1 个实例**(与 `moesi_gpu` 并列做 A/B)、NSA Hardware Directory = **SharerTracker 选型**(不计 adapter)、`moesi_gpu` vs Ruby `MOESI_AMD_Base`/`GPU_VIPER` = **同语义不同实现**(依 `07 §5.1.4` 不重复计数)。落点: `09:444`(补注)、`25-nsa-hardware.md §4.4` + `§7` 开放问题 #4(收敛) |
| **Q6** 跨域权限词表 | **A**(接受 4 值作跨域词表)**+ 投影表 + 1 项 schema 请求** | 6→4 投影**无歧义**;`O`/`M` 合并的信息损失由 **Sharer Tracker** 补偿(CEP 分层既定做法),不构成额外成本 | —(选 A);交付 6→4 投影表(`32 号 §7.2`)+ 显式声明两处语义损失(`O`≈`M` 合并 / `T` 无投影)。**并提出 R-2**: `perm` 需加「可静默升级」判别位 —— `moesi_gpu` 的 `state_transition[2][1]=3`(E+Write→M)满足 `ADR-CEP-13` 决策 3「域可见写」判据 **(a) ∧ (b)**(判据 (b) 已于 2026-10-22 补齐并**成立**,per [`答复回执 §1.1`](./cep-interface-alignment-response-2026-10-22.md)),而 4 值 `perm` 无法区分静默/显式升级;**该需求命中 `ADR-CEP-05 §7`(α 失效判据 2)已写下的触发条件** |

### 5.1 附带提交:对 CEP 框架的需求(R-1 ~ R-12)

> 完整的 12 项需求(每项含需求 / 本仓实证 / CEP 现状 / 建议落点 / 优先级)见
> [`32 号 §11`](../architecture/32-cep-based-coherence-architecture.md#11-对-cep-框架的需求r-1--r-13含-r-5--r-5--r-6-修订)。

| 优先级 | 编号 | 摘要 |
|:------:|------|------|
| **P0** | **R-2** | `perm` 加「可静默升级」判别位(命中 `ADR-CEP-05 §7` 已写下的触发条件;判据 (b) 已于 2026-10-22 补齐 → **R-2 命中**,per [`答复回执 §1.1`](./cep-interface-alignment-response-2026-10-22.md)) |
| **P0** | **R-5'** | fabric config 提供**网络命名空间 + 每网络 `vc_count`**(`vc_binding` 逐网络化的直接前提;C-4 双向映射依赖此项) |
| **P0** | **R-5''** | `ordering_assumption` 从 per-network 单值升为 **per-(network, vc_id)**(与 R-6' 捆绑;否则两个 map 的 key space 不一致) |
| **P0** | **R-6'** | 消息类词表定为 **6 类**(`request`/`response`/`snoop`/`snoop_resp`/`atomic`/`query`;排除 `CATEGORY_CREDIT` 流控类别、`forward_data` 流 6、`snoop_completion_ack` 流 10)+ `vc_binding`/`ordering_assumption` 加 **network 维度**(**schema 修订**,delta 见 `32 号 §6.4`) |
| **P0** | **R-9** | CEP 显式声明「插件接口**不含** `translate(from,to)`」(否则 Stage 1 接口形状被本仓接口绑架) |
| **P0** | **R-11** | 「真实缓存 + CEP 协议」路线在 Stage 1 前定案(直接决定 Phase 7.C 是否还写 `snoop_callback`) |
| **P0** | **R-13** | `ADR-CEP-11 §3` 版本锁定表需收录 `moesi-gpu-1.0` / `mesif-1.0`（`INV-CEP-11-IC1`: 表外取值 = **装配期 fail** → §6 的声明当前必然 fail,C-4 不可机器验收） |
| **P1** | R-1 / R-3 / R-4 / R-7 / R-8 / R-10 / R-12 | 分级目录第 6 种 SharerTracker 实现 / `consistency_labels` 按 fabric scope 分级 / `atomic` 承载一致性语义标签 / 目录式远端查询的流组合规范 / `family` 口径 / `CoherenceDomain` 弃用后的域概念对齐 / `perm` 与 Capability 的正交性 |

**可选补充**:若某问的答案依赖尚未确定的设计,请写明**依赖项**与**预计可答复时间**,
CppTLM 侧会相应把 M2 放行判据挂起(不视为阻塞答复)。

---

## 6. 放行判据(供双方对齐预期)

CppTLM 侧的 M2 准入门在 §3 答复到位后的**可检查判据**(5 条,详见 CppTLM 侧清单 §6):

| # | 判据 | 可自动化 | 答复轮状态 |
|---|------|:--------:|-----------|
| C-1 | ArchForge 侧存在**已合入**的 coherence 接口 PR(有 commit hash) | ❌ 跨仓 | 🔴 **结构性不可闭合** —— 见下方协商请求 |
| C-2 | 该 PR 含 P0-1 ~ P0-5 的结论(逐项可追溯到 ArchForge 文档行) | ❌ 人工 | ✅ 已满足(§4 末列)—— 载体为 `ADR-SOC-25` + `32 号` |
| C-3 | §3 的 6 问各有**书面结论** | ❌ 人工 | ✅ 已满足(§5) |
| C-4 | CppTLM 的 `protocol_instance.schema.json` 与 ArchForge 侧声明**能双向映射** | ✅ 机器 | 🔶 部分 —— 声明 JSON 已交付(`32 号 §6`),但消息类词表(R-6)与 network 清单(R-5)待对齐 |
| C-5 | CppTLM 侧的 10 组反向验证仍全绿(M1 冻结 + lint + ctest) | ✅ 机器 | ⏳ 不在本仓职责内 |

**🔴 治理级阻塞 —— 请求协商 C-1 的措辞**:

> C-1 要求「ArchForge 侧存在**已合入**的 coherence 接口 **PR**(有 commit hash)」。
> 但 **ArchForge 是纯设计仓**(`git log` 全为 `docs(...)` 提交,无 `src/`、无 `include/`),
> **结构上无法**产出「接口 PR」→ C-1 永远无法闭合 → CEP 的 M2 准入门**永久阻塞**。

**请求**:把 C-1 从「**接口 PR**」改为「**接口规约 PR**(design-spec PR)」——
即以 [`ADR-SOC-25`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md) +
[`32-cep-based-coherence-architecture.md`](../architecture/32-cep-based-coherence-architecture.md) +
本文件 §5 答复表为 C-1 的交付形态;**实现型 PR 归 CppTLM 仓**
(per `ADR-CEP-00 §2` 决策 1 的代码归口:全部 C++ 实现归 CppTLM)。

> **这是本轮唯一的治理级阻塞,优先级高于一切技术结论。**
> 详见 [`ADR-SOC-25` D11](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md#d11-请求把放行判据-c-1-从接口-pr改为接口规约-pr)
> 与 [`32 号 §2 F8`](../architecture/32-cep-based-coherence-architecture.md#f8-严重治理阻塞-c-1-放行判据与-archforge-仓性质冲突会造成永久阻塞)。

**时间线**:CppTLM 侧不设 ArchForge 侧的排期承诺 —— §3 的 6 问 + P0-3 的映射表到位后,
C-5 可即刻验证,C-1~C-4 随 PR 逐步闭合。

---

## 7. 相关材料

| 材料 | 位置 | 用途 |
|------|------|------|
| **ArchForge 答复的决策载体** | [`docs/adr/ADR-SOC-25-cep-aligned-coherence-architecture.md`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md) | 11 项决策(D1~D11)+ 9 份文档返工清单 + 8 项验收 |
| **ArchForge 答复的详细设计** | [`docs/architecture/32-cep-based-coherence-architecture.md`](../architecture/32-cep-based-coherence-architecture.md) | 审阅结论(8 项发现)+ CEP 分层映射 + 3 域重划 + 2 个协议实例声明 + P0-3 映射表 + R-1~R-12 需求单 |
| **完整对齐清单**(13 项 gap 矩阵 + PR 范围 + 5 条判据 + 32 个机器可读锚点) | `CppTLM/docs/implementation/2026-10-21-cep-archforge-interface-alignment.md` | 本提问单的完整依据 |
| CEP 契约层真源(21 份 ADR + 66 条 invariant) | `CppTLM/docs/adr/ADR-CEP-*.md` · `CppTLM/docs/architecture/07-coherence-exploration-platform.md` | §3 各问的约束出处 |
| CEP 协议实例声明 schema | `CppTLM/include/tlm/cep/protocol_instance.schema.json` | §1.2 的字段定义 |
| 跨仓准入门条款 | `CppTLM/docs/adr/ADR-CEP-00-platform-charter-and-governance.md` §2 决策 3 | §1.3 / §6 的依据 |
| 引用漂移检测 | `CppTLM/scripts/test/cep_archforge_alignment_check.sh` | 校验本仓文档引用的 ArchForge `file:line` 仍有效 |

---

**版本**: v0.2 · **最后更新**: 2026-10-21 · **提出方**: CppTLM CEP DRI(builder mode) · **答复方**: ArchForge coherence owner
**变更**: v0.1 提问单 → v0.2 **已填答复**(§2 勘误 + §4 逐项结论 + §5 答复表 + §5.1 需求单 + §6 治理阻塞协商请求) → v0.3 **复核修订**(Q4 答复改 per-network 矩阵;R-5→R-5'/R-5''、R-6→R-6')
