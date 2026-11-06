# -*- coding: utf-8 -*-
"""Day 21 · W3 周自测抽查器：7 大出口标准随机抽问
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day07_w3_review.py [抽几题，默认3]
产出：data/day21_self_test_log.md（自测记录落盘）
"""

# ============ 导入区 ============
import random                                 # 随机抽题
import sys                                    # 参数
from pathlib import Path                      # 路径

DATA = Path(__file__).resolve().parent.parent.parent / "data"

# ============ ① 题库：7 题 × 参考要点（全部来自本周实验数据） ============
BANK = [
    ("Prompt 五要素（R-T-C-F-E）",
     "角色/任务/约束/格式/示例。我的例子：意图分类器模板。"
     "关键数据：可解析率 0%→100%（n=5，before/after）。"),
    ("few-shot 机制与示例选择",
     "推理时用 Attention 模仿上下文示例（临时）；SFT 是参数化版本（永久）。"
     "两原则：代表性+边界性。数据：0/1/3-shot = 67%→83%→100%（n=6）；增量价值集中在边界难例。"),
    ("结构化输出四种失败与防御",
     "非JSON(正则抠块)/缺字段/值越界/类型错误 → schema 校验收集全部错误 → 错误回喂重试。"
     "验证手段：--inject 故障注入（第1轮非JSON、第2轮枚举越界、第3轮修复）。"),
    ("批处理工程三件套",
     "线程池并发（I/O 密集 GIL 释放）；重试只对 429/5xx/网络（401 不重试）；"
     "断点续跑 = JSONL 增量落盘 + 启动过滤已完成（前提：任务幂等，低温保证）。"),
    ("Token 预算与截断策略",
     "可用历史 = 窗口 − system − 本轮输入 − max_tokens(预留)。"
     "三策略：滑窗(简但丢早上下文)/保头保尾(关键设定安全)/摘要压缩(贵且有摘要幻觉)。"
     "实验：30轮对话，滑窗丢订单号、保头保尾保住。"),
    ("模板 vs 库",
     "库 = 模板 + 场景 + 设计理由 + 效果数据 + 失败边界 + 参数建议（六段）。"
     "失败边界必须从实验来，凭空想=没写。库要版本管理+回归测试（改模板重跑测试集）。"),
    ("评测参数纪律",
     "分类/裁判任务 T=0~0.2 保证可复现；生成任务可 0.8。"
     "裁判波动=评测噪声：同输入 3 次打分必须一致。参数必须显式写进报告。"),
]

# ============ ② 抽题流程（复用 W2 D7 的保护壳模式） ============
def safe_input(text):
    """非交互环境优雅退出"""
    try:
        return input(text)
    except EOFError:
        print("\n[非交互环境，测试终止]")
        sys.exit(0)

def quiz(n):
    picks = random.sample(BANK, k=min(n, len(BANK)))
    log = ["# W3 自测记录（Day21）\n", f"抽取 {len(picks)} 题\n"]
    passed = 0
    for i, (q, key) in enumerate(picks, 1):
        print(f"\n第 {i}/{len(picks)} 题：{q}")
        safe_input("  （先口述，说完回车看参考要点…）")
        print(f"  参考要点：{key}")
        mark = safe_input("  自评 [过/补]：").strip()
        passed += mark.startswith("过")
        log.append(f"{i}. {q} —— {mark}")
    log.append(f"\n结果：{passed}/{len(picks)} 过")
    out = DATA / "day21_self_test_log.md"
    out.write_text("\n".join(log), encoding="utf-8")
    verdict = ("W3 出口通过 ✓" if passed == len(picks) else
               "缓冲补课（1-2 题未过）" if passed >= len(picks) - 2 else
               "W3 预警：重学 D1-D3")
    print(f"\n结果：{passed}/{len(picks)} —— {verdict}")
    print(f"记录已存：{out}")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    quiz(int(args[0]) if args else 3)
