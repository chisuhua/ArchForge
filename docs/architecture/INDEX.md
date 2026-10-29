# Architecture 文档索引

> **版本**: v3.10 (2026-10-29 新增 41 号《CEP 对齐的债务清理与改进提案》—— 7 项债务 + 建议 diff + 追认清单) · **范围**: `docs/architecture/` 全部 54 份文档
> **关联总览**: [`../README.md`](../README.md) · **关联决策**: [`../ADR-INDEX.md`](../ADR-INDEX.md)

---

## 1. 文档分组（8 大类，47 份）

| 组 | 编号 | 主题 | 份数 | 性质 |
|----|------|------|:----:|------|
| **A. 总览蓝图** | 00 | dGPU SoC v1.0 总架构蓝图（权威起点） | 1 | ⭐ 唯一权威总览 |
| **B. 7 层架构分解** | 01-10 | L1..L10 各层架构 | 10 | 子系统蓝图 |
| **C. CDNA + SM 重构 + 审计** | 11-15, 33-40 | CDNA 真实 ISA / 校准 / EMU 选型 / 架构审计 / SM 重构 / **OSF 设计目标 + IPC 时序附录 + 依赖管理架构 + 新 ISA 依赖层设计 + 新 ISA 设计总纲 + 新 ISA 双域结构 + 新 ISA 编译器后端 + 新 ISA 规范骨架（B-0）** | 13 | 战略 + 审计 + 设计目标 + ISA 规范 |
| **D. PCIe 子链路** | 16-19, 19a | PCIe EP + SDMA + 入口 + 17 端口 IP 微架构 + 驱动可见最小 SoC | 5 | PCIe 详细 |
| **E. 子系统详细** | 20-21 | GMMU + DMA + Fabric + TEE-UDD + Topology（注：重号系列，应读为子目录） | 13 | 子系统级 MVP + Roadmap |
| **F. NSA-aware Scale-Up** | 22-31 | NSA-aware 完整 SoC + CXL + 故障注入 | 10 | NSA Stage 1-3 |
| **G. CEP 对齐一致性架构** | 32 | CEP 框架下的一致性重设计（跨仓对齐） | 1 | 跨仓答复轮 |
| **H. 总计** | — | — | **53** | — |

