# -*- coding: utf-8 -*-
"""Day 04 · numpy 手写 2 层神经网络：学会"圆圈分类"（纯 CPU，几秒跑完）
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day04_neural_network.py
网络结构：输入(2) → 隐藏层(8, tanh) → 输出(1, sigmoid) → 概率
训练目标：圆内=1，圆外=0 —— 直线永远分不开，隐藏层可以。
"""

# ============ 导入区 ============
import numpy as np                            # 数值计算库

rng = np.random.default_rng(seed=42)          # 固定随机种子：实验可复现

# ============ ① 造数据：圆内=1，圆外=0 ============
N = 300                                       # 样本量
X = rng.uniform(-1, 1, size=(N, 2))           # 300 个点均匀撒在 [-1,1]×[-1,1] 平面上
y = ((X[:, 0] ** 2 + X[:, 1] ** 2) < 0.5).astype(float)   # 标签：半径平方<0.5 → 圆内=1，圆外=0
y = y.reshape(-1, 1)                          # 变成 (300,1) 列向量，方便后面和预测值逐元素运算

# 基线 1（多数类瞎猜）：全判"圆外"——对应 D3 学过的"类别不平衡时准确率会骗人"
majority_acc = np.mean(y == 0)                # 圆内占少数，全判 0 也有 6 成多准确率
# 基线 2（线性切分）：用一条直线 x1+x2=0.7 划分——无论斜率截距怎么调，直线都不可能围出圆
linear_pred = ((X[:, 0] + X[:, 1]) < 0.7).astype(float)   # 半平面判据：直线一侧全判 1
linear_acc = np.mean(linear_pred.reshape(-1, 1) == y)     # 线性方法的准确率
print(f"① 基线对比：多数类瞎猜={majority_acc:.1%}，最优直线切分≈{linear_acc:.1%}")
print("   （圆是弯曲边界，任何直线都围不出来——这就是需要隐藏层的理由）")

# ============ ② 定义网络：2-8-1 ============
HIDDEN = 8                                    # 隐藏层神经元数量（实验 1 会改它）
LEARNING_RATE = 0.5                           # 学习率（实验 2 会改它）
EPOCHS = 5000                                 # 训练步数

W1 = rng.normal(0, 0.5, size=(2, HIDDEN))     # 输入→隐藏的权重矩阵；小随机数初始化打破对称性
b1 = np.zeros((1, HIDDEN))                    # 隐藏层偏置，初始化为 0
W2 = rng.normal(0, 0.5, size=(HIDDEN, 1))     # 隐藏→输出的权重
b2 = np.zeros((1, 1))                         # 输出层偏置

USE_ACTIVATION = True                         # 实验 3 开关：False 时隐藏层不加激活（退化为线性）

def forward(X_in):
    """前向传播：输入 → 隐藏层 → 输出概率。返回 (概率p, 隐藏层输出a1) 供反向传播复用"""
    z1 = X_in @ W1 + b1                       # 线性变换：矩阵乘法 + 偏置（X 是 (N,2)，W1 是 (2,H)）
    if USE_ACTIVATION:                        # 开关：是否加非线性
        a1 = np.tanh(z1)                      # tanh 激活：把值压到 (-1,1)，引入非线性
    else:
        a1 = z1                               # 实验用：不加激活，网络退化为线性
    z2 = a1 @ W2 + b2                         # 隐藏层 → 输出（还是线性变换）
    p = 1 / (1 + np.exp(-z2))                 # sigmoid：把任意实数压到 (0,1)，当概率用
    return p, a1                              # 两个都返回：反向传播需要 a1

def bce_loss(p, y_true):
    """二元交叉熵（BCE）：二分类标准损失。预测越偏离真实，loss 越大"""
    eps = 1e-9                                # 防止 log(0) 溢出
    return -np.mean(y_true * np.log(p + eps) + (1 - y_true) * np.log(1 - p + eps))

# ============ ③ 训练循环：前向 → 反向 → 更新 ============
print(f"\n③ 开始训练（hidden={HIDDEN}, lr={LEARNING_RATE}, epochs={EPOCHS}）:")
for epoch in range(1, EPOCHS + 1):            # 走 EPOCHS 步
    # ---- 前向传播 ----
    p, a1 = forward(X)                        # 拿到预测概率和隐藏层输出
    loss = bce_loss(p, y)                     # 当前 loss

    # ---- 反向传播（链式法则逐层回传；看懂思路即可，不用手推）----
    dz2 = (p - y) / N                         # 输出层梯度：BCE+sigmoid 组合下恰好 = (预测-真实)/N，和 D2 同构
    dW2 = a1.T @ dz2                          # W2 的梯度 = 隐藏层输出转置 × 输出层梯度
    db2 = np.sum(dz2, axis=0, keepdims=True)  # b2 的梯度 = 输出层梯度求和
    da1 = dz2 @ W2.T                          # 把误差传回隐藏层（乘 W2 转置）
    dz1 = da1 * (1 - a1 ** 2)                 # 链式法则乘局部导数：tanh 的导数 = 1 - tanh²
    dW1 = X.T @ dz1                           # W1 的梯度
    db1 = np.sum(dz1, axis=0, keepdims=True)  # b1 的梯度

    # ---- 参数更新（梯度下降，和 D2 同一个公式）----
    W1 -= LEARNING_RATE * dW1                 # 沿梯度反方向走一小步
    b1 -= LEARNING_RATE * db1
    W2 -= LEARNING_RATE * dW2
    b2 -= LEARNING_RATE * db2

    if epoch % 1000 == 0:                     # 每 1000 步报一次进度
        acc = np.mean((p > 0.5) == y)         # 准确率：概率>0.5 算判 1
        print(f"  epoch={epoch:>5}  loss={loss:.4f}  accuracy={acc:.1%}")

# ============ ④ 最终评估 + 三个实验开关 ============
p, _ = forward(X)                             # 训练结束再前向一次
final_acc = np.mean((p > 0.5) == y)           # 最终准确率
print(f"\n④ 训练完成，最终准确率：{final_acc:.1%}（目标 ≥95%；最优直线切分只有 {linear_acc:.1%}）")
print("实验提示：改 HIDDEN=2 / 64、LEARNING_RATE=0.05、USE_ACTIVATION=False 分别重跑，记录现象")
