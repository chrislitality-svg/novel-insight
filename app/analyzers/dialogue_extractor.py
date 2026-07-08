"""从章节中抽取主角说的、值得精读的长对话,送 deep 模型逐句拆解。

归属判定走"说话标记"模式而非"名字出现在附近":主角是全书话题中心,
名字会频繁出现在别人台词周围,只看"50字内有主角名"会把别人的话误判成主角的。
因此要求 主角名 + 说话动词(道/说/笑道…)紧贴引号 才算主角在说。
"""
import re

# 引号包裹的对话(中文 “” 与英文 "")
_QUOTE_RE = re.compile(r"[“\"]([^“”\"]{1,400}?)[”\"]")

# 说话动作标记(出现在引号前后,判断说话人)
_SPEECH_MARKERS = ["说道", "笑道", "问道", "答道", "回道", "应道", "叹道", "开口", "解释", "道", "说"]
_MARKER_PAT = "|".join(_SPEECH_MARKERS)

# 不能用作归属信号的泛指代词(太宽,会误判)
_PRONOUNS = {"他", "她", "它", "我", "你", "您", "他们", "她们", "男主", "主角"}

# 值得精读的意图关键词(命中越多,优先级越高)
_INTENT_KEYWORDS = [
    "放心", "保证", "一定", "不敢", "惭愧", "您看", "我看这事", "承诺", "答应",
    "包在我身上", "交给我", "请示", "汇报", "麻烦您", "拜托", "得罪", "赏脸",
    "敬您", "谢谢", "对不起", "实在", "其实", "说实话", "明人不说暗话",
    "这事", "您放心", "听我", "照办", "按您", "领导", "提点", "关照",
]

# 排除的短回应
_SHORT_RESPONSES = {"嗯", "好的", "知道了", "好", "是", "对", "行", "嗯嗯", "哦", "好吧"}

MIN_DIALOGUE_CHARS = 60
MAX_PER_CHAPTER = 5


def extract_protagonist_dialogues(content: str, protagonist_aliases: list[str]) -> list[dict]:
    """返回 [{original_text, context, speaker, listener, score}],最多 MAX_PER_CHAPTER 段。"""
    aliases = [a for a in (protagonist_aliases or []) if a]
    candidates: list[dict] = []

    for m in _QUOTE_RE.finditer(content):
        quote = m.group(1).strip()
        if len(quote) < MIN_DIALOGUE_CHARS:
            continue
        if quote in _SHORT_RESPONSES:
            continue

        start, end = m.start(), m.end()
        before = content[max(0, start - 50) : start]
        after = content[end : end + 30]

        if not _is_protagonist_speaking(before, after, aliases):
            continue

        score = _worth_score(quote)
        candidates.append(
            {
                "original_text": quote,
                "context": _build_context(content, start),
                "speaker": _protagonist_name(aliases),
                "listener": _guess_listener(quote),
                "score": score,
            }
        )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:MAX_PER_CHAPTER]


def _is_protagonist_speaking(before: str, after: str, aliases: list[str]) -> bool:
    names = [a for a in aliases if a not in _PRONOUNS and len(a) >= 2]
    if not names:
        # 没有可靠主角名时,退化为"引号前紧贴说话标记"(只能保证是某人说的话)
        return bool(re.search(rf"({_MARKER_PAT})[：:，]?\s*$", before))

    name_pat = "|".join(re.escape(n) for n in names)
    # 前置归属:……李明(笑着)说道:" —— 主角名后 6 字内出现说话动词,且紧贴引号
    if re.search(rf"({name_pat})[^。！？“”\n]{{0,6}}({_MARKER_PAT})[：:，]?\s*$", before):
        return True
    # 后置归属:"……"李明说道 —— 引号后紧跟 主角名+说话动词
    if re.search(rf"^[\s…，,]*({name_pat})[^。！？\n]{{0,4}}({_MARKER_PAT})", after):
        return True
    return False


def _worth_score(quote: str) -> float:
    score = min(len(quote) / 20.0, 8.0)  # 长度分,上限 8
    hits = sum(1 for kw in _INTENT_KEYWORDS if kw in quote)
    score += hits * 3
    return score


def _build_context(content: str, quote_start: int) -> str:
    """取引号前约 150 字作为情境(从行首开始,避免截断)。"""
    ctx_start = max(0, quote_start - 150)
    ctx = content[ctx_start:quote_start].strip()
    # 从最后一个换行处开始,保证语义完整
    if "\n" in ctx:
        ctx = ctx.rsplit("\n", 1)[-1] if len(ctx.rsplit("\n", 1)[-1]) > 20 else ctx
    return ctx[-150:]


def _guess_listener(quote: str) -> str | None:
    """对话开头若是称呼(如「王总,」「李哥,」),取作倾听者。"""
    m = re.match(r"^([一-龥]{2,5})[，,!！]", quote)
    if m:
        return m.group(1)
    return None


def _protagonist_name(aliases: list[str]) -> str:
    return "主角"
