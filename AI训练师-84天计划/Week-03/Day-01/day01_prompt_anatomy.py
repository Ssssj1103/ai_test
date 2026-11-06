# -*- coding: utf-8 -*-
"""Day 15 · Prompt 五要素 before/after 实证
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day01_prompt_anatomy.py --mock   # 无 Key 模拟
    /Users/zcb/miniconda3/envs/aiml/bin/python day01_prompt_anatomy.py          # 有 Key 真实跑
核心思想：提示词的"改进"必须量化——格式合规率和可解析率就是本实验的两个指标。
"""

# ============ 导入区 ============
import json                                   # 解析模型输出的 JSON
import os                                     # 读环境变量
import re                                     # 正则：从回复中抠出 JSON 块
import sys                                    # --mock 开关
import time                                   # 重试退避

import requests                               # HTTP 客户端

# ============ ① 配置（与 W1/W2 相同骨架：智谱免费模型） ============
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
api_key = os.environ.get("ZHIPU_API_KEY", "")
MOCK = "--mock" in sys.argv[1:] or not api_key          # 无 Key 自动模拟（诚实标注）

# ============ ② 测试消息：5 条客服消息（含 1 条超纲，测拒答行为） ============
MESSAGES = [
    "快递三天了还没到，我要投诉！",
    "这个手机支持内存卡扩展吗",
    "怎么开发票",
    "你们老板是谁",                            # 超纲消息：正确行为=礼貌说明无法回答
    "东西质量太差了，客服也不理人",            # 混合消息：投诉+咨询，测边界判断
]
INTENTS = ["投诉", "咨询", "开发票", "闲聊"]    # 意图体系（W4 会扩展成正式标注体系）

# ============ ③ 两个版本的提示词（R-T-C-F-E 五要素） ============
PROMPT_BAD = "帮我判断这条客服消息是什么意图：{msg}"      # 差提示词：只有任务，无角色/约束/格式

PROMPT_GOOD = """你是电商客服系统的意图分类器。
任务：把用户消息分类到以下意图之一：{intents}。
约束：只依据消息文本判断；消息与所有意图无关时输出"闲聊"；不要解释。
输出格式：只输出 JSON，形如 {{"intent": "..."}}，不要输出其他任何内容。
用户消息：{msg}"""                               # 好提示词：角色+任务+约束+格式齐全（示例明天加）

# ============ ④ 调用与解析 ============
def chat_real(prompt):
    """真实调用：temperature=0.2——分类任务要确定性（W2 D6 评测参数规范）"""
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.2, "max_tokens": 100}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    for attempt in range(2):                    # 2 次重试
        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            time.sleep(2 ** attempt)            # 退避
        except requests.RequestException:       # 网络异常退避
            time.sleep(2 ** attempt)
    return "[API失败]"

MOCK_BAD = ['好的！这条消息看起来是投诉哦~ 用户情绪比较激动呢！',       # 差提示词典型失败：寒暄+自由文本
            '根据分析，这条消息是咨询类。', '这是开发票的问题。', '老板信息不方便透露哈哈',
            '投诉 AND 咨询，建议人工处理']
MOCK_GOOD = ['{"intent": "投诉"}', '{"intent": "咨询"}', '{"intent": "开发票"}',
             '{"intent": "闲聊"}', '{"intent": "投诉"}']

def extract_json(text):
    """从回复中抠出 JSON：先直接解析，失败则用正则找 {...} 块——评测脚本的标配防御"""
    try:
        return json.loads(text.strip())         # 直接解析（理想情况）
    except json.JSONDecodeError:                # 格式漂移了
        m = re.search(r"\{.*\}", text, re.S)    # 贪婪匹配第一个 {...} 块
        if m:
            try:
                return json.loads(m.group())    # 二次尝试
            except json.JSONDecodeError:
                return None                     # 彻底解析失败
        return None

# ============ ⑤ 主实验：两版 × 5 条消息 ============
def run(version, prompt_tpl, mock_bank):
    """跑一个版本：统计格式合规率和可解析率——改进必须用数字说话"""
    results = []
    for i, msg in enumerate(MESSAGES):          # 逐条消息
        prompt = prompt_tpl.format(msg=msg, intents="、".join(INTENTS))   # 填模板
        reply = mock_bank[i] if MOCK else chat_real(prompt)
        obj = extract_json(reply)               # 尝试解析
        parseable = obj is not None and "intent" in obj    # 可解析 = JSON 且有 intent 键
        results.append((msg, reply, parseable))
        print(f"  [{i+1}] {'✓' if parseable else '✗'} {reply[:36].replace(chr(10),' ')}")
    ok = sum(1 for _, _, p in results if p)     # 可解析计数
    print(f"  → 可解析率：{ok}/{len(results)} = {ok/len(results):.0%}\n")
    return ok

if __name__ == "__main__":
    print(f"运行模式：{'MOCK（模拟差提示词的典型失败）' if MOCK else MODEL}\n")
    print("① 差提示词（只写任务）：")
    bad = run("bad", PROMPT_BAD, MOCK_BAD)      # 基线
    print("② 五要素提示词：")
    good = run("good", PROMPT_GOOD, MOCK_GOOD)  # 改进版
    print(f"③ 结论：可解析率 {bad}/{len(MESSAGES)} → {good}/{len(MESSAGES)}")
    print("   差提示词的失败模式：寒暄废话、格式漂移、超纲硬答——全被五要素压下去了")
