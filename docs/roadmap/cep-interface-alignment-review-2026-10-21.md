# CEP 接口对齐复核回执 — N-1 ~ N-4 裁决记录

> **类别**: SoC Architecture > Roadmap · **跨仓复核记录**
> **日期**: 2026-10-21 · **性质**: 对 [`cep-interface-alignment.md`](./cep-interface-alignment.md) 答复轮的**提交复核**
> **复核方**: CEP 侧交叉评审 · **裁决方**: ArchForge coherence owner
> **复核对象**: [`ADR-SOC-25`](../adr/ADR-SOC-25-cep-aligned-coherence-architecture.md) commit `6020f42`
> + [`32-cep-based-coherence-architecture.md`](../architecture/32-cep-based-coherence-architecture.md) commit `6020f42`
> **状态**: ✅ **4 项全部裁决完毕**（2×P0 + 2×P1）· 已回写全部落点
> **纪律**: **N-1 / N-2 属 P0，不随放行一起放过去** —— 本记录的所有裁决已在同一批次内回写文档

---

## 0. 一句话

复核新发现 **2 个 P0**（VC 分配双答案 / `vc_binding` 缺 network 维度）与 **2 个 P1**（消息类词表 / ADR 状态）；
**全部已裁决并回写**，其中 N-1 的根因是本仓 D8 把**两个不同 fabric** 的 VC 分配压成了一张扁平表 —— 已改为 **per-network 矩阵**。

---

## 1. N-1 [P0] Compute NoC 的 VC 分配存在两套互斥答案

### 1.1 复核陈述

| 槽位 | `08-noc-interconnect.md §4.3` | `ADR-SOC-25 D8` / `32 号 §6.1` |
|------|---------------------------|---------------------------|
| VC0 | Request | request/snoop |
| VC1 | Response | atomic |
| VC2 | Forward | query |
| VC3 | Reply | response/snoop_resp |

D8 的相容性论证只对过 `25-nsa`（UALink VC1=Atomic / VC2=Remote Query），**从未对过 `08 §4.3`**；
而 `moesi_gpu` 声明的 `ordering_assumption` 键正是 `compute_noc`。两套分配各自都无死锁环，但描述的是不同的 fabric。

### 1.2 取证（ArchForge 仓 + CppTLM 仓）

| 证据 | 位置 | 结论 |
|------|------|------|
| 「NoC(Network-on-Chip)Interconnect = dGPU SoC v1.0 系统拓扑的**片上网络层**」 | `08-noc-interconnect.md:45` | `08 §4.3` = **片上 Compute NoC** 的 router 层分配 |
| 「HW 发起 Fault Request Packet (经 UALink **VC0**)」 | `25-nsa-hardware.md:336` | UALink **VC0 = Fault Request** |
| 「HW 发起 Remote Atomic Packet (经 UALink **VC1**)」 | `25-nsa-hardware.md:392` | UALink **VC1 = Atomic** |
| 「L2 Miss (跨 GPU): 发起 Remote Query Packet (经 UALink **VC2**)」 | `25-nsa-hardware.md:567` | UALink **VC2 = Remote Query** |
| UALink **VC3** | `25-nsa-hardware.md` 全文 | **未分配**（空缺） |
| `vc_id` 0-3 字段 | `CppTLM/include/bundles/noc_bundles_tlm.hh:38` | 两张表共用同一 4 槽空间，**但属于不同 fabric** |

### 1.3 裁决：**不是「互斥答案」，是「同一张矩阵的两行」—— 根因在 D8 的扁平化**

**结论**：
1. 两套分配**分属不同 fabric**（片上 Compute NoC vs 卡间 UALink），**本身不冲突**；
2. **D8 / `32 号 §6.1` 的错误在于把两张 per-network 表压成了一张全局扁平 `vc_binding`**，
   于是 `moesi_gpu` 声明里的 `ordering_assumption` 键 `compute_noc` 指向了 **UALink 的槽位语义** —— 语义漂移；
3. **裁决**：**per-network 矩阵**取代扁平表。`08 §4.3` 的四槽划分（Request/Response/Forward/Reply）**保持不变**，
   仅补 6 类词表映射 + 显式标注 `network = compute_noc`；UALink 行补齐 VC3。

