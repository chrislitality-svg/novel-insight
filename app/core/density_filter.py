"""事件密度过滤:跳过纯打怪/纯描写/纯独白的章节,只把有人物互动、有人情戏的章节送 LLM。"""
import re

# 人情世故关键词
KEYWORDS = [
    "酒局", "饭局", "送礼", "汇报", "请示", "站队", "面子", "关系",
    "人情", "客气", "推辞", "应酬", "客套", "寒暄", "场面",
    "岳父", "岳母", "夫人", "太太", "老板", "总", "哥", "姐",
    "敬酒", "托付", "拜访", "介绍", "搭桥", "答应", "承诺",
    "保证", "放心", "没问题", "请客", "回礼", "问候", "伺候",
    "领导", "书记", "局长", "处长", "主任", "科长", "秘书",
    "敬意", "赏脸", "高攀", "抬举", "栽培", "提携", "关照",
]

# 中文引号包裹的对话
_DIALOGUE_RE = re.compile(r"[“\"].+?[”\"]", re.DOTALL)


def calculate_density_score(content: str, threshold: float = 30.0) -> dict:
    length = max(len(content), 1)

    dialogues = _DIALOGUE_RE.findall(content)
    dialogue_chars = sum(len(d) for d in dialogues)
    dialogue_ratio = dialogue_chars / length

    keyword_hits = sum(content.count(kw) for kw in KEYWORDS)
    keyword_density = keyword_hits / (length / 1000)

    score = min(100.0, dialogue_ratio * 100 + keyword_density * 10)

    return {
        "score": round(score, 1),
        "should_analyze": score >= threshold,
        "metadata": {
            "dialogue_ratio": round(dialogue_ratio, 3),
            "keyword_hits": keyword_hits,
            "dialogue_count": len(dialogues),
        },
    }
