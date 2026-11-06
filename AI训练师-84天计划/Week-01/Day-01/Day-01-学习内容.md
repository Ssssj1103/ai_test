# Day 01（Week 1 · D1）· 环境自检 + pandas 核心链路

> **今日一句话目标**：跑通 pandas「读 → 看 → 筛 → 分组 → 关联 → 导出」完整链路。
> 这是后续 83 天所有动手任务的地基：评测集清洗、Bad Case 统计、标注质检，本质都是今天这几招的排列组合。

## 1. 今日时间地图（3.5-4h）

| 时段 | 内容 | 产出 |
| --- | --- | --- |
| 15' | 复盘：无（第一天），直接读本文第 2 节 | 明确今天学什么 |
| 60' | 读本文第 3-5 节 + 跑通 `day01_pandas_core.py` | 脚本运行成功 |
| 10' | 休息 | |
| 60' | 改造脚本：完成 `验证.md` 实操任务 1-3 | 新增 3 段自己的代码 |
| 45' | 填 `笔记模板.md` + 过 `验证.md` 自测题 | 笔记 + 验收打勾 |
| 10' | 记录卡点 | 卡点清单 |

**只有 2.5h 的保底版**：砍掉第 5 节 merge 部分（挪到 D2 补），保住「读→看→筛→分组」和笔记输出。

## 2. 环境自检（5 分钟，已体检过，跑一遍确认即可）

```bash
# 用 aiml 环境的解释器确认版本（后面所有天都用这个解释器）
/Users/zcb/miniconda3/envs/aiml/bin/python --version
# 期望输出：Python 3.12.16

/Users/zcb/miniconda3/envs/aiml/bin/python -c "import pandas as pd; print(pd.__version__)"
# 期望输出：3.1.0
```

结论：**零安装，直接开敲**。Intel Mac 无 GPU，后面微调周用 Colab/AutoDL，本周用不到。

## 3. 核心概念：pandas 的两个对象（用自己的话记）

| 对象 | 一句话定义 | 类比测试工作 |
| --- | --- | --- |
| `DataFrame` | 带行列标签的二维表格 | 一张 Excel 缺陷清单 |
| `Series` | 单独的一列（或一行） | Excel 里的某一列，如「severity」 |

测试视角：你以前在 Excel 里做的「按模块统计缺陷数、按严重级别过滤、关联用例表」，今天全部用 pandas 代码化——**这是自动化评测流水线里"统计数据"那一步的原型**。

## 4. 今日代码讲解（`day01_pandas_core.py`，逐行注释在文件里）

脚本分 6 段，对应 6 个动作：

| 段 | 动作 | 关键函数 | 面试/实用价值 |
| --- | --- | --- | --- |
| ① 读 | 从 CSV 建表 | `pd.read_csv()` | 评测结果文件几乎都是 CSV/JSONL |
| ② 看 | 体检数据 | `head() / info() / describe() / shape` | 任何数据到手第一件事，防脏数据 |
| ③ 筛 | 布尔过滤 | `df[df["col"] == 值]`、`isin`、`&` 组合条件 | 等价于 SQL 的 WHERE |
| ④ 统计 | 分组聚合 | `groupby().agg()`、`value_counts()` | 缺陷分布表 = Bad Case 分布表 |
| ⑤ 关联 | 表连接 | `merge(how="left")`、`validate` | 缺陷单 × 模块负责人 → 责任归属 |
| ⑥ 出 | 导出结果 | `to_csv(index=False)` | 评测中间结果落盘，供下一步消费 |

**数据说明**（`data/sample_bug_reports.csv`，45 条缺陷单）：`bug_id, module, severity(严重级别), priority, status, found_in_version, tester, developer, days_to_fix, reopen_count, is_regression, found_phase`；关联表 `data/sample_module_owners.csv`：模块 → 开发团队/QA 负责人。

## 5. 今日资料清单（只看这些）

| 优先级 | 资料 | 怎么看 | 时长 |
| --- | --- | --- | --- |
| 🔴 必读 | pandas 官方《10 minutes to pandas》 https://pandas.pydata.org/docs/user_guide/10min.html | **只看前 1/3**（到 Grouping 之前），边看边在脚本里复现 | 25' |
| 🔴 必做 | 本日 `day01_pandas_core.py` | 逐段跑，每行注释对照理解 | 60' |
| 🟡 选读 | numpy Quickstart「The Basics」 https://numpy.org/doc/stable/user/quickstart.html | 只看 Basics 两节 | 15' |
| ⛔ 不看 | 任何 pandas 视频课 | 官方文档够用，别挤掉动手时间 | 0 |

## 6. 与测试工作的类比（面试要讲）

- `df.info()` 找缺失值 ≈ 测试前的环境检查——先确认数据全不全
- `groupby("module").agg()` ≈ 按模块统计缺陷密度——评测里就是「按场景统计 Bad Case 分布」
- `merge(how="left")` + 校验行数 ≈ 关联用例与缺陷的追踪矩阵——评测里就是「评测集 × 结果」对账，**行数对不上必须查**，这是数据质量意识

## 7. 明日预告

D2 机器学习通识（监督/无监督、训练/验证/测试集、过拟合）+ 梯度下降直觉实验。今天的「训练/验证/测试」概念会成为 D3 评测指标的骨架。
