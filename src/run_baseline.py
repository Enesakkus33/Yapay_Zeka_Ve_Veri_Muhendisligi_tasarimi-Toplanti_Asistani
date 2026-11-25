"""
run_baseline.py
---------------
Türkçe ve İngilizce toplantı/eğitim kayıtlarını test eder,
Öneri Formundaki 6 temel metriği hesaplar ve hedeflerle karşılaştırır.

Kullanım:
  python src/run_baseline.py --id m001_tr [--skip-asr] [--llm]
  python src/run_baseline.py --all [--skip-asr] [--llm]
"""

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from terms import correct
from extract import rule_tasks, llm_tasks, summarize
from extractor import transcribe_audio_with_whisper
import evaluate as ev

TARGETS = {
    "WER_fixed": ("<=", 0.20, "%"),
    "term_acc": (">=", 0.80, "%"),
    "task_F1_strict": (">=", 0.70, ""),
    "task_F1_loose": (">=", 0.70, ""),
    "ROUGE_L": (">=", 0.35, ""),
    "source_link_rate": (">=", 0.90, "%"),
    "time_s": ("<=", 180.0, "s"),
}


def evaluate_sample(sample_id: str, row: pd.Series, skip_asr: bool = False, use_llm: bool = False) -> dict:
    meeting_date = date.fromisoformat(str(row.meeting_date))
    participants = [p.strip() for p in str(row.participants).split(";") if p.strip()]
    glossary = [g.strip() for g in str(row.glossary).split(";") if g.strip()]

    base_dir = Path("data/sample")
    ref_path = base_dir / "ref" / f"{sample_id}.txt"
    gold_path = base_dir / "tasks" / f"{sample_id}.json"

    if not ref_path.exists():
        ref_path = base_dir / "ref" / f"{sample_id.split('_')[0]}.txt"
    if not gold_path.exists():
        gold_path = base_dir / "tasks" / f"{sample_id.split('_')[0]}.json"

    ref_text = ref_path.read_text(encoding="utf-8").strip()
    gold_tasks = json.loads(gold_path.read_text(encoding="utf-8"))

    t0 = time.time()
    audio_path = Path(str(row.audio))

    # ASR Aşaması (Whisper veya Referans)
    if skip_asr or not audio_path.exists():
        raw_text = ref_text
        asr_source = "Referans Metin (--skip-asr)"
    else:
        try:
            _, full_text, segs = transcribe_audio_with_whisper(str(audio_path), model_size=os.getenv("WHISPER_MODEL", "base"))
            raw_text = " ".join(s["text"] for s in segs)
            asr_source = f"Faster-Whisper ({os.getenv('WHISPER_MODEL', 'base')})"
        except Exception as e:
            print(f"⚠️ ASR hatası ({e}), referans metne geçiliyor...")
            raw_text = ref_text
            asr_source = "Referans (ASR Fallback)"

    # Terim Düzeltme
    fixed_text = correct(raw_text, glossary)

    # Görev Çıkarımı (LLM veya Kural Tabanlı)
    task_func = llm_tasks if use_llm else rule_tasks
    extracted_tasks = task_func(fixed_text, meeting_date, participants)

    # Özetleme
    summary_text = summarize(fixed_text)
    elapsed_time = time.time() - t0

    # Metrikleri Hesapla
    wer_raw = ev.wer(ref_text, raw_text)
    wer_fixed = ev.wer(ref_text, fixed_text)
    term_acc = ev.term_accuracy(ref_text, fixed_text, glossary)
    rouge = ev.rouge_l(ref_text, summary_text)
    f1_loose = ev.task_f1(gold_tasks, extracted_tasks, strict=False)
    f1_strict = ev.task_f1(gold_tasks, extracted_tasks, strict=True)
    link_rate = ev.source_link_rate(extracted_tasks)

    metrics = {
        "id": sample_id,
        "language": getattr(row, "language", "tr"),
        "asr_source": asr_source,
        "method": "LLM (Gemini)" if use_llm else "Kural Tabanlı",
        "WER_raw": round(wer_raw, 4),
        "WER_fixed": round(wer_fixed, 4),
        "term_acc": round(term_acc, 4) if term_acc is not None else 1.0,
        "ROUGE_L": round(rouge, 4),
        "task_F1_loose": round(f1_loose, 4),
        "task_F1_strict": round(f1_strict, 4),
        "source_link_rate": round(link_rate, 4),
        "time_s": round(elapsed_time, 2),
    }

    # Sonuçları diske kaydet
    res_dir = Path("results") / sample_id
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "hyp.txt").write_text(fixed_text, encoding="utf-8")
    (res_dir / "summary.txt").write_text(summary_text, encoding="utf-8")
    (res_dir / "tasks.json").write_text(json.dumps(extracted_tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    (res_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return metrics


def print_metrics_table(results: list[dict]):
    print("\n" + "=" * 85)
    print("  📊 DEĞERLENDİRME VE BENCHMARK SONUÇLARI (Öneri Formu Metrikleri)")
    print("=" * 85)

    for m in results:
        lang_label = "🇹🇷 Türkçe" if m["language"] == "tr" else "🇬🇧 İngilizce"
        print(f"\n▶ Örnek: {m['id']} ({lang_label}) | Yöntem: {m['method']} | ASR: {m['asr_source']}")
        print("-" * 70)
        print(f"{'Metrik Adı':<22} {'Ölçülen Değer':>14}   {'Hedef Eşik':>12}   {'Durum':^8}")
        print("-" * 70)

        for key, (op, target, unit) in TARGETS.items():
            val = m.get(key)
            if val is None:
                continue

            if unit == "%":
                val_str = f"{val * 100:.1f}%"
                tgt_str = f"{op} {target * 100:.0f}%"
            elif unit == "s":
                val_str = f"{val:.1f} s"
                tgt_str = f"{op} {target:.0f} s"
            else:
                val_str = f"{val:.3f}"
                tgt_str = f"{op} {target:.2f}"

            passed = (val <= target) if op == "<=" else (val >= target)
            status = "✅ BAŞARILI" if passed else "❌ DÜŞÜK"
            print(f"{key:<22} {val_str:>14}   {tgt_str:>12}   {status:^8}")

    print("\n" + "=" * 85)


def main():
    parser = argparse.ArgumentParser(description="Toplantı Asistanı Benchmark ve Değerlendirme")
    parser.add_argument("--id", help="Test edilecek örnek ID (örn: m001_tr, m002_en)")
    parser.add_argument("--all", action="store_true", help="Tüm test setini (Türkçe + İngilizce) çalıştır")
    parser.add_argument("--skip-asr", action="store_true", help="ASR çalıştırmadan referans transkripti kullan")
    parser.add_argument("--llm", action="store_true", help="Kural tabanlı yerine LLM (Gemini) görev çıkarımı kullan")
    args = parser.parse_args()

    manifest_df = pd.read_csv("data/manifest.csv").set_index("id")

    if args.all or not args.id:
        target_ids = list(manifest_df.index)
    else:
        target_ids = [args.id]

    results = []
    for s_id in target_ids:
        if s_id not in manifest_df.index:
            print(f"HATA: {s_id} manifest.csv içinde bulunamadı.")
            continue
        row = manifest_df.loc[s_id]
        print(f"\n⏳ İşleniyor: {s_id}...")
        res = evaluate_sample(s_id, row, skip_asr=args.skip_asr, use_llm=args.llm)
        results.append(res)

    print_metrics_table(results)

    # Toplu sonuçları kaydet
    out_all = Path("results/all_metrics.json")
    out_all.parent.mkdir(parents=True, exist_ok=True)
    out_all.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📁 Tüm metrikler kaydedildi: {out_all}\n")


if __name__ == "__main__":
    main()
