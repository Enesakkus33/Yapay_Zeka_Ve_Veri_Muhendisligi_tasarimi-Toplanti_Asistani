# 🎓 YouTube & Toplantı Asistanı (Otomatik Ders ve Toplantı Notu Üreteci)

Bu proje; YouTube eğitim videoları, konferanslar veya toplantı kayıtlarından **baştan aşağı birebir zaman damgalı transkript** çıkaran ve Google Gemini yapay zekası ile **akademik kalitede yapılandırılmış ders/toplantı notları** üreten akıllı bir pipeline sistemidir.

---

## 🏗️ Sistem Mimarisi

```text
[ YouTube Video / Toplantı Kaydı ]
               │
               ▼
   1. SES AYIKLAMA (yt-dlp)
   - Görüntü indirilmeden sadece hafif ses akışı (MP3) alınır.
   - YouTube bot korumaları (403/429) mobil istemciyle aşılır.
               │
               ▼
   2. YEREL TRANSKRİPSİYON & FALLBACK (Faster-Whisper / API)
   - Altyazı varsa çekilir, yoksa Faster-Whisper yerel modeliyle
     zaman damgalı [00:00] ham transkript üretilir.
               │
               ▼
   3. YAPAY ZEKA ANALİZİ (Google Gemini 3.5 Multimodal / Text)
   - Konuşulanları baştan sona analiz eder.
   - Özet, ana konular, kavramlar sözlüğü ve sınav/mülakat soruları çıkarır.
               │
               ▼
   4. ÇIKTI (Markdown .md)
   - output/ klasöründe hem tam transkripti hem de ders notunu saklar.
```

---

## 📑 Çıktı Formatı

Üretilen her `.md` belgesi 2 ana bölümden oluşur:

1. **BÖLÜM 1: 🎙️ Videonun Birebir Tam Transkripti**
   - Konuşulan her cümle `[00:00]` zaman damgalarıyla kelimesi kelimesine yer alır.
2. **BÖLÜM 2: 🎓 Yapay Zeka Ders Notları ve Analiz**
   - **🎯 Genel Özet:** 2-4 cümlelik net açıklama.
   - **🗂️ İşlenen Ana Başlıklar:** Kronolojik numaralı konu listesi.
   - **📖 Kapsamlı Notlar ve Açıklamalar:** Detaylı kavramlar, formüller, metaforlar ve kod blokları.
   - **⚡ Anahtar Kavramlar Sözlüğü:** Terminoloji rehberi.
   - **❓ Olası Sınav / Mülakat Soruları:** Konuyu pekiştiren soru ve cevaplar.
   - **🚀 Sonraki Adımlar ve Tavsiyeler:** Öğrenme önerileri.

---

## 🚀 Kurulum

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/Enesakkus33/Yapay_Zeka_Ve_Veri_Muhendisligi_tasarimi-Toplanti_Asistani.git
cd Yapay_Zeka_Ve_Veri_Muhendisligi_tasarimi-Toplanti_Asistani
```

### 2. Sanal Ortam Oluşturun ve Bağımlılıkları Yükleyin
```bash
python -m venv .venv
# Windows için:
.venv\Scripts\activate
# Linux/macOS için:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. API Anahtarını Tanımlayın
`.env.example` dosyasının adını `.env` olarak değiştirin ve [Google AI Studio](https://aistudio.google.com/app/apikey)'dan aldığınız API anahtarını ekleyin:

```env
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.5-flash-lite
```

---

## 💻 Kullanım

Herhangi bir YouTube linkiyle not üretmek için:

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Örnek:
```bash
python main.py "https://www.youtube.com/watch?v=hDw8ipwOVOg"
```

İşlem tamamlandığında üretilen ders notu `output/` klasörüne otomatik olarak kaydedilir.

---

## 🛠️ Kullanılan Teknolojiler

- **Python 3.10+**
- **Google GenAI SDK (Gemini 3.5 Flash / Pro)**
- **yt-dlp** (Hafif ve hızlı ses akışı ayıklama)
- **Faster-Whisper / CTranslate2** (Yerel Speech-to-Text motoru)
- **python-dotenv** (Ortam değişkenleri yönetimi)

---

## 📄 Lisans
Bu proje açık kaynaklıdır ve eğitim/araştırma amaçlı geliştirilmiştir.