```
总计: 1 + 10 + 12 + 5 + 13 + 10 + 1 = 52 ✅（2026-10-28 实测 `ls docs/architecture/*.md | grep -v INDEX | wc -l` = 52）

历史漂移修正: v3.0 曾写「32 份」且分组求和为 43 —— 两者皆与实际不符;
本版按 2026-10-21 实测校正为 45（D 组补入 19a-driver-visible-minimal-soc.md）;
v3.3 补入 33（2026-10-27）与 34（2026-10-28）；v3.5 补入 35、v3.6 补入 36、v3.7 补入 37、v3.8 补入 38/39、v3.9 补入 40（2026-10-28）。
```

---

## 2. 文件清单（按分组列出）

### A. 总览蓝图（1 份，⭐ 权威）

| 序号 | 文件 | 状态 | 主题 |
|:----:|------|:----:|------|
| [00](./00-overview.md) | `00-overview.md` | ✅ v3.1 PASS | **dGPU SoC v1.0 总架构蓝图** — 融合 NVIDIA Blackwell + AMD CDNA 3/3.5 视角（10 节 + §4-bis 范围矩阵 R01..R27） |

> **⚠️ 新读者必读**：本文件是 dGPU SoC v1.0 战略下唯一的总架构蓝图。如需 APU 形态 spec，见 `../specs/apu-soc-design.md`（Phase 7 历史阶段）。

### B. 7 层架构分解（10 份——L1..L10）

| 序号 | 文件 | 主题 | 关联 |
|:----:|------|------|------|
| [01](./01-host-interface.md) | `01-host-interface.md` | **L1 Host Interface** — PcieEndpointIP + HostBypassTLM + PcieRootComplexTLM | ADR-SOC-07/08/11/12/14/17 |
| [02](./02-command-processor.md) | `02-command-processor.md` | **L2 Command Processor** — 双 vendor PM4 解码（NvidiaMethodDecoder + AmdPm4Decoder） | ADR-SOC-04/06 |
| [03](./03-task-management-unit.md) | `03-task-management-unit.md` | **L3 Task Management Unit (TMU)** — TMU + TMD + 依赖预取 + PDL | ADR-SOC-06 D5 |
| [04](./04-work-distribution.md) | `04-work-distribution.md` | **L4 Work Distribution (WDU)** — Crossbar + CGA Cluster | ADR-SOC-06 D5 |
| [05](./05-sm-compute-unit.md) | `05-sm-compute-unit.md` | **L5 SM/CU Compute Unit** — Warp 调度 + 寄存器文件 + DSMEM/TMEM | ADR-SOC-02/03/16 |
| [06](./06-tensor-core.md) | `06-tensor-core.md` | **L6 Tensor Core** — wgmma + tcgen05 + MFMA + 5th Tensor Core | (含于 ADR-SOC-09 D7) |
| [07](./07-memory-system.md) | `07-memory-system.md` | **L7 Memory System** — HBM3e + L1/L2 + SMEM + DSMEM + TMEM + Coherence | (无独立 ADR) |
| [08](./08-noc-interconnect.md) | `08-noc-interconnect.md` | **L8 NoC Interconnect** — Mesh NoC + Router + NIC + 跨 Cluster 通信 | (无独立 ADR) |
| [09](./09-coherence-protocol.md) | `09-coherence-protocol.md` | **L9 Coherence Protocol** — MOESI/GPU 6×6 状态机 + 跨域桥接 | ADR-SOC-01 |
| [10](./10-completion-notify.md) | `10-completion-notify.md` | **L10 Completion & Notification** — Doorbell + CompletionRing + MSI-X | ADR-SOC-08 P1 |

> **注**：00-overview.md 采用 L1..L7 命名；本目录 01-10 对应 L1..L10（含 NoC/Coherence/Completion 单独成层）。两组命名差异见 §6 命名约定。

### C. CDNA + SM 重构 + 审计（13 份）

| 序号 | 文件 | 主题 | 状态 |
|:----:|------|------|:----:|
| [11](./11-cdna-real-isa-integration.md) | `11-cdna-real-isa-integration.md` | **CDNA 真实 ISA 集成架构**（双轨前端 + 统一 Timing 宿主） | 📋 Proposed |
| [12](./12-cdna-calibration-baseline.md) | `12-cdna-calibration-baseline.md` | **CDNA 真实 ISA 校准基线设计方案**（阶段 D 启动前准备） | 📋 Proposed |
| [13](./13-cdna-emu-selector.md) | `13-cdna-emu-selector.md` | **CDNA-EMU 后端实现方案选型建议**（阶段 C 启动前决策依据） | 📋 Proposed |
| [14](./14-stage-a-architecture-audit.md) | `14-stage-a-architecture-audit.md` | **CDNA 演进 change 架构溯源**（是否采用 CppTLM 模块搭建 + Bundle 连接） | — |
| [15](./15-sm-microarchitecture-design.md) | `15-sm-microarchitecture-design.md` | **dGPU SoC v1.0 SM 微架构重构设计**（反转 ADR-SOC-02 黑盒） | 📋 Proposed |
| [33](./33-sm-operand-supply-design-target.md) | `33-sm-operand-supply-design-target.md` | **SM 操作数供给下一代架构设计目标（OSF）**——MCOS 多消费者操作数槽 / ERW 弹性读窗口 / WABR 宽度自适应读 / SOP 推测供给；证据见 [`research/SM/`](../research/SM/overview.md) + [`research/SM/CudaCore/SYNTHESIS.md`](../research/SM/CudaCore/SYNTHESIS.md) | 🟡 设计目标声明 v0.5（未经评审） |
| [34](./34-sm-operand-supply-ipc-timing-analysis.md) | `34-sm-operand-supply-ipc-timing-analysis.md` | **SM 操作数供给 IPC 与时序分析（33 号配套附录）**——IPC 模型（3 源 vs 2 源序列）/ 读带宽口径 `W` 敏感性 / cycle 坐标时序图 / 复算脚本 | 🟡 分析附录 v1.1（未经评审） |
| [35](./35-sm-dependence-management-architecture.md) | `35-sm-dependence-management-architecture.md` | **SM 依赖管理架构方案：五类依赖的统一框架与双后端**——RAW / WAR / WAW / 内存依赖 / 控制同步；依赖 vs 争用的四层分离；NV + CDNA 双后端；控制位与面积预算；CppTLM 落地映射 | 🟡 架构方案 v1.0（未经评审） |
| [36](./36-new-isa-dependence-layer-design.md) | `36-new-isa-dependence-layer-design.md` | **新 ISA 依赖层设计方案：候选架构比较与推荐**——5 个候选（纯 NV / 纯 AMD / 学术 scoreboard / NV+不变式 / +硬件 tag 兜底）；机制提炼与不可照搬的约束；不变式 D-1/D-2/D-3；架构保证 A-1/A-2；ISA 可见元素清单 E-1..E-14；Q-1..Q-9 裁决记录 | 🟡 设计方案 v1.2（未经评审） |
| [37](./37-new-isa-design-charter.md) | `37-new-isa-design-charter.md` | **新 ISA 设计总纲：定位、范围、参考 ISA 政策与路线图**——Q-8 取代关系（唯一 ISA；PTX/CDNA/SASS 降级为参考）；被取代 / 不被取代的分层；ISA 范围 v1–v3；**编译器硬依赖风险**；连锁后果清单 | 🟡 设计总纲 v1.0（未经评审） |
| [38](./38-new-isa-dual-domain-structure.md) | `38-new-isa-dual-domain-structure.md` | **新 ISA 标量/向量双域结构：借鉴 CDNA 的 SOP*/VOP* 风格**——CDNA 双域机理剖析（可借鉴 6 条 / 不可照搬 3 条）；SGPR/VGPR + SALU/VALU + SCC/VCC 提案；跨域规则 X-D1..X-D5；依赖层分域适配；**33 号结论的适用域重划** | 🟡 设计方案 v1.0（未经评审） |
| [39](./39-new-isa-compiler-backend.md) | `39-new-isa-compiler-backend.md` | **新 ISA 编译器后端方案：以 PTX-EMU 子集为约束的 PTX → 自研 ISA**——PTX-EMU 四层解码器与 **10 个硬缺口**；三条路线比较与推荐；**三层分工**（LLVM 前端 + 自研后端 + PTX-EMU 作 golden model）；AMDGPU 可借鉴的 6 个 pass；编译器必须产出的元数据 A-1..A-4；**§5.1 `SIInsertWaitcnts` 迁移率核查（20–30%）→"fork 是最短路径"降级为假设（B-6）** | 🟡 设计方案 v1.1（未经评审） |
| [40](./40-new-isa-spec-skeleton.md) | `40-new-isa-spec-skeleton.md` | **新 ISA 规范骨架（B-0）**——执行模型（wave 32 / EXEC / 发散栈 + 显式 `JOIN` / `VP[8]` 谓词文件）；架构寄存器（SGPR 128 = 124+4 保留 / VGPR 256）；**编码（`fmt` 8 类、48/64 双长度、8 种形态全部恰好填满、控制块向量 21 / 标量 16 bit）**；依赖层不变式 D-1/D-1′/D-2/D-3；内存模型最小规范；双域规则 X-D1..X-D5；TBD 注册表 T-1..T-9 | 🟡 **规范骨架 v1.0 DRAFT**（冻结前置已闭合，待签批） |

