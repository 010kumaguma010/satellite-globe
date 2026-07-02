"""TEME → WGS84 geodetic coordinate conversion.

sgp4 outputs position vectors in the TEME (True Equator, Mean Equinox)
inertial frame. For display on a globe we need geodetic latitude,
longitude and height above the WGS84 ellipsoid. Rotating TEME by GMST
gives an Earth-fixed frame accurate to well under a kilometre at the
surface (polar motion and equation-of-the-equinoxes terms are ignored),
which is far below the precision of TLE data itself (~1 km at epoch).
"""

import math

WGS84_A = 6378.137  # semi-major axis, km
WGS84_F = 1.0 / 298.257223563  # flattening
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)  # first eccentricity squared


def gmst(jd_ut1: float) -> float:
    """Greenwich Mean Sidereal Time in radians (IAU 1982 model)."""
    t = (jd_ut1 - 2451545.0) / 36525.0
    seconds = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t
        + 0.093104 * t * t
        - 6.2e-6 * t * t * t
    )
    return math.radians((seconds % 86400.0) / 240.0)


def teme_to_geodetic(
    r_teme: tuple[float, float, float], jd: float, fr: float
) -> tuple[float, float, float]:
    """Convert a TEME position vector (km) at Julian date jd+fr to
    (geodetic latitude deg, longitude deg in [-180, 180], height km)."""
    theta = gmst(jd + fr)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    x_t, y_t, z = r_teme
    # Rotate about the Z axis by GMST: TEME → ECEF (pseudo Earth-fixed)
    x = x_t * cos_t + y_t * sin_t
    y = -x_t * sin_t + y_t * cos_t

    lon = math.degrees(math.atan2(y, x))

    # Iterative geodetic latitude (converges in a few steps for any orbit)
    r_xy = math.hypot(x, y)
    lat = math.atan2(z, r_xy)
    n = WGS84_A
    for _ in range(6):
        sin_lat = math.sin(lat)
        n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
        lat = math.atan2(z + n * WGS84_E2 * sin_lat, r_xy)

    sin_lat = math.sin(lat)
    if abs(lat) < math.radians(89.0):
        height = r_xy / math.cos(lat) - n
    else:  # near the poles cos(lat) → 0; use the Z-axis form instead
        height = z / sin_lat - n * (1.0 - WGS84_E2)

    return math.degrees(lat), lon, height
