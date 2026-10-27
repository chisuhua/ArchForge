# ArchForge `docs/research/` — SoC / GPU 硬件微架构调研（专利 + 论文 + 仿真器剖析）

> **版本**: v1.0 · **日期**: 2026-10-27 · **状态**: 📋 Research Index（**E 类：调研与证据**）
> **维护**: ArchForge / CppTLM Team
> **来源**: 2026-10-27 自 CppTLM 仓 `docs/research/` 迁入（拆分迁移，见 §5）
> **关联架构文档**: [`docs/architecture/00-overview.md`](../architecture/00-overview.md) · [`05-sm-compute-unit.md`](../architecture/05-sm-compute-unit.md) · [`15-sm-microarchitecture-design.md`](../architecture/15-sm-microarchitecture-design.md)

---

## 1. 范围与定位

本目录收纳 **SoC / GPU 硬件微架构的调研材料**：专利解析、学术论文解析、仿真器源码剖析。

**它们是本仓架构文档与 ADR 的证据锚点**（`00-overview.md`、`ADR-SOC-02/06/09/11/15` 等大量引用本目录）。

**使用原则**（承接 CppTLM 侧原规约）：

- ✅ 引用专利 / 论文的**设计思路**作为架构设计参考
- ❌ **不直接复制专利内容到源码**（避免版权风险）
- ❌ **不声称与专利实现等价**（仅 reference，非 conformance）
- ⚠ **架构真源在本仓 `docs/architecture/` + `docs/adr/`**；本目录是**附属证据层**，不承载"现状真相"，不单独作为设计裁决依据

---

## 2. 目录索引（74 份）

### 2.1 SM/ — SM 内部微架构（25 份）★

NVIDIA Hopper/Blackwell/Volta SM 内部实现的专利与论文综述，**含 Operand Collector 专题**。

| 文件 | 主题 |
|------|------|
| `SM/overview.md` | **NVIDIA Blackwell/Hopper SM 内部实现专利与论文综述**（10 专利 + 4 微基准论文 + 1 官方简报） |
| `SM/NVIDIA_Blackwell_Architecture_Technical_Brief_v2.1_官方技术简报_解析.md` | Blackwell 架构官方技术简报解析 |
| `SM/CudaCore/overview.md` | **★ Operand Collector 专题综述**（3 专利 + 3 论文 + GPGPU-Sim 源码剖析） |
| `SM/CudaCore/SYNTHESIS.md` | **★ Operand Collector 与寄存器架构演进总结**（7 世代表 + 3 不变式 + 4 遗留问题 + CppTLM 结论） |
| `SM/CudaCore/US7834881B2_操作数收集器架构_解析.md` | **★ Operand Collector 源头专利**（bank 仲裁 + 收集单元 + phase 错位） |
| `SM/CudaCore/US8639882B2_源操作数收集器缓存_解析.md` | **★ 源操作数收集器缓存专利**（6 槽位 + cache table + 写回失效） |
| `SM/CudaCore/US8555035B1_无冲突寄存器分配对照_解析.md` | **★ 编译期 conflict-free / aligned 路线**（"取消 OC"对照） |
| `SM/CudaCore/gpgpu-sim_操作数收集器实现剖析.md` | **★ GPGPU-Sim 4.2.0 `opndcoll_rfu_t` 源码剖析**（wavefront 仲裁 + 端口建模） |
| `SM/CudaCore/arXiv2503.20481_现代NVIDIA核心无操作数收集器_解析.md` | **★ 实测否定现代 NVIDIA 存在 OC**（定长延迟 + Allocate 预约 + RFC 语义） |
| `SM/CudaCore/arXiv1804.06826_Volta微基准_寄存器复用与bank冲突_解析.md` | **★ Volta SASS `.reuse` 标志位**（4 reuse cache + 4 slot；2×64-bit bank） |
| `SM/CudaCore/ASPLOS19_CORF_操作数收集器建模_解析.md` | **★ 学术界 OC 建模标准口径**（OC port serialization + bank conflict） |
| `SM/CudaCore/US20230289211A1_…` / `US20240231830A1_…` / `US20240378089A1_…` | CWD/CGA 准入 · SpMV 线程级均衡 · 寄存器文件配置 |
| `SM/CudaCore/arXiv2402.13499` / `2501.12084` / `2507.10789` / `2512.02189` | Hopper / Blackwell 微基准剖析（4 篇） |
| `SM/TMA/`（6 份） | TMA 多播 / mbarrier / TMAU / store-and-arrive / 描述符缓存 / DSMEM |
| `SM/Tensor/`（1 份） | wgmma warp 组矩阵乘加 |

**关联架构文档**：[`05-sm-compute-unit.md`](../architecture/05-sm-compute-unit.md)（寄存器文件 + Warp 调度）· [`15-sm-microarchitecture-design.md`](../architecture/15-sm-microarchitecture-design.md)（SM 微架构重构）· [`06-tensor-core.md`](../architecture/06-tensor-core.md)（TMA / wgmma）

### 2.2 TMU/ — Task Management Unit（16 份）

NVIDIA / AMD 任务管理单元专利族，含 `TMD.md`（Task Metadata Descriptor 完整字段布局）。

**关联**：[`03-task-management-unit.md`](../architecture/03-task-management-unit.md) · [`microarchitecture/tmu-dispatch-processor.md`](../microarchitecture/tmu-dispatch-processor.md)

### 2.3 WDU/ + WDUtoSM/ — 工作分发（6 + 8 份）

NVIDIA WDU（Work Distribution Unit）+ AMD SPI/SQ 路径。

