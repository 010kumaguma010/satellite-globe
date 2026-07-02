from satglobe.tle import alpha5_to_norad, parse_tles

ISS_L1 = "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9005"
ISS_L2 = "2 25544  51.6400 208.9163 0006317  69.9862 290.2018 15.49560532    15"


def test_parse_3le_with_zero_prefix():
    tles = parse_tles(["0 ISS (ZARYA)", ISS_L1, ISS_L2])
    assert len(tles) == 1
    assert tles[0].name == "ISS (ZARYA)"
    assert tles[0].norad == 25544


def test_parse_3le_plain_name():
    tles = parse_tles(["ISS (ZARYA)", ISS_L1, ISS_L2])
    assert tles[0].name == "ISS (ZARYA)"


def test_parse_2le_uses_norad_name():
    tles = parse_tles([ISS_L1, ISS_L2])
    assert tles[0].name == "NORAD 25544"
    assert tles[0].norad == 25544


def test_parse_skips_garbage_lines():
    tles = parse_tles(["garbage", "", "0 ISS (ZARYA)", ISS_L1, ISS_L2, "trailing junk"])
    assert len(tles) == 1
    assert tles[0].name == "ISS (ZARYA)"


def test_alpha5_plain_digits():
    assert alpha5_to_norad("25544") == 25544


def test_alpha5_letter_prefix():
    # A=10 … T=27 (I and O skipped), so T0447 → 270447
    assert alpha5_to_norad("T0447") == 270447
    assert alpha5_to_norad("A0001") == 100001
    assert alpha5_to_norad("Z9999") == 339999
