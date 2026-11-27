# YHFD Relay Pumping Calculator

This repo is one HTML page that plans a long supply line lay for Yorktown Heights Fire District (YHFD). A repo is a project folder that Git tracks. Git saves each version of the files.
The user traces a hose route on a map. The page reads the ground height along the route. It then shows the hose, the climb, the relay engines, and the pump discharge pressure (PDP) for each engine.
The plan has three parts: Find, Calculate, and Carry. Only Calculate is built. This repo holds Calculate.
Status: pilot v0.14. Alex approved the v0.2 direction. No field check is done yet.
The history of each version, v0.3 to v0.14, is in `docs/handoff-2026-11-24.md`.
The GitHub repo is private. Its name is yhfd-relay-calculator.

## Files

| Path | Content |
|---|---|
| `src/calculator.html` | The page source. Markup, styles, and two scripts: `core` (hydraulics) and `appjs` (map and screen). |
| `build.py` | Puts Leaflet, the district boundary, and the hydrant list into one HTML file. It adds a town hydrant only when no county hydrant is in 50 ft (1,378 added). |
| `data/fire-districts.geojson` | 60 named Westchester fire district boundaries. Yorktown Hgts FD is id 253. |
| `data/hydrants.json` | 22,499 hydrants, all of Westchester County. 823 have the YHFD code `YKTWN`. The county list is not complete: Hartsdale FD has 3, Fairview FD 24, Peekskill FD 1. |
| `data/hydrants-greenburgh.json` | 1,813 Town of Greenburgh hydrants in service, with the code `TOG`. |
| `scripts/fetch_hydrants.py` | Gets the hydrant list again from the county. |
| `scripts/fetch_greenburgh_hydrants.py` | Gets the town hydrants again from the Town of Greenburgh. |
| `scripts/fetch_districts.py` | Gets the district boundaries again from the county. |
| `tests/test_core.js` | 70 math checks: against the chauffeur chart, for the road draft, and for dual 3 inch lines. Runs in Node. |
| `tests/test_ui.py` | 166 page checks in Chrome through Playwright. No internet needed. |
| `package.json` | Version 0.14.0. It holds the `build`, `test`, and `test:ui` commands. |
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
| `npm test` | Builds, then runs the 70 math checks. |
| `npm run test:ui` | Builds, then runs the 166 page checks. It calls `.venv/bin/python`. |

Set `CHROME_PATH` to the Chrome program if Playwright cannot find Chrome.
On 2026-11-27, 70 of 70 math checks and 166 of 166 page checks passed on macOS with Google Chrome 158.

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

Recorded SHA-256 of `dist/YHFD Relay Pumping Calculator.html`: `600fc30eeab007bb63b6a87c3596029128b04aaa691676203daf75a5bd4555cb`
This is the v0.14 build. Older values are in `docs/handoff-2026-11-24.md`. On 2026-11-27 the copy Alex uses in OneDrive is the v0.14 build.
Claude replaced that copy nine times (v0.3, v0.4, v0.6 to v0.10, v0.13, and v0.14), each on a direct request from Alex. Rule 3 still applies.

## Hydraulic rules

All values come from the YHFD chauffeur reference chart (PDF).

- Friction loss, one rule: `C x (GPM/100)^2` PSI for each 100 ft. C = 0.08 for 5 inch hose and 0.2 for 4 inch hose.
- Dual 3 inch lines: the chart says to divide the total flow in half and to calculate for one 3 inch line (C = 0.8). This equals C = 0.2 on the total flow.
- The chart table values are the formula values, rounded for the pump panel (Alex, 2026-11-27). The page does not use the table.
- Values for each 100 ft at 500, 750, 1,000, 1,250, 1,500, and 2,000 GPM: 2, 4.5, 8, 12.5, 18, 32 for 5 inch. 5, 11.25, 20, 31.25, 45, 80 for 4 inch and dual 3 inch lines.
- Maximum pressure for 3 inch hose: 250 PSI (Alex, 2026-11-26). This value is not in the chart.
- Climb: 0.5 PSI for each foot.
- Maximum LDH pressure: 200 PSI. The page warns when a downhill run goes above it.
- Minimum pressure in the hose at each point: 10 PSI.
- Intake pressure to hold at each engine: 20 PSI (setting: 20 or 50).
- Maximum PDP: 185 PSI (setting: 150, 175, 185, or 200). The chart has Max Relay Distance values for 150 and 200 PSI only.
- Minimum PDP: 50 PSI, a pump at idle.
- PDP always rounds up to the next 5 PSI (Alex, 2026-11-27). 31 gives 35. 30 stays 30. A pump operator can set a pressure to about 5 PSI.
- Hose length: map distance and slope, plus a slack allowance (setting, 10% default).
- Ground height: one sample each 25 ft, 400 samples maximum for a route.

Relay placement: the page finds the fewest engines at the maximum PDP.
It then lowers the pressure to the lowest equal value that keeps that engine count.
The user can drag a relay engine. The page then shows the PDPs for that position and flags a limit that is broken.

## Decisions Alex made

- Calculator pilot first, before the district screen.
- Show 500, 750, and 1,000 GPM together. (v0.8 changed this list. See the decisions for v0.8.)
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

Decisions for v0.4 (Alex, 2026-11-26):

