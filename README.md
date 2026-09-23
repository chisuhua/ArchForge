# ArchForge — dGPU SoC Architecture & Design Repository

> **本仓是 CppTLM 的设计伴侣仓**，存有全部 dGPU SoC 架构设计文档。
> **源代码实现** → [CppTLM](../CppTLM/)（`include/tlm/`, `src/tlm/`）

> **目录结构（v4.0）**: 扁平化（无 `soc_arch/` 命名空间），两大内容类 + 三大横切。

## 范围

| 类 | 目录 | 性质 | 文件数 |
|----|------|------|:------:|
| **系统架构** | `docs/architecture/` | SoC 系统级（00-overview ~ 31-nsa） | 44 |
| **IP 微架构** | `docs/microarchitecture/` | 每 IP/模块一份接口契约（9 大类） | 54 |
| **决策记录** | `docs/adr/` | ADR-SOC-01~24 + README + 2 支持文档 | 27 |
| **路线图** | `docs/roadmap/` | README + 7 阶段 + 1 历史快照 | 9 |
| **设计规格** | `docs/specs/` | APU 形态 spec | 1 |
| **顶层入口** | `docs/README.md` + `docs/ADR-INDEX.md` | 仓库总览 + ADR 体系导览 | 2 |

## 快速导航

| 入口 | 用途 |
|------|------|
| [`docs/README.md`](docs/README.md) | 想理解 dGPU SoC v1.0 系统全貌 + 文档体系（v4.0 仓库入口） |
| [`docs/ADR-INDEX.md`](docs/ADR-INDEX.md) | 想查阅 ADR 决策体系（24 份决策 + 修订规划） |
| [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md) | v1.0 总架构蓝图（⭐ 权威起点，10 节 + 范围矩阵） |
| [`docs/architecture/INDEX.md`](docs/architecture/INDEX.md) | 43 份架构文档分类与阅读路径 |
| [`docs/microarchitecture/INDEX.md`](docs/microarchitecture/INDEX.md) | 52 份 IP 微架构索引（9 大类） |
| [`docs/adr/README.md`](docs/adr/README.md) | ADR 索引（v2.3, 24 份完整列表） |

## 与 CppTLM 的关系

```
ArchForge（设计仓）            CppTLM（实现仓）
┌──────────────────┐          ┌──────────────────┐
│ docs/            │  ← 引用 → │ code + tests     │
│ （架构/ADR/微架构）│          │ core framework   │
│ 系统级设计决策    │          │ 实现级设计文档     │
└──────────────────┘          └──────────────────┘
```

CppTLM 的 `AGENTS.md` / `docs/` 中引用 `docs/` 的路径，通过 **VIRTUAL_PATHS** 机制保持可读（详见 `CppTLM/scripts/test/docs_sync_check.sh`）。

## 维护约定

- **设计变更**：修改文档内容 → 在 ArchForge 仓中提交 PR
- **实现跟踪**：CppTLM 中的 openspec change 若影响设计 → 注明跨仓引用
- **回滚一致性**：跨仓变更必须同步（单仓回滚不影响另一仓状态）

## 历史

- **2026-09-20**: 从 CppTLM 仓 `docs/soc_arch/` 迁移创建（CppTLM commit: `7e15124e`）
- **2026-09-23 v4.0**: 扁平化重构 — 移除 `soc_arch/` 顶层目录；ARCHITECTURE.md 内容合并入 docs/README.md；DECISIONS.md → ADR-INDEX.md