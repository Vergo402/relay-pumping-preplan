#!/usr/bin/env python3
"""Get the Town of Greenburgh hydrants and write data/hydrants-greenburgh.json.

Source: the town water layer WaterDistributionSystem_V3, FeatureServer layer 32 (hydrants).
The script keeps only the rows with the lifecycle status In Service.
Each record in the output is [longitude, latitude, hydrant number, "TOG"].
The build merges these rows with the county list. See build.py.
"""
import json, os, sys, urllib.parse, urllib.request

LAYER = 'https://services5.arcgis.com/7CI4QzLwCwxDf9WB/arcgis/rest/services/WaterDistributionSystem_V3/FeatureServer/32'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(url, params):
    req = urllib.request.Request(url + '?' + urllib.parse.urlencode(params), headers={'User-Agent': 'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(req, timeout=60))


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'hydrants-greenburgh.json')
    meta = get(LAYER, {'f': 'json'})
    domain = [f for f in meta['fields'] if f['name'] == 'lifecyclestatus'][0]['domain']['codedValues']
    print('lifecyclestatus domain:', ', '.join('%s=%s' % (d['code'], d['name']) for d in domain))
    active = [d['code'] for d in domain if d['name'].strip().lower() == 'in service']
    assert active == [8], 'In Service is not code 8 in the layer domain: %s' % active
    rows, offset, total = [], 0, 0
    while True:
        feats = get(LAYER + '/query', {
            'where': 'lifecyclestatus=8', 'outSR': 4326, 'outFields': 'OBJECTID,Name,lifecyclestatus',
            'orderByFields': 'OBJECTID', 'resultOffset': offset, 'resultRecordCount': 1000, 'f': 'json'}).get('features', [])
        for f in feats:
            g = f.get('geometry')
            if not g or 'x' not in g or 'y' not in g:
                continue
            rows.append([round(g['x'], 6), round(g['y'], 6), (f['attributes'].get('Name') or '').strip(), 'TOG'])
        total += len(feats)
        if len(feats) < 1000:
            break
        offset += len(feats)
    assert len(rows) > 1500, 'too few hydrants: %d' % len(rows)
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(rows, separators=(',', ':')))
    print('%d hydrants written to %s (%d In Service rows read)' % (len(rows), out_path, total))


if __name__ == '__main__':
    main()
