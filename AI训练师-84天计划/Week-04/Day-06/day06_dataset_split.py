# -*- coding: utf-8 -*-
"""Day 27 · 数据集组装与质检：分层划分 train/val/test + 泄漏检查 + 质检报告骨架
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day06_dataset_split.py
产出：data/day06_train.jsonl / day06_val.jsonl / day06_test.jsonl + data/day06_qc_report.md
核心思想：划分方式决定评测结论可信度——分层/防泄漏/可复现/边界例配额，四条纪律缺一不可。
"""

# ============ 导入区 ============
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime

random.seed(27)                               # 划分种子必须固定并记录——可复现纪律
SEED = 27
RATIO = (0.8, 0.1, 0.1)                       # train / val / test
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
SRC = os.path.join(DATA, "day05_sft_samples.jsonl")
OUTS = {k: os.path.join(DATA, f"day06_{k}.jsonl") for k in ("train", "val", "test")}
REPORT = os.path.join(DATA, "day06_qc_report.md")

def norm(msg):                                # 归一化规则与 D5 保持一致（泄漏检查用）
    return re.sub(r"[\s，。！？!?.,~～]", "", msg)

# ============ ① 读 D5 样本（缺失时兜底重放 D5） ============
def load_samples():
    if os.path.exists(SRC):
        with open(SRC, encoding="utf-8") as f:
            rows = [json.loads(l) for l in f if l.strip()]
        print(f"① 读入 SFT 样本 {len(rows)} 条")
        return rows
    print("① [警告] 无 day05_sft_samples.jsonl → 重放 D5 兜底")
    d5 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Day-05", "day05_sft_build.py")
    subprocess.run([sys.executable, d5], check=True)
    with open(SRC, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

# ============ ② 二维分层划分：先按难度分层，层内按类别轮转（两个维度同时覆盖） ============
def round_robin_by_class(items, k):
    """层内按类别轮转抽 k 条——保证小类也有代表；返回 (抽中, 剩余)"""
    if k <= 0:
        return [], items
    by_cls = {}
    for s in items:
        by_cls.setdefault(s["meta"]["label"], []).append(s)
    for v in by_cls.values():
        random.shuffle(v)
    classes = sorted(by_cls)                             # sorted：遍历顺序稳定可复现
    picked, i = [], 0
    while len(picked) < k and any(by_cls[c] for c in classes):
        c = classes[i % len(classes)]
        if by_cls[c]:
            picked.append(by_cls[c].pop())
        i += 1
    rest = [s for c in classes for s in by_cls[c]]
    return picked, rest

def stratified_split(samples):
    """难度是第一分层维度（决定评测难度），类别是第二维度（层内轮转，保证每类有代表）"""
    bd = [s for s in samples if s["meta"]["difficulty"] == "boundary"]
    nm = [s for s in samples if s["meta"]["difficulty"] != "boundary"]
    random.shuffle(bd)
    random.shuffle(nm)
    n = len(samples)
    k_test = max(1, round(n * RATIO[2]))                 # test 总名额
    k_val = max(1, round(n * RATIO[1]))                  # val 总名额
    r = len(bd) / max(n, 1)                              # 全局难例占比
    k_test_bd = min(len(bd), max(1, round(k_test * r)))  # 难例至少 1 条进 test（评测要在难的地方测）
    k_val_bd = min(len(bd) - k_test_bd, max(1, round(k_val * r)))
    test_bd, bd_rest = round_robin_by_class(bd, k_test_bd)
    val_bd, bd_rest = round_robin_by_class(bd_rest, k_val_bd)
    test_nm, nm_rest = round_robin_by_class(nm, k_test - len(test_bd))
    val_nm, nm_rest = round_robin_by_class(nm_rest, k_val - len(val_bd))
    train = bd_rest + nm_rest                             # 余下全部进 train
    random.shuffle(train)
    val = val_bd + val_nm
    test = test_bd + test_nm
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test

# ============ ③ 四条纪律核对 ============
def audit(train, val, test):
    ok = {}
    # 纪律1 分层覆盖：每个 train 中的类别在 val/test 至少出现一次（"其他"在 val 允许例外）
    val_cls = {s["meta"]["label"] for s in val}
    test_cls = {s["meta"]["label"] for s in test}
    missing = [lb for lb in {s["meta"]["label"] for s in train}
               if (lb not in val_cls or lb not in test_cls)]
    ok["分层覆盖"] = (not missing, "全部类别有代表" if not missing else f"缺失类别: {missing} → 建议人工调整或补数据")
    # 纪律2 泄漏：归一化消息不得跨集合
    sets = {"train": {norm(s["input"]) for s in train},
            "val": {norm(s["input"]) for s in val},
            "test": {norm(s["input"]) for s in test}}
    leaks = (sets["train"] & sets["val"]) | (sets["train"] & sets["test"]) | (sets["val"] & sets["test"])
    ok["无泄漏"] = (not leaks, "通过" if not leaks else f"{len(leaks)} 条跨集合泄漏 → 处置：只保留 train 那份")
    # 纪律3 可复现：种子已固定（本脚本 SEED 常量）
    ok["可复现"] = (True, f"种子 {SEED}，脚本 day06_dataset_split.py")
    # 纪律4 边界例配额：val/test 难例占比与 train 的绝对差 ≤10 个百分点（小样本容差，判定口径写死）
    def bd_ratio(x):
        return sum(1 for s in x if s["meta"]["difficulty"] == "boundary") / max(len(x), 1)
    gaps = (abs(bd_ratio(val) - bd_ratio(train)), abs(bd_ratio(test) - bd_ratio(train)))
    ok["边界例配额"] = (max(gaps) <= 0.10,
                  f"train {bd_ratio(train):.0%} / val {bd_ratio(val):.0%} / test {bd_ratio(test):.0%}"
                  f"（最大差 {max(gaps)*100:.0f}pp，阈值 10pp）")
    return ok, leaks

# ============ ④ 落盘 + 质检报告骨架 ============
def write_parts(name, data):
    with open(OUTS[name], "w", encoding="utf-8") as f:
        for s in data:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

def main():
    samples = load_samples()
    print(f"② 分层划分（{RATIO[0]:.0%}/{RATIO[1]:.0%}/{RATIO[2]:.0%}）")
    train, val, test = stratified_split(samples)
    for name, part in {"train": train, "val": val, "test": test}.items():
        write_parts(name, part)
    ok, leaks = audit(train, val, test)
    print(f"③ 落盘：train {len(train)} / val {len(val)} / test {len(test)}")
    print("④ 四条纪律核对：")
    for k, (passed, detail) in ok.items():
        print(f"   {'✓' if passed else '✗'} {k}：{detail}")
    if leaks:                                            # 泄漏自动处置：val/test 删，只留 train
        val = [s for s in val if norm(s["input"]) not in leaks]
        test = [s for s in test if norm(s["input"]) not in leaks]
        write_parts("val", val); write_parts("test", test)
        print(f"   [处置] 泄漏条目已从 val/test 移除 → train {len(train)} / val {len(val)} / test {len(test)}")
    stats = {k: dict(Counter(s["meta"]["label"] for s in v)) for k, v in
             {"train": train, "val": val, "test": test}.items()}
    def bd(x):
        return sum(1 for s in x if s["meta"]["difficulty"] == "boundary")
    audit_line = "；".join(f"{k} {'✓' if p else '✗'}" for k, (p, _) in ok.items())
    L = [f"# SFT 数据集质检报告（Day27，{datetime.now():%Y-%m-%d %H:%M}）\n",
         "## ① 数据集概览\n",
         f"- 总样本：{len(train)+len(val)+len(test)}｜train/val/test = {len(train)}/{len(val)}/{len(test)}",
         "- schema 版本：v1.1｜instruction 变体：3 版",
         f"- 类别分布：train {stats['train']}｜val {stats['val']}｜test {stats['test']}",
         f"- 边界例（difficulty=boundary）：train {bd(train)} / val {bd(val)} / test {bd(test)}\n",
         "## ② 质量过程（引用上游报告）\n",
         "- 过滤漏斗：见 `day05_sft_build_report.md`（五级账本）",
         "- 一致性：见 `day04_consistency_report.md`（自一致率 + 分歧仲裁）",
         "- 标注规范：v1.1（Day23 成文 / Day25 修订）\n",
         "## ③ 划分方案\n",
         f"- 比例 80/10/10｜分层方式：按类别分堆堆内切分｜种子：{SEED}（可复现）",
         f"- 泄漏检查：{'无泄漏' if not leaks else f'{len(leaks)} 条泄漏，已从 val/test 移除'}",
         f"- 纪律核对：{audit_line}\n",
         "## ④ 已知局限（人工填写，≥4 条，诚信条款）\n",
         "- [ ] （示例）规模小：总样本 <200，仅支持小规模验证实验，不能外推生产结论",
         "- [ ] （示例）单一标注员：无互标注 Kappa，一致性证据仅自一致率",
         "- [ ] （示例）模拟数据：消息池为脚本生成的模拟客服语料，分布与真实业务有偏差",
         "- [ ] （示例）'其他'占比 ____%，接近/超过 15% 红线，长尾代表性有限\n",
         "## ⑤ 使用建议（人工填写）\n",
         "- [ ] 加载方式 / 引用版本（如 `intent-sft-v1.1-seed27`）/ 复现命令（day03→05→06 顺序）\n",
         "> 本报告为 M1 里程碑验收文件。④⑤ 必须人工完成后定稿——局限写得越具体，作品集越可信。"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(L))
    print(f"⑤ 质检报告骨架已导出（④⑤待人工完成）：{REPORT}")
    print("\n⑥ 人工下一步（不可跳过）：")
    print("   a. 完成《质检报告》④已知局限（≥4 条，如实写）和 ⑤使用建议")
    print("   b. 核对四条纪律的 ✓/✗，有 ✗ 的先处置再定稿")
    print("   c. 抽 3 条 test 样本手算检查：是否真的没在 train 里见过近亲")

if __name__ == "__main__":
    main()
