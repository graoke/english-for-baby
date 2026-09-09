"""Sentence merging and splitting rules for video transcripts.

Target: sentences suitable for a 5-year-old to repeat.
- Max 6 words or 4 seconds, whichever comes first.
- Prefer splitting at sentence-end punctuation.
- Merge very short sentences with the next one.
"""

import re
from typing import List, Dict


def split_sentences(segments: List[Dict]) -> List[Dict]:
    """Apply child-friendly splitting rules to raw transcript segments.

    Args:
        segments: List of {"text": str, "start": float, "end": float}.

    Returns:
        Merged and split segments with the same shape.
    """
    if not segments:
        return []

    # Step 1: Split each segment at punctuation boundaries
    raw_parts = []
    for seg in segments:
        text = seg["text"]
        duration = seg["end"] - seg["start"]
        # Split at . ? ! but keep the punctuation
        parts = re.split(r'(?<=[.!?])\s+', text)
        if len(parts) <= 1:
            raw_parts.append({"text": text, "start": seg["start"], "end": seg["end"]})
        else:
            # Distribute time proportionally by word count
            total_words = sum(len(p.split()) for p in parts)
            t = seg["start"]
            for p in parts:
                w = len(p.split())
                p_dur = duration * (w / total_words) if total_words else duration / len(parts)
                raw_parts.append({"text": p, "start": t, "end": t + p_dur})
                t += p_dur

    # Step 2: Apply length constraints
    result = []
    buffer = None

    for part in raw_parts:
        words = part["text"].split()

        if buffer is None:
            buffer = dict(part)
            continue

        merged_words = buffer["text"].split() + words
        merged_dur = part["end"] - buffer["start"]

        # Check if we should merge or emit buffer
        if len(merged_words) <= 6 and merged_dur <= 4.0:
            buffer["text"] = " ".join(merged_words)
            buffer["end"] = part["end"]
        else:
            # Emit buffer, start new
            result.append(buffer)
            buffer = dict(part)

    if buffer:
        result.append(buffer)

    # Step 3: Drop very short / meaningless sentences
    filtered = []
    for seg in result:
        text = seg["text"].strip()
        words = text.split()
        if len(words) < 2 and text.lower() in ("uh", "hmm", "okay", "ok", "oh", "um", "ah"):
            continue
        if len(words) < 1:
            continue
        filtered.append(seg)

    return filtered
