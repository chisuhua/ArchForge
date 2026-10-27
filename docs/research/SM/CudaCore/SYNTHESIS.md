# Operand Collector 与寄存器架构演进 — 综合总结（SYNTHESIS）

> **专题目录**: `docs/research/SM/CudaCore/`
> **创建日期**: 2026-10-27
> **状态**: 📋 Research Synthesis（背景参考，非契约）
> **上游材料**: 本目录 8 篇逐篇解析（3 专利 + 3 论文 + GPGPU-Sim 源码）+ 一手 PDF 全文
> **定位**: 把 [overview.md](overview.md) 的"逐件罗列"压缩成"**演进逻辑**"——每一代解决了什么、又暴露了什么、以及为什么下一代不能重复 NVIDIA 的老路

---

## 0. 一句话结论

> **二十年来 NVIDIA 只做了一件事：把"从寄存器堆取操作数"的成本，从【运行时】不断挪到【编译期】和【缓存】里。**
>
> 挪移的顺序是：**运行时收集（Tesla→Kepler）→ 编译期复用（Maxwell/Pascal）→ 结构性降冲突（Volta）→ 取消收集器 + 定长预约（Turing/Ampere）→ 专用化（Hopper/Blackwell 张量路径）**。
>
> 每一步都消除了上一代的**一种**成本，但都引入了新的**一种**成本；而**至今没有任何一代消除过"依赖链延迟 = 4 cycle"和"同一 RF 读端口一次只能供一个操作数"这两条**。

---

## 1. 七个世代的演进表

| 世代 | RF 组织 | 操作数供给机制 | 冲突表现 | 复用机制 | 延迟契约 | 关键代价 |
|------|---------|---------------|---------|---------|---------|---------|
| **Tesla** (2006) | 真多端口 | 1 拍取齐 | 无 | 无 | 定长 1 | **面积 + 功耗**（多端口 SRAM） |
| **Fermi** (2010) | 4 bank × 1R1W | **OC 收集器**（Collector Unit + Bank 仲裁 + Crossbar） | OC 内串行；3 源同 bank → **≥3 拍** | 无 | **可变** | 面积（crossbar）+ **延迟可变** |
| **Kepler** (2012) | 4 bank × 256 reg | OC + **复用缓存**（6 storage elements + cache table，**写回即失效**） | 同上 | 硬件 cache table | 可变 | 槽位固定 6；容量约束 |
| **Maxwell / Pascal** (2014-16) | 4 bank × 32-bit，**1 值/bank/cycle** | OC（保留） | **分配无法消除**，只能缓解 | **编译器 `.reuse`**（4 cache + 4 slot，8-byte 粒度） | 可变 | 编译器负担；**跨 warp 切换使 reuse 全失效（+1 拍）** |
| **Volta** (2017) | **2 bank × 64-bit**（`bank = reg_index % 2`） | OC 保留，但 64-bit bank 使同 bank 可取 2 值 | 3 源同 bank 才冲突；**分配可部分消除** | 同上（4 reuse cache + 4 slot） | 可变 | **放弃双发射**（每 block 只剩 1 dispatch unit） |
| **Turing / Ampere** (2018-20) | **每 sub-core 2 bank**；每 bank **1×1024-bit 读口 + 1×1024-bit 写口** | **OC 被废除**：**定长 3 周期**读源 + **Allocate 级端口预约** + result queue + bypassing | **issue 侧气泡**：0/1/2 冲突 → 5/6/7 cycle | **RFC**：每 bank 1 entry × 3 操作数位置 = **6 子条目**，编译器 `.reuse` 管理，**读一次即失效** | **定长**（编译期已知） | 3 周期窗口对 2 源指令浪费带宽；**依赖管理从硬件 scoreboard 挪到编译器控制位** |
| **Hopper / Blackwell** (2022-25) | 标量路径沿用 Ampere | 标量同 Ampere；**张量路径换血**：`wgmma` → `tcgen05` + **TMEM** | — | — | 定长 | TMEM 把操作数供给**从通用 RF 挪到专用张量内存**——**专用化 > 通用化**的又一次重演 |

