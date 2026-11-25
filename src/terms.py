"""Sözlük tabanlı bulanık terim düzeltme (LLM'siz baseline)."""
from rapidfuzz import fuzz, process

def correct(text: str, glossary: list[str], threshold: int = 85) -> str:
    words = text.split()
    n_max = max((len(g.split()) for g in glossary), default=1)
    out, i = [], 0
    while i < len(words):
        replaced = False
        for n in range(n_max, 0, -1):
            chunk = " ".join(words[i:i+n]).strip(".,!?;:")
            if not chunk: continue
            hit = process.extractOne(chunk.lower(), [g.lower() for g in glossary], scorer=fuzz.ratio)
            if hit and hit[1] >= threshold and chunk.lower() != hit[0]:
                out.append(glossary[[g.lower() for g in glossary].index(hit[0])]); i += n; replaced = True; break
        if not replaced:
            out.append(words[i]); i += 1
    return " ".join(out)
