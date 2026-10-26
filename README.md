# History Atlas — border data

The map data behind **History Atlas**, a map and timeline of how the world's
borders and empires changed from 8000 BC to 2010, and the script that makes it.

This repository exists because the data is a modified version of a
GPL-3.0 dataset, and the GPL asks that the modified work and its source are
available. Everything here is licensed under the
[GNU General Public License v3.0](LICENSE).

## Source

**Historical Basemaps** by Andres Ourednik —
<https://github.com/aourednik/historical-basemaps> — GPL-3.0. All borders,
names and years come from it. Errors in the borders themselves are best
reported there.

## What was changed

Modified by History Atlas, July 2026:

- **Geometry simplified** with the Douglas–Peucker algorithm (tolerance 0.08°),
  and coordinates rounded to two decimals, so that a year loads quickly in a
  browser (about 200 kB per year). A year whose file would exceed 400 kB is
  simplified again with a doubled tolerance, up to three times.
- **Only the name of each area is kept** (`NAME`); every other property is
  dropped.
- **Three of the source's maps are left out:** 123000 BC and 10000 BC, which
  show the spread of early human populations rather than borders, and 1492,
  which maps indigenous peoples at tribe level and is drawn at a far finer
  level of detail than the maps on either side of it.
- **A search index** (`search-index.json`) lists which map names appear in
  which years.

Two editorial adjustments are made **in the website's code when the map is
drawn, not in these files**: one area the source leaves unnamed is labelled
Switzerland (1994 and 2010), and on the 2010 map Taiwan and Hong Kong are shown
as part of China, following UN convention. The data here is as the source has
it.

## Files

| Path | Contents |
|---|---|
| `data/<year>.json` | One GeoJSON file per map. Negative years are BC: `-500.json` is 500 BC. 50 maps, 8000 BC to 2010. |
| `data/index.json` | Which years exist. |
| `data/search-index.json` | Map name → the years it appears in. |
| `tools/build_data.py` | Downloads the source maps and produces the files above. |

The texts about individual civilisations on the website are written for
History Atlas and are not part of this repository.

## Rebuilding

```
pip install shapely
cd tools
python build_data.py
```

The source files are downloaded from the Historical Basemaps repository and
cached in `tools/cache/`. With `shapely` 2.1 the map files come out
byte-for-byte identical to the ones in `data/`. The inline comments in the
script are in Swedish.

## Contact

Corrections to our modifications, and questions: mail.history.atlas@proton.me
