import csv
import json
from datetime import datetime, timezone

from satglobe.pipeline import compute_states, write_outputs
from satglobe.tle import parse_tles

ISS_3LE = [
    "0 ISS (ZARYA)",
    "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9005",
    "2 25544  51.6400 208.9163 0006317  69.9862 290.2018 15.49560532    15",
]


def test_compute_states_iss():
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # near TLE epoch
    states, skipped = compute_states(parse_tles(ISS_3LE), now)
    assert skipped == 0
    s = states[0]
    assert s.name == "ISS (ZARYA)"
    assert s.norad == 25544
    assert -51.7 <= s.lat <= 51.7  # bounded by inclination
    assert -180.0 <= s.lon <= 180.0
    assert 350.0 < s.alt_km < 460.0
    assert abs(s.inc_deg - 51.64) < 0.01
    assert abs(s.mean_motion_rev_per_day - 15.4956) < 0.01
    # TLE epoch: 2024-01-01T12:00:00Z = unix 1704110400
    assert abs(s.epoch_unix - 1704110400) < 1.0


def test_write_outputs(tmp_path):
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    states, skipped = compute_states(parse_tles(ISS_3LE), now)
    write_outputs(states, now, "test", skipped, str(tmp_path))

    with open(tmp_path / "satellites.csv", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["name", "lat", "lon", "alt_km"]
    assert rows[1][0] == "ISS (ZARYA)"
    assert len(rows) == 2

    with open(tmp_path / "orbits.csv", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0][0] == "name"
    assert rows[1][1] == "25544"

    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["satellites"] == 1
    assert meta["skipped"] == 0
    assert meta["source"] == "test"
    assert meta["generated_at_unix"] == 1704110400