- A user can save the page to a device and set their own defaults.
- The 6 defaults are: fire district, hose size, maximum PDP, intake pressure, slack, and hose on each engine. The lay is never a default. (v0.10 removed the friction basis.)
- Three layers, and a later layer wins: the built-in YHFD values, the values in a saved copy of the page, and the values saved in the browser.
- Clear sets the settings back to the defaults. A plan file keeps its own settings.
- A saved copy uses its own browser storage keys.

Decisions for v0.6 (Alex, 2026-11-26):

- Add the Town of Greenburgh hydrants to the page. Keep all county hydrants.
- Research on 2026-11-26 found no public hydrant data for Peekskill, Buchanan, Ossining, or Harrison. OpenStreetMap is not useful.
- Croton Falls FD and South Salem FD say that they have no standard hydrants. Their zero count is correct.

Decisions for v0.7 (Alex, 2026-11-26):

- Dual 3 inch lines are a supply hose option. YHFD does not carry dual 3 inch lines. Other departments can.
- With dual lines, the hose setting means the length of dual line that one engine lays. The page does no division.
- When the address point is less than 100 ft from the road, the road draft stops on the road.
- The user can drag the S and A markers. S snaps to a hydrant in 75 ft.
- The chart is in the YHFD folder: `Operations/Apparatus & Equipment/yhfd-chauffeur-reference-chart.pdf`. Read only.

Decisions for v0.8 (Alex, 2026-11-26):

- The page shows 500, 750, 1,000, 1,250, 1,500, and 2,000 GPM. The six-flow list is the reading that Claude made of the request. Alex has not confirmed it.
- The card prints 500, 1,250, and 2,000 GPM. It stays on one letter page.
- When the selected flow is not on the card, the card map and profile show 1,250 GPM.
- A long card makes the card map shorter, from 3.15 inch down to 1.8 inch. Claude added this rule to keep one page.
- The card shows one block for each flow (Alex, 2026-11-27): a large GPM label, only the engines that the flow needs, one large PDP for each engine, and one arrow for each hose section. The arrowhead is where the engine stops and pumps.
- The card does not show "ft out" or the climb for each section. The planner on the screen keeps them.
- An Impeccable critique of an earlier draft is in `.impeccable/critique/` on this Mac. Git does not track that folder. Its main lesson: black marks only, because a photocopy loses colour and small marks.

Decisions for v0.9 (Alex, 2026-11-27):

- The address search only finds the address. It makes no route.
- Step 2, "Set up the lay", holds the water source type, the lay, and the settings (six in v0.9, five from v0.10). The user sees them before a draft.
- The page drafts only on the "Draft route by road" button. The water source type and the lay start empty.
- A road draft is 5,280 ft maximum by road. Before v0.9 the limit was a search box, and a draft could be longer.
- For a draft site, a tanker dump site, or other, the user clicks the source on the map. The page drafts by road from that point. Claude added this.
- These decisions replace two v0.3 decisions: the draft after the address search, and the box of 1 mile.

Decisions for v0.10 (Alex, 2026-11-27):

- The chart table is "2 am fireman math": the formula, rounded for the pump panel. This closes chart conflict 2 in the handoff notes.
- A PDP always rounds up to the next 5 PSI.
- A card printed to PDF gets the file name `YY-MM-DD_Plan Name_Address`. The plan file keeps the found address.
- The page has one friction rule and no selector. Claude read the answer from Alex as a yes to this. Alex has not said the word yes.

Decisions for v0.11 to v0.14 (Alex, 2026-11-27). All came from an Impeccable critique. The report is in `.impeccable/critique/`.

- A card block shows a flow only when the flow needs 5 relay engines or fewer.
- With 6 or more relay engines, the block says "Not practical as a relay" and gives the real count. It shows no PDP and no arrows.
- The limit is a fixed value, `CARD_MAX_RELAYS`. It is not a setting. The planner screen still shows all engines.
- v0.12: the card map fits the route with 20 px of padding. The card shows the engine markers at 70% size. The mockup is in `docs/mockups/`.
- v0.13: when a route result exists, the four setup sections fold to one line each. Each engine row shows a large PDP. A phone scrolls to the result.
- v0.14: Clear asks first. Route handles are larger. A click on a point offers "Remove point". Flow rows work from the keyboard. The pressure demand box is gone.

## Data sources

In the table, `...` means the county server base: `https://giswww.westchestergov.com/arcgis/rest/services`

| Data | Source | Notes |
|---|---|---|
| Ground height | USGS 3DEP `https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/getSamples` | 1 metre LiDAR grid here. Values in metres. Fallback: `https://epqs.nationalmap.gov/v1/json`. |
| Hydrants | `https://giswww.westchestergov.com/arcgis/rest/services/DataHub_Infrastructure/MapServer/147` | County date: October 5, 2015. No flow values. |
| Hydrants, Town of Greenburgh | `https://services5.arcgis.com/7CI4QzLwCwxDf9WB/arcgis/rest/services/WaterDistributionSystem_V3/FeatureServer/32` | Owner: Town of Greenburgh GIS. Edited 2026-11-24. No flow values that the page can use. No licence text. |
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
- **Page defaults (Alex, 2026-11-26):** the page plans with 1,000 ft on each engine and 185 PSI maximum PDP. Alex said that these values and the two facts above are all true.
- Do not change the built-in defaults without Alex's approval.

## Open items and history

Open items and history are in `docs/handoff-2026-11-24.md`. Read that file before you plan new work.
