"""Page test for the relay calculator. It drives the built page in Chrome.

Usage: python3 tests/test_ui.py "dist/YHFD Relay Pumping Calculator.html"
Needs: pip install playwright, and Google Chrome.
Set CHROME_PATH to the Chrome program if Playwright cannot find Chrome.

The test does not use the internet. It answers map, address, and ground height
requests with stand-in data. The stand-in ground is a smooth slope.
"""
import json, os, re, sys, base64, urllib.parse, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
src = pathlib.Path(sys.argv[1]).resolve().read_text(encoding='utf-8')
os.chdir(ROOT); (ROOT / 'out').mkdir(exist_ok=True)
C = (41.2700, -73.7900)
fake = [[C[1], C[0], "T-101", "YKTWN"], [C[1]+0.002, C[0]+0.001, "T-102", "YKTWN"], [C[1]-0.003, C[0]-0.002, "X-9", "MOHGN"]]
src, n_swap = re.subn(r'(id="hydrant-data">).*?(</script>)', lambda m: m.group(1) + json.dumps(fake) + m.group(2), src, count=1, flags=re.S)
assert n_swap == 1, 'hydrant data block not found in the built page'
test_html = pathlib.Path('out/test.html'); test_html.write_text(src, encoding='utf-8')
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mO88f7jfwAJHAPb0q7eVQAAAABJRU5ErkJggg==')
# The old checks need the road query to fail, so no draft appears. The new phase turns the stand-in roads on.
GATE = {'roads': False, 'addr': C, 'road': None}  # road: a stand-in road to use in place of ROAD
# One road, TEST HILL RD: west to east past T-101, north 0.003 degrees, then east to the address. T-102 is 100 ft off the road and is the nearest by road.
ROAD = [[C[1], C[0]], [C[1]+0.00237, C[0]], [C[1]+0.00237, C[0]+0.003], [C[1]+0.0035, C[0]+0.003]]
ADDR2 = (C[0]+0.0031, C[1]+0.0035)
def handle(route):
    req = route.request; u = req.url
    if 'getSamples' in u:
        pts = json.loads(urllib.parse.parse_qs(req.post_data or '')['geometry'][0])['points']
        samples = [{'location':{'x':x,'y':y},'locationId':i,'value':str(150 + (y-41.27)*8900 + (x+73.79)*1500),'rasterId':1,'resolution':1} for i,(x,y) in enumerate(pts)]
        route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=json.dumps({'samples':samples}))
    elif 'findAddressCandidates' in u:
        route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=json.dumps({'candidates':[{'address':'100 TEST HILL RD, YORKTOWN HEIGHTS, NY, 10598','location':{'x':GATE['addr'][1],'y':GATE['addr'][0]},'score':100}]}))
    elif 'MappingWestchesterCounty_Roads/MapServer/11/query' in u and GATE['roads']:
        route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=json.dumps({'features':[{'attributes':{'ST_NM_PREF':' ','ST_NM_BASE':'TEST HILL','ST_NM_SUFF':' ','ST_TYP_AFT':'RD'},'geometry':{'paths':[GATE['road'] or ROAD]}}]}))
    elif '/tile/' in u or '/export' in u: route.fulfill(status=200, content_type='image/png', body=PNG)
    elif u.startswith('file:'): route.continue_()
    else: route.abort()
errors = []; fails = []
def ok(name, cond, info=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('  -> ' + str(info) if info != '' else ''))
    if not cond: fails.append(name)
SNAP = '''() => { const s=window.__relay.state; return {lay:s.settings.lay, pts:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, hose:s.profile?s.profile.h[s.profile.n-1]:null,
  net:s.profile?s.profile.z[s.profile.n-1]-s.profile.z[0]:null, res:s.profile?[500,750,1000].map(q=>({q, relays:s.results[q].relays.length, pdps:s.results[q].segs.map(x=>x.pdp), secs:s.results[q].segs.map(x=>Math.round(x.hose)), over:s.results[q].over, overHose:s.results[q].overHose})):null}; }'''
