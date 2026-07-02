"""Entry point: python -m satglobe [output_dir]"""

import os
import sys
from datetime import datetime, timezone

from .pipeline import compute_states, write_outputs
from .sources import fetch_tle_lines
from .tle import parse_tles


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )

    lines, source = fetch_tle_lines(
        os.environ.get("SPACETRACK_USER", ""),
        os.environ.get("SPACETRACK_PASS", ""),
    )
    tles = parse_tles(lines)
    print(f"  parsed {len(tles)} TLEs from {source}")
    if not tles:
        print("ERROR: source returned no parseable TLEs", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    states, skipped = compute_states(tles, now)
    write_outputs(states, now, source, skipped, out_dir)
    print(f"  written {len(states)} satellites ({skipped} skipped) → {out_dir}")
    print(f"  UTC: {now.isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
