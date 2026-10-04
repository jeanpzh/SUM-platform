import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in [
    "packages/contracts",
    "packages/storage",
    "services/backend-api",
    "services/indexer-service",
]:
    sys.path.insert(0, str(ROOT / directory / "src"))
