"""主角识别 Prompt:读前几章,输出主角姓名、所有代称、题材判断。"""

_PROTAGONIST_TEMPLATE = """你是一个小说文本分析助手。下面是一本小说的开头若干章。请识别本书的**主角(第一视角人物)**。

# 任务
1. 找出主角的本名(如"李明")
2. 列出主角在文中的**所有代称**:他/她、姓+名、姓+职务(如"李队""李所")、昵称、绰号等
3. 判断本书题材:从 [当代都市, 职场商战, 婚恋豪门, 武侠, 玄幻仙侠, 历史古代, 科幻, 其他] 中选一个最贴近的

# 输出格式(严格 JSON)
{
"protagonist": "主角本名",
"aliases": ["代称1", "代称2", "..."],
"setting": "题材"
}

# 待分析文本
{sample_text}

请直接输出 JSON,不要任何说明。"""


def build_protagonist_prompt(sample_text: str) -> str:
    return _PROTAGONIST_TEMPLATE.replace("{sample_text}", sample_text)
