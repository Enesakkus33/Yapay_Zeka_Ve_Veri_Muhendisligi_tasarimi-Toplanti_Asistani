"""Baseline ASR: faster-whisper (Whisper) + VAD + initial_prompt (Türkçe, code-switching için sözlük)."""
import os, time

def transcribe(audio_path: str, glossary: list[str] | None = None, model_size: str | None = None):
    from faster_whisper import WhisperModel
    model_size = model_size or os.getenv("WHISPER_MODEL", "small")
    model = WhisperModel(model_size, compute_type="int8")
    prompt = ("Türkçe toplantı. Terimler: " + ", ".join(glossary)) if glossary else None
    t0 = time.time()
    segs, _ = model.transcribe(audio_path, language="tr", vad_filter=True,
                               initial_prompt=prompt, condition_on_previous_text=False)
    out = []
    for s in segs:
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "low_conf": s.avg_logprob < -1.0 or s.no_speech_prob > 0.6})
    return out, time.time() - t0
