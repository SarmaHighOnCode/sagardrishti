"""Write the API's OpenAPI schema to docs/api/openapi.json.

Why this is committed rather than generated on demand:

The frontend's `web/src/lib/apiTypes.ts` is hand-written (deliberately —
see its module docstring). Hand-written mirrors drift silently, and this
repo already has one scar from exactly that: the API's
`BaselineGapProfile` invented `typical_gap_minutes_p50` against a
database column called `median_gap_seconds`, and nothing failed loudly.

Committing the schema makes every server-side field change show up as a
reviewable diff in the pull request that causes it, and gives the web
test suite something to check the client types against without needing a
running API. CI regenerates and fails if the committed copy is stale, so
it cannot quietly fall behind.

Usage:
    python tools/export_openapi.py            # write the file
    python tools/export_openapi.py --check    # exit 1 if stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "docs" / "api" / "openapi.json"

# services/api is not an installed package — same sys.path dance as
# services/api/tests/conftest.py.
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))


def schema() -> dict:
    from app.main import app

    return app.openapi()


def rendered() -> str:
    # sort_keys so the committed file is stable across FastAPI's internal
    # dict ordering — otherwise --check flaps for reasons unrelated to the
    # contract, and a flapping guard is one people learn to ignore.
    return json.dumps(schema(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if the committed schema is out of date.",
    )
    args = parser.parse_args()

    current = rendered()

    if args.check:
        if not OUTPUT.exists():
            print(f"{OUTPUT.relative_to(REPO_ROOT)} does not exist.", file=sys.stderr)
            print("Run: python tools/export_openapi.py", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") != current:
            print(
                f"{OUTPUT.relative_to(REPO_ROOT)} is out of date with services/api/app/schemas.py.",
                file=sys.stderr,
            )
            print("Run: python tools/export_openapi.py", file=sys.stderr)
            return 1
        print(f"{OUTPUT.relative_to(REPO_ROOT)} is up to date.")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(current, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
