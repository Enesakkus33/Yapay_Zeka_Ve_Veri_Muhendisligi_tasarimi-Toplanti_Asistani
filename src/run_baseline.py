"""Kullanım: python src/run_baseline.py --id m001 [--skip-asr] [--llm]
--skip-asr: ses yerine referans transkript kullanır (ASR sonrası hattı ses olmadan test eder)."""
import argparse, json, os, sys, time
from datetime import date
import pandas as pd
from dotenv import load_dotenv

# Windows'un varsayılan konsol kodlaması emoji içeren durum işaretlerini
# yazamayabilir; sonuç çıktısını terminalden bağımsız olarak UTF-8 yap.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from terms import correct
from extract import rule_tasks, llm_tasks, summarize
import evaluate as ev

ap = argparse.ArgumentParser(); ap.add_argument("--id", required=True)
ap.add_argument("--skip-asr", action="store_true"); ap.add_argument("--llm", action="store_true")
a = ap.parse_args()
row = pd.read_csv("data/manifest.csv").set_index("id").loc[a.id]
meeting = date.fromisoformat(row.meeting_date)
people, gloss = row.participants.split(";"), row.glossary.split(";")
base = "data/sample" if os.path.exists(f"data/sample/ref/{a.id}.txt") else "data/test_set"
ref = open(f"{base}/ref/{a.id}.txt", encoding="utf-8").read()
gold = json.load(open(f"{base}/tasks/{a.id}.json", encoding="utf-8"))

t0 = time.time()
if a.skip_asr:
    raw = ref
else:
    from transcribe import transcribe
    segs, _ = transcribe(row.audio, gloss); raw = " ".join(s["text"] for s in segs)
fixed = correct(raw, gloss)
tasks = (llm_tasks if a.llm else rule_tasks)(fixed, meeting, people)
summ = summarize(fixed)
elapsed = time.time() - t0

m = {"id": a.id, "WER_raw": ev.wer(ref, raw), "WER_fixed": ev.wer(ref, fixed),
     "term_acc": ev.term_accuracy(ref, fixed, gloss), "ROUGE_L": ev.rouge_l(ref, summ),
     "task_F1_loose": ev.task_f1(gold, tasks), "task_F1_strict": ev.task_f1(gold, tasks, strict=True),
     "source_link_rate": ev.source_link_rate(tasks), "time_s": round(elapsed, 2)}
os.makedirs(f"results/{a.id}", exist_ok=True)
json.dump(tasks, open(f"results/{a.id}/tasks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(f"results/{a.id}/hyp.txt", "w", encoding="utf-8").write(fixed)
json.dump(m, open(f"results/{a.id}/metrics.json", "w"), indent=1)

targets = {"WER_fixed": ("<=", .20), "term_acc": (">=", .80), "task_F1_strict": (">=", .70),
           "ROUGE_L": (">=", .35), "source_link_rate": (">=", .90), "time_s": ("<=", 180)}
print(f"\n{'Metrik':<18}{'Değer':>8}  Hedef")
for k, v in m.items():
    if k == "id": continue
    t = targets.get(k); mark = ""
    if t and v is not None: mark = "✅" if (v <= t[1] if t[0] == "<=" else v >= t[1]) else "❌"
    print(f"{k:<18}{(round(v,3) if v is not None else 'n/a'):>8}  {t[0]+str(t[1]) if t else ''} {mark}")
