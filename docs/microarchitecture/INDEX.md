# Microarchitecture 索引（IP 微架构）

> **版本**: v3.1 (2026-09-23 重整版 · 目录名 `modules/` → `microarchitecture/`)
> **范围**: `docs/microarchitecture/` 全部 52 份 IP 微架构文档
> **关联总览**: [`../README.md`](../README.md) · **关联决策**: [`../ADR-INDEX.md`](../ADR-INDEX.md)
> **本目录定位**: 每个 IP/模块一份接口契约，描述端口、Bundle、关键算法、状态机

---

## 0. 阅读引导

本文档是 `microarchitecture/` 目录的**微架构索引**，回答 2 个问题：

1. **本目录有什么模块？分别是什么状态？** → §1 分类总览 + §2 模块清单
2. **要找某个模块怎么办？** → §3 命名约定 + §4 阅读路径

> **重要说明**：本目录的 `README.md`（v2.1, 2026-06-11）已部分过时（仍以 Phase 7 路径描述），本文档为重整版索引。两份文档并存，**以本 INDEX.md 为权威**。

---

## 1. 分类总览（9 大类，52 份模块文档）

| # | 类别 | 文档数 | 已实施 | 规划中 | 典型模块 |
|---|------|:----:|:-----:|:-----:|---------|
| **1** | **CPU 端模块** (Initiator) | 3 | 3 | 0 | `cpu-cputlm.md`, `cpu-traffic_gen.md`, `cpu-cpusim_legacy.md` |
| **2** | **内存子系统** | 5 | 2 | 3 | `memory-memtlm.md`, `memory-hbm.md`, `memory-dram.md`, `memory-simple.md`, `memory-qos.md` |
| **3** | **Cache 层级** | 6 | 0 | 6 | `cache-l1.md`, `cache-l2.md`, `cache-protocol.md`, `cache-replacement.md`, `cache-noncoherent.md`, `cache.common.md` |
| **4** | **Interconnect / NoC** | 10 | 6 | 4 | `interconnect-crossbar.md`, `noc-router.md`, `coherent_xbar.md`, `snoop_filter.md`, `gpu-noc-mesh.md`, ... |
| **5** | **GPU / GPGPU + dGPU 切片** | 11 | 10 | 1 | `gpu-gputlm.md`, `command-processor.md`, `tmu-dispatch-processor.md`, `submit-queue.md`, `gpu-memory-cluster.md`, `gpu-shared-memory.md`, ... |
| **5b** | **GPU / dGPU SOC PCIe Slice** | 1 | 1 | 0 | `dgpu-soc-pcie-slice.md` |
| **6** | **IO / DMA / 设备** | 8 | 1 | 7 | `io-dma.md`, `io-pio.md`, `io-disk.md`, `io-ether.md`, ... |
| **7** | **Coherence / 桥接** | 3 | 2 | 1 | `coherence-domain.md`, `coherence-protocol.md`, `coherence-bridge.md` |
| **8** | **RTL 桥接** | 2 | 2 | 0 | `rtl-hybrid_cache.md`, `rtl-fragment_mapper.md` |
| **9** | **Framework Adapter (AXI)** | 2 | 2 | 0 | `axi4-stream-adapter.md`, `axi4-mapper.md` |
| **总计** | — | **52** | **29** | **23** | — |

> **已实施 (✅/🔵) 29 份 / 规划中 (🟡) 23 份 / 52 份**

---

## 2. 模块清单（按分类）

### 类别 1：CPU 端模块（3 份 — 全部已实施）

| 文件 | 类 | 状态 | 角色 |
|------|----|:----:|------|
| [`cpu-cputlm.md`](./cpu-cputlm.md) | `CPUTLM` (`include/tlm/cpu_tlm.hh`) | ✅ v2.1 | 0x1000–0x1100 线性只读，10cy 间隔 |
| [`cpu-traffic_gen.md`](./cpu-traffic_gen.md) | `TrafficGenTLM` (`include/tlm/traffic_gen_tlm.hh`) | ✅ v2.1 | 7 种流量模式（SEQUENTIAL/RANDOM/TRACE/HOTSPOT/STRIDED/NEIGHBOR/TORNADO）|
| [`cpu-cpusim_legacy.md`](./cpu-cpusim_legacy.md) | `CPUSim` (`include/modules/legacy/cpu_sim.hh`) | ⚠️ Legacy | 仅 `BUILD_LEGACY_MODULES=ON` 编译 |

### 类别 2：内存子系统（5 份 — 2 已实施 + 3 规划）

