"""Propagate TLEs to the current time and write the output data files.

Outputs (all under data/):
  satellites.csv  name,lat,lon,alt_km          — snapshot for direct display
  orbits.csv      per-satellite orbital elements — for client-side propagation
  meta.json       generation timestamp, source, row counts
"""

import csv
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from sgp4.api import Satrec, jday

from .geodesy import teme_to_geodetic
from .tle import Tle

# Julian date of the Unix epoch (1970-01-01T00:00:00Z)
_JD_UNIX_EPOCH = 2440587.5


@dataclass
class SatState:
    name: str
    norad: int
    lat: float
    lon: float
    alt_km: float
    epoch_unix: float
    inc_deg: float
    raan_deg: float
    ecc: float
    argp_deg: float
    mean_anomaly_deg: float
    mean_motion_rev_per_day: float


def propagate(tle: Tle, jd: float, fr: float) -> SatState:
    sat = Satrec.twoline2rv(tle.line1, tle.line2)
    err, r, _v = sat.sgp4(jd, fr)
    if err != 0:
        raise ValueError(f"SGP4 error {err} for {tle.name}")
    lat, lon, alt = teme_to_geodetic(r, jd, fr)
    return SatState(
        name=tle.name,
        norad=tle.norad,
        lat=lat,
        lon=lon,
        alt_km=alt,
        epoch_unix=(sat.jdsatepoch + sat.jdsatepochF - _JD_UNIX_EPOCH) * 86400.0,
        inc_deg=math.degrees(sat.inclo),
        raan_deg=math.degrees(sat.nodeo),
        ecc=sat.ecco,
        argp_deg=math.degrees(sat.argpo),
        mean_anomaly_deg=math.degrees(sat.mo),
        mean_motion_rev_per_day=sat.no_kozai * 1440.0 / (2.0 * math.pi),
    )


def compute_states(
    tles: list[Tle], now: datetime
) -> tuple[list[SatState], int]:
    """Propagate every TLE to `now`; return (states, skipped_count).

    Objects the SGP4 model rejects (decayed, corrupt elements) are skipped.
    """
    jd, fr = jday(
        now.year, now.month, now.day,
        now.hour, now.minute, now.second + now.microsecond / 1e6,
    )
    states: list[SatState] = []
    skipped = 0
    for tle in tles:
        try:
            states.append(propagate(tle, jd, fr))
        except Exception:
            skipped += 1
    return states, skipped


def write_outputs(
    states: list[SatState],
    now: datetime,
    source: str,
    skipped: int,
    out_dir: str,
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "satellites.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "lat", "lon", "alt_km"])
        for s in states:
            w.writerow([s.name, f"{s.lat:.4f}", f"{s.lon:.4f}", f"{s.alt_km:.1f}"])

    with open(os.path.join(out_dir, "orbits.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "name", "norad", "epoch_unix", "inc_deg", "raan_deg",
            "ecc", "argp_deg", "mean_anomaly_deg", "mean_motion_rev_per_day",
        ])
        for s in states:
            w.writerow([
                s.name, s.norad, f"{s.epoch_unix:.0f}",
                f"{s.inc_deg:.4f}", f"{s.raan_deg:.4f}", f"{s.ecc:.7f}",
                f"{s.argp_deg:.4f}", f"{s.mean_anomaly_deg:.4f}",
                f"{s.mean_motion_rev_per_day:.8f}",
            ])

    meta = {
        "generated_at": now.isoformat(timespec="seconds"),
        "generated_at_unix": int(now.timestamp()),
        "source": source,
        "satellites": len(states),
        "skipped": skipped,
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
