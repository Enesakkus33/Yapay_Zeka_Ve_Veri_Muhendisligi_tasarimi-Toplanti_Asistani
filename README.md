# 🎓 Türkçe ve Çok Dilli Yapay Zeka Destekli Toplantı Asistanı
### Konuşmayı Otomatik Transkript, Özet ve Önceliklendirilmiş Göreve Dönüştüren Uçtan Uca Çözüm

> **Proje Ekibi:** Mehmet Hanifi IŞIK (230292029), Enes AKKUŞ (230291025)  
> **Ders:** Yapay Zeka ve Veri Mühendisliği Tasarımı  
> **Hedef:** Türkçe odaklı, yerel veri gizliliğine duyarlı, düşük maliyetli ve yüksek doğruluklu toplantı/eğitim asistanı.

---

## 🏗️ Sistem Mimarisi ve Akış Şeması

```text
[ Toplantı / Ders Kaydı (MP3/WAV) ]
                 │
                 ▼
   1. SES ÖN İŞLEME & AYIKLAMA (yt-dlp / FFmpeg)
   - Video/Toplantı kaydından hafif ses akışı ayıklanır.
                 │
                 ▼
   2. YEREL TRANSKRİPSİYON (Faster-Whisper int8 / GPU)
   - İnternet gerektirmeden, gizlilik odaklı konuşmadan metne (ASR) dönüştürme.
   - Zaman damgalı [00:00] ham transkript üretimi.
                 │
                 ▼
   3. TERİM VE ÖZEL İSİM DÜZELTME (terms.py - Fuzzy Matching)
   - Karışık dilli teknik terimler (Code-Switching) sözlük ile düzeltilir.
                 │
                 ▼
   4. YAPAY ZEKA DERS NOTU & GÖREV ÇIKARIMI (Gemini 3.5 / LLM)
   - Akademik ders notu, özet ve kavramlar sözlüğü oluşturulur.
   - Sorumlu, mutlak tarih (dates.py) ve kaynak cümle bağlantılı görevler çıkarılır.
                 │
                 ▼
   5. ÇIKTI (Markdown .md & JSON)
   - output/ klasöründe hem birebir transkript hem yapılandırılmış notlar saklanır.
```

---

## 📊 Deneysel Sonuçlar ve Metrik Karşılaştırması

Proje Öneri Formunda taahhüt edilen **6 temel nicel metrik**, Türkçe ve İngilizce test setlerinde (`m001_tr` ve `m002_en`) test edilmiş ve karşılaştırılmıştır:

### 🎯 Karşılaştırma Tablosu

| Metrik | Hedef Eşik (Öneri Formu) | 🇹🇷 Türkçe Toplantı (`m001_tr`) | 🇬🇧 İngilizce Kayıt (`m002_en`) | Durum |
| :--- | :---: | :---: | :---: | :---: |
| **WER (Kelime Hata Oranı - Raw)** | - | %8.4 | %4.1 | Bilgi Amaçlı |
| **WER (Düzeltilmiş - Fixed)** | **$\le \%20.0$** | **%5.2** | **%3.2** | ✅ **BAŞARILI** |
| **Terim Doğruluğu (Term Accuracy)** | **$\ge \%80.0$** | **%100.0** | **%100.0** | ✅ **BAŞARILI** |
| **Görev Çıkarımı F1 (Strict)** | **$\ge 0.70$** | **0.857** | **0.800** | ✅ **BAŞARILI** |
| **Görev Çıkarımı F1 (Loose)** | **$\ge 0.70$** | **1.000** | **1.000** | ✅ **BAŞARILI** |
| **Özet Kalitesi (ROUGE-L)** | **$\ge 0.35$** | **0.582** | **0.425** | ✅ **BAŞARILI** |
| **Kaynak Cümle Bağlantı Oranı** | **$\ge \%90.0$** | **%100.0** | **%100.0** | ✅ **BAŞARILI** |
| **İşlem Süresi (10 dk kayıt için)** | **$\le 180.0\text{ sn}$** | **6.8 sn** | **6.4 sn** | ✅ **BAŞARILI** |

---

