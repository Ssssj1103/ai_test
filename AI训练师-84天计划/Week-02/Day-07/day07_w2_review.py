# -*- coding: utf-8 -*-
"""Day 14 · W2 周自测抽查器：模拟面试官随机抽问
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day07_w2_review.py [抽几题，默认3]
用法：跑一次抽 N 问 → 先自己口述 → 回车显示参考要点 → 自评 过/补。
产出：data/day14_self_test_log.md（自测记录，落盘追踪弱项）
"""

# ============ 导入区 ============
import random                                 # 随机抽题
import sys                                    # 命令行参数
from pathlib import Path                      # 路径

DATA = Path(__file__).resolve().parent.parent.parent / "data"   # 产物目录

# ============ ① 题库：7 大出口标准 × 参考要点（要点来自本周笔记，不是书） ============
BANK = [
    ("Attention 六步流程（含形状）",
     "X(3,4)→Q/K/V=X·W(3,4)→scores=QK^T(3,3)→/√dk→softmax按行→A·V(3,4)。"
     "我的实验：3词×4维手算，掩码后第1行只剩对角线。"),
    ("为什么除以 √dk？掩码加在哪？",
     "dk 大→点积方差≈dk→softmax 赢家通吃→梯度消失；除 √dk 拉回方差≈1。"
     "掩码在 softmax 之前加（-inf→权重0，行内仍归一化）。实验：×8 分数后去重分布 0.98 vs 0.02。"),
    ("三种架构一句话区分",
     "Encoder-only(BERT)双向理解；Decoder-only(GPT系)因果生成——主流LLM全是它；"
     "Enc-Dec(T5)翻译摘要。LLM 选 Decoder-only：训练目标统一+理解生成合一+KV cache 工程友好。"),
    ("BPE 机制 + 换模型为何重算 token",
     "字符起步→反复合并最高频相邻对→高频词短、生僻词碎。"
     "我的实验：'low'3轮合并成1token，'slowest'拆3块。换模型=换词表=token统计/计费/窗口全变。"),
    ("训练四阶段数据形态",
     "预训练=纯文本流万亿token；SFT=指令对1万-100万；对齐=chosen/rejected对比对；"
     "持续迭代=BadCase定向补强。训练师从第②阶段主导。"),
    ("SFT 三格式区别",
     "Alpaca=instruction/input/output 单轮；ShareGPT=conversations多轮；"
     "messages=role序列(API标准)。实证：多轮样本转Alpaca丢中间轮次（day04脚本）。"),
    ("5类幻觉诱导用例+判定纪律",
     "编造实体/知识截止/过度自信数字/伪造引用/超纲任务。"
     "纪律：PASS/FAIL/PARTIAL 在跑之前写死，防'看结果找理由'。幻觉率=FAIL/总数。"),
    ("temperature vs top_p",
     "T 改变分布形状(0尖/1.5平)，top_p 截断候选集。评测裁判任务 T=0~0.2+top_p=1，"
     "参数必须显式记录。网格实验：T=0 行去重=1，T=1.5 行随 p 发散。"),
]

# ============ ② 抽题测试流程 ============
def safe_input(prompt_text):
    """input 的保护壳：非交互环境（无标准输入）读到 EOF 时优雅退出而不是崩溃"""
    try:
        return input(prompt_text)
    except EOFError:                          # 管道/无终端场景
        print("\n[非交互环境，测试终止]")
        sys.exit(0)                           # 正常退出码，回归测试不误报

def quiz(n):
    """抽 n 题模拟面试：口述→回车→显示要点→记录自评"""
    picks = random.sample(BANK, k=min(n, len(BANK)))       # 不重复抽样
    log = [f"# W2 自测记录（Day14）\n", f"抽取 {len(picks)} 题\n"]
    passed = 0                                 # 计数通过
    for i, (q, key) in enumerate(picks, 1):    # 逐题
        print(f"\n第 {i}/{len(picks)} 题：{q}")
        safe_input("  （先口述，说完回车看参考要点…）")       # 强制先答后看，防作弊
        print(f"  参考要点：{key}")
        mark = safe_input("  自评 [过/补]：").strip()        # 自评落盘
        passed += mark.startswith("过")
        log.append(f"{i}. {q} —— {mark}")
    log.append(f"\n结果：{passed}/{len(picks)} 过")
    out = DATA / "day14_self_test_log.md"      # 记录落盘：弱项追踪
    out.write_text("\n".join(log), encoding="utf-8")
    verdict = ("出口通过 ✓" if passed == len(picks) else
               "需缓冲补课（1-2 题未过）" if passed >= len(picks) - 2 else
               "W2 预警：重学 D1-D3")
    print(f"\n结果：{passed}/{len(picks)} —— {verdict}")
    print(f"记录已存：{out}")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]   # 过滤 --mock 之类的开关参数
    n = int(args[0]) if args else 3                       # 默认抽 3 题
    quiz(n)
