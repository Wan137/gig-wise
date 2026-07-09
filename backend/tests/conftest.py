import sys
from pathlib import Path

# Make `import app...` work when pytest is run from the backend/ directory
# without needing the package installed in editable mode.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
