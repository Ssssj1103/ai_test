# -*- coding: utf-8 -*-
"""Day 22 · 标注体系设计：意图分类体系 v1 + 规则 baseline 标注器
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day01_label_schema.py
核心思想：规则 baseline 不是来分类的，是来当"Dummy 标注员"暴露体系漏洞的。
产出：data/day01_label_schema_report.md（体系 + baseline 错误分布）
"""

# ============ 导入区 ============
import random                                 # 随机种子固定保证可复现
import re                                     # 关键词匹配
from collections import Counter               # 错误分布统计

random.seed(42)                               # 固定种子：每次运行生成的消息一致（可复现纪律）

# ============ ① 标注体系 v1：类别 = 判据 + 正反例 + 优先级 ============
SCHEMA = {
    "投诉":   {"judgement": "表达不满且指向具体问题，期望处理（赔偿/道歉/处理承诺）",
               "pos": "质量太差了，必须给我个说法", "neg": "请问退货流程是什么"},
    "咨询":   {"judgement": "询问信息或流程，无不满情绪、无处理诉求",
               "pos": "这个支持七天无理由吗", "neg": "你们就是骗子，我要退货！"},
    "催发货": {"judgement": "已下单未发货，催促进度（无投诉语义时不判投诉）",
               "pos": "三天了还没发货，麻烦尽快", "neg": "货已经到了，就是有点慢"},
    "发票":   {"judgement": "与发票开具/修改相关",
               "pos": "发票抬头写错了能改吗", "neg": "发票丢了我很生气"},
    "售后退换": {"judgement": "已收货后的退/换/修诉求",
               "pos": "尺码拍错了想换个M码", "neg": "还没收到货，想取消订单"},
    "其他":   {"judgement": "以上都不适用（占比红线 15%，超标=体系要重拆）",
               "pos": "你们公司地址在哪", "neg": "我要投诉快递太慢"},
}
PRIORITY = ["投诉", "催发货", "售后退换", "发票", "咨询"]   # 仲裁优先级：可归多类时取最左

# ============ ② 生成 100 条带噪声的模拟消息（每条带真实标签） ============
PATTERNS = {                                  # 每类给若干模板（含噪声变体）
    "投诉": ["{p}太差了{angry}，必须给个说法", "气死我了，{p}有问题一直没人管{angry}"],
    "咨询": ["{p}的流程是什么", "请问{p}怎么办理"],
    "催发货": ["都三天了还没发货{angry}，快点", "什么时候能发货，等不了了"],
    "发票": ["发票{obj}写错了能改吗", "怎么开{obj}发票"],
    "售后退换": ["尺码拍错了想{act}", "有质量问题想要{act}"],
    "其他": ["你们公司地址在哪", "App闪退怎么回事"],
}
FILL = {"p": ["质量", "物流", "客服态度", "商品包装"], "angry": ["", "！！", "，客服也不理人"],
        "obj": ["抬头", "内容"], "act": ["换货", "退货"]}
REALITY = []                                  # (消息, 真实标签)
for label, tpls in PATTERNS.items():          # 每类生成 ~16 条
    for i in range(16):
        tpl = tpls[i % len(tpls)]             # 轮换模板
        msg = tpl
        for k, vals in FILL.items():          # 填充占位符
            if "{" + k + "}" in msg:
                msg = msg.replace("{" + k + "}", random.choice(vals))
        REALITY.append((msg, label))
random.shuffle(REALITY)                       # 打乱顺序（防按类分块的记忆效应）
print(f"① 模拟消息集：{len(REALITY)} 条，分布 {dict(Counter(l for _, l in REALITY))}")

# ============ ③ 规则 baseline 标注器 ============
RULES = [                                     # (类别, 关键词组)。顺序即仲裁优先级
    ("投诉", ["太差", "说法", "气死", "骗子", "投诉", "没人管"]),
    ("发票", ["发票"]),
    ("催发货", ["发货", "没发货", "什么时候发"]),
    ("售后退换", ["换", "退货", "退了", "修"]),
    ("咨询", ["什么", "怎么", "请问", "吗"]),
]

def rule_label(msg):
    """按优先级命中第一个含关键词的类别；全不中→其他"""
    for label, kws in RULES:                  # 按优先级顺序扫描
        if any(kw in msg for kw in kws):      # 任一关键词命中
            return label
    return "其他"                             # 穷尽原则：必须有兜底

# ============ ④ 评估：baseline 的错误 = 体系的漏洞清单 ============
correct = 0
errors = Counter()                            # (真实, 判成) 错误对计数
others = 0
for msg, gold in REALITY:                     # 逐条评估
    pred = rule_label(msg)
    if pred == gold:
        correct += 1
    else:
        errors[(gold, pred)] += 1             # 记录错误对
    if pred == "其他":
        others += 1
acc = correct / len(REALITY)                  # 规则法准确率（预期不高，无所谓）
print(f"\n② 规则 baseline：准确率 {correct}/{len(REALITY)} = {acc:.0%}（ Dummy 标注员，不求准）")
print(f"   '其他'占比 {others/len(REALITY):.0%}（红线 15%）")
print("   错误最集中的类别对（每一条都是体系边界规则的补全线索）：")
for (gold, pred), n in errors.most_common(5):  # TOP5 错误对
    print(f"     {gold} → 被判成 {pred}：{n} 条")

# ============ ⑤ 导出体系报告 ============
lines = ["# 标注体系 v1 报告（Day22）\n", "## 类别定义\n"]
for label, info in SCHEMA.items():            # 体系入文档
    lines.append(f"- **{label}**：{info['judgement']}｜正例：{info['pos']}｜反例：{info['neg']}")
lines.append(f"\n## 仲裁优先级\n{' > '.join(PRIORITY)}")
lines.append(f"\n## Baseline 体检\n- 准确率 {acc:.0%}｜其他占比 {others/len(REALITY):.0%}\n\n## TOP 错误对（边界规则补全清单）\n")
for (gold, pred), n in errors.most_common(8):
    lines.append(f"- {gold} → {pred}：{n} 条")
import os
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
out = os.path.join(root, "data", "day01_label_schema_report.md")
open(out, "w", encoding="utf-8").write("\n".join(lines))
print(f"\n③ 报告已导出：{out}")