### 1.4 裁决后的唯一 VC 分配矩阵（per-network，权威版见 `32 号 §6.0`）

| 网络 | VC0 | VC1 | VC2 | VC3 |
|------|-----|-----|-----|-----|
| **`compute_noc`**（片上） | `request` | `response` | `snoop` + `forward_data` | `snoop_resp` + `snoop_completion_ack` |
| **`ualink_fabric`**（卡间） | `request`（+ 非一致性的 Fault Request 共槽） | `atomic` | `query` | `response` + `snoop_resp` + `forward_data` |

**与既有文档的相容性**：
- `08 §4.3` 的四槽 **Request / Response / Forward / Reply** → 映射到 6 类词表后**槽位不变**
  （Forward 槽 = `snoop` + `forward_data`；Reply 槽 = `snoop_resp` + `snoop_completion_ack`）；
- `25-nsa` 的 **VC0=Fault Request / VC1=Atomic / VC2=Remote Query** → **原样保留**，仅补 VC3 = `response`。

### 1.5 死锁自由性论证（per ADR-CEP-09 装配期判据）

| 网络 | 依赖边 | 环 |
|------|--------|:--:|
| `compute_noc` | VC0→VC1, VC0→VC2, VC0→VC3, VC1→VC3, VC3→VC2 | **无环** ✅ |
| `ualink_fabric` | VC0→VC3, VC1→VC3, VC2→VC3 | **无环** ✅ |

**两条支撑规则（缺一即成环，必须写进协议规约）**：
1. **请求向与响应向必须异槽**（VC0 ↔ VC1/VC3）—— 已由上表满足；
2. **`snoop_resp` 不携带数据；数据一律走 `forward_data`** ——
   否则 `snoop_resp`(VC3) 依赖 `forward_data`(VC2) 而 `forward_data` 又依赖 `snoop_resp` → **VC2↔VC3 成环**。
   08 号原有的 Forward / Reply **双槽设计正是为此**（Reply = 纯状态应答，Forward = 数据通道）。

> ⚠️ 上述论证由 ArchForge 侧给出**分配表与依赖边**，最终判定仍归 CEP `ADR-CEP-09` 的机器校验。

### 1.6 落点

| 文件 | 改动 |
|------|------|
| `docs/architecture/08-noc-interconnect.md §4.3` | 标注 `network = compute_noc` + 补 6 类词表映射 + 指向 `32 号 §6.0` 权威矩阵 |
| `docs/architecture/25-nsa-hardware.md §3.1/§4.3` | 标注 `network = ualink_fabric` + 补 VC3 = `response` + 指向权威矩阵 |
| `docs/architecture/32-cep-based-coherence-architecture.md §6.0` | **新增**：per-network VC 矩阵（唯一权威）+ 死锁自由性论证 |
| `docs/architecture/32-cep-based-coherence-architecture.md §6.1/§6.2` | 声明改为 per-network 形式 |
| `docs/adr/ADR-SOC-25-...md D8` | 改为 per-network 矩阵 |

---

## 2. N-2 [P0] `vc_binding` 没有 network 维度，而 VC 分配是 per-network 的

### 2.1 复核陈述

schema 里 `vc_binding` 的 key 是消息类，一个实例却横跨 `compute_noc` + `ualink_fabric` 两网络、各有各的分配表 →
`INV-CEP-12-IC2`「named_network key 必须解析到唯一 `vc_id`」在协议实例声明内无解析面
（schema 无 network→vc_id 映射，声明也不含 fabric config）。这把 R-5 的交付物从「网络名单」升级成「每网络 × 每消息类 → vc_id」矩阵。

### 2.2 取证（CEP 侧）

| 证据 | 位置 | 内容 |
|------|------|------|
| 决策 5 | `ADR-CEP-12:118-124` | 「**粒度**:逐网络」；「key:`<vc_id \| named_network>`,且 `named_network` **必须在 fabric config 中解析到唯一 `vc_id`**」 |
| 决策 5 理由 | 同上 `:122` | 「排序是 **VC 的静态属性**,不是 flit 的字段 —— `NoCFlitBundle` 只有 `vc_id` / `flit_type` / `flit_category` / `is_write` / `is_ok` / `error_code`,**不带 ordering**」 |
| 决策 5 依据 | 同上 `:123` | 源码 `MSI_Proto.pcc:3-6` 的 `Network { Ordered fwd; Unordered resp; Unordered req; }` |
| 决策 6 | `ADR-CEP-12:84-85` | `vc_binding: <flow_or_message_class>: <vc_id>`（扁平） |
| 现行 schema | `protocol_instance.schema.json:119-130` | `ordering_assumption` = `{network: "p2p_ordered"\|"unordered"}`；`vc_binding` = `{msg_class: 0..3}` |
| invariant | `INV-CEP-12-IC2` | 「`ordering_assumption` 的 `named_network` key **必须**解析到唯一 `vc_id`」 |

