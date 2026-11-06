# -*- coding: utf-8 -*-
"""Day 18 · 批量调用工程：并发 + 限流 + 断点续跑 + 成本核算
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day04_batch_runner.py --mock
    /Users/zcb/miniconda3/envs/aiml/bin/python day04_batch_runner.py
中断实验：跑批中按 Ctrl+C 杀掉，再原样重跑一次——观察自动跳过已完成条目。
产出：data/day04_batch_results.jsonl（每完成一条立即落盘）
"""

# ============ 导入区 ============
import json                                   # 结果序列化
import os                                     # 环境变量
import sys                                    # --mock
import time                                   # 退避 + 计时
from concurrent.futures import ThreadPoolExecutor, as_completed   # 线程池并发

import requests                               # HTTP
import tiktoken                               # token 计数（成本核算用）

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
api_key = os.environ.get("ZHIPU_API_KEY", "")
MOCK = "--mock" in sys.argv[1:] or not api_key
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # 计划根
OUT_FILE = os.path.join(ROOT, "data", "day04_batch_results.jsonl")   # 结果文件（断点续跑的依据）

# ============ ① 任务集：20 条客服消息 ============
BASE = ["快递多久到", "能开发票吗", "退货流程是什么", "怎么用优惠券", "发票抬头写错了怎么办",
        "之前买的能价保吗", "会员积分怎么兑换", "赠品没收到", "尺码拍错了能换吗", "红包怎么提现",
        "配送费怎么算", "关注店铺有优惠吗", "怎么改收货地址", "积分过期了吗", "会员日是哪天",
        "订单怎么取消", "催发货", "包裹显示签收但没收到", "赠品可以换成别的吗", "拼单怎么操作"]
TASKS = [(f"task_{i:03d}", msg + "？") for i, msg in enumerate(BASE, 1)]   # (任务ID, 输入) 唯一键

# ============ ② 单条执行（重试区分错误类型——401 类不重试） ============
def chat_once(prompt):
    """单次调用，成功返回文本；限流/网络错误抛 Retryable，其他错误抛 Fatal"""
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.2, "max_tokens": 60}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:    # 网络类错误：临时性，可重试
        raise Retryable(str(e))
    if r.status_code == 200:                  # 成功
        body = r.json()
        usage = body.get("usage", {})         # usage 里有 token 统计（真实计费依据）
        return (body["choices"][0]["message"]["content"], usage.get("total_tokens", 0))
    if r.status_code == 429 or r.status_code >= 500:   # 限流/服务端错误：临时性
        raise Retryable(f"HTTP {r.status_code}")
    raise Fatal(f"HTTP {r.status_code}")      # 401/400 等客户端错误：重试无意义

class Retryable(Exception):                    # 可重试错误标记
    pass

class Fatal(Exception):                        # 致命错误标记（不重试）
    pass

def chat_with_retry(prompt, max_retry=3):
    """带指数退避重试：仅对 Retryable 生效"""
    for attempt in range(max_retry):
        try:
            return chat_once(prompt)
        except Retryable as e:                # 临时错误：退避后重试
            if attempt == max_retry - 1:      # 重试耗尽
                raise Fatal(f"重试{max_retry}次仍失败: {e}")
            time.sleep(2 ** attempt)          # 1s→2s→4s 指数退避
    raise Fatal("unreachable")

# ============ ③ 断点续跑：读已完成任务 ID ============
def load_done():
    """读结果文件里已完成任务的 ID 集合——重跑时跳过它们"""
    done = set()
    if os.path.exists(OUT_FILE):              # 文件存在才有历史
        with open(OUT_FILE, encoding="utf-8") as f:
            for line in f:                    # 逐行读 JSONL
                try:
                    done.add(json.loads(line)["task_id"])   # 收集任务 ID
                except (json.JSONDecodeError, KeyError):    # 坏行容忍（崩溃时写一半的行）
                    continue                  # 跳过坏行，不影响续跑
    return done

def process(task):
    """处理单条任务：构造提示词 → 调用 → 返回结果 dict"""
    tid, msg = task
    prompt = f'把消息分类为 投诉/咨询 之一，只输出JSON {{"intent":"..."}}。消息：{msg}'
    if MOCK:                                  # mock：本地生成，无网络（快且可重复）
        time.sleep(0.1)                       # 模拟网络延迟，让并发效果可见
        intent = "投诉" if ("没" in msg or "错" in msg or "催" in msg) else "咨询"
        reply, tokens = f'{{"intent": "{intent}"}}', 0
    else:
        reply, tokens = chat_with_retry(prompt)
    return {"task_id": tid, "input": msg, "output": reply, "tokens": tokens,
            "ts": time.strftime("%H:%M:%S")}   # 时间戳：排查顺序问题用

# ============ ④ 主流程：并发批跑 + 增量落盘 ============
def run(max_workers=4):
    t0 = time.time()                          # 计时起点
    done = load_done()                        # 已完成集合
    todo = [t for t in TASKS if t[0] not in done]   # 过滤已完成——断点续跑核心
    print(f"任务总数 {len(TASKS)}，已完成 {len(done)}（跳过），本次执行 {len(todo)}")
    ok = fail = 0
    total_tokens = 0
    with open(OUT_FILE, "a", encoding="utf-8") as f:   # append 模式：增量追加
        with ThreadPoolExecutor(max_workers=max_workers) as pool:   # 4 线程池
            futures = {pool.submit(process, t): t for t in todo}     # 提交全部任务
            for fut in as_completed(futures):  # 谁先完成先处理谁
                task = futures[fut]
                try:
                    rec = fut.result()         # 取结果
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")   # 立即落盘（不攒内存）
                    f.flush()                  # 强制刷盘：崩溃最多丢当前条
                    ok += 1
                    total_tokens += rec["tokens"]
                    print(f"  ✓ {rec['task_id']} {rec['output'][:24]}")
                except Fatal as e:             # 重试耗尽的失败：记录但不中断整批
                    fail += 1
                    err = {"task_id": task[0], "input": task[1], "error": str(e)}
                    f.write(json.dumps(err, ensure_ascii=False) + "\n")
                    print(f"  ✗ {task[0]} {e}")
    dt = time.time() - t0                      # 耗时
    print(f"\n成功 {ok} / 失败 {fail}｜耗时 {dt:.1f}s｜并发 {max_workers}")
    print(f"  串行估算 ≈ {dt * max_workers:.1f}s（加速比 ≈ {max_workers:.0f}×）")
    print(f"  token 总量 {total_tokens}｜mock 模式不产生费用")
    try:                                       # 成本参考：glm-4-flash 输入约 0.001 元/千token
        if total_tokens:
            print(f"  成本估算 ≈ {total_tokens / 1000 * 0.001:.3f} 元（按 flash 价目，正式以官网为准）")
    except Exception:
        pass

if __name__ == "__main__":
    print(f"运行模式：{'MOCK' if MOCK else MODEL}")
    try:
        run()                                  # 正常执行；Ctrl+C 会打断进入下一行
    except KeyboardInterrupt:                  # 中断实验：故意杀掉进程
        print("\n[中断] 结果已增量落盘——直接重跑本脚本可断点续跑")
        sys.exit(130)
