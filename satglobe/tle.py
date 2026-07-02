"""TLE parsing: 3LE (name + two lines) and bare 2LE, with Alpha-5 support."""

from dataclasses import dataclass

# Alpha-5 scheme: catalog numbers above 99999 replace the first digit with a
# letter (I and O are excluded to avoid confusion with 1 and 0).
_ALPHA5 = {c: str(i) for i, c in enumerate("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ")}


@dataclass(frozen=True)
class Tle:
    name: str
    line1: str
    line2: str
    norad: int


def alpha5_to_norad(field: str) -> int:
    """Decode the 5-character catalog-number field of a TLE line.

    '25544' → 25544, 'T0447' → 270447 (Alpha-5).
    """
    field = field.strip()
    head = _ALPHA5.get(field[0].upper())
    if head is None:
        raise ValueError(f"invalid catalog number field: {field!r}")
    return int(head + field[1:])


def _clean_name(raw: str) -> str:
    """Strip the '0 ' marker that 3LE name lines carry."""
    name = raw.strip()
    if name.startswith("0 "):
        name = name[2:].strip()
    return name


def parse_tles(lines: list[str]) -> list[Tle]:
    """Parse TLE text in 3-line or 2-line format into Tle records.

    Malformed groups are skipped rather than raising, since public
    catalogs occasionally contain stray lines.
    """
    clean = [line.rstrip() for line in lines if line.strip()]
    out: list[Tle] = []
    i = 0
    while i < len(clean):
        line = clean[i]
        if (
            not line.startswith(("1 ", "2 "))
            and i + 2 < len(clean)
            and clean[i + 1].startswith("1 ")
            and clean[i + 2].startswith("2 ")
        ):
            l1, l2 = clean[i + 1], clean[i + 2]
            try:
                norad = alpha5_to_norad(l1[2:7])
            except ValueError:
                i += 1
                continue
            out.append(Tle(_clean_name(line), l1, l2, norad))
            i += 3
        elif line.startswith("1 ") and i + 1 < len(clean) and clean[i + 1].startswith("2 "):
            try:
                norad = alpha5_to_norad(line[2:7])
            except ValueError:
                i += 1
                continue
            out.append(Tle(f"NORAD {norad}", line, clean[i + 1], norad))
            i += 2
        else:
            i += 1
    return out