### D. PCIe 子链路（4 份）

| 序号 | 文件 | 主题 | 状态 | 关联 |
|:----:|------|------|:----:|------|
| [16](./16-pcie-endpoint-architecture.md) | `16-pcie-endpoint-architecture.md` | **PCIe Endpoint 跨仓架构** (Driver-to-Hardware, 含 5 阶段 Oracle 评审) | Draft v0.1 | ADR-SOC-07 |
| [17](./17-sdma-engine-design.md) | `17-sdma-engine-design.md` | **SDMA 引擎设计**（重命名为 IoDmaTLM per 2026-09-19） | ⚠️ 命名迁移 | ADR-SOC-07 D3 |
| [18](./18-pcie-endpoint-entry.md) | `18-pcie-endpoint-entry.md` | **PCIe Endpoint 实施入口文档**（双仓 SSOT） | — | (跨仓入口) |
| [19](./19-pcie-ip-microarchitecture.md) | `19-pcie-ip-microarchitecture.md` | **PCIe IP 微架构**（17 端口 PcieEndpointIP 详细） | — | ADR-SOC-11/17 |

### E. 子系统详细（13 份——重号系列）

> **⚠️ 重号说明**：本组文件命名约定为 `<series>-<component>.md`，多个文件共用同一前缀数字（20-/21-）。**应读为子目录**（如 `architecture/20-gmmu/`），但当前为平铺结构。
>
> **建议清理**：未来清理时拆分为 `architecture/20-gmmu/{mvp.md, evolution-roadmap.md}` 等子目录。当前为最小侵入性整理，保留平铺但显式标注。

