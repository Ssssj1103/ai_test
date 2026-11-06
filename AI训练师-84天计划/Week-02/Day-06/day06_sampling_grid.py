# -*- coding: utf-8 -*-
"""Day 13 · 采样参数网格实验：temperature × top_p = 3×3 各 3 次
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day06_sampling_grid.py --mock   # 无 Key 模拟
    /Users/zcb/miniconda3/envs/aiml/bin/python day06_sampling_grid.py          # 有 Key 真实跑
产出：data/day06_sampling_grid.md（多样性矩阵 + 观察栏）
指标：每格"3 次输出的去重数"（1=完全一致，3=三次各不同）——多样性本身就是评测指标。
"""

# ============ 导入区 ============
import os                                     # 环境变量
import sys                                    # 参数
import time                                   # 退避
from pathlib import Path                      # 路径

import requests                               # HTTP

ROOT = Path(__file__).resolve().parent.parent.parent       # Day-06 → Week-02 → 计划根
DATA = ROOT / "data"

# ============ ① 配置（复用 W1 D6 / D5 的骨架） ============
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
api_key = os.environ.get("ZHIPU_API_KEY", "")
MOCK = "--mock" in sys.argv[1:] or not api_key       # 无 Key 自动模拟（诚实标注模式）
PROMPT = "用一句话解释什么是 RAG。"             # 固定 Prompt：控制变量
N_REPEAT = 3                                  # 每格跑 3 次看多样性

def chat_real(temperature, top_p):
    """真实调用：参数显式传入并记录——评测脚本必须把参数写死在报告里"""
    payload = {"model": MODEL, "messages": [
        {"role": "user", "content": PROMPT}],
        "temperature": temperature, "top_p": top_p, "max_tokens": 120}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    for attempt in range(3):                  # 3 次重试（27 格跑批，单次失败不能中断）
        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            time.sleep(2 ** attempt)          # 限流退避
        except requests.RequestException:     # 网络异常退避
            time.sleep(2 ** attempt)
    return "[API失败]"                        # 重试耗尽：标记失败而不是崩溃

# 预置模拟输出：按温度档给不同"多样性"——模拟真实行为模式，便于练习记录
MOCK_BANK = {
    0.0: ["RAG 是检索增强生成，先查资料再回答。"],                       # 全部一致
    0.7: ["RAG 是先检索再生成答案的技术。", "RAG 通过外挂知识库来增强大模型回答。",
          "RAG 指检索增强生成：先找资料，再据此作答。"],                 # 措辞不同意思同
    1.5: ["RAG？就是那种先去翻书再回答的 AI 技巧啦！", "检索增强生成（RAG）让模型引用外部文档。",
          "RAG = 检索 + 生成，一种让 AI 少胡说的架构。"],                # 风格发散
}

def chat_mock(temperature, top_p, call_idx):
    """模拟输出：按温度档从预置库轮换取——刻意造出'高温更多样'的格局"""
    import random                             # 局部导入：只在 mock 里需要
    bank = MOCK_BANK[round(temperature, 1)]   # 按温度取候选池
    if round(temperature, 1) == 0.0:          # 低温恒定
        return bank[0]
    return bank[(call_idx + int(top_p * 10)) % len(bank)]   # 高温：随参数与轮次变化

# ============ ② 主实验：3×3 网格 ============
def run():
    temps = [0.0, 0.7, 1.5]                   # 温度轴：确定 / 平衡 / 发散
    top_ps = [0.5, 0.9, 1.0]                  # 截断轴：严 / 中 / 不截断
    lines = ["# 采样参数网格实验（Day13）",
             f"\nPrompt：{PROMPT}｜每格 {N_REPEAT} 次｜模式：{'MOCK' if MOCK else MODEL}",
             "\n| T \\ top_p | " + " | ".join(str(p) for p in top_ps) + " |",
             "|---|" + "---|" * len(top_ps)]
    call_idx = 0                              # 全局调用计数（mock 轮换用）
    for t in temps:                           # 外层温度
        row = [f"| {t}"]
        for p in top_ps:                      # 内层 top_p
            outs = []
            for _ in range(N_REPEAT):         # 每格 3 次
                if MOCK:
                    outs.append(chat_mock(t, p, call_idx))
                else:
                    outs.append(chat_real(t, p))
                call_idx += 1
            uniq = len(set(outs))             # 去重数 = 多样性指标（1~3）
            row.append(f" 去重{uniq}（{outs[0][:12]}…）")
        lines.append(" |".join(row) + " |")
    lines += ["", "## 观察结论（自己填）", "1. ", "2. ",
              "\n> 评测参数规范：分类/裁判任务 T=0~0.2, top_p=1；写作 T≈0.7。评测脚本必须显式记录参数。"]
    out = DATA / "day06_sampling_grid.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"实验完成（{call_idx} 次调用），报告：{out}")
    print("预期规律：T=0 行三格去重=1；T=1.5 行随 top_p 增大发散——对照你的观察栏")

if __name__ == "__main__":
    print(f"运行模式：{'MOCK' if MOCK else f'真实 API（{MODEL}）'}")
    run()
