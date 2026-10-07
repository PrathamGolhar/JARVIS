import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set test environment defaults
os.environ["JARVIS_ENV"] = "test"
os.environ["JARVIS_PERMISSION_MODE"] = "assisted"
