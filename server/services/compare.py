"""
完成度评分（Completion-only scoring）—— 直接替换原 compare.py
=====================================
只回答一个问题：目标句子里的词，孩子读到了几个？
不回答读得好不好 —— 那是发音评估（GOP）的事。

设计取舍
--------
- 停顿、语气词、卡顿、重复词：不影响完成度（词袋口径天然免疫）
- 多说的词：不扣分（"读没读完"不惩罚"多读"）
- ASR 的单复数/拼写小错：宽容匹配，不误伤
- 目标里的重复词：多重集语义，读 1 次只算 1 次
"""

import re
from collections import Counter
from typing import Dict, List, Tuple

# ── 缩写展开（沿用原逻辑，并额外反建"合并形式"表）──────────────
CONTRACTIONS = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "can't": "cannot", "won't": "will not", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "hasn't": "has not", "haven't": "have not", "hadn't": "had not",
    "couldn't": "could not", "wouldn't": "would not", "shouldn't": "should not",
    "it's": "it is", "i'm": "i am", "you're": "you are", "we're": "we are",
    "they're": "they are", "i've": "i have", "you've": "you have",
    "we've": "we have", "they've": "they have", "i'll": "i will",
    "you'll": "you will", "he'll": "he will", "she'll": "she will",
    "we'll": "we will", "they'll": "they will", "i'd": "i would",
    "you'd": "you would", "he'd": "he would", "she'd": "she would",
    "we'd": "we would", "they'd": "they would", "that's": "that is",
    "who's": "who is", "what's": "what is", "where's": "where is",
    "when's": "when is", "how's": "how is",
}

# 反查：展开后两词合并 → 缩写去撇号形式。用于匹配 ASR 里的 "its" / "dont"
_MERGED = {}
for _c, _e in CONTRACTIONS.items():
    _parts = _e.split()
    if len(_parts) == 2:
        _MERGED["".join(_parts)] = _c.replace("'", "")

# ── 填充词 / 语气词：出现即忽略，不影响完成度 ────────────────────
FILLERS = {
    "uh", "um", "er", "ah", "eh", "mm", "hmm", "mhm", "mmhmm", "uhhuh",
    "oh", "huh", "yeah", "yep", "yup", "ok", "okay", "hm", "ahh", "uhm",
    "erm", "ehm", "mmmm", "uhuh", "huhuh",
}


def normalize(text: str) -> List[str]:
    """小写 → 展开缩写 → 去标点 → 去填充词。"""
    t = text.lower().strip()
    for contraction, expanded in CONTRACTIONS.items():
        t = t.replace(contraction, expanded)
    t = re.sub(r"[^a-z0-9\s]", " ", t)          # 撇号/连字符都变空格
    t = re.sub(r"\s+", " ", t).strip()
    return [w for w in t.split() if w and w not in FILLERS]


# ── 宽容匹配：应对 ASR 的单复数 / 拼写抖动 ────────────────────────
def _lev(a: str, b: str) -> int:
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 2:
        return 3
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _stem(w: str) -> str:
    """极简词形还原：去复数 / 时态后缀。够用即可，不用 NLTK。"""
    for suf, min_len in (("ies", 4), ("es", 4), ("ing", 5), ("ed", 4), ("s", 3)):
        if w.endswith(suf) and len(w) >= min_len:
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def _fuzzy_equal(a: str, b: str) -> bool:
    if a == b:
        return True
    if _stem(a) == _stem(b):                    # cat / cats, run / running
        return True
    n = max(len(a), len(b))
    budget = 2 if n >= 7 else (1 if n >= 4 else 0)
    return budget > 0 and _lev(a, b) <= budget   # three / tree, cat / cot


# ── 核心：多重集完成度 ────────────────────────────────────────────
def completion(target: str, transcript: str, fuzzy: bool = True) -> Dict:
    """返回完成度。target 里的每个词，只要在 transcript 里出现过就算读到。"""
    target_words = normalize(target)
    asr_words = normalize(transcript)

    if not target_words:
        return _result(1.0, [], [], 0, [], "empty-target")

    pool: Counter = Counter(asr_words)      # 剩余可用的 ASR 词（多重集）
    hit: List[str] = []
    missed: List[str] = []

    i = 0
    while i < len(target_words):
        w = target_words[i]

        # 1) 缩写展开出的两词（it is / do not）优先整体匹配 ASR 的 its / dont。
        #    仅在确认是缩写展开时才优先，避免误吞普通词对。
        if i + 1 < len(target_words):
            merged = w + target_words[i + 1]
            if merged in _MERGED and _consume(pool, _MERGED[merged], fuzzy):
                hit.extend([w, target_words[i + 1]])
                i += 2
                continue

        # 2) 单词直接命中
        if _consume(pool, w, fuzzy):
            hit.append(w)
            i += 1
            continue

        # 3) 兜底：任意两词合并（应对 ASR 把多词连写的情况）
        if i + 1 < len(target_words):
            merged = w + target_words[i + 1]
            if _consume(pool, merged, fuzzy):
                hit.extend([w, target_words[i + 1]])
                i += 2
                continue

        missed.append(w)
        i += 1

    ratio = len(hit) / len(target_words)
    extra = [w for w in asr_words if w not in Counter(hit)]  # 仅供参考，不扣分
    return _result(ratio, hit, missed, len(target_words), extra, "completion")


def _consume(pool: Counter, word: str, fuzzy: bool) -> bool:
    """从 pool 里消耗一个能匹配 word 的词；成功返回 True。"""
    if pool[word] > 0:
        pool[word] -= 1
        return True
    if not fuzzy:
        return False
    for cand in list(pool):
        if pool[cand] > 0 and _fuzzy_equal(word, cand):
            pool[cand] -= 1
            return True
    return False


def _result(ratio, hit, missed, total, extra, method) -> Dict:
    return {
        "hit_ratio": round(ratio, 3),
        "hit_words": hit,
        "missed_words": missed,
        "target_word_count": total,
        "extra_words": extra,
        "method": method,
    }


# ── 兼容原 compare.py 的对外接口 ────────────────────────────────
# attempt.py 只用 result["hit_ratio"] / ["hit_words"]，签名保持不变，
# 因此路由层、模型层、历史页都不用改。

def score(target: List[str], transcript: List[str]) -> float:
    """兼容旧调用：给两个已分词的列表，返回完成度。"""
    if not target:
        return 1.0
    return completion(" ".join(target), " ".join(transcript))["hit_ratio"]


def compare(target: str, transcript: str) -> dict:
    """唯一的评分子段。两阶段（序列对齐 → MiniCPM）已整体移除。"""
    return completion(target, transcript)
