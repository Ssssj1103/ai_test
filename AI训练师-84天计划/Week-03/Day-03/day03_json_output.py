# -*- coding: utf-8 -*-
"""Day 17 · 结构化输出闭环：生成 → Schema 校验 → 错误回喂重试
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day03_json_output.py --inject    # 故障注入（验证重试闭环）
    /Users/zcb/miniconda3/envs/aiml/bin/python day03_json_output.py --mock      # 无 Key 模拟
    /Users/zcb/miniconda3/envs/aiml/bin/python day03_json_output.py             # 真实跑
设计原则：校验器收集全部错误（不遇错即停），重试时把错误清单塞回提示词——一轮修复。
"""

# ============ 导入区 ============
import json                                   # JSON 编解码
import os                                     # 环境变量
import re                                     # 抠 JSON 块
import sys                                    # 参数开关
import time                                   # 退避

import requests                               # HTTP

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
api_key = os.environ.get("ZHIPU_API_KEY", "")
INJECT = "--inject" in sys.argv[1:]           # 故障注入模式：人为造坏输出验证闭环
MOCK = "--mock" in sys.argv[1:] or not api_key or INJECT   # 注入模式必须走可控输出

# ============ ① Schema 定义（声明式，可读性优先） ============
SCHEMA = {
    "intent":     {"type": str, "enum": ["投诉", "咨询", "开发票", "闲聊"], "required": True},   # 值域=枚举
    "confidence": {"type": float, "min": 0.0, "max": 1.0, "required": True},                     # 值域=区间
    "reason":     {"type": str, "max_len": 50, "required": True},                                # 长度上限
}

def validate(obj):
    """递归校验：收集全部错误（不遇错即停）→ 返回错误清单，空列表=通过"""
    errors = []                                   # 错误收集器
    if not isinstance(obj, dict):                 # 顶层必须 dict
        return ["输出不是 JSON 对象"]
    for field, rule in SCHEMA.items():            # 逐字段检查
        if field not in obj:                      # 缺字段
            if rule["required"]:
                errors.append(f"缺少字段 {field}")
            continue                              # 缺字段就不用查类型了
        val = obj[field]
        if rule["type"] is float:                 # float 特判：int 也算数字（15 和 15.0）
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                errors.append(f"{field} 应为数字，实际 {type(val).__name__}={val!r}")
            elif not (rule["min"] <= val <= rule["max"]):   # 值域检查
                errors.append(f"{field}={val} 超出 [{rule['min']},{rule['max']}]")
        elif not isinstance(val, rule["type"]):   # 其他类型检查
            errors.append(f"{field} 应为 {rule['type'].__name__}，实际 {type(val).__name__}")
        elif "enum" in rule and val not in rule["enum"]:   # 枚举值域
            errors.append(f"{field}={val!r} 不在 {rule['enum']}")
        elif "max_len" in rule and len(val) > rule["max_len"]:   # 长度上限
            errors.append(f"{field} 长度 {len(val)} > {rule['max_len']}")
    return errors                                 # 空=通过

# ============ ② 生成（带错误回喂重试） ============
def chat_real(prompt):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.2, "max_tokens": 120}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    r = requests.post(API_URL, json=payload, headers=headers, timeout=30)   # 单次（重试在外层控制）
    r.raise_for_status()                          # 非 2xx 抛异常
    return r.json()["choices"][0]["message"]["content"]

# 故障注入库：4 类坏输出各一条——不注入故障，重试代码永远验证不到
INJECT_BANK = [                                   # 依次对应 5 条消息（第 5 条正常）
    '好的！这条消息是投诉哦，用户很生气呢。',                       # ① 非 JSON
    '{"intent": "投诉"}',                                           # ② 缺 confidence/reason
    '{"intent": "牢骚", "confidence": 0.8, "reason": "用户在抱怨"}',  # ③ 值不在枚举
    '{"intent": "咨询", "confidence": "很高", "reason": "感觉是"}',   # ④ 类型错误
]
MSG = "东西质量太差了，客服也不理人"               # 本日只深测 1 条消息的完整闭环

def build_prompt(msg, feedback=None):
    """组装提示词；feedback 是上一轮的错误清单，None=首轮"""
    base = ("你是意图分类器。把消息分类为 投诉/咨询/开发票/闲聊 之一。\n"
            f'输出 JSON：{{"intent": "...", "confidence": 0到1的小数, "reason": "一句话理由(≤50字)"}}\n'
            f"消息：{msg}")
    if feedback:                                  # 错误回喂：把错误清单原文塞回去
        return base + f"\n\n你上次的输出存在以下问题，请修正后重新输出完整 JSON：{';'.join(feedback)}"
    return base

def parse_first_json(text):
    """抠第一个 {...} 块——防御层①"""
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group()) if m else None

def run_one(msg):
    """完整闭环：最多 3 轮（首轮 + 2 次重试），返回 (最终对象或None, 轮次记录)"""
    history, feedback = [], None
    for round_no in range(1, 4):                  # 3 轮上限
        if INJECT and round_no <= 2:              # 注入模式：前两轮分别注入不同坏输出（可控实验）
            reply = INJECT_BANK[[0, 2][round_no - 1]]   # 第1轮=非JSON，第2轮=枚举越界
        elif MOCK:
            reply = '{"intent": "投诉", "confidence": 0.9, "reason": "用户抱怨质量与客服"}'  # 模拟正常输出
        else:
            reply = chat_real(build_prompt(msg, feedback))
        obj = parse_first_json(reply)             # 防御层①：抠 JSON
        errors = validate(obj) if obj is not None else ["无法解析出 JSON"]   # 防御层②③④
        history.append((round_no, reply[:40], errors))
        print(f"  第{round_no}轮：{'✓ 通过' if not errors else '✗ ' + '; '.join(errors[:3])}")
        if not errors:                            # 校验通过
            return obj, history
        feedback = errors                         # 错误回喂给下一轮
    return None, history                          # 3 轮都失败：交给上层标记 FAILED

if __name__ == "__main__":
    print(f"运行模式：{'故障注入 INJECT' if INJECT else ('MOCK' if MOCK else MODEL)}")
    print(f"消息：{MSG}")
    result, log = run_one(MSG)                    # 跑完整闭环
    print(f"\n最终结果：{'✗ FAILED(3轮未过)' if result is None else json.dumps(result, ensure_ascii=False)}")
    print("观察点：注入模式下第 1 轮必挂，第 2 轮靠错误回喂修复——这就是闭环的价值")