#### E.1 GART/GMMU 系列（`20-` 前缀，3 份）

| 序号 | 文件 | 主题 | 状态 | 关联 |
|:----:|------|------|:----:|------|
| 20a | [`20-gart-module.md`](./20-gart-module.md) | GART 模块设计 (Graphics Address Remapping Table) | ⚠️ **SUPERSEDED** by GMMU v1.0 MVP | — |
| 20b | [`20-gmmu-mvp.md`](./20-gmmu-mvp.md) | GMMU v1.0 MVP 详细设计 (GPU MMU) | Draft v1.0 | (待补 ADR) |
| 20c | [`20-gmmu-evolution-roadmap.md`](./20-gmmu-evolution-roadmap.md) | dGPU GMMU 演进路线图 (v1.0 → v3.0) | Draft v1.0 | (待补 ADR) |

#### E.2 MAS-3.1 SoC 拓扑系列（`21-` 前缀，10 份）

> MAS-3.1 V3.1-Rev2.0 是 dGPU SoC 顶层物理布局，包含 5 大子系统。`21-soc-topology-mvp.md` 是顶层契约，下属 4 个子系统的 MVP + Evolution Roadmap 各 1 份，共 8 份；外加 `21-dist-scale-up-topology-b.md`（方案 B 降级）+ `21-soc-topology-mvp.md`（顶层）= 10 份。

