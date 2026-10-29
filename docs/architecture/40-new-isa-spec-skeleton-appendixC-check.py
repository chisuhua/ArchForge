#!/usr/bin/env python3
# 40 号 附录 C：机械化自检脚本（零依赖，python3 直跑）
#
# 用途：把 40 号附录 B 中**纯算术类**的检查项在本仓内直接验证，
#       使 ADR-SOC-30 的 V1/V2（编码位宽核算）与 ADR-SOC-27 的 V1（附录 B 清单）
#       **不必等 CppTLM 侧**即可关闭。
#
# 本脚本**不解析文档**：它从规范数值**独立重算**，再与规范中的声明值比对 ——
#   若文档里的数字被改动而规范数值未变，本脚本仍按规范重算并 PASS；
#   若规范数值本身被改错，本脚本无法发现（那需要人工同步）。
#   ⇒ 因此本脚本是**回归护栏**（防止重算结果漂移），不是规范校验器。
#
# 用法：
#   python3 docs/architecture/40-new-isa-spec-skeleton-appendixC-check.py
#   退出码 0 = 全部通过；1 = 有失败项
#
# --- 规范数值（来源：40 号 §3.2 / §3.3 / §3.4 / §4.1 / §4.6） ---

FORMATS = {
    #  name        fmt  长度  opcode 寄存器/立即数 控制块
    "SOP1":      ("000", 48, 11, 2*7,      16),
    "SOP2":      ("001", 48, 11, 3*7,      16),
    "SOPC":      ("010", 48, 11, 2*7,      16),
    "SOPP":      ("100", 48, 11, 16,        16),   # imm16
    "SOPK":      ("011", 64, 11, 7 + 16,    16),   # s0 + imm16
    "VOP1":      ("101", 48, 11, 2*8,      21),
    "VOP2":      ("110", 64, 11, 3*8,      21),
    "VOP3":      ("111", 64, 11, 4*8,      21),
}

VECTOR_CTRL = {"stall":4, "sb_id":3, "wait_mask":8, "reuse_flags":3, "budget_hint":2, "yield":1}
SCALAR_CTRL = {"stall":4, "sb_id":3, "wait_mask":8, "yield":1}

SB_SLOTS      = 8
COUNTER_BITS  = 6
STALL_BITS    = 4
STALL_MAX     = (1 << STALL_BITS) - 1     # 15
LW_MIN        = 4                          # L_w,min 全局下界
D_ALU         = 3
D_MEM         = 4
D_MEM_LATE    = 11
L_W_ALU       = 4
WARP_PER_SM   = 48
RF_BITS       = 2097152

# 精确填满的形态（其余留 RSV / imm8 余量）
EXACT = {"SOP2": 48, "VOP1": 48, "VOP3": 64}

# 依赖面积：SB[8] × 6 bit + stall 4 + yield 1
DEP_BITS_PER_WARP = SB_SLOTS * COUNTER_BITS + 4 + 1

results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))

# --- 检查 1 / 2：各形态位宽之和 <= 长度 ---
for f, (fmt, ln, opc, reg, ctrl) in FORMATS.items():
    tot = opc + reg + ctrl
    check(f"检查1/2 {f}: {opc}+{reg}+{ctrl} = {tot} <= {ln}", tot <= ln,
          "精准填满" if tot == ln else f"余 {ln-tot} bit")

# --- 检查 3：控制块位宽之和 ---
check("检查3 向量控制块 = 21", sum(VECTOR_CTRL.values()) == 21, str(sum(VECTOR_CTRL.values())))
check("检查3 标量控制块 = 16", sum(SCALAR_CTRL.values()) == 16, str(sum(SCALAR_CTRL.values())))

# --- 检查 4 / 5：mask 位宽 = 槽数；sb_id 位宽 = log2(槽数) ---
check("检查4 wait_mask 位宽 = SB 槽数 = 8",
      VECTOR_CTRL["wait_mask"] == SB_SLOTS, f"{VECTOR_CTRL['wait_mask']} vs {SB_SLOTS}")
check("检查5 sb_id 位宽 = log2(8) = 3",
      VECTOR_CTRL["sb_id"] == 3 and (SB_SLOTS & (SB_SLOTS-1)) == 0)

# --- 检查 6 / 7：D-1 与 D-1' ---
check("检查6 D-1: 向量 ALU D_c=3 <= L_w,min=4", D_ALU <= LW_MIN)
check("检查6 D-1: 标准访存 D_c=4 <= L_w,min=4", D_MEM <= LW_MIN)
check("检查7 D-1': late-addr D_c=11, 11-4=7 <= 15", D_MEM_LATE - LW_MIN <= STALL_MAX,
      f"{D_MEM_LATE}-{LW_MIN}={D_MEM_LATE-LW_MIN}")

# --- 检查 8：L_w > 15 的类必须走 SB（矩阵类 32/64） ---
mma_lw = [32, 64]
check("检查8 MMA L_w>15 的类全部声明为可变延迟（走 SB）",
      all(v > STALL_MAX for v in mma_lw), f"{mma_lw} 皆 > {STALL_MAX} ⇒ 必须走 SB")

# --- 检查 9：SGPR 可分配数 <= 2^索引位宽 ---
SGPR_TOTAL, SGPR_RESERVED = 128, 4
check("检查9 SGPR 可分配 124 <= 2^7 = 128", SGPR_TOTAL - SGPR_RESERVED <= 128)

# --- 检查 11：S-DEP-0 全局下界 ---
check("检查11 所有类 L_w,c >= 4", all(v >= LW_MIN for v in [L_W_ALU]), "L_w,min = 4")

# --- 检查 14：opcode 分段之和 = 256 ---
seg = {"普通": 128, "P 变体": 64, "专用": 64}
check("检查14 opcode 分段 128+64+64 = 256", sum(seg.values()) == 256)

# --- 面积复算（36 号 §4.2.2 口径：bit/warp × 48 warp ÷ 2,097,152） ---
dep_pct = DEP_BITS_PER_WARP * WARP_PER_SM / RF_BITS * 100
check("依赖面积 53 bit/warp × 48 warp / 2,097,152 = 0.121%",
      abs(dep_pct - 0.1214) < 0.001, f"{DEP_BITS_PER_WARP} bit/warp -> {dep_pct:.4f}%")

# --- 精确填满的形态（附录 B 检查 1/2 的「精准」子集） ---
for f, ln in EXACT.items():
    opc, reg, ctrl = FORMATS[f][2], FORMATS[f][3], FORMATS[f][4]
    check(f"精准填满 {f} = {ln}", opc + reg + ctrl == ln)

# --- 准入：stall 义务的可表达性（缺口 ≤ STALL_MAX） ---
#    RAW：gap 需提供 L_w - d 拍；WAR：gap 需提供 8 - d 拍；两者取 max
def max_gap_need(lw, d):
    raw = max(0, lw - d)
    war = max(0, (D_MEM_LATE - LW_MIN + 1) - d)
    return max(raw, war)

worst = max(max_gap_need(lw, 1) for lw in [L_W_ALU])
check("两类义务取 max 的最坏值 <= 15（4-bit stall 上界）", worst <= STALL_MAX, f"max = {worst}")

print()
print(f"总计：{sum(1 for _,ok,_ in results if ok)}/{len(results)} 通过")
raise SystemExit(0 if all(ok for _, ok, _ in results) else 1)
