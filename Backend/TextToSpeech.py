import pygame
import random
import pyttsx3
import os
import time
from dotenv import load_dotenv
from pathlib import Path

# Edge TTS for expressive SSML
try:
    import asyncio
    import edge_tts
    _EDGE_TTS_AVAILABLE = True
except Exception:
    _EDGE_TTS_AVAILABLE = False

# Tone state accessor (no signature changes elsewhere)
try:
    from Backend.Tone import get_tone, set_tone
except Exception:
    def get_tone(): return None
    def set_tone(v): pass

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "Data"
DATA_DIR.mkdir(exist_ok=True)
SPEECH_MP3_FILE = str(DATA_DIR / "speech.mp3")  # Edge TTS target
SPEECH_WAV_FILE = str(DATA_DIR / "speech.wav")  # pyttsx3 target

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

load_dotenv(PROJECT_ROOT / ".env")
AssistantVoice = os.getenv("AssistantVoice")  # not used by edge-tts; pyttsx3 will auto-pick best

# -------- Local TTS (pyttsx3) with tone tweaks --------
def create_tts_engine():
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        print("\n🎤 Available voices on your system:")
        for i, voice in enumerate(voices):
            print(f"   {i}: {voice.name}")

        siri_voice_found = False
        premium_voices = [
            'cortana', 'aria', 'emma', 'jenny', 'guy', 'nova',
            'natural', 'neural', 'premium', 'enhanced', 'high quality'
        ]
        for preference in premium_voices:
            for voice in voices:
                if preference in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    siri_voice_found = True
                    print(f"✅ Found premium voice: {voice.name}")
                    break
            if siri_voice_found:
                break

        if not siri_voice_found:
            best_windows_voices = ['zira', 'hazel', 'susan']
            for preference in best_windows_voices:
                for voice in voices:
                    if preference in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        siri_voice_found = True
                        print(f"✅ Selected best available voice: {voice.name}")
                        break
                if siri_voice_found:
                    break

        if not siri_voice_found and len(voices) > 1:
            engine.setProperty('voice', voices[1].id)
            print(f"✅ Using fallback voice: {voices[1].name}")
        elif not siri_voice_found and len(voices) > 0:
            engine.setProperty('voice', voices[0].id)
            print(f"✅ Using default voice: {voices[0].name}")

        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        return engine
    except Exception as e:
        print(f"TTS Engine error: {e}")
        return None

def _apply_tone_local(engine, tone: str | None):
    # Slower, clearer fallback; audible but not exaggerated
    try:
        base_rate = 125   # slower overall WPM
        base_vol  = 0.9
        rate, vol = base_rate, base_vol

        if tone == "cheerful":
            rate = int(base_rate * 1.08)    # ~+8%
            vol  = min(1.0, base_vol + 0.04)
        elif tone == "newscast":
            rate = int(base_rate * 1.03)    # ~+3%
            vol  = min(1.0, base_vol + 0.02)
        elif tone == "calm":
            rate = int(base_rate * 0.88)    # ~-12%
            vol  = max(0.0, base_vol - 0.04)
        elif tone == "empathetic":
            rate = int(base_rate * 0.92)    # ~-8%
        elif tone == "assistant":
            rate = int(base_rate * 0.98)    # ~-2%

        engine.setProperty('rate', rate)
        engine.setProperty('volume', vol)
    except Exception:
        pass