| 序号 | 文件 | 主题 | 状态 |
|:----:|------|------|:----:|
| 21a | [`21-soc-topology-mvp.md`](./21-soc-topology-mvp.md) | **dGPU SoC 顶层物理布局规范 v1.0 MVP (MAS-3.1)** | Draft v1.0 |
| 21b | [`21-tee-udd-mvp.md`](./21-tee-udd-mvp.md) | TEE + UDD v1.0 MVP 详细设计 (Task Execution Engine + Unified Data Dispatcher) | Draft v1.0 |
| 21c | [`21-tee-udd-evolution-roadmap.md`](./21-tee-udd-evolution-roadmap.md) | dGPU TEE + UDD 演进路线图 | Draft v1.0 |
| 21d | [`21-dma-backends-mvp.md`](./21-dma-backends-mvp.md) | DMA Backends v1.0 MVP 详细设计 (Unified Bridge Core + HBM/NIC/IO Protocol Engines) | Draft v1.0 |
| 21e | [`21-dma-backends-evolution-roadmap.md`](./21-dma-backends-evolution-roadmap.md) | dGPU DMA Backends 演进路线图 | Draft v1.0 |
| 21f | [`21-fabric-switch-mvp.md`](./21-fabric-switch-mvp.md) | Fabric + Scale-Up Switch v1.0 MVP 详细设计 | Draft v1.0 |
| 21g | [`21-fabric-switch-evolution-roadmap.md`](./21-fabric-switch-evolution-roadmap.md) | dGPU Fabric + Scale-Up Switch 演进路线图 | Draft v1.0 |
| 21h | [`21-microarch-ifc-mvp.md`](./21-microarch-ifc-mvp.md) | Core/Micro-Arch + RTL-IFC v1.0 MVP 详细设计 | Draft v1.0 |
| 21i | [`21-microarch-ifc-evolution-roadmap.md`](./21-microarch-ifc-evolution-roadmap.md) | dGPU Core/Micro-Arch + RTL-IFC 演进路线图 | Draft v1.0 |
| 21j | [`21-dist-scale-up-topology-b.md`](./21-dist-scale-up-topology-b.md) | 分布式 Scale-Up 拓扑规范 v0.1 (方案 B: 传统分布式, 非 NSA-aware) | Draft v0.1 |

### F. NSA-aware Scale-Up（10 份）

> NSA-aware Scale-Up 是 dGPU SoC 的中长期演进（Stage 1-3, 2026-2029），含 9 份主题文档 + 1 份综合补充。

| 序号 | 文件 | 主题 | 状态 |
|:----:|------|------|:----:|
| [22](./22-nsa-fabric-address-spec.md) | `22-nsa-fabric-address-spec.md` | **NSA-MAS**: 全局 Fabric Address 规范 v0.1 | Draft v0.1 |
| [23](./23-dist-scale-up-topology.md) | `23-dist-scale-up-topology.md` | **Dist-Topology**: 分布式 Scale-Up 拓扑规范 v0.1 (NSA-aware SoC) | Draft v0.1 |
| [24](./24-host-gpu-pcie-ifc.md) | `24-host-gpu-pcie-ifc.md` | **Host-GPU-IFC**: Host-to-GPU PCIe 互联规范 v0.1 (详细版) | Draft v0.1 |
| [25](./25-nsa-hardware.md) | `25-nsa-hardware.md` | **NSA-HW**: NSA-aware MMU + Remote Atomic + Hardware Directory 硬件规范 v0.1 | Draft v0.1 |
| [26](./26-gsp-rm-firmware.md) | `26-gsp-rm-firmware.md` | **GSP-RM**: GPU System Processor + Resource Manager 固件架构 v0.1 | Draft v0.1 |
| [27](./27-nsa-capability.md) | `27-nsa-capability.md` | **NSA-Cap**: Capability-Based 内存保护 + 多租户隔离 v0.1 | Draft v0.1 |
| [28](./28-cxl-3-fabric.md) | `28-cxl-3-fabric.md` | **CXL-3-Fabric**: CXL 3.0 Fabric 兼容与跨域透明 v0.1 | Draft v0.3 |
| [29](./29-nsa-evolution-roadmap.md) | `29-nsa-evolution-roadmap.md` | **NSA-Evolution-Roadmap**: NSA-aware 演进路线图 v0.1 (5 阶段) | Draft v0.1 |
| [30](./30-nsa-comprehensive-supplement.md) | `30-nsa-comprehensive-supplement.md` | **NSA-Compat**: NSA-aware Scale-Up 综合补充规范 v0.1 (Oracle 评审响应) | Draft v0.1 |
| [31](./31-nsa-fault-injection-plan.md) | `31-nsa-fault-injection-plan.md` | **NSA-FIT**: NSA-aware Scale-Up 故障注入测试计划 v0.1 | Draft v0.1 |

### G. CEP 对齐一致性架构（2 份）

