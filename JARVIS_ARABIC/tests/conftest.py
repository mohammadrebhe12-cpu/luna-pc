import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["JARVIS_NO_AUDIO"] = "1"
os.environ["JARVIS_HOME"] = tempfile.mkdtemp(prefix="jarvis_test_")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
