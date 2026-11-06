# 验证 · Day 01 · pandas 核心链路

## 一、自测题（不翻资料口答，答不出的回学习内容重读）

1. `df[df["severity"] == "严重"]` 和 `df.loc[df["severity"] == "严重", ["module"]]` 的输出有什么区别？
2. 两个条件同时过滤，`df[df["a"]==1 & df["b"]==2]` 会报什么问题？正确写法？
3. `groupby("module")["days_to_fix"].mean()` 和 `groupby("module").agg(平均=("days_to_fix","mean"))` 各返回什么结构？
4. `merge(how="left")` 之后行数变多了，最可能的原因是什么？怎么定位？
5. `to_csv()` 不加 `index=False` 会多出一列，这列是什么？

<details><summary>参考答案（先自己答再展开）</summary>

1. 前者返回整行（所有列），后者只返回 module 列（Series）；`.loc[行条件, 列列表]` 是「先筛行再选列」。
2. Python 运算符优先级：`&` 比 `==` 高，实际执行 `1 & df["b"]` 先运算，报错或结果错。正确：`df[(df["a"]==1) & (df["b"]==2)]`，两个条件各自加括号。
3. 前者返回 Series（索引=module，值=均值）；后者返回 DataFrame（自定义列名"平均"），一次能聚合多列。
4. 右表（关联表）的连接键有重复值，一对多连接导致行膨胀。定位：`merge` 前检查右表 `owners["module"].duplicated().sum()`，或用 `validate="m:1"` 让 pandas 直接报错。
5. 行索引列 `Unnamed: 0`——DataFrame 的 index 被当成普通列写出了。
</details>

## 二、实操验收（动手完成才能打勾）

**任务 1（筛选）**：筛出「回归测试阶段发现的、且是 P0 或 P1」的缺陷，输出 `bug_id, module, severity` 三列。

- [ ] 用 `&` + `isin` 组合实现
- [ ] 结果存到 `data/day01_task1_result.csv`（不带索引）

**任务 2（统计）**：一张「模块 × 严重级别」的缺陷数交叉表，外加每个模块的平均修复天数和总重开次数。

- [ ] 交叉表用 `crosstab` 或 `pivot_table` 任一实现
- [ ] 平均修复天数保留 1 位小数
- [ ] 按缺陷总数降序排列

**任务 3（关联+对账）**：把缺陷单和 `sample_module_owners.csv` 关联，找出「没有匹配到负责人」的模块。

- [ ] 用 `validate="m:1"` 防止行膨胀
- [ ] 用 `isna()` 找出关联失败的缺陷单数量并打印

**任务 4（改错，选做）**：下面代码有 2 个 bug，找出来并修复：

```python
result = df[df["severity"] == "严重" | df["priority"] == "P0"]
result.to_csv("day01_task4.csv")
```

- [ ] 指出两个问题：＿＿＿＿＿＿＿＿＿＿、＿＿＿＿＿＿＿＿＿＿
- [ ] 修复后能正确导出

## 三、验收标准（全部满足才算 Day 01 完成）

- [ ] `day01_pandas_core.py` 原样跑通，6 段输出都能看懂
- [ ] 实操任务 1-3 完成，产物文件存在
- [ ] 笔记模板填完，「面试怎么说」写了 3 句以上
- [ ] 自测 5 题全对（或已重读订正）

**明日预告**：D2 机器学习通识 + 梯度下降直觉实验（numpy 手写，10 行代码看到 loss 下降）。
