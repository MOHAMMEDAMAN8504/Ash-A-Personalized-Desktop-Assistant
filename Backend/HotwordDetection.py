import pvporcupine
import pyaudio
import threading
import time
import os
import numpy as np
from dotenv import load_dotenv
from pathlib import Path

# Your existing GUI imports
from Frontend.GUI import SetMicrophoneStatus, GetMicrophoneStatus, SetAssistantStatus

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

class PorcupineWakeWordDetector:
    def __init__(self):
        # Use "jarvis" (lowercase) - exactly as shown in terminal
        self.wake_word = "jarvis"  # FIXED: lowercase instead of "JARVIS"
        
        # Automatically get Picovoice API key from .env file
        self.access_key = os.getenv('PicovoiceAPIKey')
        
        self.porcupine = None
        self.audio = None
        self.stream = None
        self.is_listening = False
        self.listener_thread = None
        
        print(f"🎤 Porcupine Wake Word Detection for '{self.wake_word}'")
        #print(" Your assistant 'Ash' will respond when you say 'Jarvis'")
        
        if not self.access_key:
            print(" PicovoiceAPIKey not found in .env file")

    def initialize(self):
        """Initialize Porcupine with jarvis wake word and HIGH sensitivity"""
        try:
            if not self.access_key:
                print(" No Picovoice API key found")
                return False
            
            # Create Porcupine with built-in jarvis keyword (lowercase)
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=[self.wake_word],
                sensitivities=[0.8]  # HIGH sensitivity for better detection
            )
            
            # Create PyAudio stream with proper settings
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            #print("✅ Porcupine initialized with HIGH sensitivity (0.8)")
            #print("✅ Using PicovoiceAPIKey from .env file")
            return True
            
        except Exception as e:
            print(f" Error initializing Porcupine: {e}")
            return False

    def start_listening(self):
        """Start wake word detection"""
        if self.initialize():
            self.is_listening = True
            self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listener_thread.start()
            print(" Say 'Jarvis' clearly to activate your 'Ash' assistant!")

    def _listen_loop(self):
        """Main detection loop with proper audio processing"""
        while self.is_listening:
            try:
                current_status = GetMicrophoneStatus()
                if current_status == "False":  # Only listen when mic is OFF
                    
                    # Read audio frame using PyAudio
                    audio_data = self.stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                    
                    # Convert bytes to numpy array of 16-bit integers
                    pcm = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Process with Porcupine
                    keyword_index = self.porcupine.process(pcm)
                    
                    # Wake word detected
                    if keyword_index >= 0:
                        print(f" Wake word '{self.wake_word}' detected!")
                        print("   Activating 'Ash' assistant...")
                        
                        SetAssistantStatus("Voice activation...")
                        SetMicrophoneStatus("True")
                        
                        # Wait for conversation to end
                        while GetMicrophoneStatus() == "True":
                            time.sleep(0.5)
                        
                        print("🔄 Ready for next 'Jarvis' activation...")
                        
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Audio processing error: {e}")
                time.sleep(0.1)

    def stop_listening(self):
        """Stop wake word detection"""
        self.is_listening = False
        
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                self.audio.terminate()
            if self.porcupine:
                self.porcupine.delete()
        except Exception:
            pass
            
        print(" Wake word detection stopped")

# Global instance
hotword_detector = None

def start_hotword_detection():
    """Start hotword detection (called from Main.py)"""
    global hotword_detector
    if hotword_detector is None:
        hotword_detector = PorcupineWakeWordDetector()
        hotword_detector.start_listening()

def stop_hotword_detection():
    """Stop hotword detection"""
    global hotword_detector
    if hotword_detector:
        hotword_detector.stop_listening()
        hotword_detector = None
