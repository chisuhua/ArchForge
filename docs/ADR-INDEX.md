# ArchForge 决策体系索引（ADR 导览）

> **版本**: v3.0 (2026-09-23 重整版) · **维护**: ArchForge Team
> **范围**: dGPU SoC 应用层决策记录（与 `docs/adr/` 框架层决策分离）
> **关联总览**: [`README.md`](README.md)

---

## 0. 阅读引导

本文档是 ArchForge 的**决策体系索引**，回答 3 个问题：

1. **本仓决策体系长什么样？** → §1 ADR 命名与层划分
2. **有哪些决策？分别在管什么？** → §3 ADR 索引表 + §4 战略分组
3. **怎么维护？** → §6 维护纪律 + §7 跨仓治理边界

---

## 1. 命名空间与层划分

### 1.1 双层 ADR 体系

ArchForge 所在的 CppTLM 项目有**双层 ADR 体系**，两层**严格分离**避免混淆：

| 维度 | `docs/adr/`（框架层） | `docs/adr/`（应用层） |
|------|---------------------|-------------------------------|
| **层** | 仿真基础设施 | SoC 设计 |
| **示例议题** | 事务追踪、错误处理、端口类型 | 一致性协议、CU 建模粒度、Host-GPU 接口 |
| **稳定性** | 极稳定，跨 SoC 共用 | 较不稳定，随 SoC 拓扑变化 |
| **前缀** | `ADR-X.NN-` | `ADR-SOC-NN-` |
| **当前规模** | 13 份（X.1-X.13） | **24 份**（SOC-01..24） |
| **维护方** | 框架层 owner | SoC 设计 owner |

> **本文档范围**：仅 `docs/adr/`（应用层）。框架层 ADR 见 CppTLM 仓 `docs/adr/`。

### 1.2 ADR 命名约定

- **前缀**：`ADR-SOC-NN-<topic>.md`
- **NN**：两位数字，从 `01` 起递增（永不重用编号——替代决策创建新 ADR，旧 ADR 标记 Superseded）
- **topic**：小写连字符短语，简短描述决策主题

---

## 2. 状态图例

| 状态 | 含义 | 处理方式 |
|------|------|---------|
| ✅ Accepted | 已批准或已实施，**必须遵循** | 不可变 |
| 📋 Proposed | 起草中，需进一步讨论 | 可修订；不可实施 |
| ⏳ 待讨论 | 需要进一步讨论 | 不可实施 |
| ❌ Superseded | 决策被替代 | 仅作历史参考 |
| ⚠️ Deprecated | 已弃用（模块级，非 ADR 级） | 仅作历史参考 |
| 🔧 (无标注) | 缺状态标注（需补） | 见各 ADR 头部 |

> **ADR 不可变原则**：已签发 ADR 正文**不改**，通过 `## Status Update` 段追加状态变化；决策需变更时**创建新 ADR** 承载。

---

## 3. ADR 索引表（24 份完整列表）

> 数据来源：2026-09-23 扫读各 ADR 头部。完整列表以本仓 `docs/adr/ADR-SOC-NN-*.md` 为准。

### 3.1 已确认（✅ Accepted）— 8 份

