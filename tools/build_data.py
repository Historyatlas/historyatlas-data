#!/usr/bin/env python3
"""
Builds the border data in ../data/ for History Atlas.

Downloads the historical border maps from Historical Basemaps by Andres Ourednik
(GPL-3.0, https://github.com/aourednik/historical-basemaps), simplifies the
geometry heavily so that each file is small enough to send to a web browser,
and writes one file per year to ../data/, plus index.json (which years exist)
and search-index.json (which map names appear in which years).

Run from this folder:

    pip install shapely
    python3 build_data.py

The raw source files are cached in tools/cache/ (not committed), so a second
run does not download them again. The inline comments below are in Swedish.

To add more years: add them to YEARS below. The key is the file name in the
source repository, e.g. "1650" -> world_1650.geojson and "bc300" ->
world_bc300.geojson. Not every year exists in the source — the script warns
about and skips the ones that are missing. Available years:
https://github.com/aourednik/historical-basemaps/tree/master/geojson
"""

import json
import os
import sys
import urllib.request

try:
    from shapely.geometry import shape, mapping
except ImportError:
    sys.exit("Saknar shapely. Kör: pip install shapely")

BASE_URL = ("https://raw.githubusercontent.com/aourednik/"
            "historical-basemaps/master/geojson/world_{}.geojson")

# filnamn i källrepot -> årtal i appen (negativa = f.Kr.)
#
# Det här är i princip allt källan erbjuder, med tre medvetna undantag:
#
# - bc123000 och bc10000 visar utbredningen av tidiga människopopulationer,
#   inte gränser, och skulle dominera tidslinjens vänsterkant.
# - 1492 är en helt annan sorts karta än sina grannar: den kartlägger
#   ursprungsfolk på stamnivå ("Tsnungwe", "Kaw (Oklahoma)") med 1946 områden
#   och en medianyta på 0,09 mot 2,2 för 1400 och 1500. Lagd emellan dem
#   antyder den en dramatisk förändring mellan 1400 och 1500 som aldrig
#   hänt — det är kartkonventionen som byter, inte historien. Den såg
#   dessutom ut som en trasig karta. Lägg inte tillbaka den utan att först
#   lösa hur två så olika detaljnivåer ska kunna samsas.
YEARS = {
    "bc8000": -8000, "bc5000": -5000, "bc4000": -4000, "bc3000": -3000,
    "bc2000": -2000, "bc1500": -1500, "bc1000": -1000, "bc700": -700,
    "bc500": -500, "bc400": -400, "bc323": -323, "bc300": -300,
    "bc200": -200, "bc100": -100, "bc1": -1,
    "100": 100, "200": 200, "300": 300, "400": 400, "500": 500,
    "600": 600, "700": 700, "800": 800, "900": 900, "1000": 1000,
    "1100": 1100, "1200": 1200, "1279": 1279, "1300": 1300, "1400": 1400,
    "1500": 1500, "1530": 1530, "1600": 1600, "1650": 1650,
    "1700": 1700, "1715": 1715, "1783": 1783, "1800": 1800, "1815": 1815,
    "1880": 1880, "1900": 1900, "1914": 1914, "1920": 1920, "1930": 1930,
    "1938": 1938, "1945": 1945, "1960": 1960, "1994": 1994, "2000": 2000,
    "2010": 2010,
}

# Hur hårt geometrin förenklas. Högre = mindre fil, kantigare kustlinjer.
# 0.08 grader är avstämt mot en världsvy — höj inte utan att titta på
# resultatet, små öar börjar försvinna.
TOLERANCE = 0.08
DECIMALS = 2  # koordinatavrundning, ~1 km precision

# Enstaka årtal i källan är ritade långt mer detaljerat än övriga — 1492 har
# 1946 områden mot ett typiskt 250, och blev 652 kB där grannarna ligger på
# 200. Eftersom appen hämtar ett årtal i taget är det största årtalet som
# avgör hur snabbt sajten känns, så de förenklas hårdare tills de kommer ner
# i nivå med resten. Hellre lite kantigare kust ett år än en synlig hackning.
MAX_YEAR_BYTES = 400 * 1024

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")
# En fil per årtal i ../data/, plus ../data/index.json som listar vilka
# årtal som finns. Appen hämtar bara det årtal som visas (~200 kB, ~60 kB
# gzippat) i stället för hela datasetet (10 MB) innan något kan ritas.
OUT_DIR = os.path.join(HERE, "..", "data")


