# -*- coding: utf-8 -*-
"""Day 24 · 标注实操：命令行标注工具（断点续标 + 计时 + 规范问题日志）
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day03_label_tool.py          # 交互模式（真实标注，推荐）
    /Users/zcb/miniconda3/envs/aiml/bin/python day03_label_tool.py --auto   # 自动模式（回归验证用）
产出：data/day03_labeled.csv（标注结果）+ data/day03_session_log.md（统计 + 问题日志）
核心思想：标注是把规范暴露给真实数据的过程——卡壳点 = 规范盲区 = 明天修订规范的原料。
"""

# ============ 导入区 ============
import csv                                    # 标注结果用 CSV 存（断点续标要读回）
import os
import random
import re
import sys
import time
from collections import Counter               # 类别分布 / 耗时统计
from datetime import datetime
from itertools import product                 # 模板 × 填充 组合枚举（保证消息唯一）

random.seed(24)                               # 固定种子：消息池每次运行完全一致（可复现纪律）

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
CSV_PATH = os.path.join(DATA, "day03_labeled.csv")
LOG_PATH = os.path.join(DATA, "day03_session_log.md")

LABELS = ["投诉", "咨询", "催发货", "发票", "售后退换", "其他"]   # 与 D1 体系同源
INVALID = "无效：不入集"                       # D2 规范④：场景外消息不入集，单列不算"其他"

# ============ ① 消息池：70 条普通例 + 18 条边界例 + 6 条噪声 + 6 条手滑重发 = 100 ============
FILL = {"p": ["质量", "物流", "客服态度", "包装"],
        "a": ["必须给个说法", "气死我了", "要投诉到平台"],
        "q": ["退款", "发票", "换货", "会员"],
        "d": ["三天", "五天了", "一周"],
        "a2": ["客服也不理人", "急用", "麻烦快点"],
        "b": ["我的单", "这单", "订单"],
        "f": ["抬头", "内容", "税号", "公司名"],
        "act": ["换货", "退货", "退款"],
        "item": ["衣服", "鞋子", "家电"]}

TEMPLATES = {                                 # 每类：模板列表 + 目标条数
    "投诉": (["{p}太差了，{a}", "{p}有问题一直没人管，{a}", "你们{p}怎么这样，{a}", "{p}体验极差，{a}"], 13),
    "咨询": (["{q}的流程是什么", "请问{q}怎么办理", "{q}需要准备什么材料", "想问下{q}的规则"], 13),
    "催发货": (["都{d}了还没发货，{a2}", "{b}什么时候能发货", "催一下{b}，等不了了", "麻烦尽快发{b}"], 13),
    "发票": (["发票{f}写错了能改吗", "怎么开{f}发票", "发票能开到{f}吗"], 12),
    "售后退换": (["尺码拍错了想{act}", "有质量问题想要{act}", "{item}不合适，想{act}"], 12),
    "其他": (["你们公司地址在哪", "App闪退打不开", "想聊聊加盟合作", "有招聘岗位吗",
             "快递员电话是多少", "有没有优惠券", "在吗"], 7),   # 其他类直接给句子（长尾/闲聊）
}

def gen_class(templates, n):
    """模板 × 填充组合枚举 + 去重，取前 n 条——避免随机组合导致的重复消息"""
    out = []
    for tpl in templates:
        keys = re.findall(r"\{(\w+)\}", tpl)          # 模板里出现的占位符（按出现顺序）
        for combo in product(*[FILL[k] for k in keys]):
            msg = tpl
            for k, v in zip(keys, combo):             # 逐个替换（同一占位符可能出现多次）
                msg = msg.replace("{" + k + "}", v, 1)
            if msg not in out:
                out.append(msg)
    return out[:n]