| ADR | 议题 | 关联阶段 |
|-----|------|---------|
| [ADR-SOC-01](./adr/ADR-SOC-01-coherence-protocol-strategy.md) | 一致性协议分步走策略（I/S/M 三态 → MOESI 升级） | Phase 7.A → 7.C |
| [ADR-SOC-02](./adr/ADR-SOC-02-cu-granularity.md) | ComputeUnit 黑盒优先（不做 5-stage pipeline）⚠️ Superseded by ADR-SOC-16 | Phase 7.B+ |
| [ADR-SOC-03](./adr/ADR-SOC-03-wavefront-coalescing-abstraction.md) | Wavefront Coalescing 抽象（`coalescing_factor` 参数）⚠️ Superseded by ADR-SOC-16 | Phase 7.B+ |
| [ADR-SOC-04](./adr/ADR-SOC-04-hsapp-cp-dispatcher-simplification.md) | HSAPP/CP/Dispatcher 极简化（`KernelLaunchTLM` 取代 HSA 三件套）⚠️ Superseded partial | Phase 7.B+ |
| [ADR-SOC-05](./adr/ADR-SOC-05-gpu-directory-structure.md) | GPU 目录结构（`include/tlm/gpu/` 子目录） | Phase 7.A 起 |
| [ADR-SOC-16](./adr/ADR-SOC-16-sm-microarchitecture.md) | dGPU SoC v1.0 SM 微架构重构（反转 ADR-SOC-02 黑盒优先） | v1.0 (2027-Q3+) |
| [ADR-SOC-17](./adr/ADR-SOC-17-pcie-mock-ip.md) | 独立 PcieMockIP（gem5 风格简化端点） | Phase 9+ (2027-09-17) |
| [ADR-SOC-20](./adr/ADR-SOC-20-cpptlm-abi-secondary-slimming.md) | CppTLM ABI 二级精简 18→15 函数 + 宏化（修订版） | Phase 9+ P5 |
| [ADR-SOC-25](./adr/ADR-SOC-25-cep-aligned-coherence-architecture.md) | **一致性架构改采 CEP 框架对齐**（协议插件化 + 能力声明 + 3 域重划 + 撤下 `snoop_callback` + **per-network VC 分配矩阵** + R-1~R-13 需求单；[复核回执 N-1~N-4](roadmap/cep-interface-alignment-review-2026-10-21.md)） | 跨仓答复轮 (2026-10-21) |

### 3.2 提案（📋 Proposed）— 14 份

| ADR | 议题 | 关联阶段 |
|-----|------|---------|
| [ADR-SOC-06](./adr/ADR-SOC-06-cpptlm-v05-mvp.md) | cpptlm-v05-mvp（**MVP 切片**：UsrLinuxEmu IOCTL → CP→TMU→SQ→CudaCore + PTX-EMU 分离） | Phase 10 MVP |
| [ADR-SOC-07](./adr/ADR-SOC-07-dgpu-board-soc-layering.md) | dGPU Board/SOC 两层分离（`DGpuBoard` C++ ABI shell + `DGpuSoc` JSON 拓扑） | MVP 后续 |
| [ADR-SOC-08](./adr/ADR-SOC-08-v55-system-hw-integration-preconditions.md) | v5.5+ 系统级硬件仿真集成的前置测试契约 | OpenSpec change `2026-08-28-cpptlm-dgpu-pcie-slice-prerequisites/` |
| [ADR-SOC-09](./adr/ADR-SOC-09-v1-nvidia-amd-dual-vendor.md) | dGPU SoC v1.0 NVIDIA + AMD 双 driver stack 战略 | v1.0 (2027-Q3+) |
| [ADR-SOC-10](./adr/ADR-SOC-10-module-factory-topology.md) | dGPU SoC v1.0 ModuleFactory 拓扑层（9 类 SimModule） | v1.0 (2027-Q3+) |
| [ADR-SOC-11](./adr/ADR-SOC-11-pcie-endpoint-ip.md) | PcieEndpointIP 替代 PcieEndpointTLM（17 ports 整合模块） | Phase 4-8 |
| [ADR-SOC-12](./adr/ADR-SOC-12-host-bypass-and-rc.md) | Host Bypass 软件 bring-up 路径 + 自研 RC PF0-only 简化 | Phase 7-8 |
| [ADR-SOC-13](./adr/ADR-SOC-13-axi-stream-adapter-mapper.md) | AXI Stream Adapter + AXI4Mapper 集成 | Phase 5-6 |
| [ADR-SOC-14](./adr/ADR-SOC-14-v55-integration-revision.md) | v5.5+ 系统级硬件仿真集成修订 | v1.0+ |
| [ADR-SOC-15](./adr/ADR-SOC-15-cdna-real-isa-roadmap.md) | dGPU SoC v1.0 CDNA 真实物理 ISA 演进路线图 | v1.0+ |
| [ADR-SOC-19](./adr/ADR-SOC-19-axi-master-outbound-bridge.md) | PcieEndpointIP AXI Master/Slave 角色边界明确化 | Phase 10+ 评估 |
| [ADR-SOC-21](./adr/ADR-SOC-21-v31-rev2-topology-correction.md) | dGPU SoC V3.1-Rev2.0 拓扑修正 | Phase 9+ MAS |
| [ADR-SOC-22](./adr/ADR-SOC-22-nsa-fabric-address-format.md) | NSA-aware 64-bit Fabric Address 格式 | NSA Stage 1 |
| [ADR-SOC-23](./adr/ADR-SOC-23-nsa-vs-plan-b-selection.md) | NSA-aware 分布式 Scale-Up vs 方案 B 选型 | NSA Stage 1-3 |
| [ADR-SOC-24](./adr/ADR-SOC-24-capability-based-multitenant-isolation.md) | Capability-Based 多租户隔离选型 | NSA Stage 1-3 |

