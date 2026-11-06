# -*- coding: utf-8 -*-
"""Day 28 · M1 整合日：交付物体检 + 数据集卡片草稿 + W4 出口自测
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day07_w4_review.py
产出：data/DATASET_CARD.md（数据集卡片草稿）+ 控制台 M1 达成判定
核心思想：里程碑 = 可追溯的交付物 + 可复述的链路。卡片是数据集的"产品说明书"。
"""

# ============ 导入区 ============
import json
import os
from collections import Counter
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
CARD = os.path.join(DATA, "DATASET_CARD.md")

# ============ ① M1 交付物体检（存在性 + 关键内容粗检） ============
CHECKS = [                                   # (交付物, 路径, 必含关键词)
    ("标注实操记录", "day03_labeled.csv", ["id", "message", "label"]),
    ("标注 Session 报告", "day03_session_log.md", ["Session"]),
    ("一致性报告", "day04_consistency_report.md", ["自一致率"]),
    ("构建漏斗账本", "day05_sft_build_report.md", ["过滤漏斗"]),
    ("质检报告", "day06_qc_report.md", ["已知局限"]),
]

def audit_deliverables():
    ok = 0
    print("① M1 交付物体检：")
    for name, fname, kws in CHECKS:
        p = os.path.join(DATA, fname)
        if not os.path.exists(p):
            print(f"   ✗ {name}：缺 {fname}")
            continue
        text = open(p, encoding="utf-8").read()
        missing = [k for k in kws if k not in text]
        if missing:
            print(f"   △ {name}：{fname} 存在，但缺关键词 {missing}（人工补查）")
        else:
            ok += 1
            print(f"   ✓ {name}：{fname}")
    for split in ("train", "val", "test"):
        p = os.path.join(DATA, f"day06_{split}.jsonl")
        n = sum(1 for _ in open(p, encoding="utf-8")) if os.path.exists(p) else 0
        if n:
            ok += 1
            print(f"   ✓ 数据集 {split}：{n} 条")
        else:
            print(f"   ✗ 数据集 {split}：缺 day06_{split}.jsonl")
    return ok

# ============ ② 数据集统计（卡片的数字来源） ============
def load_stats():
    stats = {}
    for split in ("train", "val", "test"):
        p = os.path.join(DATA, f"day06_{split}.jsonl")
        if not os.path.exists(p):
            continue
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        stats[split] = {
            "n": len(rows),
            "cls": dict(Counter(r["meta"]["label"] for r in rows)),
            "bd": sum(1 for r in rows if r["meta"]["difficulty"] == "boundary"),
        }
    return stats

# ============ ③ 数据集卡片草稿（datasheet 七要素） ============
def write_card(stats):
    if not stats:
        print("② [跳过] 无数据集，无法生成卡片——先跑 D6")
        return
    total = sum(v["n"] for v in stats.values())
    L = [f"# DATASET CARD · intent-sft-v1.1-seed27（{datetime.now():%Y-%m-%d}）\n",
         "## ① 名称与版本\n", "intent-sft-v1.1-seed27（版本 = 标注规范版本 + 划分种子）\n",
         "## ② 任务与来源\n",
         "- 任务：电商客服消息意图分类（SFT 指令微调）",
         "- 来源：模拟客服消息池（脚本生成，seed 24）+ 单人标注（Day24）",
         "- 标注规范：v1.1（体系 v1 → 边界仲裁后修订）\n",
         "## ③ 规模与结构\n"]
    for k, v in stats.items():
        L.append(f"- {k}：{v['n']} 条｜类别 {v['cls']}｜边界例 {v['bd']}")
    L.append(f"- 总计：{total} 条｜结构：alpaca 三件套 + meta（label/difficulty/source_id/schema_ver）")
    L.append("- instruction 变体：3 版（简洁/详细/带判例），随机分配\n")
    L.append("## ④ 生产过程（可追溯链路）\n")
    L.append("消息池(seed24) → 标注(day03_labeled.csv) → 自一致率+仲裁(day04 报告) → "
             "五级过滤漏斗(day05 报告) → 分层划分 seed27 + 泄漏检查(day06 报告)\n")
    L.append("## ⑤ 已知局限（与质检报告④同步，人工核对后定稿）\n")
    L.append("- [ ] 总样本 <200，仅支持小规模验证，不能外推生产结论")
    L.append("- [ ] 单一标注员，无互标注 Kappa（W5 陌生人试标后补）")
    L.append("- [ ] 消息池为模拟语料，与真实业务分布有偏差")
    L.append("- [ ] '其他'类占比偏高，长尾代表性有限\n")
    L.append("## ⑥ 使用许可\n\n仅限演示与学习用途，不用于生产训练。\n")
    L.append("## ⑦ 维护计划\n")
    L.append("- 规范升级为澄清型 → 数据版本号小版本 +1，无需重标")
    L.append("- 规范升级为结构型（改类别/优先级） → 受影响类别对全部重标")
    L.append("- W5 陌生人试标完成互一致率后出 v1.2\n")
    L.append("> 复现命令：day03_label_tool.py --auto → day04_consistency.py --auto → "
             "day05_sft_build.py → day06_dataset_split.py")
    open(CARD, "w", encoding="utf-8").write("\n".join(L))
    print(f"② 数据集卡片草稿已生成：{CARD}（⑤局限和⑥许可人工核对后定稿）")