---

## 2. 四条机制轴的谱系

### 轴 1 — bank 划分：从"多端口模拟"到"宽度换端口"

```
Tesla:  1 个真多端口 SRAM（面积爆炸）
Fermi:  4 bank × (1R+1W)  → 4R4W 语义   ← 专利 US7834881B2：2 个 1R1W 模拟 2R2W
Kepler: 4 bank × 1 值/cycle（32-bit 宽）
Maxwell/Pascal: 4 bank × 32-bit（与 Kepler 同，冲突不可避免）
Volta:  2 bank × 64-bit   ← 宽度换端口：一条指令可从同 bank 取 2 个值
Ampere: 2 bank × 1024-bit ← 每 bank 1 个"整 warp 寄存器"读口
```

**规律**：NVIDIA 从未靠"加 bank 数"扩带宽，而是靠 **"加宽 bank"**。原因是 CORF 论文给出的量化结论：**一个 warp 寄存器宽 1024 bit，多一个读口的面积代价极高**。

#### 轴 1 深化：为什么 Volta 起是 **2 bank** 而不是 4 bank（2026-10-27 增补）

**一句话**：在**总读带宽守恒**的前提下，NVIDIA 把带宽从"多而窄的 bank"重新分配成"少而宽的 bank"——因为**冲突判据是"某个 bank 本拍需要的源值数是否超过它每周期的供给数 V"，而不是"源分散在几个 bank"**。**V 越大，冲突越少**。

**冲突判据（本文归纳，跨三代一致）**：

```
bank conflict  ⟺  存在某个 bank，本拍需要的源值数 > V（该 bank 每周期的供给数）
冲突气泡拍数   =  ceil(该 bank 需要的源值数 / V) − 1
```

**用这条判据核对三代实测**：

| 世代 | N（bank 数） | V（每 bank 每周期供给） | N×V（总供给/拍） | 3 源冲突条件 | 实测气泡 |
|------|-------------|----------------------|------------------|------------|---------|
| Maxwell/Pascal | 4 | 1 值（32-bit） | 4 | **≥2 源同 bank** | — |
| **Volta** | **2** | **2 值（64-bit）** | 4 | **3 源全同 bank** | — |
| **Ampere** | **2** | **1 warp 寄存器（1024-bit）** | 2 | 同上（warp 寄存器粒度） | 2 源同 bank → **1 拍气泡**；3 源同 bank → **2 拍气泡**；不同 bank → **无气泡** |

> Ampere 一列是**判据的实证校验**（arXiv:2503.20481 §5.3 原文：FMUL 两源同 bank 产生 1-cycle bubble，FFMA 三源同 bank 产生 2-cycle bubble，两源不同 bank 无 bubble）——与 `ceil(k/V) − 1` 完全吻合。

**冲突概率（本文推导，假设源寄存器号均匀分布）**：

| 组织 | 冲突条件 | 冲突概率 | 期望气泡/指令 |
|------|---------|---------|-------------|
| 4 × 32-bit（Maxwell/Pascal） | ≥2 源同 bank | 1 − (4·3·2)/4³ = **0.625** | 0.5625×1 + 0.0625×2 = **0.6875** |
| **2 × 64-bit（Volta）** | 3 源全同 bank | 2/2³ = **0.25** | 0.75×0 + 0.25×1 = **0.25** |
| 4 × 64-bit | 3 源全同 bank | 4/4³ = **0.0625** | 0.9375×0 + 0.0625×1 = **0.0625** |

→ **同样的总供给（4 值/拍）**：4×64 的冲突期望比 2×64 低 **4×**，比 4×32 低 **11×**。

**那为什么不是 4×64-bit？** 因为 **N×V 是读带宽预算，不是免费的**：