def download(name):
    """Hämtar en årtalsfil, med lokal cache så vi inte laddar ner i onödan."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"world_{name}.geojson")
    if os.path.exists(path):
        return path
    url = BASE_URL.format(name)
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        print(f"  ! kunde inte hämta {name}: {e}")
        return None
    return path


def round_coords(coords, ndigits):
    if isinstance(coords[0], (list, tuple)):
        return [round_coords(c, ndigits) for c in coords]
    return [round(c, ndigits) for c in coords]


def simplify_file(path, tolerance=TOLERANCE):
    """Förenklar geometrin och behåller bara namnfältet vi faktiskt använder."""
    # explicit UTF-8 — annars gissar Windows cp1252 och kraschar på
    # namn med tecken utanför latin-1
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = []
    for feat in data.get("features", []):
        geom = feat.get("geometry")
        if not geom:
            continue
        try:
            g = shape(geom)
            if not g.is_valid:
                g = g.buffer(0)
            g = g.simplify(tolerance, preserve_topology=True)
            if g.is_empty:
                continue
            new_geom = mapping(g)
        except Exception:
            continue

        new_geom["coordinates"] = round_coords(new_geom["coordinates"], DECIMALS)

        props = feat.get("properties", {})
        # NAME är det fält appen använder. SUBJECTO/PARTOF innehåller ofta
        # skräp (ID-nummer, "true") i källdatan — appen filtrerar bort
        # sådant i isValidPlaceName(), men vi tar bara NAME här.
        features.append({
            "type": "Feature",
            "properties": {"NAME": props.get("NAME")},
            "geometry": new_geom,
        })

    return {"type": "FeatureCollection", "features": features}


def is_valid_place_name(n):
    """Speglar isValidPlaceName() i script.js — samma skräpfilter."""
    if not n:
        return False
    n = str(n).strip()
    if len(n) < 2:
        return False
    if n in ("Unknown", "Okänt"):
        return False
    if n.lstrip("-").isdigit():
        return False
    if n.lower() in ("true", "false"):
        return False
    return True


def build_search_index(years):
    """
    Skriver ../data/search-index.json: varje kartnamn -> vilka årtal det
    förekommer i.

    Utan det här söker appen bara bland de dryga fyrtio kuraterade posterna
    i ENTITIES, medan kartan innehåller tusentals namn. En besökare som
    skriver "Portugal" eller "Byzantine" fick noll träffar trots att båda
    står utritade. Filen hämtas först när sökrutan används, så den kostar
    inget vid sidladdning.
    """
    index = {}
    for year in years:
        path = os.path.join(OUT_DIR, f"{year}.json")
        with open(path, encoding="utf-8") as f:
            fc = json.load(f)
        seen = set()
        for feat in fc.get("features", []):
            name = feat.get("properties", {}).get("NAME")
            if not is_valid_place_name(name) or name in seen:
                continue
            seen.add(name)
            index.setdefault(name, []).append(year)

    out = os.path.join(OUT_DIR, "search-index.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"), ensure_ascii=False)
    size = os.path.getsize(out)
    print(f"Skrev sökindex — {len(index)} namn, {size/1024:.0f} kB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    written = []
    missing = []
    total = 0
    largest = (0, None)

    for name, year in sorted(YEARS.items(), key=lambda kv: kv[1]):
        path = download(name)
        if not path:
            missing.append(name)
            continue
        out_path = os.path.join(OUT_DIR, f"{year}.json")
        tol = TOLERANCE
        note = ""
        for attempt in range(4):
            fc = simplify_file(path, tol)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(fc, f, separators=(",", ":"), ensure_ascii=False)
            size = os.path.getsize(out_path)
            if size <= MAX_YEAR_BYTES:
                break
            tol *= 2
            note = f"  (förenklad hårdare, tolerans {tol:.2f})"
        total += size
        if size > largest[0]:
            largest = (size, year)
        written.append(year)
        print(f"  {year:>6}  {len(fc['features']):>4} områden  {size/1024:>6.0f} kB{note}")

    if not written:
        sys.exit("Inget data hämtat — avbryter.")

    # Appen läser index.json först för att veta vilka årtal som finns, innan
    # den vet vilken fil den ska hämta.
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"ar": sorted(written)}, f, separators=(",", ":"))

    build_search_index(sorted(written))

    print(f"\nSkrev {len(written)} årtal till {OUT_DIR} "
          f"— {total/1024/1024:.2f} MB totalt")
    print(f"Störst enskilt årtal: {largest[1]} ({largest[0]/1024:.0f} kB) "
          f"— det är det som avgör hur snabbt sajten känns")
    if missing:
        print(f"Saknades i källan: {', '.join(missing)}")
    if largest[0] > MAX_YEAR_BYTES:
        print("Varning: största årtalet ligger kvar över gränsen även efter "
              "extra förenkling. Titta på det årtalet för hand.")


if __name__ == "__main__":
    main()
