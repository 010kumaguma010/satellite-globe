import math

from sgp4.api import jday

from satglobe.geodesy import WGS84_A, WGS84_E2, gmst, teme_to_geodetic


def _ecef_from_geodetic(lat_deg: float, lon_deg: float, h_km: float):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    x = (n + h_km) * math.cos(lat) * math.cos(lon)
    y = (n + h_km) * math.cos(lat) * math.sin(lon)
    z = (n * (1 - WGS84_E2) + h_km) * math.sin(lat)
    return x, y, z


def _teme_from_ecef(ecef, theta):
    x, y, z = ecef
    return (
        x * math.cos(theta) - y * math.sin(theta),
        x * math.sin(theta) + y * math.cos(theta),
        z,
    )


def _roundtrip(lat, lon, h):
    jd, fr = jday(2024, 6, 15, 12, 30, 45.0)
    teme = _teme_from_ecef(_ecef_from_geodetic(lat, lon, h), gmst(jd + fr))
    got_lat, got_lon, got_h = teme_to_geodetic(teme, jd, fr)
    assert abs(got_lat - lat) < 1e-6
    assert abs(got_h - h) < 1e-6
    dlon = (got_lon - lon + 180.0) % 360.0 - 180.0
    assert abs(dlon) < 1e-6


def test_roundtrip_mid_latitude():
    _roundtrip(35.6895, 139.6917, 408.0)  # over Tokyo at ISS altitude


def test_roundtrip_southern_hemisphere():
    _roundtrip(-45.0, -60.0, 800.0)


def test_roundtrip_equator():
    _roundtrip(0.0, 0.0, 35786.0)  # GEO altitude


def test_roundtrip_near_pole():
    _roundtrip(89.5, 10.0, 700.0)


def test_gmst_j2000():
    # GMST at the J2000.0 epoch (2000-01-01 12:00 UT1) ≈ 280.4606°
    assert abs(math.degrees(gmst(2451545.0)) - 280.4606) < 0.001


def test_longitude_range():
    jd, fr = jday(2024, 1, 1, 0, 0, 0.0)
    for lon in (-179.0, -90.0, 0.0, 90.0, 179.0):
        teme = _teme_from_ecef(_ecef_from_geodetic(10.0, lon, 500.0), gmst(jd + fr))
        _, got_lon, _ = teme_to_geodetic(teme, jd, fr)
        assert -180.0 <= got_lon <= 180.0
