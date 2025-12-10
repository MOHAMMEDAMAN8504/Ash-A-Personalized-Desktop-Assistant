import os
import warnings
import pygame
import logging
from pathlib import Path
import json

logging.getLogger().setLevel(logging.ERROR)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_DISABLE_SEGMENT_REDUCTION'] = '1'
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'
import sys
if hasattr(sys.stdout, 'buffer'):
    os.environ['CHROME_LOG_FILE'] = 'NUL'
import subprocess
import threading
import tensorflow as tf

# --- ADDED: concurrency primitive (no changes to existing logic) ---
from threading import Lock
PIPELINE_LOCK = Lock()
# --- END ADD ---

# ✅ FIX FILE PATHS - ONLY ADDITION TO YOUR CODE
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "Data"
DATA_DIR.mkdir(exist_ok=True)
CHAT_LOG_FILE = DATA_DIR / "ChatLog.json"

# ✅ FIX IMAGE GENERATION SUBPROCESS PATH
IMAGE_GENERATION_SCRIPT = PROJECT_ROOT / "Backend" / "ImageGeneration.py"

# Suppress TensorFlow warnings and delegate errors
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

# Force CPU-only inference globally
tf.config.set_visible_devices([], 'GPU')
print("🔧 TensorFlow configured for CPU-only inference")

from Frontend.GUI import ( 
GraphicalUserInterface,
SetAssistantStatus,
ShowTextToScreen,
TempDirectoryPath,
SetMicrophoneStatus,
AnswerModifier,
QueryModifier,
GetMicrophoneStatus,
GetAssistantStatus )
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from  Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
# NEW: tone setter (only addition)
from Backend.Tone import set_tone
from dotenv import load_dotenv                  # ✅ CHANGED: Import load_dotenv instead of dotenv_values
from asyncio import run 
from time import sleep
from Backend.HotwordDetection import start_hotword_detection, stop_hotword_detection

# Import centralized config
from Backend.Config import Username, Assistantname

# --- ADDED: RL policy (no behavior change if anything fails) ---
from Backend.RLPolicy import RLPolicy
policy = RLPolicy()
# --- END ADD ---

# --- ADDED: typed-input trigger files (reuse existing Frontend/Files handshake) ---
TYPED_FLAG_PATH  = Path(TempDirectoryPath('TypedTrigger.flag'))
TYPED_INPUT_PATH = Path(TempDirectoryPath('TypedInput.data'))
try:
    if not TYPED_FLAG_PATH.exists():
        TYPED_FLAG_PATH.write_text("0", encoding="utf-8")
    if not TYPED_INPUT_PATH.exists():
        TYPED_INPUT_PATH.write_text("", encoding="utf-8")
except Exception:
    pass
# --- END ADD ---

DefaultMessage = f'''{Username} : Hello {Assistantname}, How are you?
{Assistantname} : Welcome {Username}. I am doing well. How may i help you?'''
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]

# ✨ Session tracking variables for greeting
session_started = False
conversation_count = 0

def ShowDefaultChatIfNoChats():
    # ✅ FIXED PATH - Open ChatLog.json from absolute path
    try:
        File = open(CHAT_LOG_FILE, "r", encoding='utf-8')
        content = File.read()
        File.close()
        
        if len(content)<5:
            with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
                file.write("")

            with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
                file.write(DefaultMessage)
    except FileNotFoundError:
        # Create empty ChatLog if it doesn't exist
        with open(CHAT_LOG_FILE, 'w', encoding='utf-8') as file:
            file.write('[]')
        
        with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
            file.write("")

        with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
            file.write(DefaultMessage)

def ReadChatLogJson():
    with open(CHAT_LOG_FILE, 'r', encoding='utf-8') as file:  # ✅ FIXED PATH
        chatlog_data = json.load(file)
    return chatlog_data

def ChatLogIntegration():
    json_data = ReadChatLogJson()
    formatted_chatlog = ""
    for entry in json_data:
        if entry["role"] == "user":
            formatted_chatlog += f"User: {entry['content']}\n"
        elif entry["role"] == "assistant":
            formatted_chatlog += f"Assistant: {entry['content']}\n"
    formatted_chatlog = formatted_chatlog.replace("User", Username + " ")
    formatted_chatlog = formatted_chatlog.replace("Assistant", Assistantname + " ")

    with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
        file.write(AnswerModifier(formatted_chatlog))

