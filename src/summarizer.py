"""
summarizer.py
-------------
Gemini Native Audio ile:
1. Videonun baştan aşağı birebir TAM TRANSKRİPTİNİ (Zaman damgalı [00:00])
2. Yapılandırılmış profesyonel DERS NOTLARINI ve ÖZETİNİ
tek seferde üreten modül.
"""

import os
import time
import logging
from pathlib import Path
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen, eğitim videolarını dinleyip hem EKSİKSİZ BİREBİR TRANSKRİPTİNİ çıkaran hem de profesyonel DERS NOTLARI hazırlayan uzman bir asistansın.

Sana verilen ses kaydını dikkatle dinle ve çıktıyı tam olarak şu iki ana bölüm halinde Markdown olarak üret:

# 📚 [Video / Ders Konu Başlığı]

---

# 🎙️ BÖLÜM 1: VİDEONUN BİREBİR TAM TRANSKRİPTİ
(Bu bölümde videoda konuşulan HER ŞEYİ, kelimesi kelimesine, baştan sona eksiksiz olarak dök. 
Asla özetleme, atlama veya kısaltma yapma! Konuşulan her paragrafın/cümlenin başına zaman damgasını [00:00] formatında ekle.)

Örnek format:
[00:00] Merhaba arkadaşlar...
[00:15] Konuşmacının söylediği sonraki cümle...
[00:45] ...
(Videonun sonuna kadar kelimesi kelimesine devam et)

---

# 🎓 BÖLÜM 2: YAPAY ZEKA DERS NOTLARI VE ANALİZ

## 🎯 Genel Özet
(Videonun ne anlattığını açıklayan 2-4 cümlelik net özet)

## 🗂️ İşlenen Ana Başlıklar
(Videoda anlatılan ana konuları kronolojik ve numaralı liste olarak yaz)

## 📖 Kapsamlı Notlar ve Açıklamalar
(Her ana başlığı alt başlık olarak aç. Önemli terimleri **kalın** yap.
 Anlatılan formülleri, teknik kavramları, metaforları ve örnekleri detaylıca açıkla.
 Varsa kod veya komut örneklerini ``` blokları içinde yaz.)

## ⚡ Anahtar Kavramlar Sözlüğü
(Videoda geçen kritik teknik terimlerin ve tanımlarının madde işaretli listesi)

## ❓ Olası Sınav / Mülakat Soruları
(Bu konudan gelebilecek, konuyu pekiştiren 3-5 adet soru ve cevapları)

## 🚀 Sonraki Adımlar ve Tavsiyeler
(Öğrencinin bu konuyu pekiştirmesi için öneriler)
"""


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise EnvironmentError("GEMINI_API_KEY bulunamadı. Lütfen .env dosyanızı kontrol edin.")
    return genai.Client(api_key=api_key)


def generate_notes_from_audio(
    audio_path: str,
    video_title: str = "",
    model_name: str | None = None,
) -> str:
    client = _get_client()
    audio_file_path = Path(audio_path)

    logger.info(f"[Summarizer] 🚀 Ses dosyası Gemini'ye aktarılıyor ({audio_file_path.name})...")
    uploaded_file = client.files.upload(file=str(audio_file_path))
    logger.info(f"[Summarizer] Dosya yüklendi (ID: {uploaded_file.name}).")

    while uploaded_file.state.name == "PROCESSING":
        time.sleep(1)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        raise RuntimeError("Ses dosyası Gemini tarafında işlenemedi.")

    user_prompt = (
        f"Video Başlığı: {video_title}\n\n"
        "Lütfen yönergeye harfiyen uyarak:\n"
        "1. BÖLÜM 1'de videoda geçen her kelimeyi zaman damgalarıyla [00:00] BAŞTAN SONA EKSİKSİZ, KELİMESİ KELİMESİNE TRANSKRİPTE ET.\n"
        "2. BÖLÜM 2'de kapsamlı ders notlarını ve özetini çıkar."
    )

    # Farklı mimarilerdeki kararlı modeller (Flash + Pro karması)
    candidate_models = [
        "gemini-2.5-pro",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest",
        "gemini-pro-latest",
    ]
    if model_name and model_name not in candidate_models:
        candidate_models.insert(0, model_name)

    try:
        last_error = None
        for target_model in candidate_models:
            for attempt in range(2):
                logger.info(f"[Summarizer] 🧠 Gemini ({target_model}) sesi dinliyor... (Deneme {attempt+1})")
                try:
                    response = client.models.generate_content(
                        model=target_model,
                        contents=[uploaded_file, user_prompt],
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.2,
                            max_output_tokens=8192,
                        ),
                    )
                    if response.text and response.text.strip():
                        logger.info(f"[Summarizer] ✅ Transkript ve ders notu başarıyla üretildi! ({target_model})")
                        return response.text
                except Exception as e:
                    last_error = e
                    # 503 yoğunluk hatasında 5 saniye dinlen ve tekrar dene
                    if "503" in str(e) or "high demand" in str(e).lower():
                        logger.warning(f"[Summarizer] {target_model} yoğunlukta, 5 saniye bekleniyor...")
                        time.sleep(5)
                    else:
                        break # Farklı hataysa sonraki modele geç

        raise last_error
    finally:
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass
