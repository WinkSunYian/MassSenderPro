# main.py
import sys

from bootstrap.apprunner import apprunner


def main() -> int:
    return apprunner().run()


if __name__ == "__main__":
    sys.exit(main())