1. **4×64 = 2 倍读端口能量/面积**。RF 是 SM 上最大的一块面积（256 KB/SM @ Ampere），读口的 sense amp + driver 成本正比于端口宽度（CORF §1：「the cost of a port is extremely high when considering the width of a warp register」）。
2. **当时的瓶颈不是带宽**：1 条 FFMA/拍只需 **3 值/拍**，2×64 已供 4 值/拍 → **多出来的带宽无处可去**。
3. **写带宽**：每 bank 只有 1 个写口，bank 数同时决定写吞吐（FFMA 每拍写 1 个 dst，2 写口已够）。
4. **物理**：bank 是 warp 内线程条带化的载体（Fermi 的 8 sub-bank 就是为了让 32 线程的同一寄存器被一次读出），bank 过少会让阵列过宽。

**为什么不能更少（1 bank）**：写带宽退化、阵列过宽，且完全失去 bank 间的并发读能力 → **2 是甜点**。

**代价（NVIDIA 实际付出的）**：

- **bank 映射变粗**：`bank(reg) = reg_index mod 2`（Volta）比 `mod 4`（Maxwell/Pascal）更粗 → 编译器自由度下降，"3 源全同 bank"仍需靠分配规避；
- 单 bank 容量翻倍 → SRAM 宏更大（面积/时序）；
- **同期放弃双发射**（Volta 每 processing block 只剩 1 个 dispatch unit）——bank 重构 + 取消双发射是同一次取舍的两面。

**Ampere 反而"欠配"——这才是关键转折**：

- Ampere 2 bank × 1024-bit = 每子核每拍只供 **2 个 warp 寄存器**，而一条 FFMA 需要 **3 个** → **供给 < 需求**，冲突是被**设计进去**的（实测 1–2 拍气泡）。
- 缺口由 **RFC（每 bank 1 entry × 3 操作数位置 = 6 子条目）** 补——**不是靠加 bank，而是靠缓存把"读的次数"降下来**。
- 这正是下一代设计（OSF）的出发点：**减少读 → 顺带减少冲突**（见 [`docs/architecture/33-sm-operand-supply-design-target.md`](../../../architecture/33-sm-operand-supply-design-target.md) §2）。

**论文原话**（arXiv:1804.06826 §3.5，逐字）：

> "The register file on Volta is divided into 2 banks and the width of each bank is 64 bits. This differs from the 4-bank, 32-bit wide design on previous architectures. **The wider register banks make it easier for the compiler to generate conflict-free code.** On Volta, the bank of a register is the register's index modulo 2."

> "Any FFMA instruction that accesses the same bank with all its 3 source registers is said to have a bank conflict. This means the architecture **cannot satisfy the accesses simultaneously**; instead, they must be serialized which takes longer and is inefficient."

> "However, on Volta, even when row and column input registers belong to the same bank, **one can avoid the conflict by using a third input register from the other bank**."（64-bit bank 能一拍供 2 值 → 把累加器放到另一个 bank 即可解冲突）

**⚠ 口径警示**：Volta 论文的"值"是 **32-bit 线程值**，Huerta 论文的 1024-bit 端口是**整个 warp 寄存器**——**两者的"值"粒度不同，跨世代的气泡数不可直接比较**。上面的 0.6875 → 0.25 只在 **Volta 论文内部**（同口径）成立。

### 轴 2 — 端口/收集：从"运行时收集"到"运行时预约"

```
Fermi-Kepler:  Collector Unit + Bank 仲裁 → 收集延迟可变（1~3 拍）
Maxwell-Volta: 同上（但 bank 变宽 → 实际冲突概率下降）
Ampere+:       Allocate 级【端口预约窗口】→ 3 拍定长，冲突变成 issue 侧气泡
```

**关键转折点是 arXiv:2503.20481 的论证**：OC 引入可变延迟，而 NVIDIA ISA 要求延迟编译期已知（编译器要靠 `Stall counter` 排依赖）——**两者不可共存**。所以 OC 必须被取消，代价是"3 拍定长窗口"这个新的浪费。

### 轴 3 — 操作数复用：从"硬件 cache"到"编译器显式位"

