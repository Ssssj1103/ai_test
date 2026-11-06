# -*- coding: utf-8 -*-
"""Day 02 · 梯度下降直觉实验 + 过拟合演示（纯 numpy，无需 GPU）
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day02_gradient_descent.py
你将亲眼看到：① loss 一路下降 ② 学习率太大直接发散 ③ 高次多项式过拟合
"""

# ============ 导入区 ============
import numpy as np                            # numpy：数值计算库，ndarray 是一切的地基

# 固定随机种子：每次运行生成同样的"随机"数，实验可复现（评测集设计同理——要可复现）
rng = np.random.default_rng(seed=42)

# ============ ① 造数据：真实规律 + 噪声 ============
# 真实规律是 y = 2x + 1，我们只能看到带噪声的观测值——这就是"训练数据"的本质
N = 60                                        # 样本量：60 个点
x = rng.uniform(0, 1, N)                      # uniform：在 [0,1) 均匀采样（特征做了归一化，梯度下降更稳定）
NOISE = 0.1                                   # 噪声强度：模拟"现实数据总是不干净"
y = 2.0 * x + 1.0 + rng.normal(0, NOISE, N)   # normal：加均值为0、标准差为0.1的噪声

# ============ ② 手写梯度下降：学 y = w·x + b ============
LEARNING_RATE = 0.1                           # 学习率：每步沿梯度走多远（D2 核心概念）
w, b = 0.0, 0.0                               # 参数初始化：从"全错"的 w=0,b=0 出发
STEPS = 200                                   # 迭代步数：走 200 步

for step in range(1, STEPS + 1):              # 循环 step = 1..200
    pred = w * x + b                          # 前向：用当前参数预测所有点
    error = pred - y                          # 残差：预测减真实，正=预测偏高
    loss = np.mean(error ** 2)                # MSE 损失：残差平方的平均值（越小越好）

    grad_w = 2 * np.mean(error * x)           # 对 w 的梯度（MSE 求导结果，直接用结论不推导）
    grad_b = 2 * np.mean(error)               # 对 b 的梯度

    w -= LEARNING_RATE * grad_w               # 参数更新：沿梯度反方向走一小步（下降）
    b -= LEARNING_RATE * grad_b               # b 同理

    if step % 20 == 0 or step == 1:           # 每 20 步打印一次，观察下降趋势
        print(f"step={step:>3}  loss={loss:8.3f}  w={w:.3f}  b={b:.3f}")

print(f"\n② 最终：w≈{w:.3f}（真值2.0）  b≈{b:.3f}（真值1.0）  loss≈{loss:.3f}")

# ============ ③ 过拟合演示：多项式次数越高越"背题" ============
print("\n③ 过拟合实验（同一批点，三种多项式）:")
# 划分：60 个点里 40 个当"训练集"，20 个当"没见过的测试点"
x_train, y_train = x[:40], y[:40]             # 训练集：前 40 个
x_test, y_test = x[40:], y[40:]               # 测试集：后 20 个（模型没见过）

for degree in (1, 5, 15):                     # 三种模型复杂度：直线 / 5次 / 15次
    coeffs = np.polyfit(x_train, y_train, deg=degree)      # polyfit：多项式最小二乘拟合
    train_pred = np.polyval(coeffs, x_train)  # 在训练集上预测
    test_pred = np.polyval(coeffs, x_test)    # 在测试集上预测
    train_mse = np.mean((train_pred - y_train) ** 2)       # 训练误差
    test_mse = np.mean((test_pred - y_test) ** 2)          # 测试误差（泛化能力）
    print(f"{degree:>2} 次多项式  训练MSE={train_mse:8.4f}  测试MSE={test_mse:8.4f}")
    # 预期现象：1 次欠拟合两边都一般；5 次平衡；15 次训练误差≈0 但测试误差爆炸

# ============ ④ 学习率实验：太大直接发散 ============
print("\n④ 学习率实验:")
for lr in (0.01, 0.1, 50.0):                  # 三档学习率：慢 / 合适 / 离谱
    w_l, b_l = 0.0, 0.0                       # 每档都从零开始
    for _ in range(200):                      # 走 200 步，观察收敛速度差异
        err = (w_l * x + b_l) - y             # 残差
        w_l -= lr * 2 * np.mean(err * x)      # 同②的更新规则
        b_l -= lr * 2 * np.mean(err)          # b 同步更新
    final_loss = np.mean(((w_l * x + b_l) - y) ** 2)       # 该档学习率的最终 loss
    if np.isnan(final_loss) or final_loss > 10:            # nan 说明数值溢出（发散的极端形态）
        tag = "发散(太大)"                                 # 发散：步子太大直接爆炸
    elif final_loss > 0.05:                                # 还没降到噪声水平
        tag = "收敛慢，需更多步"
    else:
        tag = "正常"                                       # loss 已接近噪声下限
    print(f"lr={lr:<6} 最终loss={final_loss:12.4f}  → {tag}")
    # 预期：0.01 慢但能到；0.1 快速收敛；50 直接发散——loss 巨大
