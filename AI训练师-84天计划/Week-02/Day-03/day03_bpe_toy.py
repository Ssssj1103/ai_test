# -*- coding: utf-8 -*-
"""Day 10 · BPE 分词玩具实现：看懂 token 是怎么"合并"出来的
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day03_bpe_toy.py
纯 Python 实现，和真实 BPE（tiktoken）思路一致：反复合并最高频相邻对。
"""

# ============ 导入区 ============
from collections import Counter               # Counter：统计频率的字典子类

# ============ ① 训练 BPE：10 轮合并 ============
corpus = ["low", "lower", "lowest", "low", "new", "newest", "new", "wide", "widest", "low"]
# 语料：10 个词。注意 low/new 出现多次（高频），est 只在部分词尾出现

def get_pairs(words):
    """统计所有相邻 token 对的频率。words 是列表的列表（每个词拆成 token 列表）"""
    pairs = Counter()                         # 频率计数器
    for word in words:                        # 遍历每个词
        for i in range(len(word) - 1):        # 遍历词内相邻位置
            pairs[(word[i], word[i + 1])] += 1   # 相邻一对 +1
    return pairs

# 初始：每个词拆成字符列表（BPE 的起点是字符级）
words = [list(w) for w in corpus]             # 如 ['l','o','w'] 
merges = []                                   # 记录学到的合并规则（有序）
print("① BPE 训练过程：")
for step in range(1, 11):                     # 训练 10 轮
    pairs = get_pairs(words)                  # 统计当前所有相邻对
    if not pairs:                             # 没有可合并的对就停
        break
    best, freq = pairs.most_common(1)[0]      # 取频率最高的对（most_common 按次数降序）
    merges.append(best)                       # 记录规则
    # 执行合并：把 words 里所有的 (a,b) 相邻对替换成 a+b
    new_words = []                            # 存放合并后的结果
    for word in words:                        # 逐词处理
        merged, i = [], 0                     # merged 是新 token 序列
        while i < len(word):                  # 扫描词内每个 token
            if i < len(word) - 1 and (word[i], word[i + 1]) == best:   # 命中最高频对
                merged.append(word[i] + word[i + 1])   # 合并成一个新 token
                i += 2                        # 跳过两个位置
            else:
                merged.append(word[i])        # 不命中就原样保留
                i += 1
        new_words.append(merged)              # 收集该词
    words = new_words                         # 更新语料
    print(f"  第{step}轮 合并 {best}（出现{freq}次）→ 新token '{best[0]+best[1]}'")
    # 观察：l+o、o+w 高频对先被合并；est 在第 3-4 轮出现（w+i+d+e 和 e+s+t 竞争）

# ============ ② 用学到的规则编码新词 ============
def encode(word, merges):
    """用训练学到的合并规则（有序！）编码任意词。顺序重要：先学的规则先应用"""
    toks = list(word)                         # 从字符级开始
    for a, b in merges:                       # 按训练时的合并顺序逐条应用
        i, out = 0, []                        # 扫描当前序列
        while i < len(toks):
            if i < len(toks) - 1 and toks[i] == a and toks[i + 1] == b:   # 命中该规则
                out.append(a + b)             # 合并
                i += 2
            else:
                out.append(toks[i])           # 保留
                i += 1
        toks = out                            # 一轮规则应用完再下一条
    return toks

print("\n② 编码实验（训练见过的 vs 没见过的词）：")
for w in ["low", "lowest", "slow", "slowest", "yellow"]:   # slow/yellow 训练时没见过
    print(f"  {w:<8} → {encode(w, merges)}")
# 预期：训练见过的碎得少；没见过的词复用子规则但仍碎——这就是"生僻词被拆碎"的机制

# ============ ③ 与真实 BPE（tiktoken）对比 ============
print("\n③ tiktoken 实测对比（同一批词）：")
try:
    import tiktoken                           # 真实 BPE 实现
    enc = tiktoken.get_encoding("cl100k_base")   # GPT-3.5/4 的编码
    for w in ["low", "lowest", "slow", "yellow", "_EXTRAORDINARILY_LONG_WORD"]:
        ids = enc.encode(w)                   # 真实编码
        print(f"  {w:<28} {len(ids)} 个token：{ids[:6]}{'...' if len(ids) > 6 else ''}")
    # 方向一致：常见词 1 个 token，怪长词碎成多块
except ImportError:                           # 未安装也不阻塞
    print("  tiktoken 未安装，跳过（pip install tiktoken 可选）")

# ============ ④ 四类文本的 token 成本对比（评测成本估算直接复用） ============
print("\n④ token 成本对比表（tiktoken）：")
try:
    samples = {                               # 四类典型文本：中文/英文/数字/emoji
        "中文句": "大模型评测需要考虑准确率与一致性指标。",
        "英文句": "LLM evaluation requires accuracy and consistency metrics.",
        "数字串": "3.14159265358979323846264338327950288",
        "emoji串": "🚀🎉🤖💥🔥🧠✅❌⭐️🎯",
    }
    for name, text in samples.items():        # 逐类统计
        n = len(enc.encode(text))             # token 数
        print(f"  {name}：字符 {len(text):>3} → token {n:>3}（{n/len(text):.2f} token/字符）")
    # 预期：中文 ≈1.5-2；英文 ≈0.2-0.3/字符；数字 ≈0.5/字符；emoji 1-3 token/个
except NameError:                             # tiktoken 没装时的兜底
    print("  需要 tiktoken，跳过")
