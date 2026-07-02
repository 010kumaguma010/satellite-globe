"""Validate the client-side propagation model against full SGP4.

The Kepler+J2 model documented in satglobe/kepler.py is ported verbatim
to UdonSharp (clients/vrchat/) and JavaScript (docs/index.html); this
test pins down its accuracy so a port or a refactor that breaks the
math fails loudly.
"""

import math

from sgp4.api import Satrec

from satglobe.geodesy import teme_to_geodetic
from satglobe.kepler import Elements, propagate_ecef, propagate_eci

ISS = (
    "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9005",
    "2 25544  51.6400 208.9163 0006317  69.9862 290.2018 15.49560532    15",
)
NOAA15 = (
    "1 25338U 98030A   24001.45184023  .00000208  00000+0  10495-3 0  9992",
    "2 25338  98.5688  32.4577 0009481 224.4841 135.5581 14.26534442334337",
)
MOLNIYA = (
    "1 40296U 14074A   24001.40000000  .00000100  00000-0  00000+0 0  9993",
    "2 40296  62.8500 280.0000 7400000 270.0000  20.0000  2.00600000    17",
)

_JD_UNIX_EPOCH = 2440587.5


def _setup(l1: str, l2: str) -> tuple[Satrec, Elements]:
    sat = Satrec.twoline2rv(l1, l2)
    epoch_unix = (sat.jdsatepoch + sat.jdsatepochF - _JD_UNIX_EPOCH) * 86400.0
    el = Elements(
        epoch_unix=epoch_unix,
        inc_deg=math.degrees(sat.inclo),
        raan_deg=math.degrees(sat.nodeo),
        ecc=sat.ecco,
        argp_deg=math.degrees(sat.argpo),
        mean_anomaly_deg=math.degrees(sat.mo),
        mean_motion_rev_per_day=sat.no_kozai * 1440.0 / (2.0 * math.pi),
    )
    return sat, el


def _sgp4_at(sat: Satrec, t_unix: float) -> tuple[float, float, float]:
    jd = t_unix / 86400.0 + _JD_UNIX_EPOCH
    err, r, _v = sat.sgp4(math.floor(jd) + 0.5, jd - math.floor(jd) - 0.5)
    assert err == 0
    return r


def _max_error_km(l1: str, l2: str, minutes: list[int]) -> float:
    sat, el = _setup(l1, l2)
    return max(
        math.dist(_sgp4_at(sat, el.epoch_unix + m * 60), propagate_eci(el, el.epoch_unix + m * 60))
        for m in minutes
    )


def test_leo_within_30km_of_sgp4():
    # ~8-15 km measured; data refreshes every 10 min so ±2 h is generous
    assert _max_error_km(*ISS, minutes=[0, 10, 30, 60, 120]) < 30.0
    assert _max_error_km(*NOAA15, minutes=[0, 10, 30, 60, 120]) < 30.0


def test_high_eccentricity_within_300km_of_sgp4():
    # ~70-110 km measured on a 15,000-36,000 km orbit radius (< 0.8%)
    assert _max_error_km(*MOLNIYA, minutes=[0, 10, 30, 60, 120]) < 300.0


def test_ecef_matches_pipeline_frame():
    """propagate_ecef must land at the same geodetic point the pipeline
    writes to satellites.csv (same GMST rotation, same frame)."""
    sat, el = _setup(*ISS)
    t = el.epoch_unix
    jd = t / 86400.0 + _JD_UNIX_EPOCH

    lat_ref, lon_ref, _ = teme_to_geodetic(_sgp4_at(sat, t), math.floor(jd) + 0.5, jd - math.floor(jd) - 0.5)

    x, y, z = propagate_ecef(el, t)
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    lon = math.degrees(math.atan2(y, x))

    # Model error (~12 km) only, no frame/rotation offset
    assert abs(lat - lat_ref) < 0.2
    assert abs((lon - lon_ref + 180.0) % 360.0 - 180.0) < 0.2
