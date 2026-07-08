"""跨章节聚合 Prompt:人物画像 / 情境聚类 / 长期账时间线。"""

_CHARACTER_TEMPLATE = """你是一个人物分析专家。下面是小说中人物「{name}」在各章节出现时的人情世故场景汇总。请总结此人的处世模式。

# 汇总材料(按章节顺序)
{material}

# 任务
综合上述材料,输出对「{name}」的画像:
1. role_type:从 [主角, 重要配角, 路人] 判断其角色权重
2. behavior_pattern:用 2-4 句话总结此人的处世模式、性格底色、惯用手段

# 输出格式(严格 JSON)
{
"role_type": "主角/重要配角/路人",
"behavior_pattern": "..."
}

请直接输出 JSON。"""

_CLUSTER_TEMPLATE = """你是一个人情世故套路分析专家。下面是同一类情境(标签:「{tag}」)在小说不同章节中的多个实例。请总结这一类情境下的共性打法。

# 同类情境实例(按章节顺序)
{material}

# 任务
提炼这一类「{tag}」情境的共性套路:常见的应对手法、关键分寸、容易踩的坑。用 2-4 句话总结。

# 输出格式(严格 JSON)
{
"pattern_summary": "..."
}

请直接输出 JSON。"""

_TALLY_TEMPLATE = """你是一个叙事线索分析专家。下面按章节顺序列出了小说中主角与各方之间的"人情账目"(每条含章节序号、记下了什么账、预期如何兑现)。请梳理出人情债时间线。

# 人情账目流水(按章节顺序)
{material}

# 任务
识别:哪些"账"在后续章节兑现了(给出大致章节),哪些还悬着没还。按时间顺序组织成一条时间线。

# 输出格式(严格 JSON)
{
"timeline": [
{"chapter_index": 12, "event": "欠下/记下了什么账", "status": "已兑现/未兑现", "payoff_note": "在哪兑现或仍悬置"}
],
"summary": "用 2-3 句话总结全书的人情债脉络"
}

请直接输出 JSON。"""


_RULES_TEMPLATE = """你是一个社会规则提炼专家。下面是从一本小说各章节里抽取出的大量"社会规则/潜规则/常识"原始条目(含章节序号、规则、原因、原文证据),有重复、有零碎。请把它们归并、去重、归类成一本干净的"社会规则手册"。

# 原始条目(按章节顺序)
{material}

# 任务
1. 把意思相同/相近的条目合并成一条,保留最清楚的表述
2. 给每条规则归类:从 [官场体制, 酒桌应酬, 人情往来, 职场进退, 婚恋家庭, 利益博弈, 其他] 中选一个
3. 每条写清:规则本身 + 为什么(不懂的人会怎样吃亏) + chapters 必须完整列出输入中所有涉及该规则的章节序号(不要只挑代表)
4. 按"对现实最有用、出现最多"排序,最多输出 20 条;务必涵盖输入中所有章节区间,不要偏向早期章节

# 输出格式(严格 JSON)
{
"rules": [
{"rule": "一句话规则", "category": "官场体制", "explanation": "为什么是这样、不懂会怎样吃亏", "chapters": [12, 34, 567, 891], "occurrence": 4}
]
}

请直接输出 JSON。"""


def build_rules_prompt(material: str) -> str:
    return _RULES_TEMPLATE.replace("{material}", material)


def build_character_prompt(name: str, material: str) -> str:
    return _CHARACTER_TEMPLATE.replace("{name}", name).replace("{material}", material)


def build_situation_cluster_prompt(tag: str, material: str) -> str:
    return _CLUSTER_TEMPLATE.replace("{tag}", tag).replace("{material}", material)


def build_tally_timeline_prompt(material: str) -> str:
    return _TALLY_TEMPLATE.replace("{material}", material)