### 3.3 状态未明确标注 — 1 份

| ADR | 议题 | 备注 |
|-----|------|------|
| [ADR-SOC-18](./adr/ADR-SOC-18-cpptlm-abi-slimming.md) | CppTLM ABI 表面精简 22→18 函数 | 头部提及"HSK-10 移交"（待补 ✅/📋 状态） |

---

## 4. 战略阶段分组

### 4.1 阶段分布图（自上而下演进）

```
┌──────────────────────────────────────────────────────────────────┐
│  Phase 7 早期决策（2026-06）                                       │
│  ──────────────────────────────────                              │
│  · ADR-SOC-01  Coherence 协议分步走                                │
│  · ADR-SOC-02  CU 黑盒优先（⚠️ Superseded by 16）                  │
│  · ADR-SOC-03  Wavefront Coalescing 抽象（⚠️ Superseded by 16）    │
│  · ADR-SOC-04  HSAPP/CP/Dispatcher 极简化（⚠️ Superseded partial） │
│  · ADR-SOC-05  GPU 目录结构                                       │
├──────────────────────────────────────────────────────────────────┤
│  v0.5 MVP + Board/SOC 分层（2026-08）                              │
│  ──────────────────────────────────                              │
│  · ADR-SOC-06  cpptlm-v05-mvp（MVP 切片）                          │
│  · ADR-SOC-07  dGPU Board/SOC 两层分离                            │
│  · ADR-SOC-08  v5.5+ 集成前置测试契约                              │
├──────────────────────────────────────────────────────────────────┤
│  v1.0 战略 — 双 vendor + ModuleFactory + PCIe IP（2027-02）         │
│  ──────────────────────────────────                              │
│  · ADR-SOC-09  双 driver stack 战略                               │
│  · ADR-SOC-10  ModuleFactory 拓扑层                                │
│  · ADR-SOC-11  PcieEndpointIP（17 ports 替代）                     │
│  · ADR-SOC-12  Host Bypass + 自研 RC                              │
│  · ADR-SOC-13  AXI Stream Adapter + AXI4Mapper                     │
│  · ADR-SOC-14  v5.5+ 集成修订                                     │
│  · ADR-SOC-15  CDNA 真实物理 ISA 路线图                            │
├──────────────────────────────────────────────────────────────────┤
│  Phase 9 收尾 — SM 重构 + ABI 精简 + Mock（2027-09）                │
│  ──────────────────────────────────                              │
│  · ADR-SOC-16  SM 微架构重构（反转 ADR-SOC-02）                    │
│  · ADR-SOC-17  PcieMockIP                                          │
│  · ADR-SOC-18  ABI 精简 22→18                                     │
│  · ADR-SOC-19  AXI Master/Slave 边界（缺口评估）                   │
│  · ADR-SOC-20  ABI 二级精简 18→15（修订版）                        │
├──────────────────────────────────────────────────────────────────┤
│  NSA-aware Stage 1（2026-09-19）                                   │
│  ──────────────────────────────────                              │
│  · ADR-SOC-21  V3.1-Rev2.0 拓扑修正                               │
│  · ADR-SOC-22  64-bit Fabric Address 格式                          │
│  · ADR-SOC-23  Scale-Up vs 方案 B 选型                            │
│  · ADR-SOC-24  Capability-Based 多租户隔离                         │
├──────────────────────────────────────────────────────────────────┤
│  CEP 对齐（2026-10-21，跨仓答复轮）                                │
│  ──────────────────────────────────                              │
│  · ADR-SOC-25  一致性架构改采 CEP 框架对齐                          │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 关键决策演化路径（追溯链）

```
Phase 7.A-B（2026-06）
├─ ADR-SOC-02: CU 黑盒优先
└─ ADR-SOC-03: Wavefront Coalescing 抽象
            │
            │ ⚠️ Superseded by
            ▼
