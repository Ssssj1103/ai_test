# -*- coding: utf-8 -*-
"""Day 25 · 自一致率 + 分歧仲裁：重标 30 条 → 一致率 → 规范 v1.1 修订建议
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day04_consistency.py          # 交互重标（真实演练，推荐）
    /Users/zcb/miniconda3/envs/aiml/bin/python day04_consistency.py --auto   # 自动模式（回归验证用）
产出：data/day04_consistency_report.md（一致率 + 分歧清单 + 规范修订建议）
核心思想：一致率是"考核规范"的指标——分歧集中的类别对，就是规范④要补判例的地方。
"""

# ============ 导入区 ============
import csv
import os
import random
import sys
from collections import Counter
from datetime import datetime

random.seed(25)                               # 重标队列抽样可复现
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
D3_CSV = os.path.join(DATA, "day03_labeled.csv")
OUT = os.path.join(DATA, "day04_consistency_report.md")
LABELS = ["投诉", "咨询", "催发货", "发票", "售后退换", "其他"]

# ============ ① 读 D3 标注结果（缺失时用最小模拟兜底，保证脚本可独立回归） ============
def load_first_pass():
    if os.path.exists(D3_CSV):
        with open(D3_CSV, encoding="utf-8") as f:
            rows = [(int(r["id"]), r["message"], r["label"], float(r["seconds"] or 0))
                    for r in csv.DictReader(f)]
        print(f"① 已读 D3 标注结果：{len(rows)} 条")
        return rows
    print("① [警告] 未找到 day03_labeled.csv——用模拟数据兜底（正式练习请先跑 D3 交互标注）")
    pool = [(i, f"模拟客服消息第{i}条，关于物流问题", random.choice(LABELS), random.uniform(5, 50))
            for i in range(100)]              # 兜底数据仅保证流程可跑
    return pool

# ============ ② 重标队列：跳过条 + 慢条 + 每类随机 2 条（D4 第 3 节的规则） ============
def sample_queue(rows, n=30):
    skipped = [r for r in rows if not r[2]]                              # ① 上次跳过的（无标签）
    slow = sorted((r for r in rows if r[2]), key=lambda r: -r[3])[:10]   # ② 耗时 TOP10
    slow_ids = {r[0] for r in slow}
    by_cls = {}
    for r in rows:
        if r[2] and r[0] not in slow_ids:
            by_cls.setdefault(r[2], []).append(r)
    common = []
    for lb, items in by_cls.items():                                     # ③ 每类随机 2 条普通例
        common += random.sample(items, min(2, len(items)))
    picked = {r[0]: r for r in (skipped + slow + common)}                 # id 去重
    rest = [r for r in rows if r[0] not in picked]                        # 不足 n 时随机补足（保证 30 条有效样本量）
    random.shuffle(rest)
    for r in rest:
        if len(picked) >= n:
            break
        picked[r[0]] = r
    queue = list(picked.values())
    random.shuffle(queue)
    return queue[:n]

# ============ ③ 两种"第二次标注" ============
def auto_second(msg, first):
    """模拟第二次标注：比第一次更稳定（5% 噪声），且在'投诉/催发货'边界上易摇摆"""
    if random.random() < 0.05:
        return random.choice(LABELS)
    if "投诉" in msg and first in ("催发货", "售后退换", "咨询") and random.random() < 0.8:
        return "投诉"                                    # 边界摇摆：模拟规范盲区（见词就判投诉是典型错）
    return first

def human_second(idx, n, msg, first):
    """交互重标：先答后看（防锚定）——答完才显示第一次结果"""
    print(f"\n[{idx+1}/{n}] 「{msg}」")
    for i, lb in enumerate(LABELS, 1):
        print(f"  {i}. {lb}", end="")
    print("\n  0. 无法仲裁")
    c = input("  第二次标注: ").strip()
    second = None if c == "0" else LABELS[int(c) - 1]
    print(f"  → 第一次标的是：{first or '（跳过）'}")
    return second

