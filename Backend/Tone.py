# Backend/Tone.py
_current_tone = None  # one of: None, "cheerful", "assistant", "newscast", "calm", "empathetic"

def set_tone(tone: str | None):
    global _current_tone
    _current_tone = tone

def get_tone() -> str | None:
    return _current_tone
