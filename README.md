# ArchForge — dGPU SoC Architecture & Design Repository

> **本仓是 CppTLM 的设计伴侣仓**，存有全部 dGPU SoC 架构设计文档。
> **源代码实现** → [CppTLM](../CppTLM/)（`include/tlm/`, `src/tlm/`）

## 范围

- **dGPU SoC 架构**: `docs/soc_arch/architecture/`（00-overview ~ 31-nsa，43 份）
- **架构决策记录**: `docs/soc_arch/adr/`（ADR-SOC-01~24，27 份）
- **IP 模块微架构**: `docs/soc_arch/modules/`（53 份设计文档）
- **设计规格**: `docs/soc_arch/specs/`
- **路线图**: `docs/soc_arch/roadmap/`

## 与 CppTLM 的关系

```
ArchForge（设计仓）            CppTLM（实现仓）
┌──────────────────┐          ┌──────────────────┐
│ docs/soc_arch/   │  ← 引用 → │ code + tests     │
│ （架构/ADR/模块） │          │ core framework   │
│ 系统级设计决策    │          │ 实现级设计文档     │
└──────────────────┘          └──────────────────┘
```

CppTLM 的 `AGENTS.md` / `docs/` 中引用 `docs/soc_arch/` 的路径，通过 **VIRTUAL_PATHS** 机制保持可读（详见 `CppTLM/scripts/test/docs_sync_check.sh`）。

## 维护约定

- **设计变更**：修改文档内容 → 在 ArchForge 仓中提交 PR
- **实现跟踪**：CppTLM 中的 openspec change 若影响设计 → 注明跨仓引用
- **回滚一致性**：跨仓变更必须同步（单仓回滚不影响另一仓状态）

## 历史

于 2026-09-20 从 CppTLM 仓 `docs/soc_arch/` 迁移创建（CppTLM commit: `7e15124e`）。