# ============ ④ 主流程：重标 → 一致率 → 仲裁记录 → 报告 ============
def main():
    rows = load_first_pass()
    queue = sample_queue(rows)
    mode = "自动" if "--auto" in sys.argv else "交互"
    print(f"② 重标队列 {len(queue)} 条（跳过条 {sum(1 for r in queue if not r[2])} + 慢条 TOP10 + 每类普通例）｜模式：{mode}")
    random.seed(2025)                         # auto 模式二次固定种子：保证回归验证输出可复现
    verdicts = []                             # (消息, 第一次, 第二次, 仲裁, 依据, 动作)
    for i, (rid, msg, first, _sec) in enumerate(queue):
        if "--auto" in sys.argv:
            second = auto_second(msg, first)
        else:
            second = human_second(i, len(queue), msg, first)
        if first == second:
            basis, action = "一致，无需仲裁", "无需改"
        elif first and second:
            basis, action = "分歧：两次都'有道理' → 规范④缺判例", "补充规范④判例"
        elif second is None:
            basis, action = "无法仲裁 → 规范结构性盲区", "规范 v1.1 必改项"
        else:                                 # 第一次跳过、第二次有结论
            basis, action = "昨日跳过条已可判定 → 规范盲区已闭合", "在规范④登记新判例"
        arb = second if second else (first if first else "pending")
        verdicts.append((msg, first or "跳过", second or "无法仲裁", arb, basis, action))

    valid = [v for v in verdicts if v[1] not in ("跳过", "无法仲裁") and v[2] != "无法仲裁"]
    agree = sum(1 for v in valid if v[1] == v[2])
    rate = agree / max(len(valid), 1)
    print(f"\n③ 自一致率：{agree}/{len(valid)} = {rate:.0%}（红线 95% → {'✓ 合格' if rate >= .95 else '✗ 需修规范'}）")
    dis_pairs = Counter((v[1], v[2]) for v in valid if v[1] != v[2])
    print("   分歧对 TOP（规范④补判例的优先级清单）：")
    for (a, b), n in dis_pairs.most_common(5):
        print(f"     {a} ↔ {b}：{n} 条")
    return verdicts, rate, dis_pairs, len(queue)

def write_report(verdicts, rate, dis_pairs, n):
    L = [f"# 自一致率与分歧仲裁报告（Day25，{datetime.now():%Y-%m-%d %H:%M}）\n",
         f"- 重标 {n} 条｜有效对比 {len([v for v in verdicts if v[1] not in ('跳过', '无法仲裁') and v[2] != '无法仲裁'])} 条",
         f"- **自一致率 {rate:.0%}**（红线 95% → {'合格' if rate >= .95 else '不合格：边界规则不够具体'}）",
         "- 读法提醒：一致 ≠ 正确。一致只证明规则可稳定复现，正确性要靠金标/Gold 抽查（W5 陌生人试标补这一环）\n",
         "## 分歧对统计（→ 规范 v1.1 补判例优先级）\n"]
    for (a, b), n2 in dis_pairs.most_common():
        L.append(f"- {a} ↔ {b}：{n2} 条")
    L.append("\n## 仲裁记录（逐条，无悬案纪律）\n")
    for i, (msg, f1, s2, arb, basis, action) in enumerate(verdicts, 1):
        L.append(f"{i}. 「{msg}」｜一次: {f1}｜二次: {s2}｜仲裁: {arb}")
        L.append(f"   - 依据：{basis}")
        L.append(f"   - 动作：{action}")
    L.append("\n## 规范 v1.1 修订建议草案（人工定稿后写进《标注规范》⑦变更记录）\n")
    for (a, b), _ in dis_pairs.most_common(3):
        L.append(f"- 【{a} vs {b}】增加判例 2 条（一正一反），并在决策树第＿＿步明确仲裁顺序")
    L.append("\n> 使用纪律：pending 条目不许入 D5 训练集；v1.1 属澄清型改动，v1.0 数据无需全部重标。")
    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print(f"\n④ 报告已导出：{OUT}")
    print("\n⑤ 人工下一步（不可跳过）：")
    print("   a. 把'修订建议草案'定稿进《标注规范 v1.1》⑦变更记录")
    print("   b. 核对：分歧对是否就是 D3 问题日志里的卡壳点（应互相印证）")
    print("   c. pending 条目列表单独存档，明天 D5 清洗时剔除")

if __name__ == "__main__":
    _v, _r, _d, _n = main()
    write_report(_v, _r, _d, _n)