### 2.3 裁决：**选「给 `vc_binding` 加 network 维度」（选项 A），并把 `ordering_assumption` 同步升为 per-(network, vc_id)**

#### 2.3.1 为什么不是选项 B（把解析移出声明落到 fabric config）

决策 5 已把「named_network → vc_id」的解析面放在 **fabric config**，选项 B 看似「不改 schema」。
但选项 B 会导致三个硬伤：

| # | 硬伤 |
|---|------|
| **B-1** | **协议实例声明不再自洽**：同一协议实例跑在 2 个网络上，扁平 `vc_binding` 只有一份 → 两个网络的分配表冲突，**声明无法表达** |
| **B-2** | **死锁自由性论证失去输入**：`ADR-CEP-09` 的装配期判据要构建**通道依赖图**，而图的节点必须是 **(network, vc_id)** —— 死锁是 **per-fabric** 的现象。扁平 vc_id 空间在多网络下**无意义**（两个网络的 VC2 不是同一个东西） |
| **B-3** | **C-4 判据失效**：「`protocol_instance.schema.json` 与 ArchForge 侧声明能双向映射」若把关键表挪到 fabric config，声明侧就**不再可自校验**，机器验收无从下手 |

#### 2.3.2 为什么选项 A 必须**连带**升级 `ordering_assumption`

决策 5 的**理由**是「排序是 **VC 的静态属性**」，而其**依据**（`.pcc` 的 `Network { Ordered fwd; Unordered resp; Unordered req; }`）说明**不同网络、不同 VC 可以有不同序**。
现行 `ordering_assumption` 是 **per-network 单值**（一个网络一个序）→ **无法表达「同一网络内 VC0 有序、VC1 无序」**。

且在扁平形式下，`ordering_assumption` 的 key 既可是 `vc_id` 又可是 `named_network`（决策 5），
**`"0"` 到底指哪个网络的 VC0 存在歧义** —— 加 network 维度后该歧义一并消除。

#### 2.3.3 裁决后的目标结构

```json
"ordering_assumption": {
  "<network>": { "<vc_id>": "p2p_ordered" | "unordered" }
},
"vc_binding": {
  "<network>": { "<msg_class>": <vc_id> }
}
```

**分工**（三个面各归其位）：

| 面 | 归属 | 内容 |
|----|------|------|
| **网络命名空间 + 每网络槽位数** | **fabric config**（拓扑配置层） | `networks: { compute_noc: {vc_count: 4}, ualink_fabric: {vc_count: 4} }` |
| **消息类 → vc_id** | **协议实例声明**（`vc_binding`，逐网络） | 本仓交付 = R-5' 矩阵 |
| **排序假设** | **协议实例声明**（`ordering_assumption`，逐网络 × 逐 VC） | 本仓交付 = R-5'' 矩阵 |

#### 2.3.4 `INV-CEP-12-IC2` 的可实现化（提议修订）

```
对每个 network n：
  ① ordering_assumption[n] 的每个 vc_id v  ∈  vc_binding[n].values()
 ② vc_binding[n].values() 中每个 vc_id v  <  fabric_config.networks[n].vc_count
 ③ vc_binding[n] 的每个消息类 m 属于 CEP 规范消息类词表（6 类，见 N-3）
否则 → 装配期 fail（沿用 ADR-CEP-12 决策 3 的「不静默降级」处置）
```

#### 2.3.5 schema 修订的连带影响（须由 CEP 侧执行）

