# Backend/Config.py

import os
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

Username = os.getenv("Username", "Aman")
Assistantname = os.getenv("Assistantname", "Jarvis")

# Override system ENV vars to prevent Windows username leakage
os.environ["USERNAME"] = Username
os.environ["Username"] = Username

print(f"✅ Config loaded: Username={Username}, Assistantname={Assistantname}")
