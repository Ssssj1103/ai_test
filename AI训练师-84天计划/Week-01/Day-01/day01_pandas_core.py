# -*- coding: utf-8 -*-
"""Day 01 · pandas 核心链路：读 → 看 → 筛 → 分组 → 关联 → 导出
运行方式（用 aiml 环境的解释器）：
    /Users/zcb/miniconda3/envs/aiml/bin/python day01_pandas_core.py
数据说明：data/sample_bug_reports.csv 是 45 条缺陷单（贴测试老本行），
         后面 11 周的「评测结果统计」用的就是今天这套动作。
"""

# ============ 导入区 ============
from pathlib import Path                      # Path 用来跨平台拼接路径，避免 / 和 \ 的坑
import pandas as pd                           # pandas：表格数据处理库，约定俗成缩写为 pd

# 找到项目根目录：本文件在 Week-01/Day-01/ 下，parent 两次上溯到 AI训练师-84天计划/
ROOT = Path(__file__).resolve().parent.parent.parent   # resolve() 转绝对路径，parent 取上一级
DATA = ROOT / "data"                                   # 数据统一放 data/ 目录，全计划共用

# ============ ① 读：从 CSV 建表 ============
# read_csv 把 CSV 文件读成 DataFrame（带行列标签的二维表）；第一行自动当列名
df = pd.read_csv(DATA / "sample_bug_reports.csv")      # 返回的 df 就是内存里的"缺陷清单"
print("① 读入完成，前 3 行：")                          # 段落标记，方便对照输出
print(df.head(3))                                      # head(n) 看前 n 行，确认读对了、列名没乱码

# ============ ② 看：数据体检（任何数据到手第一件事） ============
print("\n② 数据体检：")
print(f"形状（行, 列）：{df.shape}")                    # shape 是属性不是函数，返回 (45, 12)
df.info()                                              # info() 打印每列类型和非空数量——一眼看出缺失
print(df["days_to_fix"].describe())                    # describe() 对数值列给计数/均值/分位数——看分布

# ============ ③ 筛：布尔过滤 ============
# 单条件：df[布尔Series] 返回满足条件的所有行（等价于 SQL 的 WHERE）
severe = df[df["severity"] == "严重"]                  # severity 列等于"严重"的行
print(f"\n③ 严重级别缺陷共 {len(severe)} 条")          # len(DataFrame) = 行数

# 多值：isin 接收列表，相当于 SQL 的 IN
p01 = df[df["priority"].isin(["P0", "P1"])]            # P0 或 P1 的缺陷
print(f"P0/P1 缺陷共 {len(p01)} 条")                   # 打印数量验证

# 组合条件：& 且、| 或；每个条件必须加括号（& 优先级高于 ==，不加括号必出错）
reg_p0 = df[(df["is_regression"] == "是") & (df["priority"] == "P0")]   # 回归且 P0
print(f"回归测试发现且 P0 的缺陷 {len(reg_p0)} 条")     # 组合过滤结果

# ============ ④ 统计：分组聚合 ============
# value_counts：一列里每个值出现几次（降序）， quickest 的频次统计
print("\n④ 各模块缺陷数：")
print(df["module"].value_counts())                     # 模块 → 缺陷数，评测里就是 Bad Case 分布

# groupby + agg：按模块分组，一次算多种统计量（字典写法：列名 → (新列名, 函数)）
stat = df.groupby("module").agg(                       # 按模块分组后聚合
    缺陷数=("bug_id", "count"),                        # 每组计数
    平均修复天=("days_to_fix", "mean"),                # 每组均值
    最大修复天=("days_to_fix", "max"),                 # 每组最大值
    重开总次数=("reopen_count", "sum"),                # 每组求和
).round(1)                                             # round(1) 均值保留 1 位小数，好看
stat = stat.sort_values("缺陷数", ascending=False)     # 按缺陷数降序排，最差的模块排最前
print(stat)                                            # 这张表就是「缺陷分布报告」的原型

# ============ ⑤ 关联：表连接（merge） ============
owners = pd.read_csv(DATA / "sample_module_owners.csv")   # 读入维度表：模块 → 团队/负责人
# validate="m:1" 强制检查：左表多行对右表一行；右表键重复会直接报错，防止行膨胀
merged = df.merge(owners, on="module", how="left", validate="m:1")   # how="left" 保左表全部行
print(f"\n⑤ 关联后形状：{merged.shape}")               # 行数应仍是 45；变了说明右表键重复

# 对账：找没匹配到负责人的缺陷单（关联失败 → owner 列是 NaN）
missing = merged[merged["owner"].isna()]               # isna() 判空，返回布尔 Series
print(f"关联失败的缺陷单 {len(missing)} 条")            # 数据质量意识：行数对不上必须查

# ============ ⑥ 出：导出结果（评测中间结果落盘） ============
out = DATA / "day01_module_stat.csv"                   # 输出路径
stat.to_csv(out, index=False, encoding="utf-8-sig")    # index=False 不写行索引；utf-8-sig 让 Excel 打开不乱码
print(f"\n⑥ 统计表已导出：{out}")                      # 产物确认——每天必须有文件产出