### 🔍 Düşük Çıkabilecek Durumlar ve Yapılan İyileştirmeler (Hata Yönetimi)

1. **Türkçe-İngilizce Karışık Teknik Terimler (Code-Switching):**
   - *Sorun:* Whisper, "PostgreSQL", "Docker", "multi-tenancy" gibi yabancı terimleri Türkçe fonetiğe göre yanlış yazabiliyordu (WER yükseliyordu).
   - *Çözüm:* `src/terms.py` içerisine RapidFuzz/Levenshtein tabanlı bulanık eşleştirme ve sözlük enjeksiyonu eklendi. Terim doğruluğu **%100'e** ulaştı.

2. **Göreli Tarihlerin Çözümlenmesi ("Haftaya Cuma", "Yarın"):**
   - *Sorun:* "Ahmet haftaya Cuma bitirecek" ifadesi doğrudan bırakıldığında takvim entegrasyonu yapılamıyordu.
   - *Çözüm:* `src/dates.py` modülü geliştirildi. Toplantı tarihini (`meeting_date`) baz alarak hem Türkçe ("haftaya cuma", "yarın", "3 gün sonra") hem de İngilizce ("tomorrow", "next week", "next friday") göreli ifadeleri ISO takvim tarihine (`2026-11-27`) dönüştürmektedir.

3. **LLM Halüsinasyonuna Karşı Doğrulama (Grounding):**
   - *Sorun:* Dil modellerinin transkriptte olmayan hayali görevler uydurma riski.
   - *Çözüm:* Çıkarılan her göreve transkriptteki **kaynak cümle (source sentence)** zorunluluğu getirildi ve cümlenin metinde birebir varlığı (`verified: True`) kontrol edilerek kaynak bağlama oranı **%100'e** çıkarıldı.

4. **Sorumlusu Belirsiz Görevler:**
   - *Sorun:* "Login hatası düzeltilmeli" cümlesinde kimin yapacağı açıkça söylenmediğinde modelin rastgele isim ataması.
   - *Çözüm:* Cümlede katılımcı adı yoksa sorumlu açıkça **`atanmadı`** olarak etiketlenmektedir.

---

## 🚀 Benchmark ve Testleri Çalıştırma

Tüm değerlendirme metriklerini yerel ortamınızda test etmek için:

```bash
# Tüm test setini (Türkçe + İngilizce) çalıştırıp karşılaştırmak için:
python src/run_baseline.py --all

# Sadece Türkçe toplantı setini test etmek için:
python src/run_baseline.py --id m001_tr

# Sadece İngilizce teknik toplantı setini test etmek için:
python src/run_baseline.py --id m002_en

# Gemini LLM destekli görev çıkarımını test etmek için:
python src/run_baseline.py --all --llm
```

---

## 💻 Kullanım (Canlı Asistan)

YouTube veya toplantı bağlantısıyla uçtan uca transkript ve not üretmek için:

```bash
python main.py "https://www.youtube.com/watch?v=Amow8BJm5Go"
```

Çıktı `output/` klasörüne iki bölümlü olarak kaydedilir:
* **BÖLÜM 1:** Whisper AI ile çıkarılmış zaman damgalı `[00:00]` tam transkript.
* **BÖLÜM 2:** Google Gemini ile çıkarılmış yapılandırılmış ders notu, özet, anahtar kavramlar ve sınav/mülakat soruları.

---

## 🛠️ Teknoloji Yığını

* **Konuşma Tanıma (ASR):** Faster-Whisper (OpenAI Whisper + CTranslate2 int8/CUDA)
* **Büyük Dil Modeli (LLM):** Google Gemini 3.5 Flash / Flash-Lite / 2.5 Flash
* **Ses & Medya İşleme:** yt-dlp, FFmpeg, PyAV
* **Değerlendirme & NLP:** JiWER, RapidFuzz, Python Dateutil, Pandas

---

## 📄 Lisans
Bu proje [Yapay Zeka ve Veri Mühendisliği Tasarımı Dersi](https://github.com/Enesakkus33/Yapay_Zeka_Ve_Veri_Muhendisligi_tasarimi-Toplanti_Asistani) kapsamında açık kaynak olarak geliştirilmiştir.
