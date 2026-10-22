"""NeuroSonic AI backend. Makes the sibling `ml/` package importable when running from the repo."""
import sys
from pathlib import Path

_ml = Path(__file__).resolve().parents[2] / "ml"
if _ml.exists() and str(_ml) not in sys.path:
    sys.path.insert(0, str(_ml))

__version__ = "0.1.0"
