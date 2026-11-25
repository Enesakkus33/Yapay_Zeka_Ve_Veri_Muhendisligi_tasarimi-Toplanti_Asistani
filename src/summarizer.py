"""
summarizer.py
-------------
Whisper'ın çıkardığı ham transkripti alıp Google Gemini ile
yapılandırılmış profesyonel Türkçe ders notu, özet ve kavramlar sözlüğüne dönüştürür.
"""

import os
import time
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen, konuşma transkriptlerini inceleyip bunlardan kapsamlı, profesyonel ders notları ve özetler çıkaran uzman bir akademisyensin.

Sana verilen transkripti baştan sona dikkatlice oku ve aşağıdaki yapıda Türkçe, akademik kalitede bir ders/toplantı notu üret:

## 🎯 Genel Özet
(Videonun/konuşmanın amacını ve ne anlattığını açıklayan 2-4 cümlelik net özet)

## 🗂️ İşlenen Ana Başlıklar
(Konuşmada anlatılan ana konuları kronolojik ve numaralı liste olarak yaz)

## 📖 Kapsamlı Notlar ve Açıklamalar
(Her ana başlığı alt başlık olarak aç. Önemli terimleri **kalın** yap.
 Anlatılan formülleri, teknik kavramları, metaforları ve örnekleri detaylıca açıkla.
 Varsa kod veya komut örneklerini ``` blokları içinde yaz.)

## ⚡ Anahtar Kavramlar Sözlüğü
(Konuşmada geçen kritik teknik terimlerin ve tanımlarının madde işaretli listesi)

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


def generate_study_notes(
    transcript_text: str,
    video_title: str = "",
    model_name: str | None = None,
) -> str:
    """
    Whisper transkriptini Gemini'ye metin olarak gönderir ve ders notunu üretir.
    Ses yüklemesi yapmadığı için 1-2 saniyede, sıfır kota yüküyle çalışır!
    """
    if model_name is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    client = _get_client()

    user_prompt = (
        f"Video / Toplantı Başlığı: {video_title}\n\n"
        f"Aşağıda konuşmanın Whisper tarafından çıkarılmış tam transkripti bulunmaktadır:\n"
        f"----------------------------------------\n"
        f"{transcript_text}\n"
        f"----------------------------------------\n\n"
        f"Lütfen yukarıdaki transkripti analiz ederek yönergeye uygun Türkçe ders notunu oluştur."
    )

    candidate_models = [
        model_name,
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
    ]
    candidate_models = list(dict.fromkeys(candidate_models))

    last_error = None
    for target_model in candidate_models:
        logger.info(f"[Gemini] 🧠 Ders notu üretiliyor (Model: {target_model})...")
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=8192,
                ),
            )
            if response.text and response.text.strip():
                logger.info(f"[Gemini] ✅ Ders notu üretildi! (Model: {target_model})")
                return response.text
        except Exception as e:
            last_error = e
            logger.warning(f"[Gemini] {target_model} yanıt vermedi ({e}), sonraki modele geçiliyor...")
            time.sleep(1)

    raise last_error
