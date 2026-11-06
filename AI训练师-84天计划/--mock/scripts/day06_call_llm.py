# -*- coding: utf-8 -*-
"""Day 06 · LLM API 调用工程化 v1：单次调用 → 重试 → 批量实验 → 落盘
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day06_call_llm.py --mock   # 无 Key 也能跑
    /Users/zcb/miniconda3/envs/aiml/bin/python day06_call_llm.py          # 真实调用（需 ZHIPU_API_KEY）
产出：data/day06_temperature_experiment.md（采样对比表，面试作品素材）
"""

# ============ 导入区 ============
import os                                     # 读环境变量（API Key 安全做法）
import sys                                    # 读命令行参数：--mock 开关
import time                                   # sleep：重试退避用
from pathlib import Path                      # 路径处理

import requests                               # HTTP 客户端：调 REST API（比 SDK 更通用，换厂商只改 URL）

ROOT = Path(__file__).resolve().parent.parent.parent       # 项目根：AI训练师-84天计划/
DATA = ROOT / "data"                          # 产物统一落 data/，与 D1-D5 保持一致

# ============ ① 配置加载 ============
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"   # 智谱 OpenAI 兼容端点
MODEL = "glm-4-flash"                         # 免费模型，评测练手零成本
MAX_RETRIES = 3                               # 最多重试 3 次（网络抖动/限流兜底）
TIMEOUT = 30                                  # 单请求超时秒数：不设超时的脚本是定时炸弹

api_key = os.environ.get("ZHIPU_API_KEY", "")   # 从环境变量读 Key——绝不写死在代码里
MOCK = "--mock" in sys.argv[1:]               # 命令行带 --mock 就走模拟模式（无 Key 可跑）

# ============ ② chat()：单次调用 + 重试 + 退避 ============
def chat(messages, temperature=0.7, max_tokens=200):
    """调用 Chat API，返回 (回复文本, token用量)。失败时指数退避重试。"""
    payload = {                               # 请求体：对照文档读懂每个字段
        "model": MODEL,                       # 模型名
        "messages": messages,                 # 对话历史（system 在前，user 在后）
        "temperature": temperature,           # 采样温度：0 确定性 → 1+ 高随机
        "max_tokens": max_tokens,             # 输出上限：成本闸门
    }
    headers = {"Content-Type": "application/json"}   # 请求头
    if api_key:                               # 真实模式才带鉴权
        headers["Authorization"] = f"Bearer {api_key}"   # Bearer Token 标准写法

    for attempt in range(1, MAX_RETRIES + 1): # 最多尝试 MAX_RETRIES 次
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 200:       # 成功
                body = resp.json()            # 解析响应 JSON
                text = body["choices"][0]["message"]["content"]   # 取回复文本
                usage = body.get("usage", {}) # token 用量（无则空字典）
                return text, usage            # 双返回：内容和成本数据
            if resp.status_code == 429:       # 限流：等一等再试（该重试）
                wait = 2 ** attempt           # 指数退避：2s、4s、8s
                print(f"  429 限流，{wait}s 后第 {attempt} 次重试")
                time.sleep(wait)
                continue
            # 400/401 等参数类错误：重试没用，直接抛出（区分错误类型是工程素养）
            resp.raise_for_status()
        except requests.exceptions.Timeout:   # 超时：网络抖动，可重试
            print(f"  超时，第 {attempt} 次重试")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"重试 {MAX_RETRIES} 次仍失败，检查网络/Key/参数")

def mock_chat(messages, temperature=0.7, max_tokens=200):
    """本地模拟响应：无 Key/无网也能跑通全流程结构。分数和文本是假的，仅供结构练习。"""
    user_text = messages[-1]["content"]       # 取最后一条 user 消息
    fake = f"[MOCK·t={temperature}] 关于「{user_text[:12]}…」的模拟回答"   # 造一条假回复
    time.sleep(0.1)                           # 模拟网络延迟，让重试/进度条逻辑真实运转
    return fake, {"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50}

# ============ ③ temperature 实验：3 档 × 3 次 ============
PROMPT = "用一句话解释什么是过拟合。"          # 实验用固定 Prompt：控制变量
def run_experiment():
    """同一 Prompt 在 3 档温度下各跑 3 次，输出对比表（markdown 落盘）"""
    impl = mock_chat if MOCK else chat        # mock 开关决定用哪个实现——其余代码完全复用
    rows = ["| temperature | 第1次 | 第2次 | 第3次 | 一致？ |", "|---|---|---|---|---|"]
    total_tokens = 0                          # 成本统计累计器
    for temp in (0.0, 0.7, 1.5):              # 三档：确定性 / 平衡 / 高随机
        outputs = []                          # 存 3 次输出
        for _ in range(3):                    # 同一参数跑 3 次
            text, usage = impl(               # 调用（真实或 mock）
                [{"role": "system", "content": "你是机器学习老师，回答严格准确。"},
                 {"role": "user", "content": PROMPT}],
                temperature=temp,
            )
            outputs.append(text.replace("\n", " "))   # 换行会破坏表格，替换掉
            total_tokens += usage.get("total_tokens", 0)      # 累加 token
        same = "是" if len(set(outputs)) == 1 else "否"       # set 去重后剩 1 个 = 3 次全同
        rows.append(f"| {temp} | {outputs[0][:30]} | {outputs[1][:30]} | {outputs[2][:30]} | {same} |")
        # 预期：t=0 三次几乎一致；t=1.5 措辞飘忽
    out = DATA / "day06_temperature_experiment.md"            # 实验报告落盘
    out.write_text("\n".join(rows) + f"\n\n总token用量：{total_tokens}\n", encoding="utf-8")
    print(f"③ 实验完成，报告已写入：{out}")
    print(f"   总 token 用量：{total_tokens}（真实模式下据此算成本）")

# ============ ④ 入口 ============
if __name__ == "__main__":                    # 作为主脚本运行时才执行（被 import 时不跑）
    if not api_key and not MOCK:              # 真实模式但没 Key：早失败早提示
        print("未检测到 ZHIPU_API_KEY。两种选择：\n"
              "  1) export ZHIPU_API_KEY=你的key 后重跑\n"
              "  2) python day06_call_llm.py --mock （无 Key 模式）")
        sys.exit(1)                           # 退出码非 0 = 失败，方便脚本化判断
    mode = "MOCK 模拟" if MOCK else f"真实 API（{MODEL}）"
    print(f"① 配置加载完成，当前模式：{mode}")
    if not MOCK:                              # 真实模式先发一条冒烟请求
        text, usage = chat([{"role": "user", "content": "回复'连接正常'四个字"}])
        print(f"② 冒烟测试通过：{text}（用量 {usage.get('total_tokens', '?')} token）")
    run_experiment()                          # 跑主实验
