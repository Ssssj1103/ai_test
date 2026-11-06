# -*- coding: utf-8 -*-
"""Day 19 · 多轮对话管理器：历史维护 + Token 预算 + 三种截断策略
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day05_multiturn.py
不调 API（纯本地逻辑实验）：构造 30 轮长对话，对比三种截断策略的保留/丢失行为。
关键实验：第 1 轮的关键信息（订单号）在滑窗策略下丢失——实证"截断丢上下文"。
"""

# ============ 导入区 ============
import tiktoken                               # token 计数：预算管理的标尺

enc = tiktoken.get_encoding("cl100k_base")    # GPT 系编码；国产模型字节数略异，但量级一致

def ntok(text):
    """数一段文本的 token 数——所有预算计算的基本单元"""
    return len(enc.encode(text))

# ============ ① Conversation 类：对话状态管理器 ============
class Conversation:
    """维护 messages 列表。核心认知：'多轮记忆'就是调用方手里的这个列表"""

    def __init__(self, system, budget=200):
        self.system = system                  # 系统提示词（永不截掉的"宪法"）
        self.budget = budget                  # 历史可用的 token 预算（教学值调小便于触发截断）
        self.turns = []                       # [(user, assistant), ...] 历史轮次

    def add(self, user, assistant):
        """追加一轮对话"""
        self.turns.append((user, assistant))

    def history_tokens(self):
        """当前历史的总 token 数"""
        return sum(ntok(u) + ntok(a) for u, a in self.turns)

    def build(self, strategy="window", keep_n=10):
        """按策略组装要发送的 messages——三种截断策略的实现"""
        msgs = [{"role": "system", "content": self.system}]   # system 恒在最前
        if strategy == "window":              # 策略1 滑窗：只留最近 keep_n 轮
            kept = self.turns[-keep_n:]       # 切片取尾部
            dropped = len(self.turns) - len(kept)
        elif strategy == "head_tail":         # 策略2 保头保尾：第1轮 + 最近轮（预算内）
            kept = [self.turns[0]]            # 头部固定保留（关键设定常在第1轮）
            rest = self.turns[1:]
            for t in reversed(rest):          # 从最新往回装，直到预算用完
                cost = ntok(t[0]) + ntok(t[1])
                if self._used(kept) + cost <= self.budget:
                    kept.append(t)            # 预算内：保留
            kept = [self.turns[0]] + kept[1:][::-1]   # 恢复时间顺序（去头再反转）
            dropped = len(self.turns) - len(kept)
        else:
            raise ValueError(f"未知策略 {strategy}")   # fail fast：策略名写错立即报
        for u, a in kept:                     # 把保留的轮次展开成 messages 格式
            msgs.append({"role": "user", "content": u})
            msgs.append({"role": "assistant", "content": a})
        return msgs, dropped                  # dropped=被截掉的轮数（要显式报告）

    def _used(self, kept):
        """计算一组轮次的 token 占用（策略2 里反复用）"""
        return sum(ntok(u) + ntok(a) for u, a in kept)

# ============ ② 构造 30 轮长对话（第 1 轮埋关键信息） ============
def build_long_conversation():
    """30 轮对话：第 1 轮含订单号（关键信息），后面是日常闲聊填充"""
    conv = Conversation(system="你是电商客服助手。", budget=600)
    conv.add("我的订单号是 A2026110900123，帮我查下到哪了",   # ★关键信息：只出现这一次
             "您的订单 A2026110900123 正在派送中。")
    for i in range(2, 31):                    # 29 轮填充对话（推挤历史长度）
        conv.add(f"顺便问下，你们第{i}号活动的规则是什么", f"第{i}号活动是满减，满{i*10}减{i}。")
    return conv

# ============ ③ 三策略对比 + 关键信息实验 ============
def show(msgs, name, dropped):
    """打印一次组装结果的概况"""
    total = sum(ntok(m["content"]) for m in msgs)   # 本次发送的总 token
    first_user = next((m["content"] for m in msgs if m["role"] == "user"), "")   # 第一条用户消息
    has_key = "A2026110900123" in "".join(m["content"] for m in msgs)   # 关键信息还在吗
    print(f"\n【{name}】发送 {len(msgs)} 条消息 / {total} tokens / 截掉 {dropped} 轮")
    print(f"  关键信息（订单号）{'✓ 保留' if has_key else '✗ 丢失'}")
    return has_key

if __name__ == "__main__":
    conv = build_long_conversation()          # 30 轮长对话
    print(f"① 长对话构造完成：{len(conv.turns)} 轮，历史共 {conv.history_tokens()} tokens"
          f"（预算 {conv.budget}）")

    key_results = {}                          # 各策略的关键信息保留情况
    for name, strategy, kw in [("滑窗 keep_n=10", "window", {"keep_n": 10}),
                               ("滑窗 keep_n=6", "window", {"keep_n": 6}),
                               ("保头保尾", "head_tail", {})]:
        msgs, dropped = conv.build(strategy, **kw)   # 按策略组装
        key_results[name] = show(msgs, name, dropped)

    print("\n② 关键信息实验结论：")
    for name, ok in key_results.items():      # 逐策略报告
        print(f"  {name}：{'第30轮再问订单号能答对' if ok else '第30轮再问订单号必然答错——截断丢上下文的实证'}")
    print("\n③ Token 预算公式：可用历史 = 窗口 − system − 本轮输入 − max_tokens(预留输出)")
