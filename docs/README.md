# ArchForge — dGPU SoC Architecture & Design Repository

> **本仓是 CppTLM 的设计伴侣仓**，存有全部 dGPU SoC 架构设计文档。
> **源代码实现** → [CppTLM](../CppTLM/)（`include/tlm/`, `src/tlm/`）

> **版本**: v4.0 (2026-09-23 重整版 · `soc_arch/` 层移除 + ARCHITECTURE.md 内容合并入本文 + DECISIONS.md → ADR-INDEX.md)
> **维护**: ArchForge Team

---

## 0. 阅读引导

本文档是 ArchForge 的**架构入口**，面向 4 类读者：

| 角色 | 关注点 | 推荐阅读路径 |
|------|--------|------------|
| **架构师** | 系统全景 + 关键决策 + 战略演进 | §2 文档地图 → §3 总览蓝图 → §4 决策体系 → §7 阅读路径(架构师) |
| **实现者** | 模块接口 + 微架构 + 实施细节 | §2 → §5 模块索引 → §7(实现者) → `microarchitecture/` 目录 |
| **评审者** | 决策一致性 + 跨仓依赖 + 风险 | §3 → §4 → §8 风险与依赖 → [`ADR-INDEX.md`](ADR-INDEX.md) |
| **集成者** | 跨仓契约 + ABI 状态 + 阶段计划 | §4 → [`ADR-INDEX.md`](ADR-INDEX.md) §5 ADR-SOC-08/14/18 → `roadmap/` |

---

## 1. 范围与目录结构

ArchForge 共 **211 份**设计文档，按性质分为 5 大类（两大内容类 + 三大横切 + 调研附属）：

| 类 | 目录 | 层级 | 数量 | 性质 | 受众 |
|----|------|:----:|:----:|------|------|
| **A. 系统架构** | `architecture/` | **SoC 系统级** | 45 | 系统级、分层、战略文档 | 架构师/评审者 |
| **B. IP 微架构** | `microarchitecture/` | **IP 级** | 54 | 每个 IP/模块一份接口契约 | 实现者 |
| **C. 决策记录** | `adr/` | 横切 | 27 | 24 份 ADR + README + 2 支持文档 | 架构师/评审者/集成者 |
| **D. 路线图与规格** | `roadmap/` + `specs/` | 横切 | 12 | 阶段计划 + APU 形态 spec + 跨仓对齐提问单 + 跨仓答复回执 | 集成者/规划者 |
| **E. 调研与证据** | `research/` | 附属 | 75 | 硬件微架构调研（专利 / 论文 / 仿真器剖析）+ 索引 | 架构师/实现者 |

```
ArchForge/
├── README.md                         ← 本文件（架构入口）
├── ADR-INDEX.md                      ← ADR 决策体系导览
├── architecture/                     ← A 类（45 份）
│   ├── INDEX.md
│   ├── 00-overview.md                 ★ v1.0 dGPU 总架构蓝图（权威）
│   ├── 01..10-*.md                   ← 7 层架构分解 (L1..L10)
│   ├── 11..15-*.md                   ← CDNA 系列 + SM 重构 + 架构审计
│   ├── 16..19-*.md                   ← PCIe 子链路
│   ├── 20..21-*.md                   ← 子系统详细（GMMU/DMA/Fabric/TEE/Topology）
│   └── 22..31-*.md                   ← NSA-aware Scale-Up（10 份）
├── microarchitecture/                ← B 类（54 份）
│   ├── INDEX.md
│   ├── README.md                     ← v2.1 legacy（INDEX 为权威）
│   └── *.md (52 份)
├── adr/                              ← C 类（27 份）
│   ├── README.md                     ← ADR 索引（v2.3）
│   ├── ADR-SOC-01..24-*.md           ← 24 份决策记录
│   ├── revision-plan-v1.0.md         ← ADR 修订规划
│   └── hsk9-announcement-draft.md    ← 历史公告草稿
├── roadmap/                          ← D 类（11 份）
│   ├── README.md
│   ├── roadmap-mvp-to-v05.md         ← v0.5 历史快照（🔒 冻结）
│   ├── cep-interface-alignment.md   ← CEP ↔ ArchForge 接口对齐提问单（✅ 已答复）
│   ├── cep-interface-alignment-review-2026-10-21.md  ← CEP 对齐复核回执 N-1~N-4
│   ├── cep-interface-alignment-response-2026-10-22.md ← CEP 待回应清单 10 条答复
│   └── phase9-p[0-5]-*.md            ← Phase 9 各子阶段
└── specs/
    └── apu-soc-design.md             ← APU 形态 spec（1056 行）
```