| 世代 | 机制 | 命中条件 | 失效 | 谁的负担 |
|------|------|---------|------|---------|
| Kepler | 6 storage elements + cache table | 同槽位 + 同寄存器号 | **写回即失效** | 硬件 |
| Maxwell~Ampere | **`.reuse` 标志位**（SASS 控制字） | 同 warp + 同寄存器号 + **同操作数位置** | **读一次即失效**（无论是否命中） | **编译器** |
| Ampere RFC | 每 bank 1 entry × 3 操作数位置 | 同上 | 同上 | 编译器 |

**这条轴的教训最值得记**：NVIDIA 两次都选了"**把复用决策推给编译器**"而不是硬件自动 cache。原因是——自动 cache 的**命中条件不可预测**，而编译期决策可以把复用变成**指令语义的一部分**（SASS 里可见的 `.reuse`），编译器可以精确控制收益。**代价**：跨 warp 切换会让所有 reuse 失效（Volta 论文实测：+1 拍）。

### 轴 4 — 冲突处理：三个阶段，第三次是"放弃"

```
① 运行时仲裁（Fermi-Kepler）：Bank Request Arbitration Unit，冲突→延迟变长
② 编译期保证（Maxwell/Pascal → Volta）：phase 错位 / conflict-free 分配 / 64-bit bank
③ 接受并廉价化（Ampere+）：冲突→1~2 拍 issue 气泡，不再试图消除
```

**为什么 NVIDIA 放弃了"消除冲突"**：

| 证据 | 结论 |
|------|------|
| US8555035B1 | 编译期 conflict-free 需要 copy 指令 + 寄存器压力上升 |
| Volta 64-bit bank | 结构性降冲突有效，但只解决"3 源"里的部分 |
| arXiv:2503.20481 Table 6 | **每 bank 加到 2 个读口**：MaxFlops **speed-up 1.44×**（= Ideal 行同值）、Cutlass **1.11×**（≈ Ideal 1.12×）、**Cutlass APE 反而从 9.72% 改善到 0.97%**；但 **MaxFlops APE 从 2.82% 恶化到 28.97%**（= Ideal 行同值）——**这是"该学术模型刻画不了多端口配置"的建模精度信号，不是硬件变差的实测** |
| ASPLOS'19 CORF §1 | **"the cost of a port is extremely high when considering the width of a warp register"**——这才是**硬件面积代价**的论据 |
| 同上 | 关掉 RFC：CUTLASS sgemm 掉到 **0.79×**；RFC 覆盖率 **35.9% 的静态指令** |

**NVIDIA 选择"接受冲突、让它变便宜"，而不是"消除冲突"**（理由：编译期消除要 copy 指令 + 寄存器压力；硬件消除要加端口，**面积代价极高**——CORF §1「the cost of a port is extremely high when considering the width of a warp register」）。而"让读变少"（合并、复用、窄读）是**唯一同时改善带宽与冲突**的方向：CORF 的寄存器合并实测 **读次数 -23%、IPC +9%、RF 动态能耗 -17%**；NVIDIA 的 RFC 实测 **CUTLASS sgemm 关掉 RFC 掉到 0.79×、35.9% 的静态指令至少 1 个操作数走 RFC**。

> ⚠ **v0.2 修正（2026-10-27，critic BLOCKER 3）**：v0.1 在此处写的是"**'加端口'被实测证伪为错误解法**（精度反而变差）"——**这是指标类别误用**，已删除该表述。APE（Average Percentage Error）是**仿真模型相对硬件的建模精度指标**，不是硬件面积/功耗/性能指标。
>
> **纠正后的完整结论**：
> - **加 2 读口在性能上并不差**：MaxFlops speed-up **1.44×**（与 Ideal 无限端口行同值）、Cutlass **1.11×**（≈ Ideal 1.12×）、**Cutlass APE 反而从 9.72% 改善到 0.97%**。原文明确写"**four read ports (two per bank) are sufficient to meet demand**"。
> - **MaxFlops APE 2.82% → 28.97%** 与 **Ideal 行同值** → 含义是"**Huerta 的学术模型刻画不了多端口配置**"，**不是**"多端口硬件更差"。
> - **真正的否决论据是硬件面积**：CORF §1「the cost of a port is extremely high when considering the width of a warp register」——warp 寄存器宽 1024 bit，多一个读口的面积代价极高。
> - **第二条论据是口径正确性**：真实 NVIDIA 每 bank 就是 1 个读口（实测），建模成 2 读口会让 CppTLM 与硬件脱节。
>
> **对 CppTLM 的净结论不变**（C7），但**依据换成了正确的类别**。

