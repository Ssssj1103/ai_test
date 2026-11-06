# -*- coding: utf-8 -*-
"""Day 16 · Few-shot 三变量实验：示例数量（0/1/3）× 示例选择（简单/难例）× 顺序
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day02_few_shot.py --mock
    /Users/zcb/miniconda3/envs/aiml/bin/python day02_few_shot.py
核心思想：few-shot 的"教学效果"可以用准确率量化——示例是提示词工程里最像"造数据"的动作。
"""

# ============ 导入区 ============
import json                                   # 解析输出
import os                                     # 环境变量
import re                                     # 抠 JSON 块
import sys                                    # --mock
import time                                   # 退避

import requests                               # HTTP

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
api_key = os.environ.get("ZHIPU_API_KEY", "")
MOCK = "--mock" in sys.argv[1:] or not api_key

# ============ ① 数据：6 条测试消息 + 人工标注的期望意图（对照标准） ============
TEST = [                                      # (消息, 期望意图)。后 2 条是边界难例
    ("物流太慢了，一周了还没到", "投诉"),
    ("支持七天无理由退货吗", "咨询"),
    ("怎么申请价保", "咨询"),
    ("再不发货我就去平台投诉你们", "投诉"),
    ("这个手机壳是硅胶的吗，能退吗", "咨询"),   # 难例1：商品咨询里混退货诉求
    ("你们这是欺诈，我要投诉并且要求赔偿", "投诉"),   # 难例2：投诉+赔偿，测粒度
]

# ============ ② 示例库：简单例 × 难例 ============
SHOT_SIMPLE = [("发货太慢了，气死了", "投诉")]           # 1-shot 用：简单情绪化投诉
SHOTS_3 = [                                   # 3-shot 用：覆盖 2 类 + 难例压轴（顺序原则）
    ("东西还没收到", "咨询"),
    ("客服一直不回消息，太差劲了", "投诉"),
    ("商品有质量问题，我要投诉并退货", "投诉"),   # 边界难例：投诉里带其他诉求，判主意图
]

def build_prompt(msg, shots):
    """按 R-T-C-F-E 组装提示词，shots 是 (消息, 意图) 示例列表（可空）"""
    parts = ["你是电商客服系统的意图分类器。把用户消息分类为：投诉 或 咨询。",
             "约束：只依据文本；不要解释；只输出 JSON {\"intent\": \"...\"}。"]
    for ex_msg, ex_intent in shots:           # few-shot 示例段
        parts.append(f'示例：{ex_msg} → {{"intent": "{ex_intent}"}}')
    parts.append(f'用户消息：{msg}')           # 待分类消息放最后（生成位置就近）
    return "\n".join(parts)                   # 拼成完整提示词

# ============ ③ 调用与解析（复用 D1 的防御式解析） ============
def chat_real(prompt):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.2, "max_tokens": 60}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    for attempt in range(2):
        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            time.sleep(2 ** attempt)
        except requests.RequestException:
            time.sleep(2 ** attempt)
    return "[API失败]"

# mock 输出：0-shot 刻意错边界题，1-shot 错 1 题，3-shot 全对——模拟"示例越多越准"的趋势
MOCK_TABLE = {0: ["投诉", "咨询", "咨询", "投诉", "投诉", "咨询"],   # 0-shot：难例1、2 判错
              1: ["投诉", "咨询", "咨询", "投诉", "投诉", "投诉"],   # 1-shot：难例2 对了
              2: ["投诉", "咨询", "咨询", "投诉", "咨询", "投诉"]}   # 3-shot：难例1 也对

def extract_intent(reply):
    """从回复抠意图：先 JSON 再正则兜底"""
    m = re.search(r'"intent"\s*:\s*"([^"]+)"', reply)   # 直接找 intent 字段值
    if m:
        return m.group(1)                     # 命中返回
    return reply.strip()[:10]                 # 兜底：前 10 字符（必然解析失败计入错）

# ============ ④ 三组对照实验 ============
def run_config(name, shots, mock_key):
    """跑一个配置：统计准确率 + 逐条对错"""
    correct = 0
    print(f"\n{name}：")
    for i, (msg, expect) in enumerate(TEST):  # 逐条测试
        prompt = build_prompt(msg, shots)     # 组装提示词
        reply = MOCK_TABLE[mock_key][i] if MOCK else chat_real(prompt)
        pred = extract_intent(reply)          # 抽取预测
        hit = pred == expect                  # 与人工标注对照
        correct += hit
        flag = "✓" if hit else f"✗(判成{pred})"
        print(f"  {flag} {msg[:14]}…  期望={expect}")
    acc = correct / len(TEST)                 # 准确率
    print(f"  → 准确率：{correct}/{len(TEST)} = {acc:.0%}")
    return acc

if __name__ == "__main__":
    print(f"运行模式：{'MOCK' if MOCK else MODEL}")
    a0 = run_config("① 0-shot（无示例）", [], 0)
    a1 = run_config("② 1-shot（1 个简单例）", SHOT_SIMPLE, 1)
    a3 = run_config("③ 3-shot（覆盖 2 类 + 难例压轴）", SHOTS_3, 2)
    print(f"\n④ 结论：{a0:.0%} → {a1:.0%} → {a3:.0%}")
    print("   示例的增量价值集中在边界难例——这决定了 W4 标注集里难例必须占一定比例")