| 序号 | 文件 | 主题 | 状态 |
|:----:|------|------|:----:|
| [32](./32-cep-based-coherence-architecture.md) | `32-cep-based-coherence-architecture.md` | **CEP-Coh**: CEP 框架下的 dGPU SoC + NSA 多卡一致性重设计（提问单审阅 8 项发现 + 体系 A/B 收敛诊断 + CEP 分层映射 + 3 域重划 + 2 个协议实例声明 + P0-3 映射表 + 6 问答复 + R-1~R-12 需求单） | 📋 Draft v0.1 |
| [41](./41-cep-alignment-debt-cleanup-proposal.md) | `41-cep-alignment-debt-cleanup-proposal.md` | **CEP-Debt**: CEP 对齐的债务清理与改进提案 v0.1（7 项债务登记 D1~D7 + 5 组建议 diff + 逐格追认清单 + 处置顺序；来自 CppTLM 跨仓请求，队列 #9 R-1 阻塞处置） | 📋 Draft v0.1 |

---

## 3. 阅读路径（按角色）

### 3.1 架构师 / 评审者

**目标**：理解 dGPU SoC v1.0 全貌

```
[00-overview.md]                           ← 1. 总览（必读）
  ├─ §1.3 9 类 SimModule 拓扑
  ├─ §2.1 整体形态对比 (NVIDIA vs AMD vs CppTLM)
  ├─ §3.1-3.7 L1..L7 各层
  ├─ §4-bis 范围矩阵 R01..R27  ← 2. 权威范围表（必读）
  └─ §6.1 复用 v0.5/Phase 8 模块

[01..10-*.md]                              ← 3. 按需深入某一层
[11..13-cdna-*.md]                         ← 4. CDNA 真实 ISA（v1.0+）
[15-sm-microarchitecture-design.md]        ← 5. SM 重构（v1.0 关键）
[19-pcie-ip-microarchitecture.md]          ← 6. PCIe IP（v1.0 关键）
[32-cep-based-coherence-architecture.md]   ← 7. 一致性架构（CEP 对齐，含 SoC 内 + NSA 跨卡收敛）
[33-sm-operand-supply-design-target.md]     ← 8. SM 操作数供给设计目标（OSF，🟡 DRAFT）
[34-sm-operand-supply-ipc-timing-analysis.md]← 9. OSF 的 IPC 模型与时序推导（33 号配套附录）
[35-sm-dependence-management-architecture.md]← 10. OSF 的五类依赖管理架构方案
[36-new-isa-dependence-layer-design.md]← 11. 新 ISA 的依赖层设计方案（候选比较 + 推荐）
[37-new-isa-design-charter.md]← 12. 新 ISA 设计总纲（定位 / 范围 / 参考政策 / 路线图）
[38-new-isa-dual-domain-structure.md]← 13. 新 ISA 的标量/向量双域结构
[39-new-isa-compiler-backend.md]← 14. 新 ISA 的编译器后端方案（PTX/LLVM → 自研 ISA）
[40-new-isa-spec-skeleton.md]← 15. 新 ISA 规范骨架（B-0：架构状态 / 编码 / 依赖层契约）

[../ADR-INDEX.md]                          ← 16. 决策追溯
[../microarchitecture/README.md]                     ← 17. 模块索引
```

### 3.2 实现者（某一层 / 某一模块）

```
[00-overview.md §4-bis]                    ← 1. 确认目标在 v1.0 MVP / v1.1 的位置
[NN-*.md 对应层]                            ← 2. 读该层架构文档
[../microarchitecture/<module>.md]                   ← 3. 读对应模块微架构
[../ADR-INDEX.md]                          ← 4. 查关联 ADR
[../roadmap/phase9-p*.md]                  ← 5. 查阶段计划
```

### 3.3 集成者（NSA-aware 中长期）

```
[00-overview.md]                           ← 1. 总览背景
[21-soc-topology-mvp.md]                   ← 2. MAS-3.1 V3.1-Rev2.0 顶层布局
[22..31-nsa-*.md]                          ← 3. NSA-aware Stage 1-3 详细
[32-cep-based-coherence-architecture.md]   ← 4. 一致性收敛（体系 A SoC 内 + 体系 B 跨卡 → CEP）
[../ADR-INDEX.md §3.2 ADR-SOC-21..25]      ← 5. NSA-aware + CEP 对齐决策
```

