"""Single entry point for the application.

Usage:
    python main.py          # Qt GUI
    python main.py --cli    # CLI / headless
"""

import sys
from app.app_factory import AppFactory


def main() -> None:
    AppFactory.from_args(sys.argv[1:]).run()


if __name__ == "__main__":
    main()
