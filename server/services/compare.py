"""Two-stage comparison: sequence alignment → MiniCPM phonetic evaluator (GGUF)."""

import logging
import os
import re
import threading
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import List

logger = logging.getLogger("peppa.compare")

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
    "we'd": "you would", "they'd": "they would", "that's": "that is",
    "who's": "who is", "what's": "what is", "where's": "where is",
    "when's": "when is", "how's": "how is",
}

DEFAULT_GGUF_PATH = str(Path(__file__).parent.parent.parent / "data" / "models" / "minicpm-phonetic-evaluator-q4_k_m.gguf")


def _get_gguf_path() -> str:
    return os.environ.get("MINICPM_GGUF_PATH", DEFAULT_GGUF_PATH)


def normalize(text: str) -> List[str]:
    """返回词列表（保留顺序）。"""
    t = text.lower().strip()
    for contraction, expanded in CONTRACTIONS.items():
        t = t.replace(contraction, expanded)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return t.split()


def score(target: List[str], transcript: List[str]) -> float:
    """序列对齐评分，考虑词序。"""
    if not target:
        return 1.0
    matcher = SequenceMatcher(None, target, transcript, autojunk=False)
    return sum(size for _, _, size in matcher.get_matching_blocks()) / len(target)


def find_hit_missed(target: List[str], transcript: List[str]) -> tuple:
    """找出命中的词和遗漏的词，保留词序。"""
    target_set = set(target)
    transcript_set = set(transcript)
    hit = [w for w in target if w in transcript_set]
    missed = [w for w in target if w not in transcript_set]
    return hit, missed


# ── MiniCPM GGUF (lazy load, thread-safe) ─────────────────────
_llm = None
_llm_lock = threading.Lock()
_infer_lock = threading.Lock()


def _load_llm():
    global _llm
    if _llm is not None:
        return
    with _llm_lock:
        if _llm is not None:
            return
        
        gguf_path = _get_gguf_path()
        if not Path(gguf_path).exists():
            raise FileNotFoundError(
                f"MiniCPM GGUF model not found at {gguf_path}\n"
                f"Please download the model and place it there, or set MINICPM_GGUF_PATH environment variable."
            )
        
        from llama_cpp import Llama
        logger.info("Loading MiniCPM GGUF from %s ...", gguf_path)
        t0 = time.time()
        _llm = Llama(
            model_path=gguf_path,
            n_ctx=512,
            n_threads=4,
            verbose=False,
        )
        logger.info("MiniCPM GGUF loaded in %.1fs", time.time() - t0)


def _minicpm_judge(target: str, transcript: str) -> bool:
    _load_llm()

    prompt = f"""### Instruction:
Determine if the ASR transcript is a valid phonetic match for the target word. Output only True or False.

### Input:
Target: {target} | ASR: {transcript}

### Output:
"""
    t0 = time.time()
    try:
        with _infer_lock:
            output = _llm(
                prompt,
                max_tokens=8,
                temperature=0.0,
                stop=["###", "\n"],
            )
        result = output["choices"][0]["text"].strip()
        elapsed = time.time() - t0
        logger.info("MiniCPM judge (%.2fs): target=%r transcript=%r → %s", elapsed, target, transcript, result)
        return result.lower().startswith("true")
    except Exception as e:
        logger.exception("MiniCPM inference failed: target=%r transcript=%r", target, transcript)
        return False


def compare(target: str, transcript: str) -> dict:
    """两阶段对比：序列对齐 → MiniCPM 语音评估。"""
    target_words = normalize(target)
    transcript_words = normalize(transcript)

    logger.info("Compare: target=%r → %s, transcript=%r → %s",
                target[:50], target_words, transcript[:50], transcript_words)

    if not target_words:
        return {
            "hit_ratio": 1.0, "hit_words": [], "missed_words": [],
            "target_word_count": 0, "method": "exact",
        }

    # Stage 1: 序列对齐
    ratio = score(target_words, transcript_words)
    hit, missed = find_hit_missed(target_words, transcript_words)

    if ratio >= 1.0:
        logger.info("Exact match → True")
        return {
            "hit_ratio": 1.0, "hit_words": hit, "missed_words": [],
            "target_word_count": len(target_words), "method": "exact",
        }

    # Stage 2: MiniCPM 对遗漏的词做语音评估
    minicpm_hit = list(hit)
    t0 = time.time()
    for w in missed:
        try:
            if _minicpm_judge(w, transcript):
                minicpm_hit.append(w)
        except Exception as e:
            logger.exception("MiniCPM judge exception for word %r", w)

    final_ratio = len(minicpm_hit) / len(target_words)
    new_missed = [w for w in target_words if w not in minicpm_hit]

    logger.info("Final (%.2fs): hit=%s, missed=%s, ratio=%.3f, method=minicpm",
                time.time() - t0, minicpm_hit, new_missed, final_ratio)

    return {
        "hit_ratio": round(final_ratio, 3),
        "hit_words": minicpm_hit,
        "missed_words": new_missed,
        "target_word_count": len(target_words),
        "method": "minicpm",
    }


def preload_minicpm():
    def _bg():
        try:
            _load_llm()
        except FileNotFoundError as e:
            logger.warning("MiniCPM model not found: %s", e)
        except Exception as e:
            logger.exception("MiniCPM pre-load failed")
    threading.Thread(target=_bg, daemon=True).start()