v1.0（2027-Q3+）
├─ ADR-SOC-09: 双 driver stack（含 AMD ROCm 路径）
├─ ADR-SOC-15: CDNA 真实物理 ISA 路线图
└─ ADR-SOC-16: SM 微架构重构（反转黑盒优先 → 12 ChStream 子模块）
```

```
Phase 7（2026-06）
├─ ADR-SOC-04: HSAPP/CP/Dispatcher 极简化（❌ ROCm/AQL/Doorbell 永不做）
└─ ADR-SOC-05: GPU 目录结构
            │
            │ ⚠️ 部分反转（v1.0 需要 AMD KFD + AQL 路径）
            ▼
v1.0（2027-Q3+）
├─ ADR-SOC-09: AMD ROCm 路径（双向反转）
└─ ADR-SOC-13: AXI Stream/Mapper（PCIe↔AXI 边界扩展）
```

> **关键发现**: ADR-SOC-02/03/04 三个 Phase 7 早期 ADR 与 v1.0 战略存在**直接矛盾**，已在 [`adr/revision-plan-v1.0.md`](adr/revision-plan-v1.0.md) §1.2 G1/G6 中明确标注。ADR-SOC-16 已正式 Supersede 02/03；04 仅 partial superseded（保留简化方向，新增 AMD 路径例外）。

---

## 5. ADR 与架构/模块/跨仓引用矩阵

### 5.1 ADR → 架构蓝图（architecture/）引用

| ADR | 关联架构文档 |
|-----|------------|
| ADR-SOC-01 | `architecture/09-coherence-protocol.md` |
| ADR-SOC-02 | `architecture/05-sm-compute-unit.md` (黑盒路径) |
| ADR-SOC-03 | `architecture/05-sm-compute-unit.md` (抽象层) |
| ADR-SOC-04 | `architecture/02-command-processor.md` |
| ADR-SOC-05 | `architecture/00-overview.md` §1.3 SimModule 拓扑 |
| ADR-SOC-06 | `architecture/00-overview.md` §1.1 v0.5 MVP 维度对比 |
| ADR-SOC-07 | `architecture/01-host-interface.md` + `architecture/00-overview.md` §1.3 |
| ADR-SOC-08 | `architecture/01-host-interface.md`（前置测试） |
| ADR-SOC-09 | `architecture/00-overview.md` §1.2 双 vendor + §4 D1 |
| ADR-SOC-10 | `architecture/00-overview.md` §1.3 SimModule 拓扑 |
| ADR-SOC-11 | `architecture/19-pcie-ip-microarchitecture.md` + `architecture/00-overview.md` §4 D3 |
| ADR-SOC-12 | `architecture/01-host-interface.md`（Host Bypass + RC） |
| ADR-SOC-13 | `architecture/01-host-interface.md`（AXI Stream/Mapper） |
| ADR-SOC-14 | `architecture/01-host-interface.md`（v5.5+ 集成） |
| ADR-SOC-15 | `architecture/11..13-cdna-*.md` |
| ADR-SOC-16 | `architecture/15-sm-microarchitecture-design.md` + `architecture/00-overview.md` §4 D7 |
| ADR-SOC-17 | `architecture/01-host-interface.md`（Mock IP 路径） |
| ADR-SOC-18 | （跨仓 ABI 表面，详见 CppTLM `include/abi/`） |
| ADR-SOC-19 | `architecture/01-host-interface.md`（AXI 角色边界） |
| ADR-SOC-20 | （跨仓 ABI 二级精简） |
| ADR-SOC-21 | `architecture/21-soc-topology-mvp.md`（MAS-3.1） |
| ADR-SOC-22 | `architecture/22-nsa-fabric-address-spec.md` |
| ADR-SOC-23 | `architecture/23-dist-scale-up-topology.md` + `architecture/21-dist-scale-up-topology-b.md` |
| ADR-SOC-24 | `architecture/27-nsa-capability.md` |
| ADR-SOC-25 | `architecture/32-cep-based-coherence-architecture.md` + `architecture/09-coherence-protocol.md` + `architecture/25-nsa-hardware.md` §4 |

### 5.2 ADR → 微架构（microarchitecture/）引用

| ADR | 关联模块文档 |
|-----|------------|
| ADR-SOC-02 | `microarchitecture/command-processor.md` (CP 5-state FSM) |
| ADR-SOC-04 | `microarchitecture/command-processor.md` + `microarchitecture/pm4-decoder.md` |
| ADR-SOC-05 | `microarchitecture/gpu-*.md`（gpu 子目录结构） |
| ADR-SOC-06 | `microarchitecture/dgpu-soc-pcie-slice.md` + `microarchitecture/command-processor.md` + `microarchitecture/tmu-dispatch-processor.md` + `microarchitecture/submit-queue.md` |
| ADR-SOC-07 | `microarchitecture/dgpu-soc-pcie-slice.md`（D2/D3 拆分） |
| ADR-SOC-11 | `microarchitecture/dgpu-soc-pcie-slice.md`（17 端口） |
| ADR-SOC-12 | `microarchitecture/host-bypass.md` + `microarchitecture/pcie-root-complex.md` |
| ADR-SOC-13 | `microarchitecture/axi4-stream-adapter.md` + `microarchitecture/axi4-mapper.md` |
| ADR-SOC-15 | `microarchitecture/gpu-gputlm.md`（CDNA 引擎接入） |
| ADR-SOC-16 | `microarchitecture/command-processor.md` + `microarchitecture/pm4-decoder.md` + `microarchitecture/tmu-dispatch-processor.md`（SM 重构后取代） |

### 5.3 ADR → 跨仓契约

| ADR | 跨仓引用 | 状态 |
|-----|---------|:----:|
| ADR-SOC-08 | UsrLinuxEmu ADR-089 v0.5 | 📋 + Status Update（不修订 UsrLinuxEmu 文档） |
| ADR-SOC-09 | UsrLinuxEmu 双 driver stack 依赖（待 Hub ack） | 📋 Proposed |
| ADR-SOC-14 | UsrLinuxEmu v5.5+ 集成闭环 | 📋 Proposed |
| ADR-SOC-18 | CppTLM `include/abi/cpptlm_emulator.h` 22→18 函数 | ✅ Accepted（HSK-10 移交） |
| ADR-SOC-19 | UsrLinuxEmu AXI Master 路径（缺口评估） | 📋 Proposed |
| ADR-SOC-20 | CppTLM `include/abi/cpptlm_emulator.h` 18→15 函数 + 宏 | ⏳（Hub ack 待收） |

> **跨仓治理边界**：本仓不修订 UsrLinuxEmu 文档（per ADR-035 跨仓治理边界），跨仓议题仅记录提议，由 UsrLinuxEmu owner 在其仓内签发对应 ADR。

---

## 6. ADR 撰写规范（修订时遵循）

### 6.1 必含章节

每份 ADR 必须包含：

1. **元信息块**（文件头部）：Status / Date / Impact / Category
2. **Context（背景）**：决策的"为什么"——列选项、对比
3. **Decision（决策）**：✅ 标记的采纳选项 + 理由
4. **Implementation（实施）**：各阶段任务 + 验收标准
5. **Risks / Mitigations（如适用）**
6. **References（参考文献）**：调研、roadmap、微架构、SoC spec 链接

### 6.2 参考模板

最完整示例：[`ADR-SOC-05-gpu-directory-structure.md`](adr/ADR-SOC-05-gpu-directory-structure.md)

### 6.3 状态更新规范

- **状态变更** → 追加 `## Status Update` 段（不修改历史决策内容）
- **决策变更** → 创建新 ADR（SOC-NN+1），旧 ADR 通过 Status Update 标注 "Superseded by ADR-SOC-NN+1"
- **禁止**：在 Status Update 中塞入决策性内容（违反 ADR 不可变原则）