| 文件 | 状态 | 角色 |
|------|:----:|------|
| [`memory-memtlm.md`](./memory-memtlm.md) | ✅ v2.1 | `MemoryTLM` 简化 DRAM 桩（rd 100cy / wr 120cy + 行缓冲）|
| [`memory-hbm.md`](./memory-hbm.md) | ✅ Phase 8.A Task 2 | HBM 模式（v1.0 HBM3e 战略补充）|
| [`memory-dram.md`](./memory-dram.md) | 🟡 规划中 | DRAMCtrl 扩展（bank/rank/页策略）|
| [`memory-simple.md`](./memory-simple.md) | 🟡 规划中 | SimpleMemory（吞吐/带宽/队列模型）|
| [`memory-qos.md`](./memory-qos.md) | 🟡 规划中 | QoS 内存调度 |

### 类别 3：Cache 层级（6 份 — 0-1 已实施 + 5-6 规划）

| 文件 | 状态 | 角色 |
|------|:----:|------|
| [`cache-l1.md`](./cache-l1.md) | ✅ 已实施 + v1.0 协议感知扩展 | L1 Cache + 协议状态机 |
| [`cache-l2.md`](./cache-l2.md) | 🟡 规划中 → 🔵 部分实施 | L2 Cache |
| [`cache-protocol.md`](./cache-protocol.md) | 🟡 规划中 → 🔵 部分实施 | Cache 协议（snoop fan-out）|
| [`cache-replacement.md`](./cache-replacement.md) | 🟡 规划中 | 替换策略族（LRU/LFU/FIFO/RRIP）|
| [`cache-noncoherent.md`](./cache-noncoherent.md) | 🟡 规划中 → 🔵 部分实施 | 非一致性 Cache |
| [`cache.common.md`](./cache.common.md) | 🟡 规划中 | Cache 公共基类 |

### 类别 4：Interconnect / NoC（10 份 — 6 已实施 + 4 规划）

| 文件 | 状态 | 角色 |
|------|:----:|------|
| [`interconnect-crossbar.md`](./interconnect-crossbar.md) | 🟡 规划中 | 4 端口地址路由 + 冲突检测（`CrossbarTLM`）|
| [`interconnect-arbiter.md`](./interconnect-arbiter.md) | — | N→1 + 1 出 Round-Robin（`ArbiterTLM<N>` 特化 N=2,4）|
| [`interconnect-bridge.md`](./interconnect-bridge.md) | — | 跨域桥接（gem5 Bridge 蓝图）|
| [`noc-router.md`](./noc-router.md) | ✅ v2.1 | 5 端口双向 Mesh 路由器（`RouterTLM`，XY 路由 + Credit）|
| [`noc-nic.md`](./noc-nic.md) | ✅ v2.1 | 双端口 NIC（PE 侧 CacheBundle + Net 侧 NoCFlitBundle）|
| [`noc.common.md`](./noc.common.md) | ✅ v2.1 | NoC 公共基类 + Link 物理延迟 |
| [`comm_monitor.md`](./comm_monitor.md) | — | 流量监控/带宽/延迟/outstanding |
| [`coherent_xbar.md`](./coherent_xbar.md) | ✅ 已实施 + v1.0 战略补充 | 一致性 Crossbar（含 snoop 广播）|
| [`snoop_filter.md`](./snoop_filter.md) | ✅ 已实施 + v1.0 战略补充 | Snoop Filter |
| [`gpu-noc-mesh.md`](./gpu-noc-mesh.md) | ✅ Phase 8.A Task 3 + 📋 v1.0 战略补充 | GPU NoC Mesh（per L8 子系统架构）|

### 类别 5：GPU / GPGPU + dGPU MVP 切片（11 份 — 10 已实施）

