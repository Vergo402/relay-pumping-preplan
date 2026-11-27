#!/usr/bin/env python3
"""Build the relay calculator into one HTML file.

The build puts these parts into src/calculator.html:
  - the Leaflet map library (CSS, images, and script) from node_modules
  - the fire district boundaries from data/fire-districts.geojson (60 districts)
  - the hydrant list from data/hydrants.json (county, 2015)
  - the Town of Greenburgh hydrants from data/hydrants-greenburgh.json (code TOG).
    The build keeps every county row. It adds a town row only when no county
    hydrant is within 50 ft of it.

Run `npm install` one time before the first build.
"""
import argparse, base64, json, math, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
LEAFLET = os.path.join(ROOT, 'node_modules', 'leaflet', 'dist')


def merge_town(county, town, ft=50):
    """Return the county rows plus the town rows with no county hydrant within ft feet."""
    # Flat-earth feet near latitude 41. A grid cell is ft wide, so 9 cells cover the radius.
    fx, fy = 364000 * math.cos(math.radians(41.0)), 364000.0  # feet per degree

    def cell(h):
        return int(h[0] * fx // ft), int(h[1] * fy // ft)
    grid = {}
    for h in county:
        grid.setdefault(cell(h), []).append(h)
    out, added = list(county), 0
    for t in town:
        cx, cy = cell(t)
        near = any(math.hypot((c[0] - t[0]) * fx, (c[1] - t[1]) * fy) <= ft
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) for c in grid.get((cx + dx, cy + dy), ()))
        if not near:
            out.append(t); added += 1
    return out, added


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--src', default=os.path.join(ROOT, 'src', 'calculator.html'))
    ap.add_argument('--district', default=os.path.join(ROOT, 'data', 'fire-districts.geojson'))
    ap.add_argument('--hydrants', default=os.path.join(ROOT, 'data', 'hydrants.json'))
    ap.add_argument('--town-hydrants', default=os.path.join(ROOT, 'data', 'hydrants-greenburgh.json'))
    ap.add_argument('--no-hydrants', action='store_true', help='build with an empty hydrant list')
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist', 'Relay Pumping Pre-plan.html'))
    a = ap.parse_args()

    src = open(a.src, encoding='utf-8').read()

    css = open(os.path.join(LEAFLET, 'leaflet.css'), encoding='utf-8').read()

    def datauri(m):
        p = os.path.join(LEAFLET, m.group(1))
        if os.path.exists(p):
            return 'url(data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode() + ')'
        return m.group(0)

    css = re.sub(r'url\(([^)]+\.png)\)', datauri, css)
    js = open(os.path.join(LEAFLET, 'leaflet.js'), encoding='utf-8').read()
    js = re.sub(r'//# sourceMappingURL=.*', '', js)
    assert '</script' not in js.lower(), 'Leaflet script would close the script tag'

    districts = json.load(open(a.district, encoding='utf-8'))['features']
    district = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'id': f['properties']['id'], 'name': f['properties']['name']},
         'geometry': f['geometry']} for f in districts]}
    district_json = json.dumps(district, separators=(',', ':')).replace('<', '\\u003c')

    hydrants = [] if a.no_hydrants else json.load(open(a.hydrants, encoding='utf-8'))
    added = 0
    if not a.no_hydrants:
        hydrants, added = merge_town(hydrants, json.load(open(a.town_hydrants, encoding='utf-8')))
        if a.hydrants == ap.get_default('hydrants') and a.town_hydrants == ap.get_default('town_hydrants'):
            assert 1200 <= added <= 1600, 'town rows appended out of range: %d' % added
            assert len(hydrants) > 22000 and sum(1 for h in hydrants if h[3] == 'TOG') == added, 'merge self-check failed'
    hydrant_json = json.dumps(hydrants, separators=(',', ':')).replace('<', '\\u003c')

    for mark in ('/*LEAFLET_CSS*/', '/*LEAFLET_JS*/', '__DISTRICT__', 'id="hydrant-data">[]<'):
        assert src.count(mark) == 1, 'marker not found one time in the source: ' + mark
    out = (src.replace('/*LEAFLET_CSS*/', css)
              .replace('/*LEAFLET_JS*/', js)
              .replace('__DISTRICT__', district_json)
              .replace('id="hydrant-data">[]<', 'id="hydrant-data">' + hydrant_json + '<'))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'w', encoding='utf-8').write(out)
    print('built %s (%d bytes, %d districts, %d hydrants, %d town rows appended)' % (os.path.relpath(a.out, ROOT), len(out.encode('utf-8')), len(districts), len(hydrants), added))


if __name__ == '__main__':
    main()