---

## 7. 维护纪律

### 7.1 新增 ADR 流程

1. 复制最新 SOC-NN 模板 → 编号递增
2. 完成 6 个章节（§6.1）
3. **必须经 Oracle 评审 PASS** 后签发
4. 提交后同步更新：
   - 本文档 §3 索引表
   - `docs/adr/README.md` v2.3 索引表
   - `README.md` §4 状态分布

### 7.2 状态变更流程

- 追加 `## Status Update` 段（不修改历史）
- 在同 commit 更新本文档 + adr/README.md 索引
- 批量纯状态变更可合并 1 次 Oracle 评审

### 7.3 归档/废弃

- **Superseded**：决策被新 ADR 替代，旧 ADR 头部添加"⚠️ Superseded by ADR-SOC-NN+1"标注
- **归档**：不删除，保留为历史参考；可移至 `archive/` 子目录（需讨论）

### 7.4 跨仓引用

- 关联 ADR 时用相对路径 `./ADR-SOC-NN-*.md`
- 关联跨仓文档时使用仓内相对路径（如 `../../CppTLM/...`）或 URL
- OpenSpec 链接使用仓内 `openspec/changes/` 路径

---

## 8. 支持文档

### 8.1 [`revision-plan-v1.0.md`](adr/revision-plan-v1.0.md)

