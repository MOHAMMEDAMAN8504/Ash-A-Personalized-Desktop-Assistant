# Import required libraries.
from AppOpener import close, open as appopen
from webbrowser import open as webopen
from pywhatkit import search, playonyt
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from rich import print
from groq import Groq
from pathlib import Path
import webbrowser
import subprocess
import requests
import keyboard
import asyncio
import os


# --- ADDITIVE IMPORTS  ---
import sys
import threading
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlparse, unquote
import ctypes
import winsound
from time import sleep


STOPWATCH_START = None


CANCELLED_ALARMS = set()      # safe labels
CANCELLED_TIMES = set()       # "HH:MM"
def _safe_label(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_")[:64]


#  FILE PATHS 
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "Data"
DATA_DIR.mkdir(exist_ok=True)


#  Load environment variables from absolute path
load_dotenv(PROJECT_ROOT / ".env")
GroqAPIKey = os.getenv("GroqAPIKey")


# Define CSS classes 
classes = ["zCubwf", "hgKElc", "LTKOO sY7ric", "Z0LcW", "gsrt vk_bk FzvWSb YwPhnf", "pelqee",
           "tw-Data-text tw-text-small tw-ta", "IZ6rdc", "O5uR6d LTKOO", "vlzY6d",
           "webanswers-webanswers_table_webanswers-table", "dDoNo ikb4Bb gsrt", "sXLaOe",
           "LWkfKe", "VQF4g", "qv3Wpe", "kno-rdesc", "SPZz6b"]


# Define a user-agent
useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.36 (KHTML, Like Gecko) Chrome/100.0.4896.75 Safari/537.36'


# Groq client
client = Groq(api_key=GroqAPIKey)


# Predefined responses 
professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need-don't hesitate to ask.",
]


# Message buffers 
messages = []
SystemChatBot = [{"role": "system", "content": f"Hello, I am {os.environ.get('Username', 'User')}, You're a content writer. You have to write content like letter, codes, applications, essays, notes, songs, poems etc."}]


# Google search
def GoogleSearch(Topic):
    search(Topic)
    return True


# Content writer
def Content(Topic):
    def OpenNotepad(File):
        default_text_editor = 'notepad.exe'
        subprocess.Popen([default_text_editor, File])


    def ContentWriterAI(prompt):
        messages.append({"role": "user", "content": f"{prompt}"})
        completion = client.chat.completions.create(  
            model="llama-3.1-8b-instant",
            messages=SystemChatBot + messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=1,
            stream=True,
            stop=None
        )
        Answer = ""
        for chunk in completion:
            # ← fix: choices[0].delta.content
            if chunk.choices and chunk.choices[0].delta and getattr(chunk.choices[0].delta, "content", None):
                Answer += chunk.choices[0].delta.content
        Answer = Answer.replace("</s>", "")
        messages.append({"role": "assistant", "content": Answer})
        return Answer


    Topic = str(Topic).replace("Content", "")
    ContentByAI = ContentWriterAI(Topic)
    content_filename = f"{Topic.lower().replace(' ','')}.txt"
    content_file_path = DATA_DIR / content_filename
    content_file_path.touch(exist_ok=True)
    with open(content_file_path, "w", encoding="utf-8") as file:
        file.write(ContentByAI)
    OpenNotepad(str(content_file_path))
    return True


# YouTube search
def YouTubeSearch(Topic):
    Url4Search = f"https://www.youtube.com/results?search_query={Topic}"
    webbrowser.open(Url4Search)
    return True


# Play YouTube
def PlayYoutube(query):
    playonyt(query)
    return True