BOUNDARY = [                                  # D2 边界例（判定按规范 v1.1）
    ("再不发货我就去投诉你们", "催发货"), ("我要退货，你们客服态度还特别差", "售后退换"),
    ("东西烂了必须赔，不然我就退", "投诉"), ("问下怎么投诉快递员", "咨询"),
    ("不是说你们不好，就是问问能不能快点发", "催发货"), ("哈哈你们发货真是我见过最慢的", "催发货"),
    ("呵呵，行，你们继续这样", "投诉"), ("帮我写一首关于快递的诗", INVALID), ("今天天气怎么样", INVALID),
]
SUFFIX = ["，谢谢", "，急", "，麻烦告知", "，服了", "，我不说了", "，看着办", "，谢谢呀", "，适合出门吗", ""]

NOISE = ["啊啊啊啊啊啊", "123321123", "??????", "okokok", "666666", "哈哈哈"]   # 无语义 → 其他

def build_pool():
    """70 普通 + 18 边界 + 6 噪声 + 6 手滑重发 = 100 条（每条唯一，重发条靠归一化识别）"""
    pool = []
    for label, (tpls, n) in TEMPLATES.items():
        msgs = gen_class(tpls, n)
        assert len(msgs) == n, f"{label} 生成不足 {n} 条（填充词不够）"
        pool += [(m, label) for m in msgs]
    for i, (msg, ref) in enumerate(BOUNDARY):     # 基础 9 条 + 变体 9 条（换不同后缀，全部唯一）
        pool.append((msg, ref))
        pool.append((msg + SUFFIX[i], ref))
    pool += [(j, None) for j in NOISE]            # 噪声：参考判定 None → "其他"
    dup = random.sample(pool, 6)                  # 手滑重发：真人事后补标点/空格（近重复）
    pool += [(m + random.choice(["。", " ", "，"]), ref) for m, ref in dup]
    random.shuffle(pool)                          # 打乱：防按类分块标注（记忆效应污染计时）
    return pool

# ============ ② 断点续标：读已完成的标注 ============
def load_done():
    """已有 CSV → {id: 标签}。中途退出不丢进度是工具的底线功能。"""
    if not os.path.exists(CSV_PATH):
        return {}
    with open(CSV_PATH, encoding="utf-8") as f:
        return {int(r["id"]): r["label"] for r in csv.DictReader(f)}

# ============ ③ 两种标注员 ============
def auto_annotate(msg, ref):
    """带噪声的规则标注员（--auto 模式）：模拟真人会犯的错，供回归验证。"""
    if ref == INVALID:                        # 场景外 → 无效不入集（D2 规范④）
        return INVALID
    if ref is None:                           # 无语义噪声 → 归"其他"
        return "其他"
    if "投诉" in msg and "怎么" in msg:       # 规则员典型错：见"投诉"就判投诉（实为咨询）
        return "投诉"
    # 8% 概率随机错标，且只在 5 个业务类之间摇摆（真人很少把有意图的消息硬塞进兜底类"其他"）
    return ref if random.random() > 0.08 else random.choice(LABELS[:5])

def human_annotate(idx, total, msg):
    """交互标注：返回 (标签 / INVALID / None跳过 / EXIT, 备注)"""
    print(f"\n[{idx+1}/{total}] 「{msg}」")
    for i, lb in enumerate(LABELS, 1):
        print(f"  {i}. {lb}")
    print(f"  i. {INVALID}（场景外/与业务无关）")
    print("  0. 跳过（拿不准）  p. 记规范问题  s. 保存退出")
    while True:
        c = input("  选择: ").strip().lower()
        if c == "i":
            return INVALID, "场景外"
        if c in [str(i) for i in range(len(LABELS) + 1)]:
            note = ""
            if c == "0":
                note = input("  跳过原因（卡在哪里）: ").strip()
            return (None if c == "0" else LABELS[int(c) - 1]), note
        if c == "p":
            issue = input("  规范哪部分没说清？写一句: ").strip()
            if issue:
                ISSUES.append((msg, issue))
            print("  ✓ 已记录问题日志")
        elif c == "s":
            return "EXIT", ""
        else:
            print("  无效输入，重选")