UP = [(4,3),(120,-90),(160,-220),(60,-300)]   # source (hydrant at the centre) first, then uphill
with sync_playwright() as p:
    chrome = os.environ.get('CHROME_PATH')
    b = p.chromium.launch(executable_path=chrome, args=['--no-sandbox']) if chrome else p.chromium.launch(channel='chrome')
    pg = b.new_page(viewport={'width':1440,'height':900})
    pg.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR '+str(e)))
    pg.route('**/*', handle)
    pg.goto(test_html.resolve().as_uri()); pg.wait_for_timeout(700)
    ok('no default lay: Trace route is disabled at the start', pg.is_disabled('#btnDraw') and pg.evaluate('window.__relay.state.settings.lay')==None, pg.inner_text('#layHint'))
    pg.screenshot(path='out/v2_start.png')
    opts = pg.evaluate("[...document.querySelectorAll('#setDistrict option')].map(o => o.textContent)")
    ok('district picker: 60 options, default Yorktown Hgts FD (253), hint right', len(opts)==60 and pg.input_value('#setDistrict')=='253' and 'Yorktown Hgts FD' in pg.evaluate("document.querySelector('#setDistrict').selectedOptions[0].textContent") and pg.evaluate('window.__relay.state.settings.district')==253 and pg.inner_text('#distHint')=='60 county districts. Hydraulic rules: YHFD chauffeur chart.', pg.inner_text('#distHint'))
    pg.fill('#geoText', '100 Test Hill Rd'); pg.click('#geoForm button'); pg.wait_for_timeout(600)
    try: pg.wait_for_function("document.getElementById('status').textContent.includes('No road draft')", timeout=5000)
    except Exception: pass
    ok('road query fails: no draft, the route stays empty and the status says so', pg.evaluate('window.__relay.state.points.length')==0 and not pg.evaluate('window.__relay.state.draft') and pg.inner_text('#status').startswith('Found: ') and 'No road draft: the road data did not answer. Trace the route by hand.' in pg.inner_text('#status'), pg.inner_text('#status'))
    pg.evaluate('window.__relay.map.setZoom(16,{animate:false})'); pg.wait_for_timeout(400)
    box = pg.locator('#map').bounding_box(); cx, cy = box['x']+box['width']/2, box['y']+box['height']/2
    # ---- reverse lay: attack engine first ----
    pg.click('#layRev'); ok('reverse selected: steps start at the attack engine', 'attack engine position first' in pg.inner_text('#steps') and pg.is_enabled('#btnDraw'), pg.inner_text('#status'))
    pg.click('#btnDraw'); ok('lay buttons lock during the trace', pg.is_disabled('#layFwd'))
    for dx,dy in reversed(UP): pg.mouse.click(cx+dx, cy+dy); pg.wait_for_timeout(100)
    ok('reverse status asks for the water source last', 'water source last' in pg.inner_text('#status'), pg.inner_text('#status'))
    pg.mouse.click(cx-200, cy+200); pg.wait_for_timeout(100); n5 = pg.evaluate('window.__relay.state.points.length')
    pg.click('#btnUndo'); pg.wait_for_timeout(100); st = pg.evaluate('window.__relay.state.points.map(p=>[p.lat,p.lng])')
    ok('reverse undo removes the newest click (the source end)', n5==5 and len(st)==4 and abs(st[0][0]-C[0])<0.0002)
    pg.click('#btnFinish'); pg.wait_for_selector('#flowTable', timeout=8000); pg.wait_for_timeout(300)
    rev = pg.evaluate(SNAP); print(json.dumps(rev))
    ok('reverse: water source ends as point 1 and snaps to hydrant T-101', rev['hyd'] and rev['hyd']['num']=='T-101' and abs(rev['first']['lat']-C[0])<1e-9 and abs(rev['first']['lng']-C[1])<1e-9)
    ok('reverse: route runs uphill in water order', rev['net']>100, round(rev['net']))
    ok('every section within 1,000 ft, no flags', all(max(r['secs'])<=1000 and not r['over'] and not r['overHose'] for r in rev['res']))
    txt = pg.inner_text('#results'); i = txt.find('Hose lay order'); print('LAY BLOCK (reverse):', txt[i:i+420].replace('\n',' | '))
    ok('reverse lay order: first lay starts at the attack engine, last pumps as Source', 'reverse lay' in txt and txt.find('The attack engine to')>0 and txt.find('Pumps as Source')>txt.find('The attack engine to'))
    pg.screenshot(path='out/v2_reverse.png')
    ov = pg.evaluate("(() => { const e=document.getElementById('side'); const t=[...e.querySelectorAll('table')].map(x=>x.scrollWidth); return {side:e.clientWidth, tables:t, inner:e.clientWidth-36}; })()")
    ok('sidebar tables fit the panel', all(w <= ov['inner']+1 for w in ov['tables']), ov)
    pg.locator('#side').evaluate('e => e.scrollTop = 520'); pg.wait_for_timeout(150); pg.screenshot(path='out/v2_reverse_scrolled.png')
    # ---- switch the same route to forward lay ----
    pg.click('#layFwd'); pg.wait_for_timeout(200); fw = pg.evaluate(SNAP); txt = pg.inner_text('#results'); i = txt.find('Hose lay order'); print('LAY BLOCK (forward):', txt[i:i+470].replace('\n',' | '))
    ok('switch to forward keeps the hydraulics', fw['res']==rev['res'] and fw['lay']=='forward')
    ok('forward lay order: first lay starts at the water source, last stops at the attack engine', txt.find('The water source to')>0 and 'Stops at the attack engine' in txt)
    pg.locator('#flowTable tbody tr').nth(2).click(); pg.wait_for_timeout(200)
    rel = pg.locator('.em.R').first; rb = rel.bounding_box(); pg.mouse.move(rb['x']+15, rb['y']+15); pg.mouse.down(); pg.mouse.move(rb['x']-60, rb['y']+90, steps=8); pg.mouse.up(); pg.wait_for_timeout(300)
    d = pg.evaluate(SNAP)['res'][2]; ok('hand move that makes a long section raises the hose warning', d['overHose'] and 'longer than 1,000 ft' in pg.inner_text('#results'), d)
    pg.click('#btnAuto'); pg.wait_for_timeout(200)
    pg.fill('#planNotes', 'Gate at the road. Turnaround at 900 ft.')
    pg.click('#btnCard'); pg.wait_for_timeout(700); pg.screenshot(path='out/v2_card_forward.png', full_page=True)
    pg.pdf(path='out/card_forward.pdf', format='Letter', print_background=True, prefer_css_page_size=True)
    ok('card shows the lay', 'Forward lay' in pg.inner_text('#cardHead') and 'Last lay' in pg.inner_text('#cardBody'))
    pg.click('#btnBack'); pg.click('#layRev'); pg.click('#btnCard'); pg.wait_for_timeout(600)
    pg.pdf(path='out/card_reverse.pdf', format='Letter', print_background=True, prefer_css_page_size=True)
    ok('reverse card: engines lay back to their positions', 'Reverse lay' in pg.inner_text('#cardHead') and 'back to here' in pg.inner_text('#cardBody'))
    pg.click('#btnBack'); pg.wait_for_timeout(200)
    pg.reload(); pg.wait_for_selector('#flowTable', timeout=8000); ok('reload keeps the route and its lay', pg.evaluate('window.__relay.state.settings.lay')=='reverse')
    # ---- clear: lay must be picked again ----
    pg.click('#btnClear'); pg.wait_for_timeout(150)
    ok('clear resets the lay and locks Trace route', pg.evaluate('window.__relay.state.settings.lay')==None and pg.is_disabled('#btnDraw'), pg.inner_text('#status'))
    # ---- forward lay: source first ----
    pg.evaluate('window.__relay.map.setView([%f,%f],16,{animate:false})' % C); pg.wait_for_timeout(400)
    pg.click('#layFwd'); pg.click('#btnDraw')
    for dx,dy in UP: pg.mouse.click(cx+dx, cy+dy); pg.wait_for_timeout(100)
    pg.click('#btnFinish'); pg.wait_for_selector('#flowTable', timeout=8000); pg.wait_for_timeout(300)
    f2 = pg.evaluate(SNAP)
    ok('forward trace gives the same route as the reverse trace', abs(f2['hose']-rev['hose'])<1 and f2['hyd']['num']=='T-101' and f2['res']==rev['res'], (round(f2['hose']), round(rev['hose'])))
    pg.select_option('#setCap', '200'); pg.fill('#setHosePer', '1500'); pg.dispatch_event('#setHosePer', 'change'); pg.wait_for_timeout(200)
    r3 = pg.evaluate(SNAP)['res']; ok('1,500 ft per engine and 200 PSI lowers the engine count', sum(len(x['secs']) for x in r3) < sum(len(x['secs']) for x in rev['res']), [x['secs'] for x in r3])
    # ---- v0.3 phase: district picker, road draft, handles. It runs last so the old checks keep their state. ----
    pg.click('#btnClear'); pg.wait_for_timeout(150)
    CEN = 'JSON.stringify(window.__relay.map.getCenter())'
    c0 = json.loads(pg.evaluate(CEN)); pg.select_option('#setDistrict', '226'); pg.wait_for_timeout(500); c1 = json.loads(pg.evaluate(CEN))
    nm = pg.evaluate("document.querySelector('#setDistrict').selectedOptions[0].textContent")
    ok('district change to ' + nm + ': map moves, placeholder, status, and layer label follow', abs(c1['lat']-c0['lat'])+abs(c1['lng']-c0['lng'])>0.01 and pg.get_attribute('#geoText','placeholder')=='Street address in '+nm and pg.inner_text('#status')=='District set to '+nm+'. Enter an address.' and (nm+' line') in pg.inner_text('.leaflet-control-layers-overlays'), (nm, c0, c1, pg.inner_text('#status')))
    pg.select_option('#setDistrict', '253'); pg.wait_for_timeout(500)
    ok('district set back to Yorktown Hgts FD (253)', pg.evaluate('window.__relay.state.settings.district')==253 and 'Yorktown Hgts FD' in pg.get_attribute('#geoText','placeholder'), pg.get_attribute('#geoText','placeholder'))
    # road draft: T-102 is the expected hydrant (T-101 is 2,050 ft by road, T-102 is 1,130 ft; X-9 is far from any road)
    GATE['roads'] = True; GATE['addr'] = ADDR2
    pg.fill('#geoText', '100 Test Hill Rd'); pg.click('#geoForm button')
    try: pg.wait_for_function('window.__relay.state.draft === true', timeout=8000); pg.wait_for_selector('#flowTable', timeout=8000); pg.wait_for_timeout(300)
    except Exception: pass
    dr = pg.evaluate("(() => { const s=window.__relay.state, st=document.getElementById('status'); return {draft:s.draft, n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, cls:st.className, text:st.textContent}; })()")
    print('DRAFT:', json.dumps(dr))
    ok('road draft with an empty route (hydrant T-102 by road): draft set, source hydrant, status ok', dr['draft'] is True and dr['n']>=3 and dr['hyd'] and dr['hyd']['num']=='T-102' and dr['cls']=='ok' and dr['text'].startswith('Draft route: hydrant'), dr['text'])
    ok('  first point is hydrant T-102 and last point is the address', dr['first'] and abs(dr['first']['lat']-(C[0]+0.001))<1e-9 and abs(dr['first']['lng']-(C[1]+0.002))<1e-9 and abs(dr['last']['lat']-ADDR2[0])<1e-9 and abs(dr['last']['lng']-ADDR2[1])<1e-9, (dr['first'], dr['last']))
    ok('  the results table appears for the draft', pg.locator('#flowTable').count()==1 and pg.is_visible('#flowTable'))
    pg.screenshot(path='out/v3_draft.png')
    n0 = dr['n']; pg.locator('.mid').nth(2).click(); pg.wait_for_timeout(500)
    a = pg.evaluate('({n:window.__relay.state.points.length, draft:window.__relay.state.draft})')
    ok('click on a middle handle adds one point and clears the draft flag', a['n']==n0+1 and a['draft'] is False, a)
    pg.locator('.vx').nth(2).click(button='right'); pg.wait_for_timeout(500)
    ok('right-click on a middle point handle removes one point', pg.evaluate('window.__relay.state.points.length')==n0, pg.evaluate('window.__relay.state.points.length'))
    # a click on the route line, one quarter along the longest section, adds a point (a middle handle sits at one half)
    sg = pg.evaluate("(() => { const s=window.__relay.state.points, m=window.__relay.map; return s.slice(1).map((q,i) => { const a=m.latLngToContainerPoint(s[i]), b=m.latLngToContainerPoint(q); return {x:a.x+(b.x-a.x)*0.25, y:a.y+(b.y-a.y)*0.25, len:Math.hypot(b.x-a.x,b.y-a.y)}; }); })()")
    lg = max(sg, key=lambda g: g['len']); mb = pg.locator('#map').bounding_box(); pg.mouse.click(mb['x']+lg['x'], mb['y']+lg['y']); pg.wait_for_timeout(500)
    ok('click on the route line adds one point', pg.evaluate('window.__relay.state.points.length')==n0+1, (pg.evaluate('window.__relay.state.points.length'), round(lg['len'])))
    n0 = pg.evaluate('window.__relay.state.points.length')
    pg.uncheck('#showHandles'); pg.wait_for_timeout(200); hid = (pg.locator('.vx').count(), pg.locator('.mid').count())
    pg.check('#showHandles'); pg.wait_for_timeout(200); shw = (pg.locator('.vx').count(), pg.locator('.mid').count())
    ok('Show handles off hides .vx and .mid, on shows them again', hid==(0,0) and shw==(n0, n0-1), (hid, shw))
    while pg.evaluate('window.__relay.state.points.length')>2: pg.locator('.vx').nth(1).click(button='right'); pg.wait_for_timeout(400)
    pg.locator('.vx').nth(0).dispatch_event('contextmenu'); pg.wait_for_timeout(400)  # the source engine icon covers this handle
    ok('with 2 points left, right-click removes nothing', pg.evaluate('window.__relay.state.points.length')==2)
    pg.select_option('#setDistrict', '226'); pg.wait_for_timeout(300); pg.reload(); pg.wait_for_timeout(1000)
    ok('reload keeps the fire district in the saved plan', pg.evaluate('window.__relay.state.settings.district')==226 and pg.input_value('#setDistrict')=='226', (pg.evaluate('window.__relay.state.settings.district'), pg.input_value('#setDistrict')))
    pg.select_option('#setDistrict', '253'); pg.wait_for_timeout(300)
    # ---- v0.4 phase: Maximum PDP 185, and "My defaults". Each part uses a new browser context, so storage starts empty. ----
    e0 = len(errors)
    def fresh():
        q = b.new_context(viewport={'width':1440,'height':900}).new_page()
        q.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
        q.on('pageerror', lambda e: errors.append('PAGEERROR '+str(e)))
        q.route('**/*', handle); return q
    LS = "k => localStorage.getItem(k)"
    VALS = {'district':226, 'hose':4, 'basis':'formula', 'cap':200, 'residual':50, 'slack':5, 'hosePerEngine':1500}
    VSUM = 'Mohegan FD, 4 inch, formula, 200 PSI, 50 PSI, 5%, 1,500 ft'
    def setall(q):
        for sel, v in (('#setDistrict','226'),('#setHose','4'),('#setBasis','formula'),('#setCap','200'),('#setRes','50'),('#setSlack','5')): q.select_option(sel, v)
        q.fill('#setHosePer', '1500'); q.dispatch_event('#setHosePer', 'change'); q.wait_for_timeout(300)
    def inputs(q): return q.evaluate("['#setDistrict','#setHose','#setBasis','#setCap','#setRes','#setSlack','#setHosePer'].map(s => document.querySelector(s).value)")
    q = fresh(); q.goto(test_html.resolve().as_uri()); q.wait_for_timeout(700)
    caps = q.evaluate("[...document.querySelectorAll('#setCap option')].map(o => o.value)")
    ok('Maximum PDP list is 150, 175, 185, 200', caps==['150','175','185','200'], caps)
    st = q.evaluate('window.__relay.state.settings')
    ok('a fresh page starts at 185 PSI and 1,000 ft', st['cap']==185 and st['hosePerEngine']==1000 and q.input_value('#setCap')=='185' and q.input_value('#setHosePer')=='1000', (st['cap'], st['hosePerEngine']))
    ok('status reads Defaults in use: YHFD, with the summary', q.inner_text('#defaultsStatus')=='Defaults in use: YHFD (Yorktown Hgts FD, 5 inch, chart, 185 PSI, 20 PSI, 10%, 1,000 ft).', q.inner_text('#defaultsStatus'))
    ok('the hose hint has no placeholder wording', 'placeholder' not in q.inner_text('#side').lower() and 'Set the supply hose load of your engines.' in q.inner_text('#side'))
    setall(q); q.click('#btnSaveDefaults')
    ok('Save as my defaults: status says yours with the new summary', q.inner_text('#defaultsStatus')=='Saved in this browser. Defaults in use: yours ('+VSUM+').', q.inner_text('#defaultsStatus'))
    q.evaluate("localStorage.removeItem('yhfd-relay-pilot-v1')"); q.reload(); q.wait_for_timeout(900)  # no autosave: only the saved defaults can give these values
    ok('reload: the saved defaults give 200 PSI and 1,500 ft, and the status says yours', inputs(q)==['226','4','formula','200','50','5','1500'] and q.inner_text('#defaultsStatus')=='Defaults in use: yours ('+VSUM+').', (inputs(q), q.inner_text('#defaultsStatus')))
    GATE['roads'] = True; GATE['addr'] = ADDR2
    q.fill('#geoText', '100 Test Hill Rd'); q.click('#geoForm button')
    try: q.wait_for_function('window.__relay.state.draft === true', timeout=8000); q.wait_for_selector('#flowTable', timeout=8000)
    except Exception: pass
    q.select_option('#setCap', '150'); q.wait_for_timeout(200); q.click('#btnClear'); q.wait_for_timeout(300)
    ok('Clear after a changed setting returns the settings to the saved defaults', inputs(q)==['226','4','formula','200','50','5','1500'] and q.evaluate('window.__relay.state.settings.cap')==200 and q.evaluate('window.__relay.state.settings.lay')==None, inputs(q))
    q.fill('#geoText', '100 Test Hill Rd'); q.click('#geoForm button')  # a live route, so the copy check proves the route is left out
    try: q.wait_for_function('window.__relay.state.draft === true', timeout=8000)
    except Exception: pass
    with q.expect_download() as dl: q.click('#btnCopyDefaults')
    dl.value.save_as('out/copy.html'); cp = pathlib.Path('out/copy.html').read_text(encoding='utf-8')
    ok('Save a copy: file name and status', dl.value.suggested_filename=='Relay Pumping Calculator (my defaults).html' and q.inner_text('#defaultsStatus')=='Saved "Relay Pumping Calculator (my defaults).html". Look in your Downloads folder. That copy starts with: '+VSUM+'.', q.inner_text('#defaultsStatus'))
    blk = lambda t, i: re.search(r'id="' + i + r'">(.*?)</script>', t, re.S).group(1)
    ok('the copy holds the 7 chosen values in the user-defaults block', json.loads(blk(cp, 'user-defaults'))==VALS, blk(cp, 'user-defaults')[:120])
    ok('the copy keeps the hydrant-data and district-data blocks byte for byte', blk(cp, 'hydrant-data')==blk(src, 'hydrant-data') and blk(cp, 'district-data')==blk(src, 'district-data') and len(blk(cp, 'district-data'))>1000)
    ok('the copy has no map, route, or result markup', not re.search(r'class="[^"]*leaflet-container', cp) and '<div id="map"></div>' in cp and '<div id="results"><div class="empty">No route yet.</div></div>' in cp and q.evaluate('window.__relay.state.points.length')>1)
    q2 = fresh(); q2.goto(pathlib.Path('out/copy.html').resolve().as_uri()); q2.wait_for_timeout(900)
    ok('the copy opens in a new browser with the copied values and says this file', inputs(q2)==['226','4','formula','200','50','5','1500'] and q2.inner_text('#defaultsStatus')=='Defaults in use: this file ('+VSUM+').', (inputs(q2), q2.inner_text('#defaultsStatus')))
    ok('in the copy, the Reset button reads Reset to the file defaults', q2.inner_text('#btnResetDefaults')=='Reset to the file defaults', q2.inner_text('#btnResetDefaults'))
    with q2.expect_download() as dl2: q2.click('#btnCopyDefaults')
    dl2.value.save_as('out/copy2.html')
    ok('the copy can make a further copy with the same values', json.loads(blk(pathlib.Path('out/copy2.html').read_text(encoding='utf-8'), 'user-defaults'))==VALS)
    q.click('#btnResetDefaults'); q.wait_for_timeout(400)
    ok('Reset removes the browser key, returns 185 PSI and 1,000 ft, and the status says YHFD', q.evaluate(LS, 'yhfd-relay-defaults-v1') is None and inputs(q)==['253','5','chart','185','20','10','1000'] and q.inner_text('#defaultsStatus')=='Defaults in use: YHFD (Yorktown Hgts FD, 5 inch, chart, 185 PSI, 20 PSI, 10%, 1,000 ft).', (inputs(q), q.inner_text('#defaultsStatus')))
    # ---- v0.5 phase: hydrant count line and the reason for no draft ----
    v = fresh(); v.goto(test_html.resolve().as_uri()); v.wait_for_timeout(700)
    cnt = lambda: (v.inner_text('#distCount'), v.get_attribute('#distCount', 'class'))
    NOTE = 'The county list is from 2015 and can be incomplete. Set the water source from a hydrant or a draft site that you know.'
    ok('count line, Yorktown Hgts FD with 3 stand-in hydrants: plural, warning form', cnt()==('County data: 3 hydrants in this district. ' + NOTE, 'note-box warn'), cnt())
    v.select_option('#setDistrict', '226'); v.wait_for_timeout(500)
    ok('count line, a district with none of the stand-in hydrants: "no hydrants", warning form', cnt()==('County data: no hydrants in this district. ' + NOTE, 'note-box warn'), cnt())
    v.select_option('#setDistrict', '253'); v.wait_for_timeout(500); GATE['roads'] = True
    def why(addr, road):
        GATE['addr'] = addr; GATE['road'] = road
        v.fill('#geoText', '100 Test Hill Rd'); v.click('#geoForm button')
        try: v.wait_for_function("document.getElementById('status').textContent.includes('No road draft')", timeout=8000)
        except Exception: pass
        GATE['road'] = None; return v.inner_text('#status')
    FAR = [[C[1], C[0]+0.05], [C[1]+0.002, C[0]+0.05]]   # a road about 3.4 miles from every stand-in hydrant
    t = why((C[0]+0.05, C[1]+0.001), FAR)
    ok('no hydrant in 1 mile by road: the status gives that reason', t=='Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. No road draft: the county data has no hydrant in 1 mile by road. Trace the route by hand.', t)
    t = why((C[0]+0.01, C[1]), None)   # about 3,600 ft north of the stand-in road
    ok('no road within 500 ft: the status gives that reason', t=='Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. No road draft: no road is near this address. Trace the route by hand.', t)
    ok('no page errors in the v0.4 phase', not [e for e in errors[e0:] if 'Failed to load resource' not in e], errors[e0:][:3])
    bad = [e for e in errors if 'Failed to load resource' not in e]
    ok('no console errors except the aborted requests', not bad, bad[:3])
    b.close()
for f in ('out/card_forward.pdf','out/card_reverse.pdf'):
    n = len(re.findall(rb'/Type\s*/Page(?![a-zA-Z])', pathlib.Path(f).read_bytes()))
    ok(f+' prints on one page', n==1, n)
print('console errors:', errors[:6]); print('\nFAILED: '+str(fails) if fails else '\nALL UI CHECKS PASS')
sys.exit(1 if fails else 0)