# Open application or website
def OpenApp(app, sess=requests.session()):
    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        print(f"✅ Opened {app}")
        return True
    except:
        print(f"📱 App not opened via AppOpener. Trying native launch for {app}...")


    name = app.strip()
    plat = sys.platform


    def _run(cmd):
        try:
            if isinstance(cmd, str):
                return subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            print(f"⚠️ Native launch failed: {e}")
            return None


    # Windows: PATH then UWP (AUMID)
    if plat.startswith("win"):
        r = _run(["where", name])
        if r and r.returncode == 0 and r.stdout.strip():
            exe_path = r.stdout.strip().splitlines()
            try:
                subprocess.Popen([exe_path])
                print(f"✅ Opened {name} via PATH: {exe_path}")
                return True
            except Exception as e:
                print(f"⚠️ PATH launch failed: {e}")
        ps_cmd = f"(Get-StartApps -Name '*{name}*' | Select-Object -First 1).AppID"
        r = _run(["powershell", "-NoProfile", "-Command", ps_cmd])
        aumid = (r.stdout or "").strip() if r else ""
        if aumid:
            r2 = _run(["explorer.exe", f"shell:AppsFolder\\{aumid}"])
            if r2 and r2.returncode == 0:
                print(f"✅ Opened {name} via AUMID: {aumid}")
                return True


    # macOS: scan Applications
    elif plat.startswith("darwin"):
        app_dirs = ["/Applications", "/System/Applications", "/Applications/Utilities",
                    "/System/Applications/Utilities", os.path.expanduser("~/Applications")]
        target = None
        low = name.lower()
        for base in app_dirs:
            if not os.path.isdir(base):
                continue
            try:
                candidates = [p for p in os.listdir(base) if p.lower().endswith(".app")]
                prefix = [p for p in candidates if p.lower().startswith(low)]
                subset = prefix or [p for p in candidates if low in p.lower()]
                if subset:
                    target = os.path.join(base, subset)
                    break
            except Exception:
                pass
        if target:
            try:
                subprocess.Popen(["open", target])
                print(f"✅ Opened {name} via bundle: {target}")
                return True
            except Exception as e:
                print(f"⚠️ macOS open failed: {e}")


    # Linux: PATH then .desktop via gtk-launch
    elif plat.startswith("linux"):
        r = _run(["which", name])
        if r and r.returncode == 0 and r.stdout.strip():
            try:
                subprocess.Popen([name])
                print(f"✅ Opened {name} via PATH")
                return True
            except Exception as e:
                print(f"⚠️ PATH launch failed: {e}")
        desktop_dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
        desktop_id = None
        low = name.lower()
        for d in desktop_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for fn in os.listdir(d):
                    if not fn.endswith(".desktop"):
                        continue
                    stem = fn[:-8]
                    if stem.lower().startswith(low) or low in stem.lower():
                        desktop_id = stem
                        break
                if desktop_id:
                    break
            except Exception:
                pass
        if desktop_id:
            r = _run(["gtk-launch", desktop_id])
            if r and r.returncode == 0:
                print(f"✅ Opened {name} via desktop id: {desktop_id}")
                return True


    # Web fallback: prefer official site
    print(f"📱 App not installed. Searching for {app}...")


    def extract_links(html):
        if html is None:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', {'jsname': 'UWckNb'})
        cleaned = []
        for link in links:
            href = link.get('href')
            if not href:
                continue
            if href.startswith('/url?q='):
                real = href.split('/url?q=')[1].split('&')
                real = unquote(real)
                cleaned.append(real)
            elif href.startswith('http'):
                cleaned.append(href)
        return cleaned


    def search_google(query):
        search_query = f"{query} official website"
        url = f"https://www.google.com/search?q={search_query}"
        headers = {"User-Agent": useragent}
        try:
            response = sess.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                print("Failed to retrieve search results.")
        except Exception as e:
            print(f"Search error: {e}")
        return None


    def choose_official(candidates: list[str], key: str):
        banned_hosts = {
            "play.google.com", "apps.apple.com", "microsoft.com", "www.microsoft.com",
            "support.google.com", "en.wikipedia.org", "www.wikipedia.org",
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
            "github.com", "reddit.com", "youtube.com", "www.youtube.com",
        }
        toks = key.lower().split()
        key_low = toks if toks else ""
        scored = []
        for u in candidates:
            try:
                host = urlparse(u).netloc.lower()
            except Exception:
                host = ""
            score = 0
            if key_low and key_low in host:
                score += 2
            if host and host not in banned_hosts:
                score += 1
            scored.append((score, u))
        scored.sort(key=lambda x: x, reverse=True)
        return scored[1] if scored else None


    html = search_google(app)
    if html:
        try:
            links = extract_links(html)
            if links:
                chosen = choose_official(links, app) or links
                print(f"🌐 Opening {app} website: {chosen}")
                webopen(chosen)
            else:
                fallback_url = f"https://www.google.com/search?q={app}+official+website"
                print(f"🔍 Opening search results for {app}")
                webopen(fallback_url)
        except Exception:
            fallback_url = f"https://www.google.com/search?q={app}+official+website"
            print(f"🔍 Opening search results for {app}")
            webopen(fallback_url)


    return True


