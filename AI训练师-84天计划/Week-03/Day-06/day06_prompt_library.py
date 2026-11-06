# -*- coding: utf-8 -*-
"""Day 20 · Prompt 模板库 v1：10 个入库级模板 + 渲染器 + 结构自检
运行方式：
    /Users/zcb/miniconda3/envs/aiml/bin/python day06_prompt_library.py
产出：data/prompt_library_v1.md（六段结构的提示词库文档，直接进 GitHub 作品集）
入库标准：场景/模板/设计理由/效果数据/失败边界/参数建议 六段齐全。
"""

# ============ 导入区 ============
import re                                     # 正则：提取模板里的 {变量}
from datetime import date                     # 库的版本日期

# ============ ① 模板库：每个条目 = 六段结构 ============
LIBRARY = [
    {
        "name": "意图分类器", "scene": "电商客服消息分类（投诉/咨询/开发票/闲聊）",
        "template": ("你是电商客服系统的意图分类器。\n"
                     "任务：把用户消息分类到：{intents}。\n"
                     "约束：只依据文本；与所有意图无关时输出\"闲聊\"；不要解释。\n"
                     "示例：发货太慢了气死了 → {{\"intent\": \"投诉\"}}\n"
                     "输出：只输出 JSON {{\"intent\": \"...\"}}。\n"
                     "用户消息：{msg}"),
        "why": "五要素齐全（D15）；1-shot 简单例锚定格式（D16 数据 67%→83%）",
        "evidence": "可解析率 0%→100%（D15 before/after，n=5）；3-shot 准确率 100%（D16，n=6）",
        "failure": "混合意图消息只判主意图；类别超过 4 个时需增加示例与枚举说明",
        "params": "temperature=0.2, top_p=1, max_tokens=60",
    },
    {
        "name": "拒答守卫版分类器", "scene": "需要'无法判断'出口的场景，防边界硬答",
        "template": ("你是意图分类器。类别：{intents}。\n"
                     "若消息信息不足或跨类别无法判定主意图，输出 {{\"intent\": \"无法判断\", \"reason\": \"...\"}}。\n"
                     "只输出 JSON。消息：{msg}"),
        "why": "给模型体面退出路径 → 降编造（W2 D5 幻觉实验的缓解手段）",
        "evidence": "边界题硬答率显著下降（W2 D5 诱导实验口径）",
        "failure": "拒答阈值难调：过松=大量无法判断，过紧=形同虚设",
        "params": "temperature=0.2, max_tokens=80",
    },
    {
        "name": "结构化抽取", "scene": "从客服对话抽取订单号/问题类型/诉求字段",
        "template": ("你是信息抽取器。从下面对话抽取字段，输出 JSON："
                     "{{\"order_id\": \"字符串或null\", \"issue\": \"...\", \"demand\": \"...\"}}\n"
                     "约束：字段不存在时用 null，禁止编造。对话：{dialog}"),
        "why": "显式允许 null → 防'硬凑字段值'（幻觉的另一种形态）",
        "evidence": "null 出口使编造字段显著减少（W2 D5 任务超纲类缓解）",
        "failure": "对话含多个订单号时只取一个；需在业务侧定义取哪个",
        "params": "temperature=0.2, max_tokens=120",
    },
    {
        "name": "保事实摘要", "scene": "长客服工单摘要，给人工复核用",
        "template": ("你是摘要助手。输出一段 ≤{n} 字的对话摘要，要求：保留订单号/金额/时间等事实，"
                     "不添加对话中没有的信息。\n对话：{dialog}"),
        "why": "'不添加'约束压制摘要幻觉；字数约束控制输出成本",
        "evidence": "人工抽检事实错误率低（W2 D5 判定纪律沿用：先定抽检标准）",
        "failure": "对话极长（>窗口一半）时需先分段摘要再汇总（map-reduce）",
        "params": "temperature=0.3, max_tokens=200",
    },
    {
        "name": "情感与强度打分", "scene": "用户情绪监测（1-5 分），预警升级人工",
        "template": ("你是情绪评分器。给消息的情绪强度打 1-5 分（5=极度愤怒）。\n"
                     "约束：只依据文本语气评分，不考虑标点多少。\n"
                     "示例：'等了三天了？？？？' → 4\n"
                     "只输出 JSON {{\"score\": 数字, \"trigger\": \"是否需人工, true/false\"}}。\n消息：{msg}"),
        "why": "few-shot 锚定分数粒度；结构化输出供规则引擎消费",
        "evidence": "打分任务低温保证可复现（D17 评测参数纪律）",
        "failure": "反讽/阴阳怪气易判低分——需人工抽检 5% 校准",
        "params": "temperature=0.2, max_tokens=40",
    },
    {
        "name": "数据清洗助手", "scene": "标注语料的规范化（错别字/全半角/冗余空白）",
        "template": ("你是文本清洗助手。清洗下面的文本：修正错别字、统一全半角、去除冗余空白和表情。\n"
                     "约束：不改变语义；不确定的修正保持原样并列出。\n"
                     "输出 JSON {{\"clean\": \"...\", \"uncertain\": [\"...\"]}}。文本：{text}"),
        "why": "uncertain 列表=主动上报不确定项，符合质检口径（宁可标注存疑不可静默改错）",
        "evidence": "清洗可解释、可抽查（W4 清洗流水线的前置组件）",
        "failure": "行业术语可能被'纠正'成常用词——需提供术语白名单",
        "params": "temperature=0.1, max_tokens=300",
    },
    {
        "name": "标注规范问答", "scene": "让模型按规范文档回答标注员的问题（W4 配套）",
        "template": ("你是标注规范助手。仅依据下面的规范回答，规范未覆盖时回答'规范未覆盖，请提交仲裁'。\n"
                     "规范：{rules}\n问题：{question}"),
        "why": "限定知识来源+未覆盖出口 → 防规范问答幻觉（RAG 思想的最小实现，W7 展开）",
        "evidence": "越界问题拒答率可测（诱导规范外问题即 W2 D5 方法复用）",
        "failure": "规范文档太长需分段检索（引出 W7 RAG）",
        "params": "temperature=0.2, max_tokens=200",
    },
    {
        "name": "评测裁判", "scene": "给模型回答按细则打分（W6 LLM-as-Judge 预演）",
        "template": ("你是评测裁判。按细则给回答打 1-5 分。\n细则：{rubric}\n问题：{q}\n回答：{answer}\n"
                     "约束：严格按细则评分，回答长度不影响分数。\n"
                     "只输出 JSON {{\"score\": 1-5整数, \"issues\": [\"...\"]}}。"),
        "why": "issues 字段强制给理由 → 分数可归因（W6 归因分析的基础）",
        "evidence": "裁判波动性必须实测：同输入跑 3 次看一致性（D6 多样性方法复用）",
        "failure": "裁判偏好长回答（长度偏差）——细则里显式声明'长度不影响分数'",
        "params": "temperature=0~0.2（必须低温）, max_tokens=100",
    },
    {
        "name": "多轮指代消解", "scene": "追问里'它/那个'指什么（W6 多轮评测预演）",
        "template": ("你是多轮对话助手。回答最后的问题；若'它/那个'等指代不明确，先指出指代对象再回答。\n"
                     "对话：{history}\n最后问题：{question}"),
        "why": "强制先解指代 → 输出可检查（把'理解过程'显性化）",
        "evidence": "历史完整性是多轮评测红线（D5 关键信息实验：滑窗丢订单号实证）",
        "failure": "历史被截断时指代必错——调用方须保证保头保尾策略",
        "params": "temperature=0.2, max_tokens=150",
    },
    {
        "name": "SFT 样本生成器", "scene": "造 SFT 数据的对话样本（W4 造数据的辅助）",
        "template": ("模拟一条电商客服对话（2-3 轮），主题：{topic}，用户语气：{tone}。\n"
                     "输出 JSON {{\"turns\": [{{\"role\": \"user\", \"content\": \"...\"}}, ...]}}。\n"
                     "约束：对话必须自然，不要出现'作为AI'等出戏表述。"),
        "why": "变量化批量生成 → 数据增强；JSON 结构 = 直接可入库格式（D3 闭环消费）",
        "evidence": "生成样本必须 100% 人工审核后才可入训练集（质检纪律）",
        "failure": "生成样本同质化（句式趋同）——需多样化 topic/tone 组合并去重",
        "params": "temperature=0.8（生成任务可高温）, max_tokens=400",
    },
]