**关联**：[`04-work-distribution.md`](../architecture/04-work-distribution.md) · [`microarchitecture/submit-queue.md`](../microarchitecture/submit-queue.md)

### 2.4 CP/ — Command Processor（13 份）

NVIDIA SM 队列管理器 + AMD HQD / 间接缓冲。

**关联**：[`02-command-processor.md`](../architecture/02-command-processor.md) · [`microarchitecture/command-processor.md`](../microarchitecture/command-processor.md)

### 2.5 PCIe/ — PCIe 物理行为（1 份）

`PCIe/PCIe_上的保序write.md` — MMU ordering pipe + dummy non-posted read flush。

**关联**：[`16-pcie-endpoint-architecture.md`](../architecture/16-pcie-endpoint-architecture.md)

### 2.6 顶层（5 份专利解析）

`US12333311B2` 协作群组阵列 · `US20240036952A1` 线程块调度策略 · `US20240356866A1` 交叉开关动态目的选择 · `US8917271B2` 几何图元再分配负载均衡 · `US9921847B2` 树形线程管理

---

## 3. 跨仓指针（本仓**不收**、但常被引用的 CppTLM 侧调研）

以下调研留在 **CppTLM 仓**（因为它们是该仓已签发 ADR / active change 的**判据定义真源**或**证据锚点**，且主题属 CppTLM 的**框架级能力**而非 SoC 架构建模）：

| 文件 | 留在 CppTLM 的理由 | 主要引用方 |
|------|------------------|-----------|
| `docs/research/cep-coherence-protocol-space-survey.md` | ADR-CEP-08/09/12/13/14 的**判据定义真源** | CppTLM `docs/adr/ADR-CEP-*` |
| `docs/research/cep-cohif-carrier-architecture-review-2026-10-26.md` | active change `cpptlm-cep-cohif-carrier` 的**架构依据** | CppTLM active change + `.rddf/` |
| `docs/research/gem5-*.md`（7 份） | ADR-CEP-00/17、ADR-DGPU-13/14、CppTLM `docs/architecture/06-*`/`07-*` 的证据锚点 | CppTLM 真源 1 + ADR |
| `docs/research/research-cpptlm-gpu-fused-soc-survey.md` | CppTLM 专用（名字即表明） | CppTLM `.rddf/` |

> **引用方式**：跨仓引用请用**仓名 + 仓内相对路径**（如 `CppTLM: docs/research/gem5-soc-survey.md`），**不要**用相对路径（跨仓相对路径必然失效）。

---

## 4. 命名约定

- **专利解析文件**：`US<专利号>_<中文主题>_解析.md`
- **综述文档**：`overview.md`（每子目录顶）+ `SYNTHESIS.md`（综合提取）
- **论文解析**：`arXiv<编号>_<中文主题>_解析.md`
- **仿真器剖析**：`<项目名>_<主题>实现剖析.md`
- **专利原文不存放**（仅分析）— 避免版权 + 体积问题

---

## 5. 迁移记录（2026-10-27）

自 **CppTLM 仓** `docs/research/` 迁入本仓，采用**按消费方拆分**而非整目录搬迁：

| 分类 | 处置 | 依据 |
|------|------|------|
| `CP/` `WDU/` `WDUtoSM/` `TMU/` `PCIe/` `SM/` + 顶层 5 份专利（74 份） | → **ArchForge** | 本仓 `00-overview.md` / ADR-SOC-02/06/09/11/15 等**以相对路径引用**（迁移前全部悬空，迁移后 9/12 自动解悬空） |
| `cep-*.md` `gem5-*.md` `research-cpptlm-*.md`（10 份） | → **留 CppTLM** | 是 CppTLM 已签发 ADR / active change 的判据真源与证据锚点；主题属框架级能力 |
| `docs/architecture/14-sm-operand-supply-design-target.md`（OSF 设计目标） | → **ArchForge `docs/architecture/33-…`** | silicon 侧真源在本仓；原编号 `14` 在本仓已被 `14-stage-a-architecture-audit.md` 占用 |

**连带修复（本仓相对链接 off-by-one 修正）**：本仓原先以相对路径指向 research 的链接全部写成 `../../research/…`，但这些文件都位于 **`docs/adr/` `docs/architecture/` `docs/microarchitecture/` `docs/specs/`（深度 2）**——`../../` 会落到**仓库根**，与正文写的 `docs/research/…` 不一致，**全部悬空**。本次统一修正为 `../research/…`（**17 个文件 / 94 处**），使链接与正文一致、指向本仓 `docs/research/`。

**连带修复（跨仓引用去链接化）**：另有 **54 处**指向 CppTLM 仓 `docs/research/research-cpptlm-gpu-fused-soc-survey.md`、**5 处**指向 CppTLM 仓 `docs/research/gem5-soc-survey.md` —— 这两个文件**留在 CppTLM**（是其已签发 ADR / active change 的判据证据锚点），已改为**跨仓纯文本指针**（`【CppTLM 仓】docs/research/…`），避免失效相对链接。

**迁移前后本仓相对 .md 链接失效数**：**291 → 159**（-132，-45%）；其中与 research 相关的失效仅剩 **3 处**（`2026-09-04-*.md` 三份 CDNA-EMU 选型调研——**从未在任何仓存在过**，属既有缺陷，非本次引入）。

---

## 6. 相关文档

- 本仓架构索引：[`docs/architecture/INDEX.md`](../architecture/INDEX.md)
- 本仓 ADR 索引：[`docs/adr/README.md`](../adr/README.md)
- 本仓总览：[`docs/README.md`](../README.md)
- CppTLM 仓（实现仓）：`/workspace/project/CppTLM`