# ============ ④ W4 出口自测（7 题逐题口答，脚本给判定标准） ============
EXIT_QA = [
    ("标注体系三原则 + 各举一个违反后果", "互斥/穷尽/可仲裁"),
    ("规范七部分结构 + 为什么④是灵魂", "任务/类别/仲裁/边界/流程/质量/变更"),
    ("自一致率红线依据 + 两种'高一致但失效'场景", "95%；锚定/间隔太短/全简单例"),
    ("SFT 三件套 + instruction 变体防什么", "instruction/input/output；措辞过拟合"),
    ("五级过滤漏斗 + 为什么每级记账", "跳过/无效/去重/长度/分布；数字可信"),
    ("划分四条纪律 + 违反后果", "分层/防泄漏/可复现/边界配额"),
    ("3 分钟讲数据生产链路（计时）", "体系→规范→标注→一致性→样本→划分→质检"),
]

def safe_input(text):
    """非交互环境（管道/CI）优雅退出，不抛 EOFError——W1-W3 脚本的同一保护壳"""
    try:
        return input(text)
    except EOFError:
        print("\n[非交互环境] 跳过交互环节")
        return "s"

def exit_test(scored):
    print("\n③ W4 出口自测（逐题口答后按 y 计分）：")
    results = []
    for i, (q, key) in enumerate(EXIT_QA, 1):
        print(f"   Q{i}：{q}")
        print(f"       要点提示（答完再看）：{key}")
        ok = safe_input("       答上了？(y/n): ").strip().lower() == "y"
        results.append(ok)
        if ok:
            scored += 1
    verdict = "✓ 通过，进 W5" if scored >= 6 else "✗ 未通过：未过关题目写补课动作，W5 首日先清卡点"
    print(f"\n④ 出口判定：{scored}/7 → {verdict}")
    LOG = os.path.join(DATA, "day28_self_test_log.md")     # 自测记录落盘（W3 D7 同款纪律）
    L = [f"# W4 出口自测记录（{datetime.now():%Y-%m-%d %H:%M}）\n",
         f"- 得分：{scored}/7 → {verdict}",
         f"- 判定口径：答对 ≥6 题视为通过\n", "## 逐题结果\n"]
    for i, ((q, _), passed) in enumerate(zip(EXIT_QA, results), 1):
        L.append(f"- Q{i} {'过' if passed else '未过'}：{q}")
        if not passed:
            L.append(f"  - 补课：重看对应日学习内容 + 重跑脚本，写一句卡点")
    open(LOG, "w", encoding="utf-8").write("\n".join(L))
    print(f"   自测记录已落盘：{LOG}")
    return scored

# ============ ⑤ M1 总判定 ============
def final_verdict(ok, scored, skipped=False):
    need = len(CHECKS) + 3                       # 5 份文档 + 3 个数据分片
    print("\n" + "=" * 46)
    print(f"M1 里程碑判定：交付物 {ok}/{need}｜出口自测 {'未做' if skipped else f'{scored}/7'}")
    if skipped:
        print("结论：交付物体检完成，自测未做 → 待判定（做完 7 题后回到《Day-07-验证》第四部分勾选）")
    elif ok == need and scored >= 6:
        print("结论：M1 达成 ✓ —— 三件归档 commit 后进 W5")
    else:
        print("结论：M1 未达成 —— 先补交付物/清卡点，宁可 W5 压缩 1 天")
    print("=" * 46)
    print("\n⑤ 人工下一步：")
    print("   a. DATASET_CARD.md ⑤局限/⑥许可人工核对定稿")
    print("   b. 全部交付物 commit + push（作品集素材 +1）")
    print("   c. 30 问卡片补 5 问（标注与数据质量主题）")
    print("   d. W5 预习：两人一致率 95% vs 85%，谁更可信？为什么不能只看百分比？")

if __name__ == "__main__":
    _ok = audit_deliverables()
    write_card(load_stats())
    if safe_input("\n开始出口自测？（回车开始 / 输入 s 跳过自测只做体检）: ").strip().lower() == "s":
        print("\n③ [跳过] 出口自测——M1 判定以交付物体检为准，自测请择时补做")
        _scored = -1
    else:
        _scored = exit_test(0)
    final_verdict(_ok, max(_scored, 0), skipped=_scored < 0)
