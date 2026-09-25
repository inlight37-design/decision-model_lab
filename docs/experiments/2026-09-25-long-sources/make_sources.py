"""Write this experiment's shared sources with fresh values (see README.md).

  python3 make_sources.py <new sources folder> <markers.json outside that folder>

Twenty files: long-a.md and long-b.md near the per-file limit, part-01.md … part-18.md with one marker each.
Every value is drawn independently, so no value can be inferred from another. The markers file must not sit
inside the sources folder; every file there becomes a shared source.
"""
import json, random, secrets, sys
from pathlib import Path

TARGET = 250_000          # bytes per long file; the app allows 262,144 (MAX_SOURCE_BYTES)
PARTS = 18                # 2 long + 18 parts = 20 files, the app's MAX_SOURCES
WORDS = ("ledger crate copper wire bay clerk morning shipment north gate pallet invoice audit harbor road "
         "signal lamp desk report weekly route truck driver storage shelf count label seal dock crane shift "
         "inventory order batch sample carton window corridor ramp scale meter valve filter stock record").split()


def value() -> str:
    return secrets.token_hex(4).upper()


def filler(rng: random.Random) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(rng.randint(10, 16))) + "."


def long_file(rng: random.Random, needles: dict[int, str], wide: tuple[int, str] | None) -> tuple[str, int]:
    """Numbered filler lines up to TARGET bytes. needles maps a line number (negative counts from the end) to a
    FACT sentence. wide puts one FACT near the end of a single line of about 6,000 characters."""
    reserve = 7000 if wide else 200                         # room for the wide line and the needle sentences
    bodies, size = [], 0
    while True:
        body = filler(rng)
        if size + len(body) + 7 > TARGET - reserve:           # 7 = "00001 " + newline
            break
        bodies.append(body)
        size += len(body) + 7
    total = len(bodies)
    for number, fact in needles.items():
        bodies[number - 1 if number > 0 else total + number] = fact
    if wide:
        number, fact = wide
        head = " ".join(filler(rng) for _ in range(60))[:5000]
        tail = " ".join(filler(rng) for _ in range(12))[:1000]
        bodies[number - 1] = f"{head} {fact} {tail}"
    text = "".join(f"{i:05d} {body}\n" for i, body in enumerate(bodies, 1))
    if len(text.encode("utf-8")) > TARGET:
        raise SystemExit("long file over its target size")
    return text, total


def main():
    folder, markers_path = Path(sys.argv[1]), Path(sys.argv[2])
    if folder.exists() or markers_path.resolve().is_relative_to(folder.resolve()):
        sys.exit("give a new sources folder and a markers path outside it")
    rng = random.Random(secrets.randbits(64))
    facts = {name: value() for name in ("harbor", "lantern", "quartz", "meadow", "cobalt", "violet")}
    sentence = "FACT {}: the recorded value is {}.".format
    a, a_lines = long_file(rng, {40: sentence("harbor", facts["harbor"]), 1400: sentence("lantern", facts["lantern"]),
                                 -3: sentence("quartz", facts["quartz"])}, None)
    b, b_lines = long_file(rng, {40: sentence("meadow", facts["meadow"]), -3: sentence("violet", facts["violet"])},
                           (700, sentence("cobalt", facts["cobalt"])))
    parts = {f"part-{i:02d}.md": value() for i in range(1, PARTS + 1)}
    files = {"long-a.md": a, "long-b.md": b, **{name: f"marker: {marker}\n" for name, marker in parts.items()}}
    # where each FACT sits, for the results table; the end needles are the third-to-last line
    placement = {"harbor": ("long-a.md", 40), "lantern": ("long-a.md", 1400), "quartz": ("long-a.md", a_lines - 2),
                 "meadow": ("long-b.md", 40), "cobalt": ("long-b.md", 700), "violet": ("long-b.md", b_lines - 2)}
    folder.mkdir(parents=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8", newline="\n")
    markers = {"facts": facts, "placement": placement, "wide_fact": "cobalt", "parts": parts,
               "lines": {"long-a.md": a_lines, "long-b.md": b_lines},
               "bytes": {name: len(text.encode("utf-8")) for name, text in files.items()}}
    markers_path.parent.mkdir(parents=True, exist_ok=True)
    markers_path.write_text(json.dumps(markers, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"files": len(files), "total_bytes": sum(markers["bytes"].values()),
                      "long": {k: {"bytes": markers["bytes"][k], "lines": v} for k, v in markers["lines"].items()},
                      "markers_file": str(markers_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
