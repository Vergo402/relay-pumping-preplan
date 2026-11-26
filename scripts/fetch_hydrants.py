#!/usr/bin/env python3
"""Get the hydrant list from Westchester County GIS and write data/hydrants.json.

Source: DataHub_Infrastructure map service, layer 147 (Fire Hydrants).
The county dates this data October 5, 2015. It has no flow values.
Each record in the output is [longitude, latitude, hydrant number, district code].
The district code for Yorktown Heights FD is YKTWN.
"""
import json, os, sys, urllib.parse, urllib.request

URL = 'https://giswww.westchestergov.com/arcgis/rest/services/DataHub_Infrastructure/MapServer/147/query'
# The YHFD district box plus a margin, so hydrants in the next districts show near the district line.
WEST, SOUTH, EAST, NORTH = -73.8650, 41.1930, -73.7400, 41.3340
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'hydrants.json')
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            'where': '1=1', 'geometry': '%s,%s,%s,%s' % (WEST, SOUTH, EAST, NORTH),
            'geometryType': 'esriGeometryEnvelope', 'inSR': 4326, 'outSR': 4326,
            'outFields': 'OBJECTID,DISTRICT,HYD_NUMBER,FIRENAME', 'orderByFields': 'OBJECTID',
            'resultOffset': offset, 'resultRecordCount': 1000, 'f': 'json'})
        req = urllib.request.Request(URL + '?' + q, headers={'User-Agent': 'Mozilla/5.0'})
        feats = json.load(urllib.request.urlopen(req, timeout=60)).get('features', [])
        for f in feats:
            a, g = f['attributes'], f['geometry']
            rows.append([round(g['x'], 6), round(g['y'], 6), (a.get('HYD_NUMBER') or '').strip(), (a.get('DISTRICT') or '').strip()])
        if len(feats) < 1000:
            break
        offset += len(feats)
    rows = [r for r in rows if WEST <= r[0] <= EAST and SOUTH <= r[1] <= NORTH]
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(rows, separators=(',', ':')))
    print('%d hydrants written to %s (%d with code YKTWN)' % (len(rows), out_path, sum(1 for r in rows if r[3] == 'YKTWN')))


if __name__ == '__main__':
    main()
