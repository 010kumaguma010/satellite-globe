"""
Fetch active satellite TLEs from CelesTrak, compute current lat/lon/alt,
and write results to data/satellites.csv.
"""

import csv
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone

from sgp4.api import Satrec, jday

TLE_URLS = [
    "https://celestrak.org/pub/TLE/active.txt",
    "https://celestrak.org/pub/TLE/catalog.txt",
]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "satellites.csv")


def fetch_tle_lines(url: str) -> list[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Accept": "text/plain,text/html,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://celestrak.org/",
        "Connection": "keep-alive",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8").splitlines()


def parse_tle_groups(lines: list[str]) -> list[tuple[str, str, str]]:
    groups: list[tuple[str, str, str]] = []
    clean = [l.strip() for l in lines if l.strip()]
    i = 0
    while i + 2 < len(clean):
        name, l1, l2 = clean[i], clean[i + 1], clean[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            groups.append((name, l1, l2))
            i += 3
        else:
            i += 1
    return groups


def _gmst(jd: float) -> float:
    """Greenwich Mean Sidereal Time in radians."""
    T = (jd - 2451545.0) / 36525.0
    secs = 67310.54841 + (876600 * 3600 + 8640184.812866) * T + 0.093104 * T**2 - 6.2e-6 * T**3
    return math.radians(secs % 86400 / 240)


def tle_to_latlon(line1: str, line2: str, dt: datetime) -> tuple[float, float, float]:
    sat = Satrec.twoline2rv(line1, line2)
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
    e, r, _ = sat.sgp4(jd, fr)
    if e != 0:
        raise ValueError(f"SGP4 error {e}")

    x, y, z = r  # km, TEME frame
    gmst = _gmst(jd + fr)
    lon_rad = (math.atan2(y, x) - gmst + math.pi) % (2 * math.pi) - math.pi
    lat_rad = math.atan2(z, math.sqrt(x**2 + y**2))
    alt_km = math.sqrt(x**2 + y**2 + z**2) - 6371.0

    return math.degrees(lat_rad), math.degrees(lon_rad), alt_km


def main() -> None:
    lines = None
    for url in TLE_URLS:
        print(f"Fetching TLE data from {url} …")
        try:
            lines = fetch_tle_lines(url)
            break
        except Exception as exc:
            print(f"  Warning: {exc}", file=sys.stderr)

    if lines is None:
        print("ERROR: all TLE sources failed", file=sys.stderr)
        sys.exit(1)

    groups = parse_tle_groups(lines)
    print(f"  Parsed {len(groups)} satellites")

    now = datetime.now(timezone.utc)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    ok = errors = 0
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "lat", "lon", "alt_km"])
        for name, l1, l2 in groups:
            try:
                lat, lon, alt = tle_to_latlon(l1, l2, now)
                writer.writerow([name, f"{lat:.4f}", f"{lon:.4f}", f"{alt:.1f}"])
                ok += 1
            except Exception:
                errors += 1

    print(f"  Written: {ok} rows, {errors} skipped  →  {OUTPUT}")
    print(f"  UTC: {now.isoformat()}")


if __name__ == "__main__":
    main()