def ShowChatsOnGUI():
    File = open(TempDirectoryPath('Database.data'),"r", encoding='utf-8')
    Data = File.read()
    if len(str(Data))>0:
        lines = Data.split('\n')
        result = '\n' .join(lines)
        File.close()
        File = open(TempDirectoryPath( 'Responses.data'), "w", encoding='utf-8')
        File.write(result)      
        File.close()

def InitialExecution():
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    ShowDefaultChatIfNoChats()
    ChatLogIntegration()
    ShowChatsOnGUI()

InitialExecution()

def generate_greeting():
    """Generate personalized greeting for fresh conversation"""
    import datetime
    import random
    
    current_hour = datetime.datetime.now().hour
    
    if 5 <= current_hour < 12:
        time_greeting = "Good morning"
    elif 12 <= current_hour < 17:
        time_greeting = "Good afternoon"
    elif 17 <= current_hour < 21:
        time_greeting = "Good evening"
    else:
        time_greeting = "Good night"
    
    greetings = [
        f"{time_greeting}, {Username}! How can I assist you today?",
        f"Hello {Username}! I'm {Assistantname}, ready to help.",
        f"{time_greeting}, {Username}! Welcome back.",
        f"Hi {Username}! {Assistantname} here, what can I do for you?",
        f"{time_greeting}! I'm {Assistantname}, your AI assistant."
    ]
    
    return random.choice(greetings)

# --- ADDED: Quick canned replies for casual inputs (centralized for both paths) ---
def _quick_casual_reply(text: str) -> str | None:
    key = (text or "").strip().lower()
    key = key.rstrip(".!?")  # normalize simple punctuation
    aliases = {
        "thank u": "thank you",
        "thx": "thanks",
        "thanx": "thanks",
        "k": "ok",
        "oky": "okay",
        "gm": "good morning",
        "gn": "good night"
    }
    key = aliases.get(key, key)
    canned = {
        "hello": "Hello! How can I assist you today?",
        "hi": "Hi there! What can I help you with?",
        "hey": "Hey! How can I help you?",
        "thanks": "You're welcome!",
        "thank you": "You're welcome!",
        "bye": "Goodbye! Have a great day!",
        "goodbye": "Goodbye! Take care!",
        "ok": "Understood. Is there anything else I can help with?",
        "okay": "Got it! Anything else you need?",
        "yes": "Great! How can I assist you further?",
        "no": "Alright! Let me know if you need anything else."
    }
    return canned.get(key)
# --- END ADD ---

