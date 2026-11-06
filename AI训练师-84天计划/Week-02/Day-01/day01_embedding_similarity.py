# -*- coding: utf-8 -*-
"""Day 08 · 嵌入与点积相似度直觉：手算"Attention 的原材料"
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day01_embedding_similarity.py
用 4 维玩具词向量演示：语义相关 → 向量相近 → 点积大。
真实模型的嵌入是 4096+ 维且从语料学出，数学性质完全一样。
"""

# ============ 导入区 ============
import numpy as np                            # 数值计算库
np.set_printoptions(precision=2, suppress=True)   # 打印时保留 2 位小数、不显示科学计数法

# ============ ① 造玩具词向量：4 个词 × 4 维 ============
# 每行是一个词的"嵌入向量"。维度含义人造：[可爱度, 智力, 危险度, 机器度]
# 真实模型里这些维度没有人类可读含义，但几何性质（方向=语义）相同
words = ["猫", "狗", "国王", "机器人"]
E = np.array([                                # 嵌入矩阵：行=词，列=维度
    [0.9, 0.3, 0.1, 0.0],                     # 猫：可爱、低危、不机器
    [0.9, 0.4, 0.1, 0.0],                     # 狗：和猫很像（只在智力上略高）
    [0.3, 0.9, 0.4, 0.1],                     # 国王：智力高、有威慑
    [0.1, 0.8, 0.2, 0.9],                     # 机器人：机器度拉满
])

# ============ ② 点积相似度矩阵：每对词的相关性 ============
# E @ E.T：4×4 乘 4×4 → 得 4×4 矩阵，第 i 行第 j 列 = 词i · 词j（点积）
# 这一步和 Attention 的 Q@K^T 在数学上完全一样——你已经算过 Attention 核心了
sim = E @ E.T                                 # 相似度矩阵
print("① 点积相似度矩阵（行=查询词，列=被查词）：")
print(f"{'':>6}", *[f"{w:>6}" for w in words])   # 表头
for w, row in zip(words, sim):                # 逐行打印
    print(f"{w:>6}", *[f"{v:6.2f}" for v in row])
# 预期：猫-狗 相似度最高（向量几乎相同）；猫-机器人 最低（方向差异大）

# ============ ③ softmax 预演：把分数变成"关注度权重" ============
def softmax(x):
    """softmax：把任意实数向量压成和为 1 的概率分布（Attention 权重的由来）"""
    e = np.exp(x - x.max())                   # 减最大值防溢出（数值技巧，真实模型同款）
    return e / e.sum()                        # 归一化：除以总和

# 拿"猫"对全部词的相似度做 softmax → 猫该"关注"谁
weights = softmax(sim[0])                     # sim[0] = 猫对 猫/狗/国王/机器人 的分数
print("\n② 「猫」对各词的注意力权重（softmax 后，和为 1）：")
for w, wt in zip(words, weights):             # 展示权重
    bar = "█" * int(wt * 40)                  # 简易条形图，直观看比例
    print(f"  {w}: {wt:.3f} {bar}")
# 注意"猫"对自己的权重最大——这就是为什么真实 Attention 要加 √d 缩放和掩码（D2 讲）

# ============ ④ 词向量算术：king + queen - man 经典实验 ============
# 语义方向可以在向量空间里做加减（真实模型的著名现象）
manual = {                                    # 补两个词的手工向量，供算术实验
    "男人": np.array([0.1, 0.9, 0.4, 0.1]),   # 智力高但"可爱度"低
    "女王": np.array([0.6, 0.8, 0.3, 0.1]),   # 智力高且更"可爱"——差异主要在第一维
}
queen_minus_man = manual["女王"] - manual["男人"]       # "性别差异"方向向量
target = E[2] + queen_minus_man               # 国王 + (女王-男人) ≈ 期待得到"女王"方向
print("\n③ 词向量算术：国王 + (女王 - 男人) = ?")
sims = [(w, float(target @ v)) for w, v in zip(words, E)]   # 和词表里每个词算点积
sims += [("女王", float(target @ manual["女王"])), ("男人", float(target @ manual["男人"]))]
for w, s in sorted(sims, key=lambda x: -x[1]):          # 按相似度降序
    print(f"  {w}: {s:.2f}")
# 预期："女王"排最前——向量方向能承载语义关系（嵌入空间的可组合性）