| 文件 | 类 | 状态 | 角色 |
|------|----|:----:|------|
| [`gpu-gputlm.md`](./gpu-gputlm.md) | `GPUTLM` (`include/tlm/gpu/gpu_tlm.hh`) | ✅ v0 (Phase 7.A) | GPU 黑盒发起器（5 setter + 50% 读写混合 + 7 stats）|
| [`gpu-tcc.md`](./gpu-tcc.md) | `TCC_TLM` (规划) | 🟡 规划中 | GPU L2（aggregate + write coalescing + snoop fan-in）|
| [`gpu-pcie_bridge.md`](./gpu-pcie_bridge.md) | (规划) | 🟡 规划中 | GPU↔PCIe 桥接 |
| [`gpu-memory-cluster.md`](./gpu-memory-cluster.md) | `MemoryCluster` (v1.0 HBM3e 扩展) | ✅ Phase 8.A Task 2 + 📋 v1.0 | GPU 内存子系统（per L7 + ADR-SOC-09 D5）|
| [`gpu-shared-memory.md`](./gpu-shared-memory.md) | `SharedMemoryTLM` (v1.0 SMEM/LDS + DSMEM/TMEM) | ✅ Phase 8.A Task 1 + 📋 v1.0 | SM 内部共享内存（per L6 + ADR-SOC-09 D5）|
| [`command-processor.md`](./command-processor.md) | `CommandProcessorTLM` | 🔵 MVP (ADR-SOC-06) | NVIDIA PM4 CP (5-state FSM + backpressure + DEGRADED) |
| [`pm4-decoder.md`](./pm4-decoder.md) | (子模块) | 🔵 MVP (ADR-SOC-06) | PM4 method packet 解析 |
| [`tmu-dispatch-processor.md`](./tmu-dispatch-processor.md) | `TmuDispatchProcessorTLM` | 🔵 MVP (ADR-SOC-06) | TMU Glue (3 端口 dispatch_in/cta_out/done_in + dep 链) |
| [`submit-queue.md`](./submit-queue.md) | `SubmitQueueTLM` | 🔵 MVP (ADR-SOC-06) | WDU 分发网络 (4 端口) |
| [`completion-ring.md`](./completion-ring.md) | `CompletionRingTLM` | 🔵 MVP (ADR-SOC-06) | 完成通知 FIFO (4 端口, 多源汇聚) |

### 类别 5b：GPU / dGPU SOC PCIe Slice（1 份 — 已实施）

| 文件 | 状态 | 角色 |
|------|:----:|------|
| [`dgpu-soc-pcie-slice.md`](./dgpu-soc-pcie-slice.md) | 🔵 Implemented (ADR-SOC-07) | dGPU SOC PCIe 切片（4 端口 PcieEndpointTLM + SdmaEngineTLM）|

### 类别 6：IO / DMA / 设备（8 份 — 1 已实施 + 7 规划）

| 文件 | 状态 | 角色 |
|------|:----:|------|
| [`io-pio.md`](./io-pio.md) | 🟡 规划中 | PIO Device（gem5 PioDevice 蓝图）|
| [`io-dma.md`](./io-dma.md) | ✅ 已实施 + v1.0 战略补充 | DMA Device（5 端口 `SdmaEngineTLM` + PCIe master）|
| [`io-disk.md`](./io-disk.md) | 🟡 规划中 | SimpleDisk（gem5 SimpleDisk）|
| [`io-terminal.md`](./io-terminal.md) | 🟡 规划中 | Terminal（gem5 Terminal）|
| [`io-uart.md`](./io-uart.md) | 🟡 规划中 | Uart8250 |
| [`io-ether.md`](./io-ether.md) | 🟡 规划中 | EtherLink + EtherDevice |
| [`io-pci.md`](./io-pci.md) | 🟡 规划中 | PciDevice abstract |
| [`io-nvram.md`](./io-nvram.md) | 🟡 规划中 | NVRAM（非易失存储）|

### 类别 7：Coherence / 桥接（3 份 — 2 已实施 + 1 规划）

| 文件 | 状态 | 角色 |
|------|:----:|------|
| [`coherence-domain.md`](./coherence-domain.md) | ✅ 已实施 + v1.0 战略补充 | MESI/MOESI enum + snoop fanout + home node + 跨域 bridge |
| [`coherence-protocol.md`](./coherence-protocol.md) | ✅ 已实施 + v1.0 战略补充 | MOESI 状态机（6 状态）|
| [`coherence-bridge.md`](./coherence-bridge.md) | 🟡 规划中 → 🔵 部分实施 | 跨 coherence 域桥接（gem5 Bridge）|

### 类别 8：RTL 桥接（2 份 — 全部已实施）

| 文件 | 类 | 状态 | 角色 |
|------|----|:----:|------|
| [`rtl-hybrid_cache.md`](./rtl-hybrid_cache.md) | `HybridCacheComponent` (`include/rtl/hybrid_cache_component.hh`) | ✅ v2.1 | 纯 C++20 CppHDL 组件，2 态 FSM |
| [`rtl-fragment_mapper.md`](./rtl-fragment_mapper.md) | `FragmentMapper` (`include/rtl/fragment_mapper.hh`) | ✅ v2.1 | TLM↔RTL fragment 转换模板 |

### 类别 9：Framework Adapter（AXI）（2 份 — 全部已实施）

