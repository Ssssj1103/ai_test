# -*- coding: utf-8 -*-
"""Day 09 · 手推 Self-Attention：3 个词 × 4 维，每步打印中间结果
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day02_attention_by_hand.py
目标：面试能脱稿默写 Q→K→V→缩放→softmax→加权和 六步流程。
"""

# ============ 导入区 ============
import numpy as np                            # 数值计算库
np.set_printoptions(precision=3, suppress=True)   # 打印友好：3 位小数、不用科学计数法

# ============ ① 输入与参数 ============
tokens = ["猫", "追", "老鼠"]                  # 3 个词组成句子
X = np.array([                                 # 每个词的输入向量（4 维，手工设计便于观察）
    [1.0, 0.0, 0.5, 0.0],                     # 猫
    [0.0, 1.0, 0.5, 0.0],                     # 追
    [0.0, 0.5, 0.0, 1.0],                     # 老鼠
])                                            # 形状 (3,4)：3 词 × dk=4 维

Wq = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)   # 查询投影（单位阵：简化教学）
Wk = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float)   # 键投影（交换 2、3 维制造差异）
Wv = np.eye(4)                                # 值投影：单位阵，V=原向量

# ============ ② 六步全流程 ============
print(f"输入 X 形状：{X.shape}（3 词 × 4 维）")

Q = X @ Wq                                    # 第2步a：查询——每个词"在找什么"
K = X @ Wk                                    # 第2步b：键——每个词"提供什么匹配特征"
V = X @ Wv                                    # 第2步c：值——每个词"实际携带的信息"
print(f"\nQ 形状 {Q.shape}（和 X 相同：投影不改变形状，只改变'视角'）")

scores = Q @ K.T                              # 第3步：打分——词i的Q × 词j的K 点积，(3,3)
print("\n第3步 scores（未缩放）= Q @ K^T：")
print(scores)                                 # 对角线大：词和自己最像

dk = X.shape[1]                               # dk = 4（键向量维度）
scaled = scores / np.sqrt(dk)                 # 第4步：缩放——除以 √dk，把方差拉回约 1
print(f"\n第4步 缩放后 scores/√{dk}：")
print(scaled)

def softmax(x, axis=-1):
    """softmax：按指定轴归一化成概率分布；减最大值防 exp 溢出（工程标配）"""
    e = np.exp(x - x.max(axis=axis, keepdims=True))   # 数值稳定技巧：减行最大值
    return e / e.sum(axis=axis, keepdims=True)         # 归一化

A = softmax(scaled, axis=-1)                  # 第5步：按行 softmax——每行和为 1
print("\n第5步 注意力权重 A（每行 = 一个词对各词的关注度）：")
print(A)                                      # 看每行最大值在哪，就是那个词"最关注谁"

output = A @ V                                # 第6步：加权求和——新表示 = 按权重混合全句信息
print(f"\n第6步 输出 {output.shape}：每行是'带上下文的词向量'")
for i, t in enumerate(tokens):                # 逐词解读
    print(f"  {t} 的新表示 ≈ {A[i].argmax()}号位主导（权重 {A[i].max():.2f}）")

# ============ ③ 缩放实验：分数过大时 softmax"赢家通吃" ============
print("\n③ 缩放实验：真实模型 dk=64+，点积分数会大得多——用 ×8 模拟大维度下的分数量级：")
big_scores = scores * 8                       # 模拟大 dk 下未缩放的分数（方差随 dk 线性增大）
A_big = softmax(big_scores)                   # 大分数直接 softmax
print("大分数未缩放的权重（观察'赢家通吃'）：")
print(np.round(A_big, 3))                     # 接近 one-hot：每行只有一个词拿到几乎全部权重
print(f"大分数时权重方差 {A_big.var():.3f} vs 缩放后 {A.var():.3f}")
# 结论：分数过大 → 分布尖锐 → 只有 top1 位置有梯度 → 训练不稳定（必须除 √dk 的原因）

# ============ ④ 因果掩码：decoder 只许看过去 ============
print("\n④ 因果掩码实验（自回归生成场景）：")
mask = np.triu(np.ones((3, 3)), k=1)          # 上三角全 1：标记"未来位置"（k=1 排除对角线）
masked_scores = scaled - mask * 1e9           # 未来位置分数变 -1e9，softmax 后权重≈0
A_masked = softmax(masked_scores)             # 重新归一化
print(A_masked)                               # 第1行只剩自己对角线：生成第1个词时看不见未来
print("掩码在 softmax 之前加：-1e9 经 softmax 自然变 0，行内仍归一化")