# ============ ② 渲染器：变量填充 + fail fast ============
def render(tpl_text, **vars):
    """填充 {变量}；缺变量直接抛错（fail fast：残缺提示词不许出厂）"""
    return tpl_text.format(**vars)            # 缺变量时 KeyError 自然抛出，信息含变量名

# ============ ③ 结构自检：库的"静态检查" ============
def audit(entry):
    """检查六段是否齐全 + 模板五要素（关键词等价类匹配）+ 效果数据非空。返回错误清单"""
    errs = []
    for k in ("name", "scene", "template", "why", "evidence", "failure", "params"):
        if not entry.get(k):                    # 任何一段缺失
            errs.append(f"缺段落 {k}")
    tpl = entry.get("template", "")
    checks = [                                  # 五要素的等价关键词类（一种表达即可）
        (("你是", "模拟", "作为"), "角色"),
        (("输出", "回答", "打"), "格式"),
        (("约束", "不要", "禁止", "仅依据", "不添加", "不改变", "必须", "若"), "约束"),
    ]
    for kws, hint in checks:
        if not any(k in tpl for k in kws):      # 一种都没命中才算缺
            errs.append(f"模板缺{hint}要素关键词")
    if "..." in entry.get("evidence", "") or not entry.get("evidence"):
        errs.append("效果数据为空或含占位符（不许编数字）")
    return errs

