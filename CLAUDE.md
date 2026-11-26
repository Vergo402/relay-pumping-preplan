# YHFD Relay Pumping Calculator

This repo is one HTML page that plans a long supply line lay for Yorktown Heights Fire District (YHFD). A repo is a project folder that Git tracks. Git saves each version of the files.
The user traces a hose route on a map. The page reads the ground height along the route. It then shows the hose, the climb, the relay engines, and the pump discharge pressure (PDP) for each engine.
The plan has three parts: Find, Calculate, and Carry. Only Calculate is built. This repo holds Calculate.
Status: pilot v0.3. Alex approved the v0.2 direction. No field check is done yet.
v0.3 adds a fire district picker for 60 Westchester districts and a road draft. The hydraulic rules are still the YHFD rules.
The GitHub repo is private. Its name is yhfd-relay-calculator.

## Files

| Path | Content |
|---|---|
| `src/calculator.html` | The page source. Markup, styles, and two scripts: `core` (hydraulics) and `appjs` (map and screen). |
| `build.py` | Puts Leaflet, the district boundary, and the hydrant list into one HTML file. |
| `data/fire-districts.geojson` | 60 named Westchester fire district boundaries. Yorktown Hgts FD is id 253. |
| `data/hydrants.json` | 22,499 hydrants, all of Westchester County. 823 have the YHFD code `YKTWN`. |
| `scripts/fetch_hydrants.py` | Gets the hydrant list again from the county. |
| `scripts/fetch_districts.py` | Gets the district boundaries again from the county. |
| `tests/test_core.js` | 47 math checks: 36 against the chauffeur chart and 11 for the road draft. Runs in Node. |
| `tests/test_ui.py` | 34 page checks in Chrome through Playwright. No internet needed. |
| `package.json` | Version 0.3.0. It holds the `build`, `test`, and `test:ui` commands. |
| `docs/handoff-2026-11-24.md` | The handoff notes: open items and history. |
| `docs/mockups/` | The mockups that Alex accepted. A build must match its mockup. |
| `dist/` | Build output. Git ignores it. |
| `out/` | Test output. Git ignores it. |
| `node_modules/` | Leaflet 1.9.4, the map library. Git ignores it. |
| `.venv/` | The Python virtual environment for Playwright. Git ignores it. |

Leaflet is a map library. Node runs JavaScript outside a browser. Playwright is a tool that drives a browser for a test.

## Commands

One-time setup. Run each step in the repo folder.

1. Run `npm install`. This gets Leaflet. npm is the package tool for Node.
2. Run `python3 -m venv .venv`. This makes a virtual environment, a private folder for Python packages.
3. Run `.venv/bin/pip install playwright`.

Homebrew Python blocks a global pip install. For this reason Playwright lives in `.venv/`.
No Playwright browser download is necessary. The page test uses the installed Google Chrome.

| Command | Result |
|---|---|
| `python3 build.py` | Writes `dist/YHFD Relay Pumping Calculator.html`. |
| `npm test` | Builds, then runs the 47 math checks. |
| `npm run test:ui` | Builds, then runs the 34 page checks. It calls `.venv/bin/python`. |

Set `CHROME_PATH` to the Chrome program if Playwright cannot find Chrome.
On 2026-11-26, 47 of 47 math checks and 34 of 34 page checks passed on macOS with Google Chrome 158.

## Rules

1. Show the plan first. Wait for Alex to approve it before each change.
2. Do not change `src/calculator.html`, the hydraulic rules, or the data files. Change them only when Alex asks for it in that session.
3. Never write to the OneDrive YHFD folder. Alex uses this copy: `~/Library/CloudStorage/OneDrive-Personal/02 - YHFD (Yorktown Heights Engine Co 1)/Operations/Water Supply Pre-Plans/YHFD Relay Pumping Calculator.html`
4. Keep the repo out of OneDrive. OneDrive sync caused problems for Alex before. Code lives in `~/Developer`.
5. Do not make `MEMORY.md` files. Put lasting facts in this file.
6. Write all documents in ASD-STE100. This is a controlled form of English with short, plain sentences.
7. Use plain language. Define each technical term the first time you use it.
8. After a build, check the SHA-256. The SHA-256 is a fingerprint of a file. It must equal the recorded value below.
9. Change the recorded value only when Alex approved a source change. Then record the new value here.

Recorded SHA-256 of `dist/YHFD Relay Pumping Calculator.html`: `1578de0c132e717478485b611000a093dc1717129a5399a8ef89bd293a08f761`
This is the v0.3 build. The copy Alex uses in OneDrive is still v0.2 until Alex replaces it.
The v0.2 value was `21e80ce837c58ff39c76c82a0030220d7f9b859dc50db28cb6cfe615406c2e09`.

