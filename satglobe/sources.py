"""TLE data sources: Space-Track.org (authenticated) and CelesTrak (public).

Both are asked for 3LE format so satellite names are always included.
"""

import sys

import requests

SPACETRACK_LOGIN = "https://www.space-track.org/ajaxauth/login"
# The gp class is Space-Track's current recommendation (tle_latest is
# deprecated). Prefer non-decayed objects with a recent epoch; fall back
# to progressively looser queries if the strict one is rejected.
SPACETRACK_QUERIES = [
    "https://www.space-track.org/basicspacedata/query/class/gp/"
    "decay_date/null-val/epoch/%3Enow-30/orderby/norad_cat_id/format/3le",
    "https://www.space-track.org/basicspacedata/query/class/gp/"
    "epoch/%3Enow-30/orderby/norad_cat_id/format/3le",
    "https://www.space-track.org/basicspacedata/query/class/gp/format/3le",
]

CELESTRAK_URLS = [
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
    "https://celestrak.org/pub/TLE/active.txt",
]

_HEADERS = {
    "User-Agent": "satellite-globe/2.0 (github.com/010kumaguma010/satellite-globe)",
    "Accept": "text/plain,*/*",
}


def fetch_spacetrack(user: str, password: str) -> list[str]:
    with requests.Session() as session:
        resp = session.post(
            SPACETRACK_LOGIN,
            data={"identity": user, "password": password},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        failed = (isinstance(result, dict) and result.get("Login") == "Failed") or (
            isinstance(result, str) and "fail" in result.lower()
        )
        if failed:
            raise ValueError(
                f"login failed ({result!r}) — check SPACETRACK_USER / SPACETRACK_PASS"
            )

        for url in SPACETRACK_QUERIES:
            resp = session.get(url, timeout=120)
            if resp.status_code == 200 and resp.text.strip():
                return resp.text.splitlines()
            snippet = resp.text[:200].replace("\n", " ")
            print(f"  query {url} → {resp.status_code}: {snippet}", file=sys.stderr)
        raise ValueError("all Space-Track queries failed")


def fetch_celestrak(url: str) -> list[str]:
    resp = requests.get(url, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    if not resp.text.strip():
        raise ValueError("empty response")
    return resp.text.splitlines()


def fetch_tle_lines(user: str, password: str) -> tuple[list[str], str]:
    """Try each source in priority order; return (lines, source_name)."""
    if user and password:
        print("Fetching TLE data from Space-Track.org …")
        try:
            return fetch_spacetrack(user, password), "space-track"
        except Exception as exc:
            print(f"  warning: Space-Track failed: {exc}", file=sys.stderr)

    for url in CELESTRAK_URLS:
        print(f"Fetching TLE data from {url} …")
        try:
            return fetch_celestrak(url), "celestrak"
        except Exception as exc:
            print(f"  warning: {exc}", file=sys.stderr)

    raise RuntimeError(
        "all TLE sources failed. Set SPACETRACK_USER / SPACETRACK_PASS secrets "
        "for reliable access (free account: https://www.space-track.org/)"
    )
