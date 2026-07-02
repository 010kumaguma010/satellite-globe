"""Reference implementation of the client-side propagation model.

This is the exact algorithm the VRChat client (clients/vrchat/
SatelliteGlobe.cs) and the web viewer (docs/index.html) use to turn a
row of data/orbits.csv into a position at an arbitrary time: two-body
Kepler propagation plus secular J2 drift of the node and perigee.

It intentionally trades accuracy for simplicity — no short-period
perturbations, no drag — which keeps it cheap enough to run for tens of
thousands of satellites per frame in Udon/JavaScript. Against full SGP4
it stays within a few tens of km near epoch (see tests/test_kepler.py),
i.e. visually indistinguishable on a globe. The data files are
regenerated every 10 minutes, so the elements never get old enough for
the model to drift visibly.

Keep the three implementations in sync: this file is the one under test.
"""

import math
from dataclasses import dataclass

from .geodesy import gmst

MU = 398600.4418  # Earth gravitational parameter, km^3/s^2
J2 = 1.08262668e-3
RE = 6378.137  # Earth equatorial radius, km
_JD_UNIX_EPOCH = 2440587.5


@dataclass(frozen=True)
class Elements:
    """One row of data/orbits.csv."""

    epoch_unix: float
    inc_deg: float
    raan_deg: float
    ecc: float
    argp_deg: float
    mean_anomaly_deg: float
    mean_motion_rev_per_day: float


def propagate_eci(el: Elements, t_unix: float) -> tuple[float, float, float]:
    """Position in the inertial (TEME-like) frame at Unix time t, in km."""
    n = el.mean_motion_rev_per_day * 2.0 * math.pi / 86400.0  # rad/s
    a = (MU / (n * n)) ** (1.0 / 3.0)
    e = el.ecc
    p = a * (1.0 - e * e)

    inc = math.radians(el.inc_deg)
    cos_i, sin_i = math.cos(inc), math.sin(inc)

    # Secular J2 drift of RAAN and argument of perigee
    factor = 1.5 * J2 * (RE / p) ** 2 * n  # rad/s
    dt = t_unix - el.epoch_unix
    raan = math.radians(el.raan_deg) - factor * cos_i * dt
    argp = math.radians(el.argp_deg) + 0.5 * factor * (5.0 * cos_i * cos_i - 1.0) * dt

    # Kepler's equation, Newton iteration (e < 0.8 for everything in orbit)
    m = math.radians(el.mean_anomaly_deg) + n * dt
    ecc_anom = m
    for _ in range(6):
        ecc_anom -= (ecc_anom - e * math.sin(ecc_anom) - m) / (1.0 - e * math.cos(ecc_anom))

    nu = math.atan2(
        math.sqrt(1.0 - e * e) * math.sin(ecc_anom), math.cos(ecc_anom) - e
    )
    r = a * (1.0 - e * math.cos(ecc_anom))

    # Perifocal → inertial: R3(-raan) · R1(-inc) · R3(-argp)
    u = argp + nu  # argument of latitude
    cos_u, sin_u = math.cos(u), math.sin(u)
    cos_o, sin_o = math.cos(raan), math.sin(raan)
    x = r * (cos_o * cos_u - sin_o * sin_u * cos_i)
    y = r * (sin_o * cos_u + cos_o * sin_u * cos_i)
    z = r * (sin_u * sin_i)
    return x, y, z


def propagate_ecef(el: Elements, t_unix: float) -> tuple[float, float, float]:
    """Earth-fixed position at Unix time t, in km (rotate ECI by GMST)."""
    x, y, z = propagate_eci(el, t_unix)
    theta = gmst(t_unix / 86400.0 + _JD_UNIX_EPOCH)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    return x * cos_t + y * sin_t, -x * sin_t + y * cos_t, z