def MainExecution():
    global session_started, conversation_count  # ✨ Add this line
    
    # ✨ GREETING LOGIC - Add this block at the very beginning
    if not session_started:
        greeting = generate_greeting()
        ShowTextToScreen(f"{Assistantname} : {greeting}")
        SetAssistantStatus("Greeting...")
        set_tone("cheerful")  # NEW
        TextToSpeech(greeting)
        SetMicrophoneStatus("False")  # ← ADDED LINE
        session_started = True
        conversation_count = 1
        return True
    
    # ✨ Increment conversation count
    conversation_count += 1
    
    # YOUR EXISTING CODE STARTS HERE (keep everything exactly the same)
    TaskExecution = False
    ImageExecution = False
    ImageGenerationQuery = ""

    SetAssistantStatus("Listening...")
    Query = SpeechRecognition()
    ShowTextToScreen(f"{Username} : {Query}")

    # --- ADDED: Short-circuit canned replies for casual utterances (voice) ---
    _ans = _quick_casual_reply(Query)
    if _ans:
        SetAssistantStatus("Answering ...")
        set_tone("cheerful")  # NEW
        ShowTextToScreen(f"{Assistantname} : {_ans}")
        TextToSpeech(_ans)
        SetMicrophoneStatus("False")
        return True
    # --- END ADD ---

    SetAssistantStatus("Thinking ...")
    Decision = FirstLayerDMM(Query)

    print("")
    print(f"Decision : {Decision}")
    print("")

    G = any([i for i in Decision if i.startswith("general")])
    R = any([i for i in Decision if i.startswith("realtime")])

    Mearged_query = " and ".join(
        [" ".join(i.split()[1:]) for i in Decision if i.startswith("general") or i.startswith("realtime")]
    )

    # STRICT: trigger only on "generate image" or "create image"
    for queries in Decision:
        ql = queries.lower().strip()
        if ql.startswith("generate image") or ql.startswith("create image"):
            ImageGenerationQuery = str(queries)
            ImageExecution = True
            break

    for queries in Decision:
        if TaskExecution == False:
            if any(queries.startswith(func) for func in Functions):
                run(Automation(list(Decision)))
                TaskExecution = True
                # ✅ MICROPHONE FIX: Turn off mic after automation
                SetMicrophoneStatus("False")
                return True

    if ImageExecution == True:
        # ... keep all your existing image generation code ...
        with open(str(PROJECT_ROOT / "Frontend" / "Files" / "ImageGeneration.data"), "w") as file:  # ✅ FIXED PATH
            file.write(f"{ImageGenerationQuery},True")

        try:
            print(" Starting image generation subprocess...")
        
            # ✅ FIXED SUBPROCESS PATH - Use absolute path
            p1 = subprocess.Popen(
                [sys.executable, str(IMAGE_GENERATION_SCRIPT)],  # ✅ FIXED PATH
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE, 
                shell=False
            )
        
            subprocesses.append(p1)
        
            stdout, stderr = p1.communicate(timeout=120)
        
            if p1.returncode == 0:
                print(" Image generation completed successfully")
            
                if os.path.exists(str(DATA_DIR)):  # ✅ FIXED PATH
                    images = [f for f in os.listdir(str(DATA_DIR)) if f.endswith('.jpg') or f.endswith('.png')]
                    print(f" Generated {len(images)} images")
                else:
                    print(" Data folder not found")
            else:
                print(f" Image generation failed:")
                print(f"Return code: {p1.returncode}")
                if stderr:
                    print(f"Error: {stderr.decode()}")
                if stdout:
                    print(f"Output: {stdout.decode()}")
            
        except subprocess.TimeoutExpired:
            p1.kill()
            print(" Image generation timed out after 2 minutes")
        except Exception as e:
            print(f" Error starting ImageGeneration.py: {e}")
        
        # ✅ MICROPHONE FIX: Turn off mic after image generation
        SetMicrophoneStatus("False")
        return True

    # --- RL: only adjusts internal k for realtime; routing logic unchanged ---
    if G and R or R:
        try:
            from Backend.RealtimeSearchEngine import set_top_k
            choice_search = policy.choose("search")
            set_top_k(choice_search.get("retrieval_k", 5))
        except Exception:
            choice_search = {"retrieval_k": 5}
        SetAssistantStatus("Searching ... ")
        Answer = RealtimeSearchEngine(QueryModifier(Mearged_query))
        ShowTextToScreen(f"{Assistantname} : {Answer}")
        SetAssistantStatus("Answering ... ")
        set_tone("newscast")  # NEW
        TextToSpeech(Answer)
        try:
            policy.reward("search", choice_search, success=bool(Answer and str(Answer).strip()))
        except Exception:
            pass
        SetMicrophoneStatus("False")  # ← ADDED LINE
        return True
    
    else:
        for Queries in Decision:
            
            if "general" in Queries:
                # --- RL: only adjusts temperature; logic unchanged ---
                try:
                    from Backend.Chatbot import set_temperature
                    choice_chat = policy.choose("chat")
                    set_temperature(choice_chat.get("temperature", 0.7))
                except Exception:
                    choice_chat = {"temperature": 0.7}
                SetAssistantStatus ("Thinking ... ")
                QueryFinal = Queries.replace("general " ,"")
                Answer = ChatBot(QueryModifier(QueryFinal))
                ShowTextToScreen(f"{Assistantname} : {Answer}")
                SetAssistantStatus("Answering ...")
                set_tone("assistant")  # NEW
                TextToSpeech(Answer)
                try:
                    policy.reward("chat", choice_chat, success=bool(Answer and str(Answer).strip()))
                except Exception:
                    pass
                SetMicrophoneStatus("False")  # ← ADDED LINE
                return True
            
            elif "realtime" in Queries:
                # --- RL: only adjusts internal k; logic unchanged ---
                try:
                    from Backend.RealtimeSearchEngine import set_top_k
                    choice_search = policy.choose("search")
                    set_top_k(choice_search.get("retrieval_k", 5))
                except Exception:
                    choice_search = {"retrieval_k": 5}
                SetAssistantStatus("Searching ... ")
                QueryFinal = Queries.replace("realtime ", "")
                Answer = RealtimeSearchEngine(QueryModifier(QueryFinal))
                ShowTextToScreen(f"{Assistantname} : {Answer}")
                SetAssistantStatus("Answering ...")
                set_tone("newscast")  # NEW
                TextToSpeech(Answer)
                try:
                    policy.reward("search", choice_search, success=bool(Answer and str(Answer).strip()))
                except Exception:
                    pass
                SetMicrophoneStatus("False")  # ← ADDED LINE
                return True
            
            elif "exit" in Queries:
                QueryFinal = "Okay, Bye!"
                Answer = ChatBot(QueryModifier(QueryFinal))
                ShowTextToScreen(f"{Assistantname} : {Answer}")
                SetAssistantStatus("Answering ...")
                set_tone("calm")  # NEW
                TextToSpeech(Answer)
                SetMicrophoneStatus("False")  # ← ADDED LINE
                
                # ✨ Reset session for next fresh start
                session_started = False
                conversation_count = 0
                
                SetAssistantStatus("Answering ...")
                import os  # ✅ FIXED: Add import os here to prevent "os referenced before assignment"
                os._exit(1)
    
    # ✅ MICROPHONE FIX: Fallback - ensure mic is always turned off at the end
    SetMicrophoneStatus("False")
    return True

