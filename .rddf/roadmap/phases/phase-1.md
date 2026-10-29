---
id: phase-1
kind: phase
status: active
primary_scope: docs/architecture
co_scopes: [docs/adr]
phase_refs: []
主题: CEP 对齐债务清理与规约追认
---

# Phase 1: CEP 对齐债务清理与规约追认

**目标**: 清掉 ArchForge 侧 CEP 对齐遗留的 7 项文档债务（D1~D7），使 `mesif` 声明与 CppTLM 侧 R-1 裁决口径一致，并把 MESIF 规约缺口收敛为可追认、可判据化的状态。

**来源**: CppTLM 跨仓请求（队列 #9 `cpptlm-cep-mesif-adapter` 的 R-1 阻塞处置）· 原 ArchForge `docs/architecture/41-cep-alignment-debt-cleanup-proposal.md`（已于 2026-10-29 移除，债务清单迁入改进提案）。

**状态**: 🟡 active（改进提案已登记，待 design 阶段审查批准）

## 关联

- 改进提案: `.rddf/improvements/cep-alignment-debt-cleanup.md`
- 本仓决策: `docs/adr/ADR-SOC-25-cep-aligned-coherence-architecture.md`
- 受影响架构文档: `docs/architecture/32-cep-based-coherence-architecture.md` · `docs/architecture/25-nsa-hardware.md`
- 跨仓依据: CppTLM `ADR-CEP-04 §13`（R-1 裁决）· `ADR-CEP-12 §13`（权威迁移）· openspec change `cpptlm-cep-mesif-state-spec`（规约层，Phase 0~5 未开始）
