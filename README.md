# Türkçe Toplantı Asistanı – Hafta 3: Veri + AI Baseline

Yapay Zeka ve Veri Mühendisliği Tasarımı dersi projesi. Mehmet Hanifi IŞIK & Enes AKKUŞ.

## Hafta 3 teslimleri
- [x] Test seti şablonu: `data/manifest.csv`, `data/<set>/ref|tasks|audio`
- [x] EDA notebook: `notebooks/eda.ipynb`
- [x] Baseline AI hattı: Whisper (faster-whisper + VAD + initial_prompt) → sözlük/bulanık terim düzeltme → kural tabanlı (veya `--llm` Groq) görev çıkarımı → extractive özet → öncelik
- [x] Göreli tarih çözümleme ("haftaya Cuma" → mutlak tarih): `src/dates.py`
- [x] Değerlendirme: WER, terim doğruluğu, ROUGE-L, görev F1 (gevşek/sıkı), kaynak bağlama oranı: `src/evaluate.py`
- [ ] Gerçek kayıtlarla ilk metrikler (aşağıdaki tabloyu doldur)

## Kurulum / çalıştırma
```bash
py -3.12 -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/run_baseline.py --id m001 --skip-asr     # ses olmadan, ASR sonrası hat testi
python src/run_baseline.py --id m001                # Whisper ile (data/sample/audio/m001.wav gerekir)
python src/run_baseline.py --id m001 --llm          # GROQ_API_KEY ile LLM çıkarımı
```


## Baseline sonuçları vs. hedef

Ölçüm: örnek toplantı `m001`, `--skip-asr` ile (ASR hatası dahil değil). Tarih: 18.11.2026.

| Metrik | Hedef | Sonuç | Durum |
|---|---|---|---|
| WER | ≤ %20 | 0.0 (ASR atlandı, anlamlı değil) | ses ile ölçülecek |
| Terim doğruluğu | ≥ %80 | 1.0 | ✅ |
| Görev F1 (sıkı) | ≥ 0.70 | 1.0 | ✅ |
| ROUGE-L | ≥ 0.35 | 0.718 | ✅ |
| Kaynak bağlama | ≥ %90 | 1.0 | ✅ |
| İşlem süresi | ≤ 3 dk / 10 dk kayıt | 3.2 sn (yalnızca LLM kısmı) | Whisper ile ölçülecek |

### Görev çıkarımı yaklaşımlarının karşılaştırması

| Yaklaşım | F1 (gevşek) | F1 (sıkı) | Süre |
|---|---|---|---|
| Kural tabanlı | 1.0 | 1.0 | 0.0 sn |
| Yalnızca LLM (gpt-oss-120b) | 1.0 | 0.75 | 4.0 sn |
| LLM + kural tabanlı tarih çözümleme (melez) | 1.0 | 1.0 | 3.2 sn |

**Hata analizi:** Yalnızca LLM, "haftaya Cuma" ifadesini 27 Kasım yerine 20 Kasım olarak çevirdi (toplantı 18 Kasım Çarşamba). Tarih, kaynak cümleden `src/dates.py` ile yeniden hesaplanınca hata giderildi.

**Sınırlamalar:**
- Sonuçlar tek ve kısa (5 cümle) bir örnekten geliyor, genellenemez. Gerçek kayıtlarla yeniden ölçülecek.
- Kural tabanlı yöntemin kuralları bu örneğe bakılarak yazıldı, 1.0 skoru iyimser.
- `dates.py` gün adlarını kelime içinde arıyor ("pazarlama" → "pazar" gibi yanlış eşleşme riski).
