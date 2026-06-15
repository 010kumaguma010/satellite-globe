"""
Fetch active satellite TLEs, compute current lat/lon/alt,
and write results to data/satellites.csv.

Primary source: Space-Track.org (requires SPACETRACK_USER / SPACETRACK_PASS env vars).
Fallback:       CelesTrak pub/TLE (may be blocked from GitHub Actions IP ranges).
"""

import csv
import math
import os
import sys
from datetime import datetime, timezone

import requests
from sgp4.api import Satrec, jday

OUTPUT = os.path.join(os.path.dirname(__file__), "data", "satellites.csv")

SPACETRACK_LOGIN = "https://www.space-track.org/ajaxauth/login"
SPACETRACK_QUERIES = [
    # GP catalog — various filter combinations
    "https://www.space-track.org/basicspacedata/query/class/gp/CURRENT/true/FORMAT/tle",
    "https://www.space-track.org/basicspacedata/query/class/gp/EPOCH/%3Enow-30/FORMAT/tle",
    "https://www.space-track.org/basicspacedata/query/class/gp/FORMAT/tle",
]

CELESTRAK_URLS = [
    "https://celestrak.org/pub/TLE/active.txt",
    "https://celestrak.org/pub/TLE/catalog.txt",
]


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_from_spacetrack(user: str, password: str) -> list[str]:
    with requests.Session() as session:
        resp = session.post(
            SPACETRACK_LOGIN,
            data={"identity": user, "password": password},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        failed = (
            (isinstance(result, dict) and result.get("Login") == "Failed")
            or (isinstance(result, str) and "fail" in result.lower())
        )
        if failed:
            raise ValueError(f"Login failed ({result!r}) — check SPACETRACK_USER / SPACETRACK_PASS")

        for query_url in SPACETRACK_QUERIES:
            resp = session.get(query_url, timeout=60)
            if resp.status_code == 200:
                return resp.text.splitlines()
            snippet = resp.text[:300].replace("\n", " ")
            print(f"  Query {query_url} → {resp.status_code}: {snippet}", file=sys.stderr)
        raise ValueError("All Space-Track queries failed")


def fetch_from_celestrak(url: str) -> list[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Accept": "text/plain,*/*",
        "Referer": "https://celestrak.org/",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text.splitlines()


# ---------------------------------------------------------------------------
# TLE parsing
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    lines: list[str] | None = None

    # 1. Space-Track (preferred when credentials are available)
    user = os.environ.get("SPACETRACK_USER", "")
    password = os.environ.get("SPACETRACK_PASS", "")
    if user and password:
        print("Fetching TLE data from Space-Track.org …")
        try:
            lines = fetch_from_spacetrack(user, password)
        except Exception as exc:
            print(f"  Warning: Space-Track failed: {exc}", file=sys.stderr)

    # 2. CelesTrak fallback
    if lines is None:
        for url in CELESTRAK_URLS:
            print(f"Fetching TLE data from {url} …")
            try:
                lines = fetch_from_celestrak(url)
                break
            except Exception as exc:
                print(f"  Warning: {exc}", file=sys.stderr)

    if lines is None:
        print(
            "ERROR: all TLE sources failed.\n"
            "Set SPACETRACK_USER and SPACETRACK_PASS secrets for reliable access.\n"
            "Register free at https://www.space-track.org/",
            file=sys.stderr,
        )
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