> 跨切关注点：AXI 协议边界 adapter，连接 PCIe EP ↔ NoC ↔ 内存子系统。

| 文件 | 类 | 状态 | 角色 |
|------|----|:----:|------|
| [`axi4-stream-adapter.md`](./axi4-stream-adapter.md) | `Axi4StreamAdapter` (per ADR-SOC-13) | 🔵 Implemented (Phase 5) | AXI↔TLP 边界 adapter（PCIe↔AXI 边界 + outstanding 跟踪）|
| [`axi4-mapper.md`](./axi4-mapper.md) | `Axi4Mapper` (per ADR-SOC-13) | 🔵 Implemented (Phase 6) | AXI4 OOO + rid 关联（512-bit 限制）|

---

## 3. dGPU 数据面核心（v0.5 MVP 已实施 — 实施者快速定位）

```
DGpuBoard (C++ shell, include/tlm/gpu/dgpu_board_shell.hh)
└── DGpuSoc (SimModule 容器, include/tlm/gpu/dgpu_soc.hh)
    │
    ├── PCIe slave side
    │   ├── PcieEndpointTLM (4 ports, tlm::gpu)              ← dgpu-soc-pcie-slice.md
    │   │   └── ConfigSpace + BarRouter + MSI-X
    │   └── (v1.0) PcieEndpointIP (17 ports)                ← architecture/19-pcie-ip-microarchitecture.md
    │       ├── stream_id 路由 (per function: PF=0, VF0..15=1..16)
    │       └── MSI-X / Config Space / BAR (内部组件)
    │
    ├── PCIe master side
    │   └── SdmaEngineTLM (5 ports, tlm::gpu)               ← io-dma.md / dgpu-soc-pcie-slice.md
    │       └── (v1.0) IoDmaTLM 重命名                      ← architecture/17-sdma-engine-design.md
    │
    ├── Command pipeline (5-state FSM)
    │   ├── CommandProcessorTLM (4 ports, tlm::gpu)          ← command-processor.md
    │   │   └── Pm4Decoder (NVIDIA PM4 method packet)        ← pm4-decoder.md
    │   └── (v1.0) 双 vendor 双 decoder                      ← architecture/02-command-processor.md
    │
    ├── Task management
    │   └── TmuDispatchProcessorTLM (3 ports, tlm::gpu)      ← tmu-dispatch-processor.md
    │       └── (v1.0) TMU 完整版 (US11182207B2 依赖预取)    ← architecture/03-task-management-unit.md
    │
    ├── Work distribution
    │   └── SubmitQueueTLM (4 ports, tlm::gpu)               ← submit-queue.md
    │       └── (v1.0) WDU + Round-Robin crossbar            ← architecture/04-work-distribution.md
    │
    ├── Completion
    │   └── CompletionRingTLM (4 ports, tlm::gpu)           ← completion-ring.md
    │       └── MSI-X 中断 + Doorbell                       ← architecture/10-completion-notify.md
    │
    └── Memory
        └── MemoryTLM (VRAM)                                 ← memory-memtlm.md
            └── (v1.0) HBM3e + L2 + L1 + SMEM               ← architecture/07-memory-system.md
```

> **v1.0 关键升级**：4 端口 → 17 端口 PcieEndpointIP；增加 HostBypassTLM + PcieRootComplexTLM；CU 蓝图模式；双 vendor 双 decoder。

---

## 4. 命名约定

### 4.1 文件命名

| 模式 | 含义 | 示例 |
|------|------|------|
| `<domain>-<type>.md` | 域+类型 | `gpu-gputlm.md`, `memory-memtlm.md`, `io-dma.md` |
| `noc.<common>.md` | 公共基类 | `noc.common.md`, `cache.common.md` |
| `<subcomponent>.md` | 子组件 | `host-bypass.md`, `pcie-root-complex.md`, `axi4-stream-adapter.md` |

### 4.2 命名迁移

| 文件 | 旧类名 | 新类名 | 迁移日期 |
|------|--------|--------|---------|
| `17-sdma-engine-design.md` (架构) | `SdmaEngineTLM` | `IoDmaTLM` | 2026-09-19 |
| `io-dma.md` (模块) | `SdmaEngineTLM` | `IoDmaTLM` | 2026-09-19 |

> 过渡期旧类保留并加 `[[deprecated]]` 标注。

---

## 5. 已废弃模块（⚠️ Deprecated）