# -------- Edge TTS expressive synthesis via SSML --------
def _edge_params_from_tone(tone: str | None):
    # Use percent for cross-compatibility with edge-tts
    if tone == "cheerful":
        voice = os.getenv("EDGE_TTS_VOICE_CHEERFUL", "en-US-JennyNeural")
        style, styledegree = "cheerful", "2"
        rate, pitch, volume = "+6%", "+2%", "+0%"
    elif tone == "newscast":
        voice = os.getenv("EDGE_TTS_VOICE_NEWS", "en-US-GuyNeural")
        style, styledegree = "newscast", "2"
        rate, pitch, volume = "+2%", "0%", "+0%"
    elif tone == "calm":
        voice = os.getenv("EDGE_TTS_VOICE_CALM", "en-US-AriaNeural")
        style, styledegree = "calm", "2"
        rate, pitch, volume = "-10%", "-2%", "+0%"
    elif tone == "empathetic":
        voice = os.getenv("EDGE_TTS_VOICE_EMPATHETIC", "en-US-AriaNeural")
        style, styledegree = "empathetic", "2"
        rate, pitch, volume = "-6%", "0%", "+0%"
    elif tone == "assistant":
        voice = os.getenv("EDGE_TTS_VOICE_ASSISTANT", "en-US-AndrewNeural")
        style, styledegree = "assistant", "2"
        rate, pitch, volume = "-2%", "0%", "+0%"
    else:
        voice = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")
        style, styledegree = None, None
        rate, pitch, volume = "+0%", "0%", "+0%"
    return voice, style, styledegree, rate, pitch, volume

def _build_ssml(text: str, voice: str, style: str | None, styledegree: str | None, rate: str, pitch: str, volume: str) -> str:
    # Add gentle pauses and emphasis for human-like delivery
    import re

    def decorate(txt: str, tone: str | None):
        # Emphasize common interjections without changing displayed text
        interj = r"\b(okay|ok|sure|alright|got it|no problem|understood)\b"
        txt = re.sub(interj, r"<emphasis level='moderate'>\1</emphasis>", txt, flags=re.IGNORECASE)
        # Add short pause after first short sentence for clarity
        parts = re.split(r"([.!?])", txt, maxsplit=1)
        if len(parts) >= 3 and len(parts[0]) <= 60:
            txt = f"{parts[0]}{parts[1]} <break time='250ms'/>{''.join(parts[2:])}"
        # Tone-specific pacing
        if tone == "cheerful":
            txt = f"<break time='100ms'/>{txt}"
        elif tone == "newscast":
            txt = txt.replace(",", ", <break time='120ms'/>")
        elif tone in ("calm", "empathetic"):
            txt = txt.replace(",", ", <break time='180ms'/>")
        return txt

    # Build inner with tone-aware decorations
    # We derive tone from style name if present.
    tone_hint = style if style else None
    inner_text = decorate(text, tone_hint)

    prosody_open = f"<prosody rate='{rate}' pitch='{pitch}' volume='{volume}'>"
    prosody_close = "</prosody>"

    if style:
        express_open = f"<mstts:express-as style='{style}'" + (f" styledegree='{styledegree}'>" if styledegree else ">")
        express_close = "</mstts:express-as>"
        inner = f"{express_open}{prosody_open}{inner_text}{prosody_close}{express_close}"
    else:
        inner = f"{prosody_open}{inner_text}{prosody_close}"

    return (
        "<speak version='1.0' "
        "xmlns='http://www.w3.org/2001/10/synthesis' "
        "xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>"
        f"<voice name='{voice}'>{inner}</voice>"
        "</speak>"
    )

async def _edge_tts_to_file(text: str, out_mp3: str, tone: str | None):
    voice, style, styledegree, rate, pitch, volume = _edge_params_from_tone(tone)
    ssml = _build_ssml(text, voice, style, styledegree, rate, pitch, volume)

    # Minimal: convert semitone (e.g., "+2st") to percent (e.g., "+12%") so Communicate accepts it
    def _pct(s: str | None, default: str) -> str:
        if not s: return default
        s = s.strip()
        if s.endswith("st"):  # semitone -> percent
            try:
                n = float(s[:-2].strip())
                p = (2**(n/12.0) - 1.0) * 100.0  # 1 st ≈ +5.95%
                return f"{p:+.0f}%"
            except Exception:
                return default
        if s.endswith("%"):  # already percent
            return s
        try:                 # plain number (e.g., "0" or "+4")
            return f"{float(s):+.0f}%"
        except Exception:
            return default

    rate   = _pct(rate,   "+0%")
    pitch  = _pct(pitch,  "0%")
    volume = _pct(volume, "+0%")

    try:
        communicate = edge_tts.Communicate(ssml, voice=voice, rate=rate, pitch=pitch, volume=volume, ssml=True)
    except TypeError:
        communicate = edge_tts.Communicate(ssml, voice=voice, rate=rate, pitch=pitch, volume=volume)
    await communicate.save(out_mp3)