ISSUES = []                                   # 规范问题日志：规范哪部分没说清（模块级，交互中累积）

# ============ ④ 主流程：标注 + 计时 + 落盘 ============
def main():
    pool = build_pool()
    done = load_done()
    auto = "--auto" in sys.argv
    rows = []                                 # (id, 消息, 标签, 耗时s, 备注)
    print(f"① 消息池 {len(pool)} 条｜已完成 {len(done)} 条（断点续标）｜模式：{'自动' if auto else '交互'}")
    t0 = time.time()
    for idx, (msg, ref) in enumerate(pool):
        if idx in done:                       # 已标的跳过
            continue
        if auto:
            label, note, cost = auto_annotate(msg, ref), "", round(random.uniform(8, 60), 1)
        else:
            st = time.time()
            label, note = human_annotate(idx, len(pool), msg)
            if label == "EXIT":
                break
            cost = round(time.time() - st, 1)
            if cost > 45:                     # 卡壳探测器：远超平均耗时的条目
                ISSUES.append((msg, f"[自动] 标注耗时 {cost}s > 45s，疑似边界卡壳"))
        rows.append((idx, msg, label or "", cost, note))
    if rows:
        new_file = not os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["id", "message", "label", "seconds", "note"])
            w.writerows(rows)
    elapsed = round(time.time() - t0)
    labeled = [r for r in rows if r[2] and r[2] != INVALID]   # 有效标注（无效不算完成）
    invalid = [r for r in rows if r[2] == INVALID]
    print(f"\n② 本次新标 {len(rows)} 条｜有效 {len(labeled)}｜无效 {len(invalid)}｜用时 {elapsed}s")
    return pool, rows, labeled, invalid, elapsed

def write_log(pool, rows, labeled, invalid, elapsed):
    """标注 session 报告：总账 + 分布 + 卡壳清单 + 问题日志"""
    cnt = Counter(r[2] for r in labeled)
    costs = sorted(r[3] for r in rows if r[3] > 0)
    p90 = costs[int(len(costs) * 0.9)] if costs else 0
    slow = sorted((r for r in rows if r[3] > 45), key=lambda r: -r[3])[:5]
    other_ratio = cnt["其他"] / max(len(labeled), 1)
    L = [f"# 标注 Session 报告（Day24，{datetime.now():%Y-%m-%d %H:%M}）\n",
         f"- 新标 {len(rows)} 条｜有效 {len(labeled)}｜无效不入集 {len(invalid)}｜用时 {elapsed}s",
         f"- 平均 {sum(costs)/max(len(costs),1):.1f}s/条｜P90 {p90}s\n",
         f"- 类别分布：{dict(cnt)}",
         f"- '其他'占比 {other_ratio:.1%}（红线 15% → {'✓ 通过' if other_ratio <= .15 else '✗ 需复查体系'}）\n",
         "\n## 慢条目 TOP5（>45s，边界信号）\n"]
    for r in slow:
        L.append(f"- 「{r[1]}」 {r[3]}s")
    L.append("\n## 规范问题日志（D4 修订规范的原料）\n")
    for i, (msg, issue) in enumerate(ISSUES, 1):
        L.append(f"{i}. 「{msg}」→ {issue}")
    if not ISSUES:
        L.append("（无——--auto 模式不产生问题日志；交互模式下为空说明规范可执行性很好）")
    open(LOG_PATH, "w", encoding="utf-8").write("\n".join(L))
    print(f"③ Session 报告已导出：{LOG_PATH}")
    print("\n④ 人工下一步（不可跳过）：")
    print("   a. 通读问题日志，给每条写'对应规范哪部分'")
    print("   b. 跳过条目补初步判定建议（明天仲裁时用）")
    print("   c. 记住你最犹豫的 3 条消息——明天重标它们")

if __name__ == "__main__":
    _pool, _rows, _labeled, _invalid, _elapsed = main()
    write_log(_pool, _rows, _labeled, _invalid, _elapsed)