---

## 2. 文档地图（横向关系）

### 2.1 三层文档结构

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer 1 — 战略层（"做什么 / 为什么"）                            │
│  ──────────────────────────────────                              │
│  · architecture/00-overview.md  ★ v1.0 dGPU 总架构蓝图 (权威)   │
│  · specs/apu-soc-design.md     · APU 形态 spec（Phase 7 历史）  │
│                                                                  │
│  Layer 2 — 子系统层（"每一层怎么设计"）                           │
│  ──────────────────────────────────                              │
│  · architecture/01..10-*.md    · 7 层架构分解 (L1..L10)          │
│  · architecture/11..15-*.md    · CDNA 系列 + SM 微架构 + 审计    │
│  · architecture/16..19-*.md    · PCIe 子链路详细                 │
│                                                                  │
│  Layer 3 — 模块实现层（"每个模块怎么实现"）                       │
│  ──────────────────────────────────                              │
│  · microarchitecture/*.md (52 份)  · 每 IP/模块一份微架构契约   │
│  · microarchitecture/INDEX.md       · 模块分类索引                │
│                                                                  │
│  决策侧链 ────────────────                                       │
│  · adr/ADR-SOC-*.md           · 决策缘由（追溯 Layer 1/2/3）   │
│  · adr/revision-plan-v1.0.md  · 决策修订框架                     │
│  · ADR-INDEX.md               · ADR 体系导览                     │
│                                                                  │
│  演进侧链 ────────────────                                       │
│  · roadmap/phase9-p*.md       · Phase 9+ 近期计划                │
│  · roadmap/cep-interface-alignment · CEP 跨仓接口对齐（已答复）   │
│  · roadmap/roadmap-mvp-to-v05 · v0.5 历史快照                   │
│  · architecture/20..21-*.md    · 子系统级详细（应读为子目录）    │
│  · architecture/22..31-*.md    · NSA-aware 系列（中长期）        │
│  · architecture/32-*.md         · CEP 对齐一致性架构（跨仓）    │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 关键交叉引用矩阵

| 议题 | 架构蓝图 | 决策记录 | 模块微架构 |
|------|---------|---------|----------|
| Coherence 协议 | `architecture/09-coherence-protocol.md` | `ADR-SOC-01`, `ADR-SOC-09` (D1), **`ADR-SOC-25`** (CEP 对齐) | `microarchitecture/coherence-protocol.md`, `coherence-domain.md`, `coherence-bridge.md`, `snoop_filter.md` |
| PCIe EP | `architecture/01-host-interface.md` | `ADR-SOC-07`, `ADR-SOC-11`, `ADR-SOC-12`, `ADR-SOC-17` | `microarchitecture/dgpu-soc-pcie-slice.md`, `pcie-root-complex.md`, `host-bypass.md` |
| GMMU/IOMMU | `architecture/20-gmmu-*.md` | (待补 ADR) | (在 `microarchitecture/io-dma.md` 中) |
| SM/CU | `architecture/05-sm-compute-unit.md` | `ADR-SOC-02`, `ADR-SOC-16` | `microarchitecture/gpu-gputlm.md`, `command-processor.md`, `tmu-dispatch-processor.md` |
| Tensor Core | `architecture/06-tensor-core.md` | (含于 ADR-SOC-09 D7) | (TBD) |
| Memory | `architecture/07-memory-system.md` | (无独立 ADR) | `microarchitecture/gpu-memory-cluster.md`, `gpu-shared-memory.md`, `gpu-tcc.md` |
| NoC | `architecture/08-noc-interconnect.md` | (无独立 ADR) | `microarchitecture/gpu-noc-mesh.md`, `noc-router.md`, `noc-nic.md` |
| ModuleFactory | (在 `architecture/00-overview.md` §1.3) | `ADR-SOC-10` | (无独立文档) |
| Dual-vendor | `architecture/00-overview.md` §1.2 + §2 | `ADR-SOC-09`, `ADR-SOC-15` | `microarchitecture/gpu-pcie_bridge.md` |
| NSA-aware | `architecture/22..31-*.md` | `ADR-SOC-21..24` | (TBD Stage 1+) |
| ABI 表面 | (跨仓) | `ADR-SOC-18`, `ADR-SOC-20` | (跨仓 CppTLM) |

---

## 3. 总览蓝图（权威起点）

### 3.1 单一权威起点

> **⚠️ 关键**：本仓存在**两份"总架构蓝图"**，适用场景不同，请勿混淆。

| 文档 | 视角 | 战略阶段 | 适用范围 |
|------|------|---------|---------|
| **`architecture/00-overview.md`** ★ | **dGPU SoC v1.0**（独立显卡） | 2027-Q3+ | v1.0 MVP + v1.1 完整版（NVIDIA + AMD 双 driver） |
| **`specs/apu-soc-design.md`** | APU SoC（CPU+GPU 集成） | Phase 7（已实施） | APU 形态的 6 子阶段（历史阶段 spec） |

**新读者请从 [`architecture/00-overview.md`](architecture/00-overview.md) 开始**——这是 dGPU SoC v1.0 战略下唯一的总架构蓝图。

### 3.2 00-overview.md 结构（10 节 + 1 范围矩阵）

| 节 | 主题 | 关键产出 |
|----|------|---------|
| §0 | 阅读引导 | 7 层架构地图 + 配套文档层级 |
| §1 | 范围与目标 | v1.0 战略 + 1.1 维度对比 + 1.2 双 vendor 决策 + 1.3 SimModule 拓扑 |
| §2 | 系统拓扑（7 层 L1..L7） | 整体形态对比 + 7 层 ASCII 图 + 4 流视图 |
| §3 | 架构层详解 | L1..L7 各层组件/端口/路径 |
| §4 | 关键决策 D1..D8 | 融合策略/蓝图模式/PCIe IP/Memory/TMU/WDU/Tensor/Coherence |
| **§4-bis** | **v1.0 MVP / v1.1 完整版 范围矩阵**（**权威**） | R01..R27 27 项特性实施阶段表 |
| §5 | 数据流图（4 视图） | 命令流/数据流/配置流/中断流 |
| §6 | 兼容性分析 | v0.5/Phase 8 复用 + 扩展点 + Bundle 字段对位 |
| §7 | ADR 与模块微架构引用矩阵 | ADR/模块/OpenSpec 全链路 |
| §8 | 风险与缓解 R1..R7 | 7 项风险 + 等级 + 缓解 |
| §9 | 反模式（明确不做） | 13 项排除项 |
| §10 | 维护记录 | 4 个版本（v1.0 → v3.1 PASS） |

---

## 4. 决策体系（ADR 导览）

> 完整 ADR 索引见 [`ADR-INDEX.md`](ADR-INDEX.md)。本节为快速导航。

### 4.1 ADR 状态分布（截至 2026-09-23）

| 状态 | 数量 | 含义 |
|------|:----:|------|
| ✅ Accepted | 7 | 已批准或已实施，必须遵循 |
| 📋 Proposed | 14 | 起草中，需进一步讨论 |
| ⚠️ Superseded | 2 | 决策被替代 |
| 🔧 未标 | 1 | 缺状态标注（需补） |

### 4.2 ADR 按战略阶段分组

| 阶段 | ADR 范围 | 主题 |
|------|---------|------|
| **Phase 7 早期**（2026-06） | 01-05 | Coherence 协议、CU 黑盒、Wavefront 抽象、HSA 简化、目录结构 |
| **v0.5 MVP + Board/SOC 分层**（2026-08） | 06-08 | MVP 切片、Board/SOC 分离、v5.5 集成前置 |
| **v1.0 战略**（2027-02） | 09-15 | 双 vendor、ModuleFactory、PCIe IP、Host Bypass/RC、AXI Stream、v5.5 修订、CDNA 真实 ISA |
| **Phase 9+ 收尾**（2027-09） | 16-20 | SM 微架构重构、Mock IP、ABI 精简、AXI Outbound 缺口、二级精简 |
| **NSA-aware Stage 1**（2026-09-19） | 21-24 | 拓扑修正、Fabric Address、Scale-Up 选型、Capability 隔离 |

---

## 5. 模块体系（IP 微架构）

### 5.1 模块分类（9 大类）

> 详细分类见 [`microarchitecture/INDEX.md`](microarchitecture/INDEX.md)。

| # | 类型 | 文档数 | 已实施 | 典型模块 |
|---|------|:----:|:-----:|---------|
| 1 | CPU 端模块（Initiator） | 3 | 3 | `cpu-cputlm.md`, `cpu-traffic_gen.md`, `cpu-cpusim_legacy.md` |
| 2 | 内存子系统 | 5 | 2 | `memory-memtlm.md`, `memory-hbm.md` |
| 3 | Cache 层级 | 6 | 0-1 | `cache-l1.md`, `cache-l2.md`, `cache-protocol.md`, `cache-replacement.md`, `cache-noncoherent.md`, `cache.common.md` |
| 4 | Interconnect / NoC | 10 | 6 | `interconnect-crossbar.md`, `noc-router.md`, `coherent_xbar.md`, `snoop_filter.md`, `gpu-noc-mesh.md`, ... |
| 5 | GPU / GPGPU（含 dGPU 切片） | 11 | 10 | `gpu-gputlm.md`, `command-processor.md`, `tmu-dispatch-processor.md`, `submit-queue.md`, `gpu-memory-cluster.md`, `gpu-shared-memory.md`, ... |
| 5b | GPU / dGPU SOC PCIe Slice | 1 | 1 | `dgpu-soc-pcie-slice.md` |
| 6 | IO / DMA / 设备 | 8 | 1 | `io-dma.md`, `io-pio.md`, `io-disk.md`, `io-ether.md`, ... |
| 7 | Coherence / 桥接 | 3 | 2 | `coherence-domain.md`, `coherence-protocol.md`, `coherence-bridge.md` |
| 8 | RTL 桥接 | 2 | 2 | `rtl-hybrid_cache.md`, `rtl-fragment_mapper.md` |
| 9 | Framework Adapter (AXI) | 2 | 2 | `axi4-stream-adapter.md`, `axi4-mapper.md` |

### 5.2 dGPU 数据面核心模块（v0.5 MVP 已实施）

```
DGpuBoard (C++ shell)
└── DGpuSoc (SimModule 容器)
    ├── PcieEndpointTLM (4 端口, per ADR-SOC-07 D2)
    ├── SdmaEngineTLM (5 端口, per ADR-SOC-07 D3)
    ├── CommandProcessorTLM (5-state FSM, NVIDIA PM4)
    ├── TmuDispatchProcessorTLM (TMU Glue, 3 端口)
    ├── SubmitQueueTLM (WDU 分发网络, 4 端口)
    ├── CompletionRingTLM (4 端口)
    └── MemoryTLM (VRAM)
```

> **v1.0 升级路径**：4 端口 PcieEndpointTLM → 17 端口 PcieEndpointIP（per `architecture/19-pcie-ip-microarchitecture.md`），并加入 HostBypassTLM + PcieRootComplexTLM。

---

## 6. 与 CppTLM 的关系

```
ArchForge（设计仓）            CppTLM（实现仓）
┌──────────────────┐          ┌──────────────────┐
│ docs/            │  ← 引用 → │ code + tests     │
│ （架构/ADR/微架构）│          │ core framework   │
│ 系统级设计决策    │          │ 实现级设计文档     │
└──────────────────┘          └──────────────────┘
```

CppTLM 的 `AGENTS.md` / `docs/` 中引用 `docs/` 的路径，通过 **VIRTUAL_PATHS** 机制保持可读（详见 `CppTLM/scripts/test/docs_sync_check.sh`）。

---

## 7. 推荐阅读路径

### 7.1 架构师（想理解系统全貌）

1. **[`architecture/00-overview.md`](architecture/00-overview.md)** —— 通读 §0-§4-bis（关键）+ §7（引用矩阵）
2. **[`ADR-INDEX.md`](ADR-INDEX.md)** —— 浏览 ADR 总览，理解关键决策
3. [`architecture/01..10-*.md`](architecture/) —— 按需深入某一层（L1..L10）
4. [`microarchitecture/INDEX.md`](microarchitecture/INDEX.md) —— 理解模块分类

### 7.2 实现者（想实现某一模块）

1. **`architecture/00-overview.md` §4-bis** —— 确认目标模块在 v1.0 MVP / v1.1 的位置
2. **定位模块文档**：[`microarchitecture/`](microarchitecture/) 目录
3. **查关联 ADR**：[`ADR-INDEX.md`](ADR-INDEX.md) 找到对应决策
4. **查 Phase 计划**：[`roadmap/`](roadmap/) 找到对应阶段
5. **跨仓查 CppTLM**：`/workspace/project/CppTLM/`（实现仓）

### 7.3 评审者（想审查决策一致性）

1. **[`ADR-INDEX.md`](ADR-INDEX.md)** —— 审阅 ADR 体系 + 修订规划
2. **[`adr/revision-plan-v1.0.md`](adr/revision-plan-v1.0.md)** —— 审阅修订框架
3. **[`architecture/00-overview.md` §8 + §4-bis](architecture/00-overview.md)** —— 风险表 + 范围矩阵
4. **核对 OpenSpec 链接**：`adr/*.md` 中 OpenSpec 引用需与 CppTLM 仓 `openspec/changes/` 一致

### 7.4 集成者（跨仓/跨工具链）

1. [`ADR-INDEX.md` §5](ADR-INDEX.md) —— ADR-SOC-08/14/18/20 跨仓治理
2. [`roadmap/phase9-post-phase8-roadmap.md`](roadmap/phase9-post-phase8-roadmap.md) —— 总览
3. [`architecture/00-overview.md` §6](architecture/00-overview.md) —— v0.5/Phase 8 复用分析
4. `/workspace/project/UsrLinuxEmu/` —— UsrLinuxEmu 端依赖

---

## 8. 风险与依赖

### 8.1 文档体系本身的风险

| # | 风险 | 等级 | 缓解 |
|---|------|:---:|------|
| **D1** | 重号文件（`20-*.md` 3 份、`21-*.md` 10 份）平铺在 `architecture/` 顶层，违反数字序号唯一原则 | 🟡 中 | 本文 §2.1 已显式标注"应读为子目录"；后续清理建议改为 `architecture/20-gmmu/`、`architecture/21-soc-topology/` 等子目录 |
| **D2** | `revision-plan-v1.0.md` 与正式 ADR 同目录，身份混淆（不是 ADR，是规划） | 🟢 低 | 已在本索引 §2.1 区分；后续建议移至 `adr/planning/` |
| **D3** | `hsk9-announcement-draft.md` 历史公告草稿，未明确归档 | 🟢 低 | 已在 §2.1 标注为"参考"；后续建议移至 `archive/` |
| **D4** | `microarchitecture/README.md`（v2.1 早期）部分过时（仍以 Phase 7 路径描述） | 🟡 中 | 本节 §5 已提供新的分类视角；INDEX.md 为权威 |
| **D5** | 部分 ADR（如 18）状态未在头部标注 | 🟢 低 | 见 ADR-INDEX.md 统一索引 |

### 8.2 跨仓依赖（关键集成点）

| 依赖类型 | 本仓文档 | 跨仓契约 |
|---------|---------|---------|
| **ABI 表面冻结** | `ADR-SOC-18`, `ADR-SOC-20` | CppTLM `include/abi/cpptlm_emulator.h` 18-15 函数；Hub ack 待收 |
| **v5.5+ 集成前置测试** | `ADR-SOC-08`, `ADR-SOC-14` | UsrLinuxEmu ADR-089 v0.5；5 项 Tier 2 前置测试 |
| **PCIe EP 整合** | `ADR-SOC-11`, `ADR-SOC-17` | CppTLM Phase 4-8（17 端口 PcieEndpointIP + Mock IP） |
| **NSA-aware 路线** | `ADR-SOC-21..24`, `architecture/22..31-*.md` | OpenSpec `2026-09-19-cpptlm-nsa-scale-up-umbrella` |
| **CDNA 真实 ISA** | `ADR-SOC-15`, `architecture/11..13-*.md` | OpenSpec `cpptlm-dgpu-d1-cdna-isa-sm-rewrite` |

---

## 9. 维护纪律

1. **新增架构文档** → 同步更新本文档 §2 文档地图 + §5 模块索引（如适用）
2. **新增 ADR** → 同步更新 [`ADR-INDEX.md`](ADR-INDEX.md) §3 索引表 + [`adr/README.md`](adr/README.md) v2.3 索引
3. **状态变更** → 遵循 ADR 不可变原则（追加 `## Status Update` 段，不修改历史决策）
4. **跨仓引用** → 使用相对路径 `./` 或 `../`；OpenSpec 链接使用仓内 `openspec/changes/` 路径
5. **归档** → 标记 `🔒 冻结` / `⚠️ SUPERSEDED` 状态，不删除

---

## 10. 维护记录

| 日期 | 版本 | 修订 |
|------|------|------|
| 2026-09-23 | v4.0 | `soc_arch/` 层移除；ARCHITECTURE.md 内容合并入本文；DECISIONS.md → ADR-INDEX.md |
| 2026-09-23 | v3.1 | modules/ → microarchitecture/ 改名（Oracle 方案 D）|
| 2026-09-23 | v3.0 | 新增 README.md / ADR-INDEX.md / architecture/INDEX.md / microarchitecture/INDEX.md |
| 2027-02-09 | v2.x | dGPU SoC v1.0 总架构蓝图 v3.1 PASS（per `architecture/00-overview.md` §10）|
| 2026-06-12 | v1.0 | APU spec 初版（per `specs/apu-soc-design.md`） |

---

## 历史

于 2026-09-20 从 CppTLM 仓 `docs/soc_arch/` 迁移创建（CppTLM commit: `7e15124e`）。
> **2026-09-23 v4.0 更新**：在 ArchForge 仓内进一步扁平化，移除 `soc_arch/` 顶层目录。

**维护**: ArchForge Team