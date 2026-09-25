"""Write this experiment's shared sources with fresh values (see README.md).

  python3 make_sources.py <new sources folder> <markers.json outside that folder>

Twenty files, just under the app's 1 MiB total (MAX_SOURCES_TOTAL): long-a.md … long-d.md near the per-file limit,
part-01.md … part-16.md with one marker each. Every value is drawn independently, so no value can be inferred from
another. The markers file must not sit inside the sources folder; every file there becomes a shared source.
"""
import json, random, secrets, sys
from pathlib import Path

TOTAL_LIMIT = 1024 * 1024  # the app's MAX_SOURCES_TOTAL
TARGET = 261_000           # bytes per long file; the app allows 262,144 (MAX_SOURCE_BYTES)
PARTS = 16                 # 4 long + 16 parts = 20 files, the app's MAX_SOURCES
WORDS = ("ledger crate copper wire bay clerk morning shipment north gate pallet invoice audit harbor road "
         "signal lamp desk report weekly route truck driver storage shelf count label seal dock crane shift "
         "inventory order batch sample carton window corridor ramp scale meter valve filter stock record").split()
# (file, front, middle, end) FACT names; front is line 40, middle the middle line, end the third-to-last line
NAMES = (("long-a.md", "harbor", "lantern", "quartz"), ("long-b.md", "meadow", "cobalt", "violet"),
         ("long-c.md", "ember", "falcon", "garnet"), ("long-d.md", "juniper", "kestrel", "saffron"))


def value() -> str:
    return secrets.token_hex(4).upper()


def filler(rng: random.Random) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(rng.randint(10, 16))) + "."


def long_file(rng: random.Random, front: str, middle: str, end: str) -> tuple[str, int, int]:
    """Numbered filler lines up to TARGET bytes with three FACT sentences. Returns text, line count, middle line."""
    bodies, size = [], 0
    while True:
        body = filler(rng)
        if size + len(body) + 7 > TARGET - 200:           # 7 = "00001 " + newline; 200 leaves room for the facts
            break
        bodies.append(body)
        size += len(body) + 7
    total = len(bodies)
    mid = total // 2
    bodies[40 - 1], bodies[mid - 1], bodies[total - 3] = front, middle, end
    text = "".join(f"{i:05d} {body}\n" for i, body in enumerate(bodies, 1))
    if len(text.encode("utf-8")) > TARGET:
        raise SystemExit("long file over its target size")
    return text, total, mid


def main():
    folder, markers_path = Path(sys.argv[1]), Path(sys.argv[2])
    if folder.exists() or markers_path.resolve().is_relative_to(folder.resolve()):
        sys.exit("give a new sources folder and a markers path outside it")
    rng = random.Random(secrets.randbits(64))
    sentence = "FACT {}: the recorded value is {}.".format
    facts, placement, lines, files = {}, {}, {}, {}
    for name, *where in NAMES:
        for fact in where:
            facts[fact] = value()
        text, total, mid = long_file(rng, *(sentence(fact, facts[fact]) for fact in where))
        files[name], lines[name] = text, total
        placement.update({where[0]: (name, 40), where[1]: (name, mid), where[2]: (name, total - 2)})
    parts = {f"part-{i:02d}.md": value() for i in range(1, PARTS + 1)}
    files.update({name: f"marker: {marker}\n" for name, marker in parts.items()})
    sizes = {name: len(text.encode("utf-8")) for name, text in files.items()}
    if len(files) != 20 or sum(sizes.values()) > TOTAL_LIMIT:
        raise SystemExit("sources do not fit the app limits")
    folder.mkdir(parents=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8", newline="\n")
    markers = {"facts": facts, "placement": placement, "parts": parts, "lines": lines, "bytes": sizes}
    markers_path.parent.mkdir(parents=True, exist_ok=True)
    markers_path.write_text(json.dumps(markers, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"files": len(files), "total_bytes": sum(sizes.values()), "limit": TOTAL_LIMIT,
                      "long": {k: {"bytes": sizes[k], "lines": v} for k, v in lines.items()},
                      "markers_file": str(markers_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