# --- ADDED: typed-input pipeline that reuses existing logic and output ---
def RunPipelineFromText(raw_text: str) -> bool:
    global session_started, conversation_count
    with PIPELINE_LOCK:
        try:
            SetMicrophoneStatus("True")  # block wake-word path during handling
            text_in = (raw_text or "").strip()
            if not text_in:
                return True

            # same greeting as voice for fresh session
            if not session_started:
                greeting = generate_greeting()
                ShowTextToScreen(f"{Assistantname} : {greeting}")
                SetAssistantStatus("Greeting...")
                set_tone("cheerful")  # NEW
                TextToSpeech(greeting)
                session_started = True
                conversation_count = 1

                # --- NEW LOGIC: if the first typed text is a casual greeting, stop after greeting ---
                tnorm = text_in.lower().strip().strip(".!?")
                if tnorm in {
                    "hi","hello","hey","heyy","hii","yo","sup",
                    "good morning","good afternoon","good evening","good night"
                }:
                    # do NOT answer the greeting; just end after the spoken greeting
                    return True
                # -------------------------------------------------------------------------------

            else:
                conversation_count += 1

            # --- ADDED: Short-circuit canned replies for casual inputs (typed) ---
            _ans = _quick_casual_reply(text_in)
            if _ans:
                SetAssistantStatus("Answering ...")
                set_tone("cheerful")  # NEW
                ShowTextToScreen(f"{Assistantname} : {_ans}")
                TextToSpeech(_ans)
                return True
            # --- END ADD ---

            SetAssistantStatus("Thinking ...")
            Query = QueryModifier(text_in)
            Decision = FirstLayerDMM(Query)

            G = any(i.startswith("general") for i in Decision)
            R = any(i.startswith("realtime") for i in Decision)
            Mearged_query = " and ".join(
                " ".join(i.split()[1:]) for i in Decision if i.startswith(("general","realtime"))
            )

            # actions first
            if any(i.startswith(tuple(Functions)) for i in Decision):
                run(Automation(list(Decision)))
                return True

            # STRICT: typed image trigger only on "generate image"/"create image"
            img_q = next(
                (
                    q for q in Decision
                    if q.lower().strip().startswith("generate image")
                    or q.lower().strip().startswith("create image")
                ),
                None
            )
            if img_q:
                (PROJECT_ROOT / "Frontend" / "Files" / "ImageGeneration.data").write_text(f"{img_q},True", encoding="utf-8")
                SetAssistantStatus("Generating images ...")
                p = subprocess.Popen([sys.executable, str(IMAGE_GENERATION_SCRIPT)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                p.communicate(timeout=120)
                return True

            # realtime aggregate
            if R or (G and R):
                try:
                    from Backend.RealtimeSearchEngine import set_top_k
                    choice_search = policy.choose("search")
                    set_top_k(choice_search.get("retrieval_k", 5))
                except Exception:
                    choice_search = {"retrieval_k": 5}
                SetAssistantStatus("Searching ... ")
                Answer = RealtimeSearchEngine(QueryModifier(Mearged_query))
                ShowTextToScreen(f"{Assistantname} : {Answer}")
                SetAssistantStatus("Answering ... ")
                set_tone("newscast")  # NEW
                TextToSpeech(Answer)
                try:
                    policy.reward("search", choice_search, success=bool(Answer and str(Answer).strip()))
                except Exception:
                    pass
                return True

            # single branches
            for q in Decision:
                if q.startswith("general "):
                    try:
                        from Backend.Chatbot import set_temperature
                        choice_chat = policy.choose("chat")
                        set_temperature(choice_chat.get("temperature", 0.7))
                    except Exception:
                        choice_chat = {"temperature": 0.7}
                    SetAssistantStatus("Thinking ... ")
                    qf = q.replace("general ", "")
                    Answer = ChatBot(QueryModifier(qf))
                    ShowTextToScreen(f"{Assistantname} : {Answer}")
                    SetAssistantStatus("Answering ...")
                    set_tone("assistant")  # NEW
                    TextToSpeech(Answer)
                    try:
                        policy.reward("chat", choice_chat, success=bool(Answer and str(Answer).strip()))
                    except Exception:
                        pass
                    return True
                if q.startswith("realtime "):
                    try:
                        from Backend.RealtimeSearchEngine import set_top_k
                        choice_search = policy.choose("search")
                        set_top_k(choice_search.get("retrieval_k", 5))
                    except Exception:
                        choice_search = {"retrieval_k": 5}
                    SetAssistantStatus("Searching ... ")
                    qf = q.replace("realtime ", "")
                    Answer = RealtimeSearchEngine(QueryModifier(qf))
                    ShowTextToScreen(f"{Assistantname} : {Answer}")
                    SetAssistantStatus("Answering ...")
                    set_tone("newscast")  # NEW
                    TextToSpeech(Answer)
                    try:
                        policy.reward("search", choice_search, success=bool(Answer and str(Answer).strip()))
                    except Exception:
                        pass
                    return True
                if q == "exit":
                    Answer = ChatBot(QueryModifier("Okay, Bye!"))
                    ShowTextToScreen(f"{Assistantname} : {Answer}")
                    SetAssistantStatus("Answering ...")
                    set_tone("calm")  # NEW
                    TextToSpeech(Answer)
                    session_started = False
                    conversation_count = 0
                    os._exit(1)

            return True
        except Exception as e:
            print(f"[typed] error: {e}")
            return True
        finally:
            SetMicrophoneStatus("False")
# --- END ADD ---

def FirstThread():
    # ✅ START HOTWORD DETECTION
    start_hotword_detection()
    
    # Your existing code stays exactly the same
    while True:
        try:
            # --- ADDED: typed input trigger handling (before mic branch) ---
            if TYPED_FLAG_PATH.exists() and TYPED_FLAG_PATH.read_text(encoding="utf-8").strip() == "1":
                try:
                    text = TYPED_INPUT_PATH.read_text(encoding="utf-8").strip()
                except Exception:
                    text = ""
                TYPED_FLAG_PATH.write_text("0", encoding="utf-8")  # reset immediately
                if text:
                    RunPipelineFromText(text)
                continue
            # --- END ADD ---

            CurrentStatus = GetMicrophoneStatus()

            if CurrentStatus == "True":
                MainExecution()  # Your greeting works perfectly!
            else:
                AIStatus = GetAssistantStatus()
                
                if "Available..." in AIStatus:
                    sleep(0.1)
                else:
                    SetAssistantStatus("Available ...")
                    
        except Exception as e:
            print(f" Thread error: {e}")
            # ✅ MICROPHONE FIX: Turn off mic on errors too
            SetMicrophoneStatus("False")
            sleep(1)
            
        except KeyboardInterrupt:
            print(" Thread stopped by user")
            stop_hotword_detection()  # ✅ CLEANUP
            break

def SecondThread():
    GraphicalUserInterface()

if __name__ == "__main__":
    thread2 = threading.Thread(target=FirstThread, daemon=True)
    thread2.start()
    SecondThread()
