from typing import Dict, Any

def analyze_prose_metrics(text: str) -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return {"word_count": 0, "dialogue_ratio": 0.0, "avg_sentence_len": 0.0}
    words = text.split()
    dialogue_lines = sum(1 for l in lines if l.startswith('"') or l.startswith('“') or l.startswith('-'))
    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    return {
        "word_count": len(words),
        "dialogue_ratio": round(dialogue_lines / len(lines), 3),
        "avg_sentence_len": round(len(words) / max(len(sentences), 1), 1)
    }