**ADR 修订规划**（非 ADR 本身）：
- 状态：📋 Draft v2（Metis 评审修复中）
- 日期：2027-02-09
- 内容：v1.0 战略下 ADR-SOC 修订框架（10 个现有 ADR 修订 + 6 个新 ADR）
- 关键差距 G1-G10 + 修订清单 A1-A7 + 状态追加 B + 新增 C1-C6
- **本文档不是 ADR**，是 ADR 体系的演进规划

### 8.2 [`hsk9-announcement-draft.md`](adr/hsk9-announcement-draft.md)

**历史公告草稿**（仅参考）：
- HSK-9 公告草稿（cross-repo 公告模板）
- 状态：⚠️ 历史参考
- 已完成其历史使命，不更新

---

## 9. 维护记录

| 日期 | 版本 | 修订 |
|------|------|------|
| 2026-10-21 | v3.2 | `ADR-SOC-25` 推进至 ✅ Accepted（复核轮 N-1~N-4 裁决完毕）；新增 `docs/roadmap/cep-interface-alignment-review-2026-10-21.md` 复核回执 |
| 2026-10-21 | v3.1 | 新增 `ADR-SOC-25`（一致性架构改采 CEP 框架对齐） |
| 2026-09-23 | v3.0 | ArchForge 重整：新建本文档；按战略阶段重排 ADR；新增 §4 演化路径追溯；§5 三维引用矩阵 |
| 2026-09-20 | v2.3 | `docs/adr/README.md` v2.3 新增 ADR-SOC-21/22/23/24 |
| 2026-08-20 | v2.2 | ADR-SOC-06 迁回本目录（per Phase I.4） |
| 2026-06-14 | v1.0 | ADR-SOC-01..05 初始签发 |

---

**维护**: ArchForge Team · **上游同步**: CppTLM 仓 `docs/adr/`（框架层 ADR）