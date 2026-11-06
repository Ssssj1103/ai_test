# -*- coding: utf-8 -*-
"""Day 03 · 评测指标：手算混淆矩阵指标 + sklearn 对账 + 阈值实验 + AUC
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day03_metrics.py
核心：先手算，再让 sklearn 验证你的手算——一致 = 你真的懂了。
"""

# ============ 导入区 ============
import numpy as np                            # 数值计算库
from sklearn.metrics import (                 # sklearn 评测指标模块：行业标准实现
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score,
)

rng = np.random.default_rng(seed=7)           # 固定种子：每次运行结果一致（可复现原则）

# ============ ① 造模拟数据：200 条"客服消息"是否投诉 ============
N = 200                                       # 总样本量
POS_RATE = 0.30                               # 正类（投诉）占比 30%：轻度不平衡，接近真实
y_true = (rng.random(N) < POS_RATE).astype(int)   # 真实标签：随机抽，1=投诉 0=非投诉

# 模拟模型打分：投诉消息给高分，非投诉给低分，再叠噪声（噪声大小决定模型好坏）
scores = np.where(                            # np.where：按条件二选一地生成数组
    y_true == 1,                              # 条件：真实是投诉
    rng.normal(0.65, 0.18, N),                # 投诉消息：得分以 0.65 为中心的正态分布
    rng.normal(0.35, 0.18, N),                # 非投诉：以 0.35 为中心
)
scores = np.clip(scores, 0.0, 1.0)            # clip：把得分夹在 [0,1] 区间内（概率语义）

# ============ ② 手算混淆矩阵 + 四大指标，与 sklearn 对账 ============
THRESHOLD = 0.5                               # 判定阈值：得分≥0.5 判"投诉"
y_pred = (scores >= THRESHOLD).astype(int)    # 得到预测标签（0/1 数组）

TP = int(np.sum((y_pred == 1) & (y_true == 1)))   # 真阳：预测投诉 且 真的投诉
FP = int(np.sum((y_pred == 1) & (y_true == 0)))   # 假阳：预测投诉 但 其实不是（误报）
FN = int(np.sum((y_pred == 0) & (y_true == 1)))   # 假阴：预测不是 但 其实是（漏报）
TN = int(np.sum((y_pred == 0) & (y_true == 0)))   # 真阴：都判对为非投诉
print(f"① 混淆矩阵（阈值={THRESHOLD}）：TP={TP} FP={FP} FN={FN} TN={TN}")

# 手算四大指标（分母可能为 0，加 max(…, 1) 防除零）
acc_hand = (TP + TN) / N                                  # 准确率 = 判对总数 / 总数
pre_hand = TP / max(TP + FP, 1)                           # 精确率 = 抓对的 / 所有报的
rec_hand = TP / max(TP + FN, 1)                           # 召回率 = 抓对的 / 所有真的
f1_hand = 2 * pre_hand * rec_hand / max(pre_hand + rec_hand, 1e-9)   # F1 = P、R 调和平均

# sklearn 算同一批预测，用来对账
acc_lib = accuracy_score(y_true, y_pred)                  # sklearn 准确率
pre_lib = precision_score(y_true, y_pred, zero_division=0)   # zero_division=0：分母为0时报0不报错
rec_lib = recall_score(y_true, y_pred, zero_division=0)   # sklearn 召回率
f1_lib = f1_score(y_true, y_pred, zero_division=0)        # sklearn F1

print("\n② 手算 vs sklearn 对账（必须一致）：")
for name, mine, lib in [("Accuracy", acc_hand, acc_lib), ("Precision", pre_hand, pre_lib),
                        ("Recall", rec_hand, rec_lib), ("F1", f1_hand, f1_lib)]:
    flag = "✓" if abs(mine - lib) < 1e-9 else "✗ 不一致！"   # 浮点比较用误差容忍，不用 ==
    print(f"  {name:<10} 手算={mine:.4f}  sklearn={lib:.4f}  {flag}")

# ============ ③ 阈值实验：看 P/R 此消彼长 + AUC ============
print("\n③ 阈值实验（Precision↑ 则 Recall↓，反之亦然）：")
for t in (0.1, 0.3, 0.5, 0.7, 0.9):           # 从宽松到严格扫 5 档阈值
    pred_t = (scores >= t).astype(int)        # 每档阈值重新生成预测
    p = precision_score(y_true, pred_t, zero_division=0)   # 该阈值下的精确率
    r = recall_score(y_true, pred_t, zero_division=0)      # 该阈值下的召回率
    print(f"  阈值={t:.1f}  Precision={p:.3f}  Recall={r:.3f}")
    # 预期规律：阈值越低 → 报得越多 → Recall 高 Precision 低；越高则相反

auc = roc_auc_score(y_true, scores)           # AUC：只吃"得分"不需要阈值，衡量排序能力
print(f"\n④ AUC={auc:.3f}（0.5=瞎猜，1.0=完美排序；与阈值无关）")

# ============ ⑤ 用例：找"召回率≥0.9"的阈值（漏报代价高的场景） ============
best_t = None                                 # 存放找到的阈值
for t in np.arange(0.05, 0.95, 0.05):         # 0.05 步长扫阈值
    r = recall_score(y_true, (scores >= t).astype(int), zero_division=0)
    if r >= 0.9:                              # 第一个满足召回≥0.9 的阈值
        best_t = round(float(t), 2)           # 记录下来
        break                                 # 找到就停
if best_t is not None:                        # 找到了
    p_best = precision_score(y_true, (scores >= best_t).astype(int), zero_division=0)
    print(f"⑤ 满足 Recall≥0.9 的最高阈值={best_t}，此时 Precision={p_best:.3f}")
else:                                         # 扫完都没有（模型太差）
    print("⑤ 没有任何阈值能达到 Recall≥0.9——模型排序能力不足，该换模型/补特征了")