# -------- Synthesis entry (Edge first, then local) --------
async def TextToAudioFile(text) -> None:
    # Clean previous outputs
    for p in (SPEECH_MP3_FILE, SPEECH_WAV_FILE):
        try:
            if os.path.exists(p): os.remove(p)
        except Exception:
            pass

    used_edge = False
    try:
        if _EDGE_TTS_AVAILABLE and not os.getenv("EDGE_TTS_DISABLED", "").strip():
            await _edge_tts_to_file(text, SPEECH_MP3_FILE, get_tone())
            time.sleep(0.2)
            if os.path.exists(SPEECH_MP3_FILE) and os.path.getsize(SPEECH_MP3_FILE) > 0:
                used_edge = True
        else:
            used_edge = False
    except Exception as e:
        print(f"[edge-tts] fallback due to: {e}")
        used_edge = False

    if not used_edge:
        try:
            engine = create_tts_engine()
            if engine:
                _apply_tone_local(engine, get_tone())
                # IMPORTANT: save local synthesis to WAV, not MP3
                engine.save_to_file(text, SPEECH_WAV_FILE)
                engine.runAndWait()
                engine.stop()
                time.sleep(0.5)
        except Exception as e:
            print(f"TTS Error: {e}")

    # reset tone for next call
    try: set_tone(None)
    except Exception: pass

# -------- Playback (auto-pick Edge MP3 or local WAV) --------
def _pick_audio_path() -> str | None:
    if os.path.exists(SPEECH_MP3_FILE) and os.path.getsize(SPEECH_MP3_FILE) > 0:
        return SPEECH_MP3_FILE
    if os.path.exists(SPEECH_WAV_FILE) and os.path.getsize(SPEECH_WAV_FILE) > 0:
        return SPEECH_WAV_FILE
    return None

def TTS(Text, func=lambda r=None: True):
    try:
        import asyncio
        asyncio.run(TextToAudioFile(Text))

        pygame.mixer.quit()
        time.sleep(0.2)
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()
        time.sleep(0.2)

        path = _pick_audio_path()
        if not path:
            print("❌ Audio file not found!")
            return False

        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play(fade_ms=0)
        print("🔊 Playing audio...")

        while pygame.mixer.music.get_busy():
            if func() == False:
                pygame.mixer.music.stop()
                break
            pygame.time.wait(50)

        print("✅ Audio playback completed!")
        return True

    except Exception as e:
        print(f"❌ Error in TTS: {e}")
        return False

    finally:
        try:
            func(False)
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            time.sleep(0.2)
        except Exception as e:
            print(f"Cleanup error: {e}")

def TextToSpeech(Text, func=lambda r=None: True):
    Data = str(Text).split(".")
    responses = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "Sir, you'll find more text on the chat screen for you to see.",
        "The rest of the answer is now on the chat screen, sir.",
        "Sir, please look at the chat screen, the rest of the answer is there.",
        "You'll find the complete answer on the chat screen, sir.",
        "The next part of the text is on the chat screen, sir.",
        "Sir, please check the chat screen for more information.",
        "There's more text on the chat screen for you, sir.",
        "Sir, take a look at the chat screen for additional text.",
        "You'll find more to read on the chat screen, sir.",
        "Sir, check the chat screen for the rest of the text.",
        "The chat screen has the rest of the text, sir.",
        "There's more to see on the chat screen, sir, please look.",
        "Sir, the chat screen holds the continuation of the text.",
        "You'll find the complete answer on the chat screen, kindly check it out sir.",
        "Please review the chat screen for the rest of the text, sir.",
        "Sir, look at the chat screen for the complete answer."
    ]
    if len(Data) > 4 and len(Text) >= 250:
        TTS(" ".join(Text.split(".")[0:2]) + ". " + random.choice(responses), func)
    else:
        TTS(Text, func)

if __name__ == "__main__":
    print(" 🎤 TextToSpeech Ready!")
    while True:
        try:
            user_input = input("\n Enter the text: ")
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("👋 Goodbye!")
                break
            TextToSpeech(user_input)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f" Error: {e}")