## Hydraulic rules

All values come from the YHFD chauffeur reference chart (PDF).

- Friction loss, 5 inch hose, PSI for each 100 ft: 2 at 500 GPM, 5 at 750 GPM, 10 at 1,000 GPM.
- Friction loss, 4 inch hose: 5, 10, and 20.
- Formula option: `C x (GPM/100)^2 x (ft/100)`, with C = 0.08 for 5 inch and 0.2 for 4 inch.
- Climb: 0.5 PSI for each foot.
- Maximum LDH pressure: 200 PSI. The page warns when a downhill run goes above it.
- Minimum pressure in the hose at each point: 10 PSI.
- Intake pressure to hold at each engine: 20 PSI (setting: 20 or 50).
- Maximum PDP: 150 PSI (setting: 150, 175, or 200).
- Minimum PDP: 50 PSI, a pump at idle.
- PDP rounds to the nearest 5 PSI at or above the demand, with a 1 PSI tolerance.
- Hose length: map distance and slope, plus a slack allowance (setting, 10% default).
- Ground height: one sample each 25 ft, 400 samples maximum for a route.

Relay placement: the page finds the fewest engines at the maximum PDP.
It then lowers the pressure to the lowest equal value that keeps that engine count.
The user can drag a relay engine. The page then shows the PDPs for that position and flags a limit that is broken.

## Decisions Alex made

- Calculator pilot first, before the district screen.
- Show 500, 750, and 1,000 GPM together.
- The product is a tool to plan, plus printed cards.
- Hydrants come from public county data.
- A reverse lay / forward lay selector with no default. The user picks one for each new route.
- The lay sets the click order. Reverse: attack engine first, water source last. Forward: the opposite.
- The lay sets which engine lays each hose section. The page shows the lay order.
- Hard limit: no hose section is longer than the supply hose on one engine. The page adds relay engines to hold it.

The route points are always stored in water order: source first, attack engine last.

Decisions for v0.3 (Alex, 2026-11-26):

- Any Westchester district can be selected. YHFD is the default. The page keeps the YHFD chart and title.
- After the address search, the page drafts a route from the nearest hydrant by road to the address. The user edits the draft.
- The draft shows only when the route is empty. With no road or no hydrant in 1 mile, the user traces by hand.
- The page holds all county hydrants. The picker lists the 60 named districts.

## Data sources

In the table, `...` means the county server base: `https://giswww.westchestergov.com/arcgis/rest/services`

| Data | Source | Notes |
|---|---|---|
| Ground height | USGS 3DEP `https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/getSamples` | 1 metre LiDAR grid here. Values in metres. Fallback: `https://epqs.nationalmap.gov/v1/json`. |
| Hydrants | `https://giswww.westchestergov.com/arcgis/rest/services/DataHub_Infrastructure/MapServer/147` | County date: October 5, 2015. No flow values. |
| Street map | `.../WestchesterCountyBasemap_WGS84/MapServer` | Tiles. |
| Aerial photo 2025 | `.../MappingWestchesterCounty_AerialPhoto2025/MapServer/export` | Image export. |
| 2 ft contours | `.../2FtContours_WGS84/MapServer` | Tiles from zoom 18 only. |
| Driveways and buildings | `.../DataHub_BasemapPlanimetrics/MapServer` layers 10 and 5 | Driveways are polygons. 10,140 in the district box. Useful for the Find part. |
| Address search | `.../geocoding/GeocodeServer/findAddressCandidates` | County geocoder. The page sends the district box as `searchExtent` (JSON form). |
| Fire districts | `.../Datahub_Boundaries/MapServer/153` | 64 records. The build keeps the 60 named districts. |
| Roads | `.../MappingWestchesterCounty_Roads/MapServer/11` | Street centerlines. The page reads them live for the road draft. 1,000 records for each request. |
| Topo map | `https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer` | Tiles to zoom 16. |

The page needs an internet connection. Both servers allowed requests from a page opened as a local file.

## Answers to open items

- **Open item 1, hose loads (Alex, 2026-11-25):** each YHFD engine carries 1,500 ft of 5 inch supply hose.
- **Open item 2, relay pressure policy (Alex, 2026-11-26):** the department maximum PDP for relays is 200 PSI.
- The page defaults are still 1,000 ft and 150 PSI. For now, set both values by hand in the page settings.
- Set "Supply hose on each engine (ft)" to 1500.
- Set "Maximum PDP" to 200 PSI.
- Do not change the defaults without Alex's approval. The change touches `src/calculator.html`, the tests, and the SHA-256.
- The page hint calls the hose load a placeholder. Update that hint with the default change.

## Open items and history

Open items and history are in `docs/handoff-2026-11-24.md`. Read that file before you plan new work.
