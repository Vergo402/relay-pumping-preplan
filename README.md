# YHFD Relay Pumping Calculator

This tool is an aid to plan a long supply hose lay with relay engines. It is pilot v0.6. No field check is done yet.

## What the tool does

The tool is one HTML page, a web page in one file. It is for Yorktown Heights Fire District (YHFD). A user can select any of 60 Westchester fire districts, but the hydraulic rules are the YHFD rules.
The problem: long driveways that climb hills. Hose length and elevation loss make relay pumping hard to plan.

You trace a hose route on a map. The page reads the ground height along the route. It then shows these items:

- the hose to lay
- the climb
- the relay engines
- each engine position
- each pump discharge pressure (PDP)

The page shows 500, 750, and 1,000 GPM side by side. It also makes a one-page pre-plan card to print.

The tool has a three-part plan:

1. **Find.** Screen the full district for long, steep driveways. Not started.
2. **Calculate.** This page. Built.
3. **Carry.** Printed pre-plan cards for problem addresses. The page makes one card at a time.

## How to build it

Run each step in the repo folder. The repo is the project folder that Git tracks.

One-time setup:

1. Run `npm install`. This gets Leaflet 1.9.4, the map library. npm is the package tool for Node, a program that runs JavaScript.
2. Run `python3 -m venv .venv`. This makes a virtual environment, a private folder for Python packages.
3. Run `.venv/bin/pip install playwright`. Playwright is a tool that drives a browser for a test.

Homebrew Python blocks a global pip install. For this reason Playwright lives in `.venv/`.
No Playwright browser download is necessary. The page test uses the installed Google Chrome.

Build:

1. Run `python3 build.py`.

The build puts Leaflet, the district boundary, and the hydrant list into the page source `src/calculator.html`. It writes one file:
`dist/YHFD Relay Pumping Calculator.html`

## How to test it

The repo has two test sets. Each command builds the page first.

| Command | Checks | Result |
|---|---|---|
| `npm test` | 49 math checks. 36 are against the chauffeur chart, with the chart Max Relay Distance values at 150 and 200 PSI. 13 are for the road draft. | 49 of 49 pass. |
| `npm run test:ui` | 60 page checks in Chrome through Playwright. | 60 of 60 pass. |

The page test needs no internet. It answers map, address, and ground height requests with stand-in data. The stand-in ground is a smooth slope.
The page test needs Google Chrome. Set `CHROME_PATH` to the Chrome program if Playwright cannot find Chrome.
The results above are from 2026-11-26 on macOS with Google Chrome 158.

## How to use the built page

1. Open `dist/YHFD Relay Pumping Calculator.html` in a browser.
2. Select the fire district. Yorktown Hgts FD is the default.
3. Enter the address and select **Go**.
4. Look at the draft route. It goes from the nearest hydrant by road to the address.
5. Drag a point to match the driveway. Click a middle handle or the line to add a point. Right-click a point to remove it.
6. Select reverse lay or forward lay. The page has no default.

With no road or no hydrant in 1 mile, the page makes no draft. Then trace by hand:

1. Select reverse lay or forward lay.
2. Select **Trace route**.
3. Click the route on the map. Reverse: click the attack engine first and the water source last. Forward: click in the opposite order.
4. Select **Finish**.

The page needs an internet connection.

To keep your own start values:

1. Set the fire district and the values in **Settings**.
2. Select **Save as my defaults** to keep them in this browser.
3. Select **Save a copy of this page with my defaults** to get a file that starts with them on any device.

The built-in start values are the YHFD values: 5 inch hose, 185 PSI maximum PDP, and 1,000 ft of hose on each engine.
The user can drag a relay engine. The page then shows the PDPs for that position and flags a limit that is broken.

## Limits

- The page does not know the flow a hydrant or draft site can give.
- It does not include appliance loss or attack line pressures.
- The county hydrant data is from 2015. The county dates it October 5, 2015.
- The Town of Greenburgh hydrant data is from 2026. It shows no licence text. Ask the town before you share the page outside YHFD.
- A forward lay needs one more engine at the water source. That engine lays no supply hose. The page says this in a note. It does not add it to an engine count.
- The page stores the last plan in the browser. A saved plan file (JSON) is the durable copy.
- No field check is done yet.
- The draft follows the road centerline. The last leg to the address is a straight line to the tax parcel point. Edit it to match the driveway.
- The draft uses hydrants only. It does not know draft sites.
- The county hydrant list is not complete. Some districts have few or no hydrants in it. The page shows the count and a warning.
- The supply hose on each engine is a 1,000 ft placeholder. It now sets the engine count.

## Data sources

- Ground height: USGS 3DEP, with `https://epqs.nationalmap.gov/v1/json` as the fallback.
- Hydrants: Westchester County GIS, layer 147 of the DataHub_Infrastructure service. 22,499 hydrants. No flow values.
- Hydrants in the Town of Greenburgh: the town water layer `WaterDistributionSystem_V3`, layer 32. 1,813 hydrants in service. The build adds the 1,378 that are not in the county list. No flow values.
- Fire districts and roads: Westchester County GIS.
- Street map, aerial photo 2025, 2 ft contours, driveways, buildings, and address search: Westchester County GIS.
- Topo map: USGS, `https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer`

The full list with URLs is in `CLAUDE.md`.