| 文件/类 | 状态 | 取代者 |
|---------|------|--------|
| ~~`cuda-core-adapter.md`~~ | ❌ Deprecated (per Task 12) | `IComputeDevice` (per ADR-SOC-16) |
| ~~`ptx-emu-submodule-mvp.md`~~ | ❌ Deprecated (per Task 12) | `IComputeDevice::set_instr_descriptor_buf` |
| ~~`dgpu-board.md`~~ | ⚠️ Superseded | `dgpu-soc-pcie-slice.md` + 新 shell 模式 |
| `cpu-cpusim_legacy.md` (`CPUSim`) | ⚠️ Legacy | `cpu-cputlm.md` (`CPUTLM`) |

> **注**：上述 deprecated 模块文档已不存在于本目录，但部分模块名在旧文档中仍被引用。实施时请使用最新文档。

---

## 6. 阅读路径

### 6.1 找特定模块

```
1. 确定类别（1-8）
2. 在 §2 模块清单中找到文件
3. 阅读模块文档（包含：Header / 命名空间 / 角色 / 注册位置 / 状态）
4. 查关联架构：../README.md §5 引用矩阵
5. 查关联 ADR：../ADR-INDEX.md §5.2
```

### 6.2 实施 dGPU 模块

```
读 [architecture/00-overview.md] §4-bis 范围矩阵 R01..R27
  ↓
定位模块 [本目录对应 .md 文件]
  ↓
查关联 ADR [ADR-INDEX.md §5.2]
  ↓
查阶段计划 [roadmap/phase9-p*.md]
```

### 6.3 跨仓查实现

> 本目录文档描述**接口契约**。具体 C++ 实现位于 CppTLM 仓：
> - Header：`/workspace/project/CppTLM/include/tlm/`
> - Source：`/workspace/project/CppTLM/src/tlm/`

---

## 7. Bundle 与 StreamAdapter 体系

### 7.1 Bundle 类型映射

| Bundle | Header | 用于 |
|--------|--------|------|
| `CacheReqBundle` / `CacheRespBundle` | `include/bundles/cache_bundles_tlm.hh` | CacheTLM / MemoryTLM / CPU / TrafficGen / Crossbar / Arbiter / NICTLM (PE 侧) |
| `NoCFlitBundle` | `include/bundles/noc_bundles_tlm.hh` | RouterTLM / LinkTLM / NICTLM (Network 侧) — REQUEST/RESPONSE/CREDIT |
| `ComputeReqBundle` / `ComputeRespBundle` | `include/bundles/compute_bundles_tlm.hh` | GPUTLM v0 (Phase 7.A) — 核心 8 字段 + kernel_id/workgroup_id/wavefront_id/coalescing_factor |
| `CacheReqBundleRTL` / `CacheRespBundleRTL` | `include/bundles/cache_bundles_rtl.hh` | HybridCacheComponent（RTL 侧）|

### 7.2 StreamAdapter 形态

| Adapter | Header | 用于 |
|---------|--------|------|
| `StreamAdapter<ModuleT, Req, Resp>` | `include/framework/stream_adapter.hh` | 单端口模块（CacheTLM/MemoryTLM/CPUTLM/GPUTLM）|
| `MultiPortStreamAdapter<ModuleT, Req, Resp, N>` | `include/framework/multi_port_stream_adapter.hh` | 多端口模块（CrossbarTLM 4 端口 / ArbiterTLM）|
| `BidirectionalPortAdapter<ModuleT, BundleT, N>` | `include/framework/bidirectional_port_adapter.hh` | 双向（RouterTLM 5 端口）|
| `DualPortStreamAdapter<...>` | `include/framework/dual_port_stream_adapter.hh` | 双类型端口（NICTLM PE+Net 侧 / TCC_TLM）|

---

## 8. 维护纪律

1. **新增模块** → 同步更新本文档 §1 分类总览 + §2 模块清单
2. **状态变更**（已实施 / 规划中 / Deprecated）→ 文档头部状态字段更新
3. **类名迁移** → 旧类加 `[[deprecated]]`，新类建立，保留 6 个月兼容期
4. **归档** → 标记 `❌ Deprecated` 或 `⚠️ Superseded`，保留为历史参考
5. **跨仓引用** → Header / Source 路径使用 CppTLM 仓内相对路径

---

## 9. 维护记录

| 日期 | 版本 | 修订 |
|------|------|------|
| 2026-09-23 | v3.0 | ArchForge 重整：新建本文档；按 8 大类重整；明确已实施 23 / 规划中 27 |
| 2026-06-11 | v2.1 | 原始 README.md（基于 Phase 7 调研）|
| — | v1.0 | 早期模块文档创建 |

---

**维护**: ArchForge Team