---

## 4. 命名约定澄清

### 4.1 序号约定

| 前缀范围 | 含义 | 数量 |
|---------|------|:----:|
| `00-` | 总览蓝图 | 1 |
| `01-` .. `10-` | 7 层 + 附加层（L1..L10） | 10 |
| `11-` .. `15-` | CDNA 系列 + SM 重构 + 架构审计 | 5 |
| `16-` .. `19-` | PCIe 子链路（4 份） | 4 |
| `20-` | GART/GMMU 系列（重号，3 份） | 3 |
| `21-` | MAS-3.1 SoC 拓扑系列（重号，10 份） | 10 |
| `22-` .. `31-` | NSA-aware 系列 | 10 |
| `32-` | CEP 对齐一致性架构 | 1 |
| `33-` | SM 操作数供给设计目标（OSF） | 1 |
| `34-` | SM 操作数供给 IPC 与时序分析（33 号附录） | 1 |

### 4.2 重号系列说明（⚠️ 命名冲突）

**问题**：20-/21- 前缀被多个文件共用，违反数字序号唯一原则。

**历史原因**：
- `20-` 系列原计划为 GMMU 子目录（含 mvp/roadmap），实际只有 3 份未拆分子目录
- `21-` 系列原计划为 MAS-3.1 子目录（含 5 大子系统各 2 份 + 顶层），实际 10 份未拆分子目录

**临时缓解**：本索引用 20a/b/c、21a/b/c/... 标识区分。

**彻底解决**（建议未来清理）：
```
architecture/
├── 20-gmmu/
│   ├── mvp.md                          (was 20-gmmu-mvp.md)
│   ├── evolution-roadmap.md            (was 20-gmmu-evolution-roadmap.md)
│   └── gart-archive.md                 (was 20-gart-module.md, ⚠️ SUPERSEDED)
├── 21-soc-topology/
│   ├── overview.md                     (was 21-soc-topology-mvp.md)
│   ├── tee-udd/
│   │   ├── mvp.md                      (was 21-tee-udd-mvp.md)
│   │   └── evolution-roadmap.md        (was 21-tee-udd-evolution-roadmap.md)
│   ├── dma-backends/
│   │   ├── mvp.md
│   │   └── evolution-roadmap.md
│   ├── fabric-switch/
│   │   ├── mvp.md
│   │   └── evolution-roadmap.md
│   ├── microarch-ifc/
│   │   ├── mvp.md
│   │   └── evolution-roadmap.md
│   └── plan-b-archive.md               (was 21-dist-scale-up-topology-b.md)
```

### 4.3 L1..L7 vs L1..L10 命名差异

| 来源 | 范围 | 层数 |
|------|------|:----:|
| `00-overview.md` §2 | L1 Host 接口 + L2 命令流 + L3 命令协议 + L4 TMU/TMD + L5 WDU→SM + L6 SM/CU + L7 Memory | 7 |
| `00-overview.md` §3 | 同上 | 7 |
| `01..10-*.md` 编号 | L1..L10（含 L8 NoC + L9 Coherence + L10 Completion） | 10 |

**3 个差异层**（00-overview L7 Memory 拆分）：
- **L8 NoC**：独立于 Memory（`08-noc-interconnect.md`）
- **L9 Coherence**：独立于 Memory（`09-coherence-protocol.md`）
- **L10 Completion & Notification**：新增层（`10-completion-notify.md`）

> 这是命名演化结果，新读者以 `01..10` 10 层架构为基准。

---

## 5. 归档与废弃

### 5.1 ⚠️ SUPERSEDED 文档

| 文件 | 状态 | 取代者 | 备注 |
|------|:----:|--------|------|
| `20-gart-module.md` | ⚠️ SUPERSEDED | `20-gmmu-mvp.md` | 2026-09-19 归档；仅作历史参考 |

