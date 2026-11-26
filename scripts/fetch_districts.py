#!/usr/bin/env python3
"""Get the fire district boundaries from Westchester County GIS and write data/fire-districts.geojson.

Source: Datahub_Boundaries map service, layer 153 (Fire Districts). The layer has 64 records.
The script keeps the 60 named districts. It drops the 3 records with no name and
FIREID 200 (DES SPECIAL OPERATIONS).
Esri rule: a clockwise ring is an outer ring. A counterclockwise ring is a hole.
Each hole goes into the outer ring that contains it.
One outer ring makes a Polygon. More than one makes a MultiPolygon.
Each feature has the properties id, name (display name), and county_name (raw county name).

Option --check-export PATH: PATH is a JSON list exported from the county viewer.
The script then checks the id set, the names, and the ring point counts against the live data.
It does not compare coordinates, because the export uses a different projection.
"""
import argparse, json, os, urllib.parse, urllib.request

URL = 'https://giswww.westchestergov.com/arcgis/rest/services/Datahub_Boundaries/MapServer/153/query'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DROP_IDS = {200}
KEEP_UPPER = {'FD', 'V.A.'}
NAMES = {257: 'V.A. Hudson Valley'}  # the county name has no space after V.A.


def display_name(raw):
    """Collapse repeated spaces and title-case each word. Keep FD and V.A. in capitals."""
    return ' '.join(w if w in KEEP_UPPER else w.capitalize() for w in raw.split())


def area(ring):
    """Signed area. A negative value means a clockwise ring (the y axis points north)."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1])) / 2


def inside(pt, ring):
    """Ray casting test for a point in a ring."""
    x, y = pt
    res = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            res = not res
    return res


def split_rings(rings):
    """Return a list of polygons. Each polygon is [outer ring, hole, hole, ...]."""
    polys = []
    for r in rings:
        if area(r) < 0:
            polys.append([r])
    for r in rings:
        if area(r) >= 0:
            owners = [p for p in polys if inside(r[0], p[0])]
            assert owners, 'hole with no outer ring'
            owners[0].append(r)
    return polys


def to_geometry(rings):
    rnd = [[[round(x, 6), round(y, 6)] for x, y in r] for r in rings]
    polys = split_rings(rnd)
    if len(polys) == 1:
        return {'type': 'Polygon', 'coordinates': polys[0]}
    return {'type': 'MultiPolygon', 'coordinates': polys}


def fetch():
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            'where': '1=1', 'outFields': 'FIREID,FIRENAME', 'outSR': 4326, 'returnGeometry': 'true',
            'orderByFields': 'FIREID', 'resultOffset': offset, 'resultRecordCount': 20, 'f': 'json'})
        req = urllib.request.Request(URL + '?' + q, headers={'User-Agent': 'Mozilla/5.0'})
        feats = json.load(urllib.request.urlopen(req, timeout=120)).get('features', [])
        rows += feats
        if not feats:
            break
        offset += len(feats)
    return rows


def check_export(path, live):
    """Compare the county viewer export with the live rings by id, name, and point counts."""
    exp = {f['attributes']['FIREID']: f for f in json.load(open(path, encoding='utf-8'))
           if (f['attributes']['FIRENAME'] or '').strip() and f['attributes']['FIREID'] not in DROP_IDS}
    assert set(exp) == set(live), 'id sets differ'
    for i, f in live.items():
        assert exp[i]['attributes']['FIRENAME'] == f['attributes']['FIRENAME'], 'name differs: %s' % i
        a = [len(r) for r in exp[i]['geometry']['rings']]
        b = [len(r) for r in f['geometry']['rings']]
        assert a == b, 'ring point counts differ: %s %s %s' % (i, a, b)
    print('export check passed for %d districts' % len(live))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('out', nargs='?', default=os.path.join(ROOT, 'data', 'fire-districts.geojson'))
    ap.add_argument('--check-export', metavar='PATH')
    a = ap.parse_args()
    raw = fetch()
    assert len(raw) == 64, 'expected 64 records, got %d' % len(raw)
    live = {f['attributes']['FIREID']: f for f in raw
            if (f['attributes']['FIRENAME'] or '').strip() and f['attributes']['FIREID'] not in DROP_IDS}
    assert len(live) == 60, 'expected 60 districts, got %d' % len(live)
    if a.check_export:
        check_export(a.check_export, live)
    feats = []
    for i, f in live.items():
        name = f['attributes']['FIRENAME']
        feats.append({'type': 'Feature',
                      'properties': {'id': int(i), 'name': NAMES.get(int(i)) or display_name(name), 'county_name': name},
                      'geometry': to_geometry(f['geometry']['rings'])})
    feats.sort(key=lambda f: f['properties']['name'])
    with open(a.out, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({'type': 'FeatureCollection', 'features': feats}, separators=(',', ':')))
    kinds = {}
    for f in feats:
        kinds[f['geometry']['type']] = kinds.get(f['geometry']['type'], 0) + 1
    print('%d districts written to %s %s' % (len(feats), a.out, kinds))


if __name__ == '__main__':
    main()
