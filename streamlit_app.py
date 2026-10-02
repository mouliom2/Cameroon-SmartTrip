
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
sys.path.insert(0, str(APP_DIR))

exec((APP_DIR / "llm_app.py").read_text(encoding="utf-8"))