---

## 3. 贯穿二十年的三条不变式

| # | 不变式 | 证据 |
|---|--------|------|
| **I1** | **RF 读端口是稀缺资源**，面积代价 ≈ warp 寄存器宽度（1024 bit）的量级 | CORF §1："the cost of a port is extremely high"；Ampere 实测每 bank 仅 1 读口 |
| **I2** | **操作数供给延迟必须编译期已知**，否则编译器无法排依赖 | arXiv:2503.20481 §5.3；`Stall counter` 控制字（Volta 论文 §2.1） |
| **I3** | **冲突的最优解在编译期**，硬件只负责让冲突变便宜 | `.reuse` 位（Volta 论文）→ US8555035B1 → Ampere 的"接受气泡" |

---

## 4. 四条至今未解的问题（SOTA 的入口）

> 编号 P1–P4，直接对应下一代架构设计的四个目标。

### P1 — 依赖链延迟钉死在 4 cycle

- 实测：Volta `FFMA` 依赖延迟 **4 cycle**（Pascal 6）；Ampere `mad.lo.f32` 依赖 CPI **4**。
- 原因：**结果必须"先写 RF，再读出"**。NVIDIA 已有 result queue + bypassing（arXiv:2503.20481 证实），但那是**同一流水线级内**的旁路，缩短的是 RF 往返，**不是 ALU 流水线本身**。
- 后果：当 kernel 的 ILP < 4（很常见），SM 吞吐被依赖链而非算力限制。

### P2 — 定长 3 周期窗口对 2 源指令浪费约 25% 读带宽

- 实测："all the fixed-latency instructions **spend three cycles for reading source operands**, **even if some of these cycles the instruction is idle** (for instance when there are only two source operands)".
- 结构性浪费：FFMA 3 源占满窗口；FADD/FMUL 2 源却也占 3 拍。

### P3 — RFC 是"读一次即失效"，producer→多 consumer 链几乎无法复用

- 实测语义："A cached value is unavailable after a read request arrives to the same bank and operand position, **regardless of whether it hits**"。
- 后果：要让第 3 条指令还能命中，**每一条消费者都必须重新置 `.reuse` 位**（论文 Listing 2 Example 1 vs 2 精确展示了这一点）。
- 这直接限制了 GEMM/Attention 这类"A 的一个元素被 N 个 B 元素消费"模式的收益——而这正是 GPU 最核心的算子模式。

### P4 — 窄值仍按全宽读取

- RF 物理上已经支持窄宽度（Fermi 起 8 sub-bank × 128-bit 条带，CORF 靠这个做寄存器打包）。
- 但 bank 读口固定 1024 bit，**不管值实际多窄**。
- 后果：int8/bf16 混合 kernel 的 RF 读带宽浪费 2–4×。

---

## 5. 学术建模口径 vs 硬件实测口径（必须分开引用）

| 维度 | 学术模型（CORF / Accel-Sim / GPGPU-Sim） | NVIDIA 实测（Volta/Ampere/Turing） |
|------|---------------------------------------|-----------------------------------|
| OC 是否存在 | **假设存在**（Fermi 基线，CU0–CU3） | **Volta 起不存在**（arXiv:2503.20481 实测否定） |
| 冲突表现 | **指令在 OC 内多等**（可变延迟） | **issue 侧气泡**（定长延迟） |
| bank 映射 | GPGPU-Sim：`bank = (reg + warp_id) % N`（**加了 warp id**，是建模折中） | Volta 实测：`bank = reg_index % 2`（**不加 warp id**） |
| 复用缓存 | **完全没有**（`reuse cache` 全仓 0 命中） | `.reuse` 位 + RFC 6 子条目 |
| 依赖管理 | 硬件 scoreboard | 编译器控制位（Dependence counter + Stall counter + Yield） |
| 精度基线 | Accel-Sim MAPE **18.24%** | 重写后 **13.98%**（RTX A6000） |

