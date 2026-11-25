"""Sözlük tabanlı bulanık terim düzeltme (LLM'siz baseline)."""
try:
    from rapidfuzz import fuzz, process
    def _match(chunk, candidates, threshold):
        hit = process.extractOne(chunk.lower(), candidates, scorer=fuzz.ratio)
        return (hit[0], hit[1]) if hit and hit[1] >= threshold else None
except ImportError:
    from difflib import SequenceMatcher
    def _match(chunk, candidates, threshold):
        best_cand, best_score = None, 0
        for c in candidates:
            score = SequenceMatcher(None, chunk.lower(), c).ratio() * 100
            if score > best_score:
                best_cand, best_score = c, score
        return (best_cand, best_score) if best_score >= threshold else None

def correct(text: str, glossary: list[str], threshold: int = 85) -> str:
    words = text.split()
    n_max = max((len(g.split()) for g in glossary), default=1)
    candidates = [g.lower() for g in glossary]
    out, i = [], 0
    while i < len(words):
        replaced = False
        for n in range(n_max, 0, -1):
            chunk = " ".join(words[i:i+n]).strip(".,!?;:")
            if not chunk: continue
            hit = _match(chunk, candidates, threshold)
            if hit and chunk.lower() != hit[0]:
                out.append(glossary[candidates.index(hit[0])]); i += n; replaced = True; break
        if not replaced:
            out.append(words[i]); i += 1
    return " ".join(out)
