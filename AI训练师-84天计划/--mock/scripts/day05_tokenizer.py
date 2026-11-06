# -*- coding: utf-8 -*-
"""Day 05 · Tokenizer 直觉实验：看懂"文本 → token"的过程
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day05_tokenizer.py
主线用纯 Python 模拟分词逻辑（保证零依赖可跑）；
装了 tiktoken 的话会自动用真实 BPE 词表做对比（pip install tiktoken）。
"""

# ============ 导入区 ============
import re                                     # 正则模块：用来做简单的中英文切分
from pathlib import Path                      # 路径处理

# ============ ① 一个"玩具分词器"：理解 token 的粒度概念 ============
def toy_tokenize(text: str) -> list[str]:
    """玩具分词器：英文按词、中文按字、标点单算——模拟'词元化'的粗略逻辑
    （真实 BPE 是高频字节对合并，这里只求直觉）"""
    # \w 匹配字母数字下划线（含中文），[\u4e00-\u9fff] 是汉字区，其余逐字符
    tokens = re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]|[0-9]+|\S", text)   # 四类：英文词/汉字/数字/其他符号
    return tokens

samples = {                                   # 三类测试文本：英文 / 中文 / 混排+emoji（边界用例思维）
    "英文": "The model failed to answer the user's question correctly.",
    "中文": "模型没有正确回答用户的问题。",
    "混排": "这个 bug 在 v2.3.0 复现，emoji测试🎉 + English mixed 文本。",
}

print("① 玩具分词器结果：")
for name, text in samples.items():            # 遍历三个样本
    toks = toy_tokenize(text)                 # 切分
    print(f"  {name}：字符数={len(text):>3}  粗估token数={len(toks):>3}  前5个={toks[:5]}")
    # 观察：中文"一字一token"，英文"一词一token"——同样意思，中文token更多

# ============ ② Token 与上下文窗口的换算 ============
print("\n② 上下文窗口换算（用①的实测比例粗估）：")
# 真实模型里中文 1 字 ≈ 1~2 token（BPE 对汉字的合并率低），英文 1 词 ≈ 1.3 token
CHINESE_TOKEN_PER_CHAR = 1.6                  # 中文经验值：每字平均 1.6 个 token（不同模型有差异）
ENGLISH_TOKEN_PER_WORD = 1.3                  # 英文经验值：每词平均 1.3 个 token
window_tokens = 128_000                       # 假设上下文窗口 128K token（主流大杯模型规格）

cn_chars_fit = int(window_tokens / CHINESE_TOKEN_PER_CHAR)   # 能装多少个中文字
en_words_fit = int(window_tokens / ENGLISH_TOKEN_PER_WORD)   # 能装多少个英文词
print(f"  128K token 窗口 ≈ 中文 {cn_chars_fit:,} 字 ≈ 英文 {en_words_fit:,} 词")
print(f"  → 评测集长文档任务时，先算 token 再设计样本长度，防止'爆窗'截断")

# ============ ③ 真实 BPE 对比（可选：装了 tiktoken 才生效） ============
print("\n③ tiktoken 实测对比（未安装则跳过）：")
try:
    import tiktoken                           # OpenAI 的 BPE 分词器库
    enc = tiktoken.get_encoding("cl100k_base")   # GPT-3.5/4 使用的编码方案
    for name, text in samples.items():        # 同样三个样本
        ids = enc.encode(text)                # encode：文本 → token ID 列表
        print(f"  {name}：token数={len(ids):>3}  前8个ID={ids[:8]}")
        # 观察：emoji 和生僻字会被拆成多个字节级 token——这就是"边界用例"
except ImportError:                           # 没装 tiktoken
    print("  tiktoken 未安装。想实测真实 BPE：pip install tiktoken（可选，不阻塞主线）")

# ============ ④ 训练四阶段速记卡（输出成文件，面试前背） ============
stages = [                                    # 四阶段：阶段名 → 喂的数据 → 学到什么
    ("预训练", "万亿级网页/书籍/代码（纯文本流）", "预测下一个token：语言+知识的底子"),
    ("SFT 监督微调", "指令→高质量回答 对（万~百万条）", "听懂指令、按格式作答"),
    ("偏好对齐 RLHF/DPO", "同一问题的 好回答 vs 差回答 对", "有用/诚实/无害的价值观"),
    ("持续迭代", "Bad Case 修复数据、新知识", "持续改进——训练师的日常"),
]
out = Path(__file__).resolve().parent / "day05_training_stages.md"   # 速记卡输出路径
lines = ["# 训练四阶段速记卡（Day05 产出）", "", "| 阶段 | 喂什么 | 学什么 |", "|---|---|---|"]
for s, data, learn in stages:                 # 逐阶段写表
    lines.append(f"| {s} | {data} | {learn} |")
out.write_text("\n".join(lines), encoding="utf-8")   # 落盘——每天必须有文件产出
print(f"\n④ 训练四阶段速记卡已生成：{out.name}")
