"""行为分析 Prompt——半科普导向：弱化剧情依赖，提取可迁移的做人道理。"""

_BEHAVIOR_TEMPLATE = """你是人情世故分析专家。读下面这一章，提炼其中**脱离具体剧情也能直接用的做人道理和说话策略**。

假设你的读者**完全没读过这本书、不知道人物背景**，你要让他们从这一章里学到实用的处世技巧。

# 待分析章节
【章节标题】{chapter_title}
【章节内容】
{chapter_content}

# 任务

## 1. 这一章有什么人情互动（一句话）
概括本章核心的人际互动场景。如果完全没有，直接全部填 null/空数组。

## 2. 可迁移的做人道理
不讲具体剧情，用 2-3 句话讲清：这一章体现的**处世原则**是什么。读者读到就能想到自己生活中类似的场景。

格式：
【处世原则】一句话讲清。
【为什么对】一句话讲清这样做为什么有用、不这样做会怎样。
【适用场景】这种原则可以用于现实中的什么场景。

## 3. 社会规则 / 潜规则
本章有没有"没人教就不懂"的规则？没有就空数组。

## 4. 标签
2-3 个凝练标签，让读者一眼知道这章的主题。

# 输出（严格 JSON）
{
"scene_summary": "一句话概括本章关键人情互动",
"characters_involved": ["主角", "具体人名"],
"freeform_analysis": "【处世原则】...\n【为什么对】...\n【适用场景】...",
"social_rules": [{"rule": "一句话规则", "why": "为什么/不懂会怎样", "evidence": "原文关键句"}],
"core_lesson": "一句话核心道理（可直接用的话术建议）",
"tags": ["2-3个凝练标签"]
}

# 注意
- 本章完全没有人情戏 → scene_summary="无显著人情戏", freeform_analysis=null, 其余空
- freeform_analysis 要脱离具体剧情，讲的是普遍原则
- 标签宁少勿滥

请直接输出 JSON。"""


def build_behavior_prompt(chapter_title: str, chapter_content: str) -> str:
    return _BEHAVIOR_TEMPLATE.replace("{chapter_title}", chapter_title).replace(
        "{chapter_content}", chapter_content
    )
