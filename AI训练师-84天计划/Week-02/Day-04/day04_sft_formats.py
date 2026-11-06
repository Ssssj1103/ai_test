# -*- coding: utf-8 -*-
"""Day 11 · SFT 数据三种格式互转：Alpaca / ShareGPT / OpenAI messages
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day04_sft_formats.py
产出：data/day04_alpaca.jsonl、day04_sharegpt.jsonl、day04_messages.jsonl
W4 造 SFT 数据集时直接复用本文件的转换与校验函数。
"""

# ============ 导入区 ============
import json                                   # JSON 编解码：三种格式都是 JSON 系
from pathlib import Path                      # 路径处理

DATA = Path(__file__).resolve().parent.parent.parent / "data"   # 产物目录：Day-04→Week-02→计划根/data

# ============ ① 源数据：统一中间格式（自设计） ============
# 思路：先定义一份"中立"的中间格式（最完整的表达），再向三种目标格式投影
# 中间格式字段：system(可空) / turns=[{role, content}]（≥1 轮）/ task_type（分类用）
samples = [
    {   # 样本1：单轮知识问答
        "system": "你是电商客服助手，回答简洁准确。",
        "turns": [{"role": "user", "content": "快递一般几天到？"},
                  {"role": "assistant", "content": "默认快递 3-5 天送达，偏远地区 5-7 天。"}],
        "task_type": "单轮问答",
    },
    {   # 样本2：多轮带上下文
        "system": "你是电商客服助手，回答简洁准确。",
        "turns": [{"role": "user", "content": "我买的手机壳到了，但是颜色不对"},
                  {"role": "assistant", "content": "抱歉给您带来不便。请提供订单号，我帮您登记换货。"},
                  {"role": "user", "content": "订单号 20261105001"},
                  {"role": "assistant", "content": "已登记换货申请，1 个工作日内会有专员联系您确认新颜色。"}],
        "task_type": "多轮工单",
    },
    {   # 样本3：带附加输入的改写任务（Alpaca 的 input 字段专门服务这类）
        "system": "",
        "turns": [{"role": "user", "content": "把下面的客服回复改得更委婉：\n『这不是我们的问题，是你自己填错地址了。』"},
                  {"role": "assistant", "content": "非常抱歉，检测到收货地址与实际送达地址不一致。麻烦您核对一下下单时填写的地址，我们协助您联系快递网点处理。"}],
        "task_type": "文本改写",
    },
    {   # 样本4：分类任务
        "system": "",
        "turns": [{"role": "user", "content": "判断这条用户消息的意图（投诉/咨询/闲聊）：\n『快递三天了还没发货，客服也不回消息』"},
                  {"role": "assistant", "content": "投诉"}],
        "task_type": "意图分类",
    },
]
print(f"① 源数据：{len(samples)} 条（覆盖 {', '.join(sorted(set(s['task_type'] for s in samples)))}）")

# ============ ② 中间格式 → Alpaca ============
def to_alpaca(samples):
    """Alpaca：instruction 指令 / input 附加输入 / output 期望输出。
    限制：只能表达'单轮'——多轮样本只能压缩最后一问一答（信息有损，这是 Alpaca 的硬伤）"""
    rows = []
    for s in samples:
        user_turns = [t for t in s["turns"] if t["role"] == "user"]      # 所有用户轮
        bot_turns = [t for t in s["turns"] if t["role"] == "assistant"]  # 所有助手轮
        instruction = s["system"] or "根据用户消息作出得体回复。"          # system 并入 instruction
        instruction += "\n" + user_turns[-1]["content"]                  # 取最后一问（简化处理）
        # 若最后一条用户消息里有"改写：xxx"式的附加内容，可拆到 input；教学简化不拆
        rows.append({"instruction": instruction.strip(), "input": "",
                     "output": bot_turns[-1]["content"]})                # 最后一答
    return rows

# ============ ③ 中间格式 → ShareGPT ============
def to_sharegpt(samples):
    """ShareGPT：conversations 数组，from 取值 human/gpt/system（多轮原样保留）"""
    role_map = {"user": "human", "assistant": "gpt", "system": "system"}   # 角色名映射
    rows = []
    for s in samples:
        conv = [{"from": role_map[t["role"]], "value": t["content"]} for t in s["turns"]]   # 逐轮映射
        rows.append({"conversations": conv})
    return rows

# ============ ④ 中间格式 → OpenAI messages ============
def to_messages(samples):
    """messages：role 取值 system/user/assistant，API 事实标准"""
    rows = []
    for s in samples:
        msgs = []
        if s["system"]:                       # system 存在才放（可为空）
            msgs.append({"role": "system", "content": s["system"]})
        msgs += [{"role": t["role"], "content": t["content"]} for t in s["turns"]]   # 多轮原样
        rows.append({"messages": msgs})
    return rows

# ============ ⑤ 写 JSONL + schema 校验 ============
def dump_jsonl(rows, path):
    """写 JSONL：每行一个独立 JSON 对象（训练数据标准格式）"""
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:                        # 逐条写行
            f.write(json.dumps(r, ensure_ascii=False) + "\n")   # ensure_ascii=False 保中文可读
    print(f"已写出 {len(rows)} 条 → {path.name}")

def validate(rows, fmt):
    """schema 校验：交付前的契约检查——一条格式错，训练框架整批报错"""
    rules = {"alpaca": set("instruction input output".split()),        # 必需字段
             "sharegpt": {"conversations"}, "messages": {"messages"}}
    ok = 0
    for i, r in enumerate(rows):              # 逐条检查
        missing = rules[fmt] - set(r)         # 缺哪些必需字段
        if missing:                           # 有缺失立即报告（fail fast）
            print(f"  ✗ [{fmt}] 第{i+1}条缺字段：{missing}")
        else:
            ok += 1
    print(f"校验 {fmt}：{ok}/{len(rows)} 通过")

if __name__ == "__main__":
    a, g, m = to_alpaca(samples), to_sharegpt(samples), to_messages(samples)   # 三格式全转
    dump_jsonl(a, DATA / "day04_alpaca.jsonl")     # 落盘三份
    dump_jsonl(g, DATA / "day04_sharegpt.jsonl")
    dump_jsonl(m, DATA / "day04_messages.jsonl")
    validate(a, "alpaca"); validate(g, "sharegpt"); validate(m, "messages")    # 全部校验
    print("\n观察点：样本2（多轮）在 Alpaca 里丢了中间轮次——这就是'多轮必须用对话格式'的实证")
