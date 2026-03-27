from __future__ import annotations

import sys


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)
