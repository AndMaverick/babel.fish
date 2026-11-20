# babel_fish.py
# Launcher: kept so that "python babel_fish.py --input ... --lang de --tone formal" still works. The code lives in the babel_fish/ package.
# Babel.Fish: from translation to true cultural fluency.

import sys

from babel_fish import babel_fish  # noqa: F401  (the original one-call function, still importable from here)
from babel_fish.cli import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python babel_fish.py --input \"Our product reduces costs by 20%.\" --lang de --tone formal")
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
