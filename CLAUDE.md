# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Guidelines

Always apply [Karpathy Guidelines](~/.agents/skills/karpathy-guidelines/SKILL.md):
1. **Think Before Coding** — State assumptions, surface tradeoffs, ask when unclear.
2. **Simplicity First** — Minimum code, no speculative features, no premature abstractions.
3. **Surgical Changes** — Touch only what's needed, match existing style, clean up only your own mess.
4. **Goal-Driven Execution** — Define verifiable success criteria, loop until verified.

## Project overview

A single-page browser tool that geocodes addresses in bulk and plots them on a map. Users upload CSV/XLSX/XLS files; the app converts addresses to lat/lon via the Gaode (高德) geocoding API, then displays markers on a Leaflet/OpenStreetMap map. Exports include map screenshots (PNG), CSV with coordinates, and KML.

## Running locally

No build step. Serve the root directory over HTTP (not `file://`, which causes CORS issues with fetch-based geocoding):

```bash
npx http-server -p 8080 -c-1
# or
python -m http.server 8080
```

Then open `http://localhost:8080`. Paste a Gaode Web Service Key into the UI and save it (stored in `localStorage`).

## Architecture

All logic lives in **`index.html`** (HTML + inline `<script>`) and **`style.css`**. No framework, no package manager, no bundler.

**CDN dependencies** (loaded in `<head>`):
- **Leaflet 1.9.4** — OpenStreetMap tile rendering and marker management
- **leaflet-ruler 1.0.5** — distance measurement tool on the map
- **SheetJS (xlsx) 0.18.5** — reads CSV, XLSX, XLS files client-side
- **html2canvas 1.4.1** — renders the map `<div>` to a PNG for export

**Key data flow** (`index.html` inline script):

1. **File upload** (`#fileInput` change handler) → `FileReader` reads as `ArrayBuffer` → SheetJS parses to JSON rows.
2. **Address column detection** — first tries known column names (`地址`, `address`, `Addr`, etc.), with three fallbacks:
   - `stripBomKey()` strips UTF-8 BOM from headers (issue with Excel-exported CSV on Windows).
   - GBK/ANSI re-decode (`codepage: 936`) for Chinese-locale CSV files where UTF-8 produces garbled headers.
   - `inferAddressColumnKey()` heuristic scoring when columns are named `Column1`, `Column2`... (text length, CJK characters, address keywords like 省/市/区/路).
3. **Geocoding** (`geoCode()`) → calls Gaode `/v3/geocode/geo` with exponential-backoff retry on rate limits (`infocode: 10021`). Falls back to JSONP if `fetch` fails (e.g., `file://` protocol). Skips trivially short strings and rows that look like spilled header text.
4. **Foreign address handling**: If Gaode returns a result in China for an address with mostly Latin characters, the result is discarded and Photon (OSM geocoder) is tried instead as a browser-side fallback.
5. **Markers** → `L.marker` per successfully geocoded row, with a popup showing all row fields. After all rows are processed, `fitBounds` zooms to the marker group.
6. **Export** — three buttons:
   - PNG: `html2canvas` on the map div.
   - CSV: SheetJS writes `allData` (now with `lat`/`lon` fields) back to a CSV file.
   - KML: generates KML XML string from rows that have `lat`/`lon`, triggers download via `Blob` + object URL.

**Global state** (all in the inline script's top-level scope):
- `map` — the Leaflet map instance
- `allData` — array of row objects (mutated in place with `lat`/`lon` added after geocoding)
- `markers` — array of `L.marker` instances currently on the map
- `GAODE_KEY` / `LS_GAODE_KEY` — default key placeholder and localStorage key name

## Gaode API key

The app requires a Gaode (高德) **Web Service** key (not a JS API key). Users can either:
- Paste it in the UI and click "保存 Key" (persists to `localStorage`), or
- Replace `GAODE_KEY` in the source with their own key.

Without a valid key, geocoding is skipped entirely.
