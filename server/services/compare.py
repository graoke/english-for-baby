"""Two-stage comparison: exact match → MiniCPM phonetic evaluator (GGUF)."""

import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Set

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
    "we'd": "we would", "they'd": "they would", "that's": "that is",
    "who's": "who is", "what's": "what is", "where's": "where is",
    "when's": "when is", "how's": "how is",
}

# 默认模型路径（相对于项目根目录）
DEFAULT_GGUF_PATH = str(Path(__file__).parent.parent.parent / "data" / "models" / "minicpm-phonetic-evaluator-q4_k_m.gguf")


def _get_gguf_path() -> str:
    """从环境变量获取 MiniCPM GGUF 模型路径。"""
    return os.environ.get("MINICPM_GGUF_PATH", DEFAULT_GGUF_PATH)


def normalize(text: str) -> Set[str]:
    t = text.lower().strip()
    for contraction, expanded in CONTRACTIONS.items():
        t = t.replace(contraction, expanded)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return set(t.split())


# ── MiniCPM GGUF (lazy load, thread-safe) ─────────────────────
_llm = None
_llm_lock = threading.Lock()
_infer_lock = threading.Lock()  # Separate lock for inference (GGUF not thread-safe)


def _load_llm():
    global _llm
    if _llm is not None:
        return
    with _llm_lock:
        if _llm is not None:
            return
        
        gguf_path = _get_gguf_path()
        
        # 检查模型文件是否存在
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
    """Ask MiniCPM GGUF if transcript is a valid phonetic match for target."""
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
    """Two-stage comparison: exact match first, then MiniCPM judge."""
    target_words = normalize(target)
    transcript_words = normalize(transcript)

    logger.info("Compare: target=%r → %s, transcript=%r → %s",
                target[:50], target_words, transcript[:50], transcript_words)

    if not target_words:
        return {
            "hit_ratio": 1.0, "hit_words": [], "missed_words": [],
            "target_word_count": 0, "method": "exact",
        }

    # Stage 1: exact word match
    hit = target_words & transcript_words
    missed = target_words - transcript_words
    exact_ratio = len(hit) / len(target_words)

    if exact_ratio >= 1.0:
        logger.info("Exact match → True")
        return {
            "hit_ratio": 1.0, "hit_words": sorted(hit), "missed_words": [],
            "target_word_count": len(target_words), "method": "exact",
        }

    # Stage 2: MiniCPM judge for each missed word
    minicpm_hit = set(hit)
    t0 = time.time()
    for w in missed:
        try:
            if _minicpm_judge(w, transcript):
                minicpm_hit.add(w)
        except Exception as e:
            logger.exception("MiniCPM judge exception for word %r", w)

    new_missed = target_words - minicpm_hit
    final_ratio = len(minicpm_hit) / len(target_words)

    logger.info("Final (%.2fs): hit=%s, missed=%s, ratio=%.3f, method=minicpm",
                time.time() - t0, minicpm_hit, new_missed, final_ratio)

    return {
        "hit_ratio": round(final_ratio, 3),
        "hit_words": sorted(minicpm_hit),
        "missed_words": sorted(new_missed),
        "target_word_count": len(target_words),
        "method": "minicpm",
    }


def preload_minicpm():
    """Pre-load MiniCPM GGUF in background thread to avoid blocking first request."""
    def _bg():
        try:
            _load_llm()
        except FileNotFoundError as e:
            logger.warning("MiniCPM model not found: %s", e)
        except Exception as e:
            logger.exception("MiniCPM pre-load failed")
    threading.Thread(target=_bg, daemon=True).start()