### 5.2 命名迁移

| 文件 | 旧名 | 新名 | 迁移日期 |
|------|------|------|---------|
| `17-sdma-engine-design.md` | SdmaEngineTLM | IoDmaTLM | 2026-09-19（per `2026-09-19-cpptlm-dgpu-gmmu-mvp`） |

### 5.3 Draft v0.1/v1.0 状态

> 所有 Draft v0.1/v1.0 状态文档均**待 Oracle 评审**。详见各文档头部"审计"字段。

---

## 6. 维护纪律

1. **新增架构文档** → 同步更新本文档 §2 文件清单 + §4 命名约定
2. **新增子目录系列** → 先评估是否重号；如重号，先创建子目录结构再迁入
3. **状态变更** → 文档头部状态字段更新（无 ADR 不可变约束）
4. **归档** → 标记 `⚠️ SUPERSEDED` 状态，保留为历史参考，不删除
5. **跨仓引用** → OpenSpec 链接使用仓内 `openspec/changes/` 路径

---

## 7. 维护记录

| 日期 | 版本 | 修订 |
|------|------|------|
| 2026-10-29 | v3.10 | 新增 41 号《CEP 对齐的债务清理与改进提案》（7 项债务 D1~D7 + 5 组建议 diff + 逐格追认清单 + 处置顺序；CppTLM 跨仓请求）
| 2026-10-28 | v3.9 | 新增 40 号《新 ISA 规范骨架（B-0）》；36 号 v1.3（Q-10 控制块按域裁剪 21/16 bit、Q-11 WAR 改由写者 stall 表达、§4.5 按 7/8-bit 字段重算编码表、E-3/E-7/E-14 补全）；38 号 v1.1（动机排序、SGPR 保留集枚举、删"标量 32-bit"、VCC 迁出 SGPR）；39 号 v1.1（fork 降级为假设 + B-6、元数据表同步）；37 号 v1.1（新增 C-7）；分组 C 扩为 13 份；总数 53 |
| 2026-10-28 | v3.8 | 新增 38 号《新 ISA 标量/向量双域结构》+ 39 号《新 ISA 编译器后端方案》；33/34 号补「向量域」适用域限定；37 号 §3.1 范围表拆标量/向量两行；分组 C 扩为 12 份；总数 52 |
| 2026-10-28 | v3.7 | 新增 37 号《新 ISA 设计总纲》（Q-8 取代关系的落地：范围 / 参考 ISA 政策 / 编译器硬依赖 / 连锁后果）；36 号升至 v1.2（Q-7/Q-8/Q-9 落定）；分组 C 扩为 10 份；总数 50 |
| 2026-10-28 | v3.6 | 新增 36 号《新 ISA 依赖层设计方案：候选架构比较与推荐》；33/35 号加交叉指针；分组 C 扩为 9 份；总数 49 |
| 2026-10-28 | v3.5 | 新增 35 号《SM 依赖管理架构方案：五类依赖的统一框架与双后端》；33 号 §5 加指针；分组 C 扩为 8 份；总数 48 |
| 2026-10-28 | v3.4 | 33 号升至 **v0.5**（开放项裁决：`W=2` / `d=1` / WAR 依赖计数器）+ 34 号升至 v1.1；上游「5/6/7」误读回写 |
| 2026-10-28 | v3.3 | 新增 34 号《SM 操作数供给 IPC 与时序分析》（33 号配套附录）；33 号升至 v0.4；分组 C 扩为 7 份；总数 47 |
| 2026-09-23 | v3.0 | ArchForge 重整：新建本文档；按 7 大类重新分组；显式标注重号系列 |
| 2027-02-09 | v2.x | `00-overview.md` v3.1 PASS（per `architecture/00-overview.md` §10） |
| 2026-06-12 | v1.0 | 早期架构文档创建 |

---

**维护**: ArchForge Team