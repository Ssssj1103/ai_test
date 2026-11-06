# -*- coding: utf-8 -*-
"""Day 07 · GitHub 作品仓库初始化：一键搭骨架 + 生成本周归档 + 输出 git 命令
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day07_repo_init.py ~/ai-trainer-journey
说明：本脚本只创建本地仓库目录和文件；push 到 GitHub 的命令最后会打印出来，手动执行。
"""

# ============ 导入区 ============
import shutil                                 # 文件复制用：归档本周产出
import subprocess                             # 调用外部命令：git diff --stat 统计
import sys                                    # 读命令行参数
from pathlib import Path                      # 路径处理

PLAN_ROOT = Path(__file__).resolve().parent.parent.parent   # 计划根目录（84天计划/）
WEEK1 = PLAN_ROOT / "Week-01"                 # 本周目录

# ============ ① 解析目标目录并创建骨架 ============
target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "ai-trainer-journey"   # 默认 ~/ai-trainer-journey
if target.exists():                           # 已存在则不覆盖，防误删
    print(f"目录已存在，跳过创建：{target}")
else:                                         # 首次运行
    for sub in ("notes", "scripts", "datasets", "reports", "flashcards"):   # 五大目录
        (target / sub).mkdir(parents=True)    # parents=True 连父目录一起建
    print(f"① 仓库骨架已创建：{target}")

# ============ ② 生成 README（仓库门面 = 简历第一屏） ============
readme = """# AI 训练师转行学习仓（软件测试 → LLM 评测）

> 12 周 / 84 天系统学习：LLM 原理 → Prompt 工程 → 数据标注与 SFT → 评测体系 → RAG → LoRA 微调
> 背景：软件测试工程师，主打「测试思维 → 模型评测」的能力迁移。

## 目录
- `notes/` 每周学习笔记（含实验记录）
- `scripts/` 可运行脚本（全部逐行注释）
- `datasets/` 自建数据集（SFT/评测集）
- `reports/` 评测报告、质检报告
- `flashcards/` 面试问答卡片

## 进度
- [x] Week 1：LLM 原理速通 + Python 数据栈（pandas/指标/神经网络直觉/API 调用）
- [ ] Week 2：Transformer 与幻觉（进行中）
"""
readme_path = target / "README.md"            # README 路径
if not readme_path.exists():                  # 不覆盖已有 README
    readme_path.write_text(readme, encoding="utf-8")   # 写入门面文件
    print("② README.md 已生成")

# ============ ③ 归档本周产出（脚本 → scripts/，报告 → reports/） ============
copied = 0                                    # 计数器
for day_dir in sorted(WEEK1.glob("Day-*")):   # 遍历 Day-01..07
    for py in day_dir.glob("*.py"):           # 每个 .py 脚本
        shutil.copy2(py, target / "scripts" / py.name)   # copy2 保留元数据
        copied += 1
for report in PLAN_ROOT.glob("data/day0*.md"):   # data/ 下的实验报告
    shutil.copy2(report, target / "reports" / report.name)
    copied += 1
print(f"③ 已归档 {copied} 个产出文件到仓库")

# ============ ④ 生成 LLM 基础卡片 v1 模板（内容自己填，来自本周笔记） ============
card = target / "flashcards" / "llm-basics-v1.md"
if not card.exists():                         # 只生成一次
    card.write_text("""# LLM 基础卡片 v1（Week 1 产出）

## Q1: 为什么神经网络需要非线性激活函数？
**30 秒版**：（用自己的话填，引用圆圈分类实验：去掉 tanh 准确率从 __% 掉到 __%）
**追问预备**：tanh/ReLU/GELU 区别？（W2 补）

## Q2: 训练集/验证集/测试集为什么要分开？
**30 秒版**：
**追问预备**：评测集污染是什么？（W6 补）

## Q3: 精确率和召回率的取舍？
**30 秒版**：
**追问预备**：F1 什么时候失真？（W6 补）

## Q4: LLM 训练四阶段各自喂什么数据？
**30 秒版**：
**追问预备**：SFT 数据规模一般多大？（W4 补）

## Q5: 为什么大模型会幻觉？
**30 秒版**：
**追问预备**：怎么量化幻觉率？（W6 补）

## Q6: 怎么保证模型评测可复现？
**30 秒版**：
**追问预备**：temperature=0 为什么也不完全确定？
""", encoding="utf-8")
    print("④ 卡片模板已生成：flashcards/llm-basics-v1.md（按本周笔记填充）")

# ============ ⑤ 输出 git 命令清单（手动执行） ============
commands = [
    f"cd {target}",
    "git init -b main",
    "git add -A",
    'git commit -m "Add week1: pandas metrics neural net LLM basics"',
]
try:                                          # 统计本周代码量（报告用，失败不影响）
    diff = subprocess.run(                    # 调 git diff --stat 统计行数
        ["git", "diff", "--stat", "HEAD"], cwd=str(target),
        capture_output=True, text=True, timeout=10,
    )
except Exception:                             # git 不可用等
    pass
print("⑤ 依次执行以下命令完成首次提交与推送：")
for c in commands:                            # 逐条打印
    print(f"  {c}")
print("  # GitHub 上新建空仓库后：")
print(f"  git remote add origin git@github.com:你的用户名/{target.name}.git")
print("  git push -u origin main")
print("\n完成标准：GitHub 页面能看到 README 渲染 + scripts/ 下 7 个脚本 + 绿点亮起")
