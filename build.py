#!/usr/bin/env python3
"""Build the relay calculator into one HTML file.

The build puts these parts into src/calculator.html:
  - the Leaflet map library (CSS, images, and script) from node_modules
  - the district boundary from data/yhfd-district.geojson
  - the hydrant list from data/hydrants.json

Run `npm install` one time before the first build.
"""
import argparse, base64, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
LEAFLET = os.path.join(ROOT, 'node_modules', 'leaflet', 'dist')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--src', default=os.path.join(ROOT, 'src', 'calculator.html'))
    ap.add_argument('--district', default=os.path.join(ROOT, 'data', 'yhfd-district.geojson'))
    ap.add_argument('--hydrants', default=os.path.join(ROOT, 'data', 'hydrants.json'))
    ap.add_argument('--no-hydrants', action='store_true', help='build with an empty hydrant list')
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist', 'YHFD Relay Pumping Calculator.html'))
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

    feature = json.load(open(a.district, encoding='utf-8'))['features'][0]
    ring = [[round(x, 6), round(y, 6)] for x, y in feature['geometry']['coordinates'][0]]
    district = {'type': 'Feature', 'properties': {'name': feature['properties']['FIRENAME']},
                'geometry': {'type': 'Polygon', 'coordinates': [ring]}}

    hydrants = [] if a.no_hydrants else json.load(open(a.hydrants, encoding='utf-8'))
    hydrant_json = json.dumps(hydrants, separators=(',', ':')).replace('<', '\\u003c')

    for mark in ('/*LEAFLET_CSS*/', '/*LEAFLET_JS*/', '__DISTRICT__', 'id="hydrant-data">[]<'):
        assert src.count(mark) == 1, 'marker not found one time in the source: ' + mark
    out = (src.replace('/*LEAFLET_CSS*/', css)
              .replace('/*LEAFLET_JS*/', js)
              .replace('__DISTRICT__', json.dumps(district, separators=(',', ':')))
              .replace('id="hydrant-data">[]<', 'id="hydrant-data">' + hydrant_json + '<'))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'w', encoding='utf-8').write(out)
    print('built %s (%d bytes, %d hydrants)' % (os.path.relpath(a.out, ROOT), len(out.encode('utf-8')), len(hydrants)))


if __name__ == '__main__':
    main()