| 项 | 现状 | 修订后 |
|----|------|--------|
| `ordering_assumption.additionalProperties` | `{enum: [...]}` | `{type: object, additionalProperties: {enum: [...]}}`（嵌套一层） |
| `vc_binding.additionalProperties` | `{type: integer, 0..3}` | `{type: object, additionalProperties: {type: integer, 0..3}}`（嵌套一层） |
| `ADR-CEP-12` 决策 5 / 决策 6 | 扁平 | 逐网络嵌套 |
| `INV-CEP-12-IC2` | 不可实现 | 按 §2.3.4 可机器校验 |

> **本仓侧状态**：两份协议实例声明已按**目标形式**书写（`32 号 §6.1/§6.2`），
> 并附**提议的 schema delta**（`32 号 §6.4`）供 CEP 侧合入。
> 在 CEP 侧 schema 修订合入前，**本仓声明按现行 schema 校验会 fail（预期）** —— 不做「迁就现行 schema 的降级写法」。

### 2.4 落点

| 文件 | 改动 |
|------|------|
| `docs/architecture/32-cep-based-coherence-architecture.md §6.1/§6.2` | 声明改为 per-network 嵌套形式 |
| `docs/architecture/32-cep-based-coherence-architecture.md §6.4` | **新增**：提议的 schema delta |
| `docs/architecture/32-cep-based-coherence-architecture.md §11` | **R-5 升级为 R-5' / R-5''**；**R-6 升级为 R-6'**（含 schema 修订） |
| `docs/adr/ADR-SOC-25-...md D8` | 改为 per-network 矩阵 + schema 修订诉求 |

---

## 3. N-3 [P1] 消息类词表漏列 `snoop_resp`；`CATEGORY_CREDIT` 不应混入

### 3.1 复核陈述

R-6 的词表（5 类）漏列 `snoop_resp` —— 它自家声明用了 6 类，而 `snoop_resp` 是 canonical 10 流的**流 4**，
`CEN-Ib3` / `CEN-Ib4` / `CEN-Ib10` 都以它为对象，是**一等消息类**；另 `CATEGORY_CREDIT` 是流控类别、不该混进该词表。

### 3.2 取证

| 证据 | 位置 |
|------|------|
| 流 4 = `snoop_resp` | `07 号 §3.1:174`（`snoop_resp`: node → center,snoop 响应:hit + state + dirty + data + txn_id） |
| `CEN-Ib3` | `snoop` 必有 `snoop_resp` |
| `CEN-Ib4` | `snoop_resp` 必须含 `txn_id` 用于 ack 配对 |
| `CEN-Ib10` | `snoop_completion_ack` 配对 `snoop_resp` 不配对 `completion` |
| `CATEGORY_CREDIT = 2` | `CppTLM/include/bundles/noc_bundles_tlm.hh:62`（注释即写「Credit 信号专用类别」） |

### 3.3 裁决：**词表更正为 6 类；`CATEGORY_CREDIT` 明确排除**

**CEP 规范消息类词表（6 类，权威）**：

| # | 消息类 | canonical 流 | 方向 | 语义 |
|---|--------|------------|------|------|
| 1 | `request` | 流 1 | node → center | 缓存行请求（读 / 唯一化 / 写回 / 驱逐） |
| 2 | `response` | 流 2 | center → node | 请求完成 + data + perm + error |
| 3 | `snoop` | 流 3 | center → node | snoop 查询 / 失效 / clean / forward |
| 4 | `snoop_resp` | 流 4 | node → center | snoop 响应：hit + state + dirty + data + txn_id |
| 5 | `atomic` | 流 1 的独立属性 | node → center | 原子意图（CEN-Ib11） |
| 6 | `query` | 流 8 | node ↔ center | 地址归属 / sharer 查询 |

**明确排除**：
- **`CATEGORY_CREDIT`** —— **流控类别**，不是一致性消息类，**不进 `vc_binding` 词表**；
  credit 是 credit-based 流控的链路层信号，随所在 VC 的流一起走，**不单独占槽**。
- **`forward_data`（流 6）** 与 **`snoop_completion_ack`（流 10）** —— **不单列为消息类**：
  它们是**已有槽位的承载实例**，分别复用 `snoop` 槽（Forward 槽）与 `snoop_resp` 槽（Reply 槽）。
  理由：CEP 的 Stub Cache 只感知 5 条流（`07 号 §3.2`），流 6 / 流 10 对 stub **不可显式为接口**
  （CEN-Ib6 不可分辨性 / CEN-Ib10 配对语义）—— 它们**不是一级消息类**。

