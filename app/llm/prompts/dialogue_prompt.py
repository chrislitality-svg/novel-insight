"""对话精读 Prompt——半科普导向：弱化具体剧情，产出可迁移的话术模板。

输出面向不了解剧情的人，让读者学到"以后遇到类似场景怎么说话"。"""

_DIALOGUE_TEMPLATE = """你是沟通策略分析专家。下面是一段对话，请从中提炼出**脱离具体剧情也能直接使用的说话策略**。

假设你的读者**完全没看过这本书、不知道人物背景**，你的分析要能直接教他说话。

# 对话背景（仅供理解语境）
【情境】{context}
【说话人】{speaker}
【对话对象】{listener}
【关系】{relationship}

# 对话原文
{original_text}

# 任务

## 1. 这是一个什么场景（一句话）
从 [酒桌应酬、站队表态、求人办事、婉拒推辞、敲打/被敲打、汇报请示、道歉认错、化解尴尬、谈判博弈] 中选一个。

## 2. 表面说 vs 实际意思
用一句话点破：这段话表面上在说什么、本质上在达成什么？

## 3. 话术公式（重点）
把这段对话抽象成一个**可套用的话术公式**。剥离具体人名、具体事件，只保留表达框架和技巧。

格式示例：
"先夸赞对方平台 + 表达向往 → 转折抛出客观限制 + 强调师恩 → 把拒绝包装成‘沉淀学习’ → 留一句‘以后万一有机会’不把路堵死"

这个公式要让读者看完就知道："哦，遇到这种情况，我可以按照这个结构说话"。

## 4. 话术拆解（分步，每步讲清"说什么 + 为什么这么排"）
把话术公式展开为具体步骤，每步注明这样做在沟通心理学上的原因。

## 5. 逐句分析
按自然语义切句，每句标：字面意思 / 真实意图 / 用的技巧。
技巧库：示弱、施压、示忠、给退路、借势、以退为进。

## 6. 适用场景标签
这段对话策略可以迁移到现实中的哪些场景？（写具体场景，如"同事挖你跳槽时""领导当众批评团队时""饭局上给大领导敬酒时"）

# 输出（严格 JSON）
{
"speaker_role": "主角/领导/朋友/下属/同事/家人 中选一个",
"scenario": "场景类型",
"subtext": "表面说X，实际要Y",
"speech_template": "一句话话术公式，剥离具体人物和事件",
"speech_structure": [
{"step": 1, "content": "这一步说什么", "purpose": "心理原因"}
],
"sentence_breakdown": [
{"sentence": "原句", "literal_meaning": "字面", "real_intent": "真实意图", "techniques": ["示弱"]}
],
"overall_techniques": ["最多2-3个凝练技巧"],
"signal_strength": 2,
"lesson": "以后遇到XXX场景，可以这样说话/回复：...（给出可直接用的话术建议）"
}

# 注意
- speech_template 要剥离具体人名、事件，只留表达框架
- lesson 必须给出"可以直接用"的话术建议
- 技巧最多 2-3 个，宁少勿滥
- signal_strength 1-5，5=表态最强

请直接输出 JSON。"""


def build_dialogue_prompt(
    *,
    context: str,
    speaker: str,
    listener: str,
    relationship: str,
    original_text: str,
) -> str:
    return (
        _DIALOGUE_TEMPLATE.replace("{context}", context or "(无)")
        .replace("{speaker}", speaker or "主角")
        .replace("{listener}", listener or "(未知)")
        .replace("{relationship}", relationship or "(未知)")
        .replace("{original_text}", original_text)
    )
