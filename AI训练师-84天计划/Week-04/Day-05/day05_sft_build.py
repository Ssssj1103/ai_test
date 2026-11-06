# -*- coding: utf-8 -*-
"""Day 26 · SFT 样本构造：标注结果 → 三件套样本 + 五级过滤漏斗
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day05_sft_build.py
产出：data/day05_sft_samples.jsonl + data/day05_sft_build_report.md（漏斗账本）
核心思想：instruction 把"数据"变成"任务"；过滤漏斗每一步都要有账——数字可信 = 账目可信。
"""

# ============ 导入区 ============
import csv
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime

random.seed(26)                               # 指令变体分配可复现
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
D3_CSV = os.path.join(DATA, "day03_labeled.csv")
OUT_JSONL = os.path.join(DATA, "day05_sft_samples.jsonl")
OUT_MD = os.path.join(DATA, "day05_sft_build_report.md")

# ============ ① 读标注结果（缺失时兜底：重放 D3 的 auto 标注，保证可独立回归） ============
def load_labels():
    if os.path.exists(D3_CSV):
        with open(D3_CSV, encoding="utf-8") as f:
            rows = [(int(r["id"]), r["message"], r["label"], float(r["seconds"] or 0))
                    for r in csv.DictReader(f)]
        print(f"① 读入标注结果 {len(rows)} 条")
        return rows
    print("① [警告] 无 day03_labeled.csv → 重放 D3 auto 标注兜底（正式练习请先完成 D3/D4）")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Day-03"))
    import day03_label_tool as d3             # 复用 D3 的消息池与 auto 标注员
    random.seed(24)
    pool = d3.build_pool()
    rows = [(i, m, d3.auto_annotate(m, rf), round(random.uniform(8, 60), 1))
            for i, (m, rf) in enumerate(pool)]
    with open(D3_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "message", "label", "seconds", "note"])
        w.writerows(rows)
    print(f"   已生成兜底标注 {len(rows)} 条，继续")
    return rows

# ============ ② instruction 变体池（同一任务的多种"问法"，防措辞过拟合） ============
INSTRUCTIONS = [
    "简洁版：将用户消息分类为以下类别之一：投诉/咨询/催发货/发票/售后退换/其他。只输出类别名。",
    "详细版：你是电商客服质检系统。判断用户消息的意图分类任务，可选：投诉（不满+具体问题+处理诉求）、"
    "咨询（询问流程信息）、催发货（已下单未发货催进度）、发票（开票/改票）、售后退换（收货后退换修）、"
    "其他（以上都不是）。注意：有投诉词但核心诉求是催进度时判催发货。只输出类别名。",
    "带判例版：把消息分类为 投诉/咨询/催发货/发票/售后退换/其他 之一，只输出类别名。\n"
    "判例：「再不发货就投诉你们」→催发货；「怎么投诉快递员」→咨询；「尺码拍错想换」→售后退换。",
]

# ============ ③ 五级过滤漏斗（每级都有账） ============
def funnel(rows):
    ledger = [("0 原始", 0, "—")]
    # ① 跳过条：label 为空（D4 的 pending 不许混入训练集）
    step1 = [r for r in rows if r[2]]
    ledger.append(("① 剔跳过条", len(rows) - len(step1), "label 为空（pending 未仲裁）"))
    # ② 无效条：标注为"无效：不入集"
    step2 = [r for r in step1 if not r[2].startswith("无效")]
    ledger.append(("② 剔无效条", len(step1) - len(step2), "场景外消息不入集"))
    # ③ 去重：完全重复 + 归一化后近重复
    seen, dedup = set(), []
    for r in step2:
        key = re.sub(r"[\s，。！？!?.,~～]", "", r[1])       # 归一化：去空白和常见标点
        if r[1] in seen or key in seen:
            continue
        seen.add(r[1]); seen.add(key)
        dedup.append(r)
    ledger.append(("③ 去重(含近重复)", len(step2) - len(dedup), "归一化后仍相同"))
    # ④ 长度护栏：<2 或 >200 → 可疑清单（人工过目后决定去留，不直接删）
    suspects = [r for r in dedup if len(r[1]) < 2 or len(r[1]) > 200]
    step4 = [r for r in dedup if r not in suspects]
    ledger.append(("④ 长度护栏", len(suspects), f"{len(suspects)} 条入可疑清单（人工过目）"))
    # ⑤ 分布体检："其他"红线复查
    cnt = Counter(r[2] for r in step4)
    other_ratio = cnt["其他"] / max(len(step4), 1)
    ledger.append(("⑤ 分布体检", 0, f"'其他'占比 {other_ratio:.1%}（红线 15% → "
                   f"{'✓ 通过' if other_ratio <= .15 else '✗ 体系要重拆'}）"))
    return step4, suspects, ledger, other_ratio