# Close app
def CloseApp(app):
    if "chrome" in app:
        pass
    else:
        try:
            close(app, match_closest=True, output=True, throw_error=True)
            return True
        except:
            return False


close("setting")  


# System commands
def System(command):
    _IS_WIN = sys.platform.startswith("win")
    _IS_MAC = sys.platform.startswith("darwin")
    _IS_LINUX = sys.platform.startswith("linux")

    # --- ADD: PowerShell safe runner just for toast ops ---
    PS_TIMEOUT_SECS = 12
    def _run_ps(args_list, timeout=PS_TIMEOUT_SECS):
        try:
            return subprocess.run(args_list, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            #print("⚠️ PowerShell call timed out (non-interactive safeguard)")
            return None
        except Exception as e:
            print(f"⚠️ PowerShell call failed: {e}")
            return None
    # ------------------------------------------------------

    def _run(cmd):
        try:
            if isinstance(cmd, str):
                return subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            print(f"⚠️ Failed: {e}")
            return None

    # Deterministic mute/unmute
    def mute():
        if _IS_WIN:
            keyboard.press_and_release("volume up")
            keyboard.press_and_release("volume mute")
            print("🔇 System muted")
            return
        keyboard.press_and_release("volume mute")
        print("🔇 System muted")

    def unmute():
        if _IS_WIN:
            keyboard.press_and_release("volume up")
            keyboard.press_and_release("volume down")
            print("🔊 System unmuted")
            return
        keyboard.press_and_release("volume mute")
        print("🔊 System unmuted")

    def volume_up():
        for _ in range(3):
            keyboard.press_and_release("volume up")
        print("🔊 Volume increased")

    def volume_down():
        for _ in range(3):
            keyboard.press_and_release("volume down")
        print("🔉 Volume decreased")

    def lock_screen():
        if _IS_WIN:
            return _run(r"rundll32.exe user32.dll,LockWorkStation")
        if _IS_MAC:
            return _run(["pmset", "displaysleepnow"])
        if _IS_LINUX:
            return _run(["loginctl", "lock-session"])
        return None

    def sleep_now():
        if _IS_WIN:
            return lock_screen()
        if _IS_MAC:
            return _run(["pmset", "sleepnow"])
        if _IS_LINUX:
            return _run(["systemctl", "suspend"])
        return None

    def screen_off():
        if _IS_MAC:
            return _run(["pmset", "displaysleepnow"])
        if _IS_WIN:
            return lock_screen()
        if _IS_LINUX:
            return _run(["loginctl", "lock-session"])
        return None

    # Helper: ring + popup exactly at target time and STOP when popup closes
    def _local_ring_at(target_dt: datetime, label_text: str):
        def _worker():
            try:
                wait_s = max(0, (target_dt - datetime.now()).total_seconds())
                threading.Event().wait(wait_s)

                # NEW: skip if cancelled by label or time
                hhmm = target_dt.strftime("%H:%M")
                s_lbl = _safe_label(label_text)
                if s_lbl in CANCELLED_ALARMS or hhmm in CANCELLED_TIMES:
                    return

                wav = PROJECT_ROOT / "Data" / "alarm.wav"  # dedicated alarm file
                beep_stop = threading.Event()
                beep_thread = None

                if wav.exists():
                    # Loop WAV until popup is dismissed
                    winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)  # loop async
                else:
                    # Controlled beep loop that can be stopped
                    def _beep_loop(stop_evt: threading.Event):
                        while not stop_evt.is_set():
                            winsound.Beep(1500, 400)  # 400 ms tone
                            if stop_evt.wait(0.15):
                                break
                    beep_thread = threading.Thread(target=_beep_loop, args=(beep_stop,), daemon=True)
                    beep_thread.start()

                # Show popup now (blocking until user clicks OK or closes with X)
                MB_OK = 0x0
                MB_ICONWARNING = 0x30
                MB_SYSTEMMODAL = 0x1000
                ctypes.windll.user32.MessageBoxW(None, f"Alarm: {label_text}", "Jarvis Alarm",
                                                 MB_OK | MB_ICONWARNING | MB_SYSTEMMODAL)  # returns on OK/X

                # Stop any async/looping WAV immediately
                winsound.PlaySound(None, winsound.SND_PURGE)  # stop current playback

                # Stop beep loop if it was used
                if beep_thread is not None:
                    beep_stop.set()
                    beep_thread.join(timeout=1.0)

            except Exception as e:
                print(f"⚠️ Local ring error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    # --- ADD: one-time non-interactive BurntToast bootstrap to avoid hangs ---
    def _bootstrap_burnttoast():
        ps = r"""
$ErrorActionPreference='Stop'
try {
  # Ensure NuGet provider and trusted PSGallery without prompts
  if (-not (Get-PackageProvider -Name NuGet -ErrorAction SilentlyContinue)) {
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser
  }
  if (-not (Get-PSRepository -Name 'PSGallery' -ErrorAction SilentlyContinue)) {
    Register-PSRepository -Name 'PSGallery' -SourceLocation 'https://www.powershellgallery.com/api/v2' -InstallationPolicy Trusted
  } else {
    Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted -ErrorAction SilentlyContinue
  }
  if (-not (Get-Module -ListAvailable -Name BurntToast)) {
    Install-Module BurntToast -Scope CurrentUser -Force -Confirm:$false
  }
  Import-Module BurntToast -ErrorAction Stop
} catch { }
"""
        _run_ps(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps])
    # ------------------------------------------------------------------------

    # WINDOWS: Toast alarm via BurntToast (OS schedule) + immediate local ring
    def _schedule_alarm_windows(hhmm: str, label: str):
        safe_label = "".join(ch for ch in label if ch.isalnum() or ch in (" ", "_", "-")).strip()
        task_name = f"JarvisAlarm_{safe_label}".replace(" ", "_")[:64]
        note_path = DATA_DIR / f"alarm_{safe_label.lower().replace(' ','_')}.txt"
        script_path = DATA_DIR / f"toast_{safe_label.lower().replace(' ','_')}.ps1"

        # Ensure BurntToast is ready non-interactively (prevents hangs)
        _bootstrap_burnttoast()

        ps_script = f"""
try {{
  Import-Module BurntToast -ErrorAction Stop
}} catch {{
  try {{ Install-Module BurntToast -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop }} catch {{}}
  Import-Module BurntToast -ErrorAction Stop
}}
$now = Get-Date
$parts = '{hhmm}'.Split(':')
$h = [int]$parts[0]; $m = [int]$parts[1]
$dt = ($now.Date).AddHours($h).AddMinutes($m)
if ($dt -le $now) {{ $dt = $dt.AddDays(1) }}

$t1 = New-BTText -Content 'Alarm'
$t2 = New-BTText -Content '{label.replace("'", "`'")}'
$bind = New-BTBinding -Children $t1,$t2
$vis  = New-BTVisual -BindingGeneric $bind
$aud  = New-BTAudio -Source 'ms-winsoundevent:Notification.Looping.Alarm2' -Loop
$act  = New-BTAction -SnoozeAndDismiss
$c    = New-BTContent -Visual $vis -Audio $aud -Actions $act -Scenario alarm

Submit-BTNotification -Content $c -Schedule -DeliveryTime $dt -UniqueIdentifier ('Jarvis-{safe_label}')
""".strip()

        try:
            script_path.write_text(ps_script, encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Could not write toast script: {e}")

        try:
            note_path.write_text(f"ALARM: {label}\nTIME: {hhmm}\n", encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Could not write alarm note: {e}")

        # Compute the same target datetime for the local ring
        now = datetime.now()
        h, m = [int(x) for x in hhmm.split(":")]
        target_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target_dt <= now:
            target_dt += timedelta(days=1)

        # Schedule the OS toast (non-interactive, timed)
        _run_ps([
            "powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass", "-File", str(script_path)
        ])

        # Immediate local ring/popup at the same target (no delay)
        if _IS_WIN:
            _local_ring_at(target_dt, label)

        return True

    def _delete_task_windows(task_name: str):
        r = _run(["schtasks", "/delete", "/tn", task_name, "/f"])
        if r and r.returncode == 0:
            print(f"🗑️ Deleted scheduled task: {task_name}")
            return True
        print(f"⚠️ Delete failed")
        return False

    def _schedule_alarm_local(hhmm: str, label: str):
        def _worker():
            try:
                now = datetime.now()
                h, m = [int(x) for x in hhmm.split(":")]
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                wait_s = (target - now).total_seconds()
                print(f"⏰ Alarm '{label}' scheduled at {target.strftime('%H:%M')} (waiting {int(wait_s)}s)")
                threading.Event().wait(wait_s)
                note = DATA_DIR / f"alarm_{label.lower().replace(' ','_')}.txt"
                with open(note, "w", encoding="utf-8") as f:
                    f.write(f"ALARM: {label}\nTIME: {target.strftime('%H:%M')}\n")
                if _IS_WIN:
                    _local_ring_at(target, label)
                elif _IS_MAC:
                    _run(["osascript", "-e", f'display notification "{label}" with title "Alarm"'])
                elif _IS_LINUX:
                    _run(["notify-send", "Alarm", label])
                print(f"⏰ Alarm '{label}' triggered")
            except Exception as e:
                print(f"⚠️ Alarm error: {e}")
        threading.Thread(target=_worker, daemon=True).start()
        return True

    def _parse_duration_s(text: str) -> int:
        total = 0
        toks = text.replace("hours","h").replace("mins","m").replace("minutes","m").replace("secs","s").split()
        for t in toks:
            if t.endswith("h"): total += int(t[:-1])*3600
            elif t.endswith("m"): total += int(t[:-1])*60
            elif t.endswith("s"): total += int(t[:-1])
            elif t.isdigit(): total += int(t)
        return max(1, total)

    # ---- ADDITIVE: cancel helpers and parsing ----
    def _cancel_scheduled_toast_by_id(safe_label: str):
        ps = f"""
try {{
  Import-Module BurntToast -ErrorAction Stop
  Remove-BTNotification -UniqueIdentifier 'Jarvis-{safe_label}'
}} catch {{
  try {{
    Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
    $app = 'BurntToast'
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)
    $scheduled = $notifier.GetScheduledToastNotifications()
    foreach ($n in $scheduled) {{
      if ($n.Id -eq 'Jarvis-{safe_label}') {{ $notifier.RemoveFromSchedule($n) }}
    }}
  }} catch {{ }}
}}
"""
        _run_ps(['powershell','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-Command', ps])
        CANCELLED_ALARMS.add(safe_label)
        return True

    def _cancel_scheduled_toast_by_time(hhmm: str):
        ps = f"""
try {{
  Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
  $app = 'BurntToast'
  $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)
  $scheduled = $notifier.GetScheduledToastNotifications()
  foreach ($n in $scheduled) {{
    $t = $n.DeliveryTime.ToLocalTime()
    if ($t.Hour -eq {int(hhmm.split(':')[0])} -and $t.Minute -eq {int(hhmm.split(':')[1])}) {{
      $notifier.RemoveFromSchedule($n)
    }}
  }}
}} catch {{ }}
"""
        _run_ps(['powershell','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-Command', ps])
        CANCELLED_TIMES.add(hhmm)
        return True

    def _normalize_time_tokens(tokens: list[str]) -> str | None:
        # Accept "20:14", "20 14", or "2014" → "20:14"
        for t in tokens:
            if ":" in t and all(x.isdigit() for x in t.split(":", 1)):
                return t
        nums = [t for t in tokens if t.isdigit()]
        if len(nums) >= 2 and len(nums[0]) <= 2 and len(nums[1]) <= 2:
            return f"{int(nums[0]):02d}:{int(nums[1]):02d}"
        if len(nums) == 1 and len(nums[0]) in (3,4):
            n = nums[0].zfill(4); return f"{n[:2]}:{n[2:]}"
        return None

    print(f"🔧 System function received: '{command}'")
    command_clean = command.lower().strip()

    # ---- ADDITIVE: handle delete variants before generic "alarm" ----
    if command_clean.startswith("alarm delete") or command_clean.startswith("delete alarm") or command_clean.startswith("delete task"):
        if not _IS_WIN:
            print("🗑️ Delete is only implemented on Windows in this build.")
            return False
        parts = command.strip().split()
        # Remove keywords and normalize time if present
        tail = [p for p in parts if p.lower() not in ("alarm","delete","at")]
        hhmm = _normalize_time_tokens(tail)
        if hhmm:
            _cancel_scheduled_toast_by_time(hhmm)   # cancel OS-scheduled toast(s) for that minute
            # Intentionally do NOT call schtasks here; toasts are not tasks and schtasks cannot cancel them
            return True
        # Else treat the remainder as a label-based deletion
        label = " ".join(tail).strip() or "Alarm"
        safe_label = _safe_label(label)
        _cancel_scheduled_toast_by_id(safe_label)   # cancel OS toast by id
        _delete_task_windows(f"JarvisAlarm_{safe_label}")  # Task Scheduler (no-op if none)
        return True

    if "mute" in command_clean:
        if "unmute" in command_clean:
            unmute()
        else:
            mute()
    elif any(word in command_clean for word in ["up", "increase", "raise", "louder", "higher"]):
        volume_up()
    elif any(word in command_clean for word in ["down", "decrease", "lower", "quieter"]):
        volume_down()
    elif command_clean == "volume":
        print("🔊 No direction specified, increasing volume by default")
        volume_up()
    elif "lock" in command_clean or "lock screen" in command_clean:
        lock_screen()
    elif "sleep" in command_clean:
        sleep_now()
    elif "screen off" in command_clean or "turn off screen" in command_clean or "display off" in command_clean:
        screen_off()
    elif "alarm" in command_clean:
        parts = command.strip().split()
        hhmm = None
        label = "Alarm"
        for i, p in enumerate(parts):
            if ":" in p and all(x.isdigit() for x in p.split(":", 1)):
                hhmm = p
                label = " ".join(parts[i+1:]).strip() or "Alarm"
                break
        if hhmm:
            ok = False
            if _IS_WIN:
                ok = _schedule_alarm_windows(hhmm, label)
            if not ok:
                _schedule_alarm_local(hhmm, label)
        else:
            print("⏰ Usage: system alarm HH:MM <label>")
    elif command_clean.startswith("timer "):
        text = command_clean.removeprefix("timer ").strip()
        dur_s = _parse_duration_s(text)
        lbl = "Timer"
        words = [w for w in text.split() if not any(w.endswith(x) for x in ["h","m","s"]) and not w.isdigit()]
        if words:
            lbl = " ".join(words).strip().title()
        target = datetime.now() + timedelta(seconds=dur_s)
        if _IS_WIN:
            _local_ring_at(target, lbl or "Timer")
        else:
            _schedule_alarm_local((datetime.now() + timedelta(seconds=1)).strftime("%H:%M"), lbl or "Timer")
        print(f"⏲️ Timer set for {dur_s} seconds: {lbl}")
    elif command_clean.startswith("stopwatch"):
        global STOPWATCH_START
        if "start" in command_clean:
            STOPWATCH_START = datetime.now()
            print("⏱️ Stopwatch started")
        elif "stop" in command_clean:
            if STOPWATCH_START:
                elapsed = datetime.now() - STOPWATCH_START
                secs = int(elapsed.total_seconds())
                mins, s = divmod(secs, 60)
                hrs, m = divmod(mins, 60)
                msg = f"Elapsed: {hrs:02d}:{m:02d}:{s:02d}"
                ctypes.windll.user32.MessageBoxW(None, msg, "Stopwatch", 0x0 | 0x40)
                STOPWATCH_START = None
            else:
                print("⏱️ Stopwatch is not running")
        else:
            print("⏱️ Usage: system stopwatch start | system stopwatch stop")
    elif command_clean.startswith("delete alarm") or command_clean.startswith("delete task"):
        # Retained for backward compatibility; main delete handled earlier
        if not _IS_WIN:
            print("🗑️ Delete is only implemented on Windows in this build.")
            return False
        parts = command.strip().split()
        task_name = None
        if command_clean.startswith("delete alarm") and len(parts) >= 3:
            label = " ".join(parts[2:]).strip()
            safe_label = _safe_label(label)
            task_name = f"JarvisAlarm_{safe_label}"
            _cancel_scheduled_toast_by_id(safe_label)
        elif command_clean.startswith("delete task") and len(parts) >= 3:
            task_name = " ".join(parts[2:]).strip()
        else:
            print("🗑️ Usage: system delete alarm <label>  OR  system delete task <task_name>")
            return False
        _delete_task_windows(task_name)
    else:
        print(f" No Function Found. For {command}")
        return False

    return True


# ---- ADDITIVE HELPERS (no changes to existing functions) ----
def GenerateImageWeb(prompt: str):
    try:
        q = quote_plus(prompt)
        url = f"https://www.bing.com/images/create?q={q}"
        webopen(url)
        print(f"🖼️ Opened image generator for: {prompt}")
        return True
    except Exception as e:
        print(f"⚠️ Image generation open failed: {e}")
        return False


def _normalize_commands(cmds: list[str]) -> list[str]:
    expanded = []
    for c in cmds:
        if not isinstance(c, str):
            continue
        parts = [p.strip() for p in c.split(",") if p.strip()]
        further = []
        for p in parts:
            if p.lower().startswith(("content ", "write ", "create ")):
                further.append(p)
            else:
                further.extend([x.strip() for x in p.split(" and ") if x.strip()])
        expanded.extend(further if further else [c])
    return expanded or cmds


def _intent_for_freeform(text: str):
    t = text.lower().strip()
    if t.startswith(("open ", "close ", "play ", "content ", "google search ", "youtube search ", "system ")):
        return None
    if t.startswith(("write ", "compose ", "draft ")):
        return "content " + text
    # STRICT: only these two forms map to image
    if t.startswith(("generate image", "create image")):
        return "image " + text
    if t.startswith(("lock ", "sleep ", "screen off", "turn off screen", "display off", "alarm ", "delete alarm", "delete task")):
        return "system " + text
    if t.startswith(("search youtube for ", "youtube ")):
        return "youtube search " + t.replace("search youtube for ", "").replace("youtube ", "")
    if t.startswith(("search google for ", "google ")):
        return "google search " + t.replace("search google for ", "").replace("google ", "")
    if t.startswith(("open instagram", "open insta")):
        return "open instagram"
    if t.startswith(("open facebook", "open fb")):
        return "open facebook"
    if t.startswith(("play ", "listen to ")):
        return "play " + t.replace("listen to ", "")
    return text


# Translate and execute
async def TranslateAndExecute(commands: list[str]):
    funcs_other = []
    system_specs = []  # (priority, func)

    # Priority: make audio actions start just before lock/sleep to avoid lock racing first
    def _system_priority(param: str) -> int:
        p = param.strip().lower()
        if p.startswith(("mute", "unmute")) or p in ("volume",):
            return 1
        if p.startswith(("screen off", "turn off screen", "display off")):
            return 2
        if p.startswith(("lock", "lock screen")):
            return 3
        if p.startswith("sleep"):
            return 4
        if p.startswith(("alarm", "delete alarm", "delete task")):
            return 5
        return 9

    commands = _normalize_commands(commands)

    for command in commands:
        command_lower = command.lower().strip()
        mapped = _intent_for_freeform(command)
        if mapped and mapped != command:
            command_lower = mapped.lower().strip()

        if command_lower.startswith("open "):
            if "open it" in command_lower or "open file" == command_lower:
                continue
            else:
                funcs_other.append(asyncio.to_thread(OpenApp, command_lower.removeprefix("open ")))

        elif command_lower.startswith("general "):
            continue

        elif command_lower.startswith("realtime "):
            continue

        elif command_lower.startswith("close "):
            funcs_other.append(asyncio.to_thread(CloseApp, command_lower.removeprefix("close ")))

        elif command_lower.startswith("play "):
            funcs_other.append(asyncio.to_thread(PlayYoutube, command_lower.removeprefix("play ")))

        elif command_lower.startswith("content "):
            funcs_other.append(asyncio.to_thread(Content, command_lower.removeprefix("content ")))

        elif command_lower.startswith("google search "):
            funcs_other.append(asyncio.to_thread(GoogleSearch, command_lower.removeprefix("google search ")))

        elif command_lower.startswith("youtube search "):
            funcs_other.append(asyncio.to_thread(YouTubeSearch, command_lower.removeprefix("youtube search ")))

        # STRICT: Only "image " prefixed by our mapper (generate/create image)
        elif command_lower.startswith("image ") or command_lower.startswith("generate image") or command_lower.startswith("create image"):
            prompt = command_lower.replace("image ", "").replace("generate image", "").replace("create image", "").strip() or "an image"
            funcs_other.append(asyncio.to_thread(GenerateImageWeb, prompt))

        elif command_lower.startswith("system "):
            system_param = command_lower.removeprefix("system ").strip()
            print(f"🔧 Processing system command: {command}")
            pr = _system_priority(system_param)
            system_specs.append((pr, asyncio.to_thread(System, system_param)))

        else:
            print(f"No Function Found. For {command}")

    # Start non-system tasks in the same order; start system tasks in a safe priority order
    funcs = funcs_other + [f for _, f in sorted(system_specs, key=lambda t: t)]

    if funcs:
        results = await asyncio.gather(*funcs)
        for result in results:
            if isinstance(result, str):
                yield result
            else:
                yield result
    else:
        yield True


# Automation
async def Automation(commands: list[str]):
    async for result in TranslateAndExecute(commands):
        pass
    return True


if __name__ == "__main__":
    asyncio.run(Automation([]))
