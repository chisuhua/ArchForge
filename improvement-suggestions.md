# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `improvement-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `improvement-approved.md` 等待实施 → 实施后归档。
> **跨仓提示**: 本仓是 CppTLM 的设计伴侣仓；提案若含跨仓依赖（如 CppTLM 侧 openspec change / ADR 裁决），必须在「来源」列写明跨仓锚点，否则跨仓债不可见。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [cep-alignment-debt-cleanup](.rddf/improvements/cep-alignment-debt-cleanup.md) | P1 | CppTLM 跨仓请求（队列 #9 `cpptlm-cep-mesif-adapter` 的 R-1 阻塞处置）· 取代已移除的 `docs/architecture/41-cep-alignment-debt-cleanup-proposal.md` · 跨仓锚点：CppTLM `ADR-CEP-04 §13`（R-1 裁决）/ `ADR-CEP-12 §13`（权威迁移）/ openspec change `cpptlm-cep-mesif-state-spec`（规约层） | 2026-10-29 | 待审查 |