# ============ ④ 主流程：自检全部 + 导出 markdown ============
if __name__ == "__main__":
    print("① 库结构自检：")
    passed = 0
    for i, e in enumerate(LIBRARY, 1):         # 逐条自检
        errs = audit(e)
        passed += not errs
        print(f"  [{'✓' if not errs else '✗ ' + ';'.join(errs)}] {e['name']}")
    print(f"  自检通过 {passed}/{len(LIBRARY)}")

    # 渲染冒烟测试：抽 1 个模板填变量看能不能出完整提示词
    demo = render(LIBRARY[0]["template"], intents="投诉、咨询、开发票、闲聊", msg="怎么开发票")
    print(f"\n② 渲染冒烟测试（模板1）：\n---\n{demo}\n---")

    # 导出 markdown：作品①的主体文件
    lines = [f"# Prompt 模板库 v1\n\n> 维护人：__ ｜ 更新：{date.today()} ｜ 自检 {passed}/{len(LIBRARY)}\n"]
    for i, e in enumerate(LIBRARY, 1):
        lines += [f"\n## {i}. {e['name']}\n",
                  f"- **场景**：{e['scene']}",
                  f"- **设计理由**：{e['why']}",
                  f"- **效果数据**：{e['evidence']}",
                  f"- **失败边界**：{e['failure']}",
                  f"- **参数建议**：{e['params']}",
                  f"\n```text\n{e['template']}\n```\n"]
    import os                                  # 本地导入：仅在导出时需要
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = os.path.join(root, "data", "prompt_library_v1.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"\n③ 库文档已导出：{out}（进 GitHub 作品集）")
    print("下一步：补 3 个自己行业的模板（改动 LIBRARY 后重跑自检）")
