"""Baseline görev çıkarımı + özet + önceliklendirme.
Varsayılan: kural tabanlı (çevrimdışı). GROQ_API_KEY varsa --llm ile few-shot LLM kullanılır."""
import os, re, json
from datetime import date
from dates import resolve

ACTION = re.compile(r"(acak|ecek|acağım|eceğim|malı|meli|halledecek|hazırlayacak|tamamlayacak|bitirecek|düzeltmemiz)", re.I)
URGENT = re.compile(r"(acil|hemen|kritik|bugün|öncelikli)", re.I)
SPLIT = re.compile(r"(?<=[.!?])\s+")

def sentences(text): return [s.strip() for s in SPLIT.split(text) if s.strip()]

def rule_tasks(text: str, meeting: date, participants: list[str]):
    sents, tasks = sentences(text), []
    for i, s in enumerate(sents):
        if not ACTION.search(s): continue
        own = next((p for p in participants if p.lower() in s.lower()), None)
        if own is None:  # "bunu Zeynep halledecek" gibi: önceki cümleden devral değil, aynı cümlede ara
            own = "atanmadı"
        due = resolve(s, meeting)
        pri = "Yüksek" if URGENT.search(s) else ("Orta" if due else "Düşük")
        tasks.append({"task": s, "assignee": own, "due": due.isoformat() if due else None,
                      "priority": pri, "source": s, "verified": True})
    return tasks

def llm_tasks(text: str, meeting: date, participants: list[str]):
    import requests
    prompt = (f"Toplantı tarihi: {meeting}. Katılımcılar: {', '.join(participants)}.\n"
              "Transkriptten görevleri JSON liste olarak çıkar: task, assignee ('atanmadı' olabilir), "
              "due (YYYY-MM-DD veya null), source (transkriptten BİREBİR cümle). Sadece JSON döndür.\n\n" + text)
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Groq hatası {r.status_code}: {r.text}")
    raw = r.json()["choices"][0]["message"]["content"]
    tasks = json.loads(re.sub(r"```json|```", "", raw).strip())
    for t in tasks:  # halüsinasyon kontrolü: kaynak cümle transkriptte var mı?
        t["verified"] = t.get("source", "") in text
        d = resolve(t.get("source", ""), meeting)   # göreli tarihi kuralla düzelt
        if d:
            t["due"] = d.isoformat()
        t["priority"] = "Yüksek" if URGENT.search(t.get("source", "")) else ("Orta" if t.get("due") else "Düşük")
    return tasks
def summarize(text: str, n: int = 3):
    """Baseline özet: ilk n görev/karar içeren cümle (extractive)."""
    s = [x for x in sentences(text) if ACTION.search(x)]
    return " ".join(s[:n]) if s else " ".join(sentences(text)[:n])
