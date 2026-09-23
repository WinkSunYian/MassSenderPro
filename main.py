# main.py
import sys

from bootstrap import AppRunner


def main() -> int:
    return AppRunner().run()


if __name__ == "__main__":
    sys.exit(main())
