"""Run the bundled composite Action without importing from the consumer checkout."""

from pathlib import Path
import sys


ACTION_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ACTION_ROOT / "src"))

from hypothesisctl.cli import main  # noqa: E402


raise SystemExit(main())