# ============ ④ 组装 SFT 样本（三件套 + 元数据） ============
RULES = [                                     # 与 D1 的规则 baseline 同源：规则判错 = 模型的难例
    ("投诉", ["太差", "说法", "气死", "骗子", "投诉", "没人管", "态度"]),
    ("发票", ["发票"]),
    ("催发货", ["发货", "什么时候发", "尽快发", "催一下"]),
    ("售后退换", ["换", "退货", "退了", "修", "退款"]),
    ("咨询", ["什么", "怎么", "请问", "吗"]),
]

def rule_label(msg):
    """D1 的规则标注器：命中第一个含关键词的类别，全不中 → 其他"""
    for lb, kws in RULES:
        if any(k in msg for k in kws):
            return lb
    return "其他"

def build_samples(rows):
    samples = []
    for rid, msg, label, sec in rows:
        # 难度标签语义 = "模型视角的难例"：规则 baseline 判错 → boundary（耗时只作参考，不作为判据）
        difficulty = "boundary" if rule_label(msg) != label else "normal"
        samples.append({
            "instruction": random.choice(INSTRUCTIONS),    # 变体随机分配
            "input": msg,
            "output": label,
            "meta": {"label": label, "difficulty": difficulty,
                     "source_id": rid, "schema_ver": "v1.1"},
        })
    return samples

# ============ ⑤ 落盘 + 账本报告 ============
def main():
    rows = load_labels()
    kept, suspects, ledger, other_ratio = funnel(rows)
    samples = build_samples(kept)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    cnt = Counter(s["meta"]["label"] for s in samples)
    n_bd = sum(1 for s in samples if s["meta"]["difficulty"] == "boundary")
    print(f"② 漏斗：{len(rows)} → {len(samples)} 条有效样本（明细见报告账本）")
    print(f"③ 类别分布：{dict(cnt)}｜边界例标记 {n_bd} 条｜'其他'占比 {other_ratio:.1%}")
    L = [f"# SFT 样本构建报告（Day26，{datetime.now():%Y-%m-%d %H:%M}）\n", "## 过滤漏斗账本\n",
         "| 步骤 | 剔除数 | 说明 |", "| --- | --- | --- |"]
    for name, n, why in ledger:
        L.append(f"| {name} | {n} | {why} |")
    L.append(f"\n**最终样本：{len(samples)} 条**｜类别分布：{dict(cnt)}｜边界例：{n_bd}")
    L.append("\n## instruction 变体分布\n")
    for i, ins in enumerate(INSTRUCTIONS, 1):
        n = sum(1 for s in samples if s["instruction"] == ins)   # 值比较，不用 is（字符串对象身份不可靠）
        L.append(f"- 变体{i}（{ins[:12]}…）：{n} 条")
    L.append("\n## 可疑清单（长度护栏拦截，人工过目后决定去留）\n")
    for rid, msg, *_ in suspects:
        L.append(f"- [{rid}] 「{msg[:50]}」")
    if not suspects:
        L.append("-（无）")
    L.append("\n## 样本示例（第 1 条）\n```json\n"
             + json.dumps(samples[0], ensure_ascii=False, indent=2) + "\n```")
    L.append("\n> 溯源：每条样本 meta.source_id 可回溯 day03_labeled.csv 原始行；"
             "schema_ver 对应《标注规范》版本，保证数据-规范可对齐。")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L))
    print(f"④ 构建报告已导出：{OUT_MD}")
    print("\n⑤ 人工下一步（不可跳过）：")
    print("   a. 逐级核对漏斗账本数字（100 → 最终 N 能对上）")
    print("   b. 可疑清单逐条决定去留，处置理由写进报告")
    print("   c. 自己加第 4 版 instruction 变体后重跑，对比分布")

if __name__ == "__main__":
    main()
