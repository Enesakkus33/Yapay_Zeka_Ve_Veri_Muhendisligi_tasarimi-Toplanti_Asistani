"""Metrikler: WER, terim doğruluğu, ROUGE-L, görev F1 (gevşek + sıkı), kaynak bağlama oranı."""
import re
from difflib import SequenceMatcher

def norm(t): return re.sub(r"[^\w\s]", "", t.lower().replace("İ", "i").replace("I", "ı")).split()

def wer(ref: str, hyp: str) -> float:
    try:
        import jiwer
        return float(jiwer.wer(" ".join(norm(ref)), " ".join(norm(hyp))))
    except ImportError:
        # jiwer yoksa saf Python Levenshtein Word Error Rate hesaplayıcı
        r = norm(ref)
        h = norm(hyp)
        if not r: return 0.0 if not h else 1.0
        d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
        for i in range(len(r) + 1): d[i][0] = i
        for j in range(len(h) + 1): d[0][j] = j
        for i in range(1, len(r) + 1):
            for j in range(1, len(h) + 1):
                if r[i - 1] == h[j - 1]:
                    d[i][j] = d[i - 1][j - 1]
                else:
                    d[i][j] = min(d[i - 1][j] + 1,      # deletion
                                  d[i][j - 1] + 1,      # insertion
                                  d[i - 1][j - 1] + 1)  # substitution
        return d[len(r)][len(h)] / len(r)

def term_accuracy(ref: str, hyp: str, glossary: list[str]) -> float | None:
    r, h = " ".join(norm(ref)), " ".join(norm(hyp))
    terms = [g.lower() for g in glossary if g.lower() in r]
    return sum(t in h for t in terms) / len(terms) if terms else None

def rouge_l(ref: str, hyp: str) -> float:
    a, b = norm(ref), norm(hyp)
    if not a or not b: return 0.0
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)):
        for j in range(len(b)):
            dp[i+1][j+1] = dp[i][j]+1 if a[i] == b[j] else max(dp[i][j+1], dp[i+1][j])
    l = dp[-1][-1]; p, r = l/len(b), l/len(a)
    return 0 if l == 0 else 2*p*r/(p+r)

def task_f1(gold: list[dict], pred: list[dict], strict: bool = False, thr: float = 0.45):
    used, tp = set(), 0
    for g in gold:
        for k, p in enumerate(pred):
            if k in used: continue
            sim = SequenceMatcher(None, " ".join(norm(g["task"])), " ".join(norm(p["task"]))).ratio()
            ok = sim >= thr or set(norm(g["task"])) & set(norm(p["task"])) >= set(norm(g["task"]))
            if ok and strict:
                ok = g["assignee"] == p["assignee"] and g["due"] == p["due"]
            if ok: used.add(k); tp += 1; break
    prec = tp/len(pred) if pred else 0; rec = tp/len(gold) if gold else 0
    return 0 if tp == 0 else 2*prec*rec/(prec+rec)

def source_link_rate(pred: list[dict]) -> float:
    return sum(bool(t.get("source")) and t.get("verified", False) for t in pred)/len(pred) if pred else 0.0