**为什么 `snoop_resp` 必须是一等消息类**：
`CEN-Ib3`（snoop 必有 snoop_resp）+ `CEN-Ib4`（须含 txn_id）+ `CEN-Ib10`（ack 配对它而非 completion）
三条 invariant 都以它为对象；且它在**协议插件内承担瞬态态收敛**职责（`INV-CEP-05-IC1` 的 `T` 态由它终结）——
漏列它会让协议侧无法声明「snoop 应答走哪个 VC」。

### 3.4 落点

| 文件 | 改动 |
|------|------|
| `docs/architecture/32-cep-based-coherence-architecture.md §6.0` | 词表 6 类（权威）+ 排除项说明 |
| `docs/architecture/32-cep-based-coherence-architecture.md §11 R-6` | R-6 → **R-6'**：词表 6 类 + schema 修订（合并 N-2） |
| `docs/roadmap/cep-interface-alignment.md §5.1` | R-6 → R-6'，词表同步 |

---

## 4. N-4 [P1] ADR-SOC-25 仍为 Proposed

### 4.1 复核陈述

`ADR-SOC-25` 仍为 Proposed，其验收项 **V-7** 待 D-9、**V-8** 已由我方回执满足。

### 4.2 裁决：**推进至 Accepted**，验收项状态显式化

**裁决**：ADR 的「决策」本身（D1~D11）已由本仓拍板，**文档返工（D-9）是决策的后果而非前置** → 可推进至 **✅ Accepted**。

但**验收项状态须按事实修正**，不得把未完成项写成已完成：

| 验收项 | 原表述 | 修正后状态 |
|--------|--------|-----------|
| **V-7** | 「9 份文档返工完成且无悬空引用」 | 🔶 **进行中** —— 返工清单见 `ADR-SOC-25 §3.1`；**返工落地会打断 CppTLM 的 21 个 CI 锚点，必须与 CppTLM 侧锚点重生成同批** |
| **V-8** | 「R-1 ~ R-12 需求单送达并有 CEP 侧回执」 | 🔶 **部分满足** —— 送达 ✅（commit `6020f42`）；CEP 侧回执 = **本记录**（N-1~N-4 已回执）；**R-1 ~ R-13 的逐条技术回执仍待** |

> ⚠️ V-8 的原文含「CEP 侧逐条回执」之意。本轮复核回执的是 **N-1~N-4（对本仓交付物的复核）**，
> **不等于** CEP 侧对 R-1 ~ R-13 的逐条技术回执 —— 后者仍待，不作已满足计。

### 4.3 落点

| 文件 | 改动 |
|------|------|
| `docs/adr/ADR-SOC-25-...md` | 状态 → ✅ Accepted；§5 验收项状态列显式化；§6 Status Update 增补本轮复核 |
| `docs/adr/ADR-SOC-25-...md` | 全文引用本回执路径（**V-8 的可追溯载体**） |

---

## 5. 本轮回执对放行判据的影响

| 判据 | 变化 |
|------|------|
| **C-1** | 不变 —— 仍为**治理级阻塞**，待协商把「接口 PR」改为「接口规约 PR」（`ADR-SOC-25 D11`） |
| **C-2** | 不变 —— P0-1~P0-5 结论已给（`cep-interface-alignment.md §4`） |
| **C-3** | 不变 —— 6 问结论已给（§5）；**Q4 答复按 N-1/N-2 更新** |
| **C-4** | 🔴 **受影响** —— `vc_binding` 的 schema 形态变更后，「协议实例声明 ↔ schema 双向映射」须待 CEP 侧合入 schema 修订（R-6'）才可机器验收 |
| **C-5** | 不变 |

> **结论**：**N-1 / N-2 不随放行一起放过去** —— C-4 在 schema 修订合入前**不可机器验收**，
> 这两条必须由 CEP 侧先合入 schema delta，再重跑 C-4。

---

## 6. 维护记录

| 日期 | 版本 | 修订 |
|------|------|------|
| 2026-10-21 | v0.1 | 首版：提交复核 N-1~N-4（2×P0 + 2×P1）及裁决；全部落点已回写 |

**下次更新**：待 CEP 侧对 R-1 ~ R-13 逐条回执后补「CEP 侧回执」列
