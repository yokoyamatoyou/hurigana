import sys
from pathlib import Path

# Append the repository root so tests can import the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