> **引用警告**：任何基于 Accel-Sim / GPGPU-Sim 的 bank 冲突统计，都建立在"OC 存在 + 可变延迟"这一**已被现代硬件否定的假设**之上。

---

## 6. 与本目录其它文档的关系

| 文档 | 在本总结中的角色 |
|------|----------------|
| [overview.md](overview.md) | 专题综述（专利群 + 论文群 + 参数总表）—— **广度** |
| [US7834881B2 解析](US7834881B2_操作数收集器架构_解析.md) | 轴 1/2/4 的源头 |
| [US8639882B2 解析](US8639882B2_源操作数收集器缓存_解析.md) | 轴 3 的源头 |
| [US8555035B1 解析](US8555035B1_无冲突寄存器分配对照_解析.md) | 轴 4 的"编译期"分支 |
| [gpgpu-sim 剖析](gpgpu-sim_操作数收集器实现剖析.md) | 学术口径的代码真身 |
| [arXiv:2503.20481 解析](arXiv2503.20481_现代NVIDIA核心无操作数收集器_解析.md) | 轴 2 的转折点 + P1/P2/P3 的证据 |
| [arXiv:1804.06826 解析](arXiv1804.06826_Volta微基准_寄存器复用与bank冲突_解析.md) | 轴 1/3 的 SASS 级证据 |
| [ASPLOS'19 CORF 解析](ASPLOS19_CORF_操作数收集器建模_解析.md) | 轴 1 的量化依据（端口成本）+ P4 的来源 |
| [33-sm-operand-supply-design-target.md](../../../architecture/33-sm-operand-supply-design-target.md) | **本总结 P1–P4 的应答设计**（🟡 设计目标声明，位于 `docs/architecture/`，非本文档目录） |

---

## 7. 对 CppTLM 的直接结论

| # | 结论 | 依据 |
|---|------|------|
| C1 | **默认口径必须选"现代口径"**（定长 3 周期 + Allocate 预约 + issue 气泡），**不要**照抄 GPGPU-Sim 的 OC 可变延迟模型 | arXiv:2503.20481 实测否定现代 OC；Accel-Sim sm_90 已切 SIMPLE |
| C2 | **数据冒险与端口争用必须分层** | US7834881B2 原文并列；GPGPU-Sim 中 Scoreboard 与 OC 互不引用 |
| C3 | **bank 映射用硬件口径** `bank = reg_index % N`，不用 gpgpu-sim 的 `+ warp_id` | Volta 实测 §3.5 |
| C4 | **操作数来源寄存器号已在 `InstrDescriptor::src_regs[4]` 里**，不需要给 bundle 加字段就能算 bank | `include/tlm/gpu/instruction_descriptor.hh` |
| C5 | **`InstrDescriptor` 实测 128 字节、断言 `<= 128` → 余量 0**，任何新字段都不能加；复用/预算位应塞进 `CtrlBits::reserved_ctrl0/1`（另有 `reserved_hdr`+`reserved_mem` 共 8B padding 可回收，但属跨仓契约变更） | 实测编译验证（2026-10-27） |
| C6 | **reuse cache 是可建模的低成本增量**（`RegFileUnit` 加一张表 + 写入口失效钩子） | US8639882B2 权项 2/3 + Ampere 实测语义 |
| C7 | **不要建模"加 RF 读口"这条路径** | ① 硬件面积：CORF §1「the cost of a port is extremely high」（warp 寄存器 1024 bit 宽）；② 口径正确性：真实 NVIDIA 实测每 bank 就是 1 读口。**注意**：论据**不是** Table 6 的 APE 数字（那是建模精度指标，见 §2 修正说明） |

---

*本总结基于 2026-10-27 本次下载的一手材料（3 件 NVIDIA 专利 PDF + 3 篇论文 PDF + 本机 GPGPU-Sim 4.2.0 源码）整理。所有数值均来自原文，跨世代对照已标注世代与口径差异。*
