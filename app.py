
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
sys.path.insert(0, str(APP_DIR))

from gradio_app import demo

if __name__ == "__main__":
    demo.launch()
