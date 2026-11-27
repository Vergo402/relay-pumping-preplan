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
# ADDR2 is about 110 ft from the road end, so the draft keeps the address point. ADDR_SHORT is about 36 ft from the road end.
ADDR2 = (C[0]+0.0033, C[1]+0.0035)
ADDR_SHORT = (C[0]+0.0031, C[1]+0.0035)
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
def draft(q, kind='Hydrant', lay='#layRev'):  # v0.9: the draft needs the type and the lay, then the button
    q.select_option('#sourceType', kind); q.click(lay); q.click('#btnDraft')
SNAP = '''() => { const s=window.__relay.state; return {lay:s.settings.lay, pts:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, hose:s.profile?s.profile.h[s.profile.n-1]:null,
  net:s.profile?s.profile.z[s.profile.n-1]-s.profile.z[0]:null, res:s.profile?[500,750,1000,1250,1500,2000].map(q=>({q, relays:s.results[q].relays.length, pdps:s.results[q].segs.map(x=>x.pdp), secs:s.results[q].segs.map(x=>Math.round(x.hose)), over:s.results[q].over, overHose:s.results[q].overHose})):null}; }'''
# The card blocks. Each block gives its label, mark, engine texts, arrowhead counts, "Lays" values, and the planner lay values for the same flow.
CARD = """() => { const up=n=>Math.ceil((n-0.5)/100)*100, st=window.__relay.state;
  return [...document.querySelectorAll('#cardBody .blk')].map(b => { const q=+b.querySelector('.fl b').textContent.replace(',',''), segs=st.results[q].segs;
    return { label:b.querySelector('.fl b').textContent, mark:b.querySelector('.fl').innerText.includes('On the map'), layout:b.querySelector('.fl small').textContent,
      engines:[...b.querySelectorAll('.e')].map(e=>e.innerText.replace(/\\n/g,' | ')), pumps:segs.length, hl:b.querySelectorAll('.hl').length, hr:b.querySelectorAll('.hr').length, sections:b.querySelectorAll('.s').length,
      lays:[...b.querySelectorAll('.s b')].map(e=>e.textContent), plan:segs.map(g=>up(g.hose).toLocaleString('en-US')+' ft'), text:b.innerText }; }); }"""
CARDMAP = "[...document.querySelectorAll('#cardBody .blk')].map(b => b.querySelector('.fl').innerText.includes('On the map') ? b.querySelector('.fl b').textContent : '').filter(Boolean)"
UP = [(4,3),(120,-90),(160,-220),(60,-300)]   # source (hydrant at the centre) first, then uphill
with sync_playwright() as p:
    chrome = os.environ.get('CHROME_PATH')
    b = p.chromium.launch(executable_path=chrome, args=['--no-sandbox']) if chrome else p.chromium.launch(channel='chrome')
    pg = b.new_page(viewport={'width':1440,'height':900})
    pg.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR '+str(e)))
    pg.route('**/*', handle)
    pg.goto(test_html.resolve().as_uri()); pg.wait_for_timeout(700)
    ok('no default lay: Trace by hand is disabled at the start', pg.is_disabled('#btnDraw') and pg.evaluate('window.__relay.state.settings.lay')==None, pg.inner_text('#layHint'))
    pg.screenshot(path='out/v2_start.png')
    opts = pg.evaluate("[...document.querySelectorAll('#setDistrict option')].map(o => o.textContent)")
    ok('district picker: 60 options, default Yorktown Hgts FD (253), hint right', len(opts)==60 and pg.input_value('#setDistrict')=='253' and 'Yorktown Hgts FD' in pg.evaluate("document.querySelector('#setDistrict').selectedOptions[0].textContent") and pg.evaluate('window.__relay.state.settings.district')==253 and pg.inner_text('#distHint')=='60 county districts. Hydraulic rules: YHFD chauffeur chart.', pg.inner_text('#distHint'))
    pg.fill('#geoText', '100 Test Hill Rd'); pg.click('#geoForm button'); pg.wait_for_timeout(600); draft(pg)
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
    fc = pg.evaluate(CARD)
    ok('forward card: right arrowheads, no left ones, Lays values equal the planner values, the key line says that the source engine lays no hose', 'Forward lay' in pg.inner_text('#cardHead') and all(b['hr']==b['sections']==b['pumps'] and b['hl']==0 and b['lays']==b['plan'] and 'Lays no hose' not in b['text'] for b in fc) and pg.inner_text('#cardBody .key').endswith('The source engine lays no hose.'), fc[0])
    ok('forward card: the key line shows', pg.inner_text('#cardBody .key').startswith('The arrow shows the way each engine drives as it lays hose.'))
    pg.locator('#right').screenshot(path='out/v08-card-forward-preview.png')
    pg.click('#btnBack'); pg.click('#layRev'); pg.click('#btnCard'); pg.wait_for_timeout(600)
    pg.pdf(path='out/card_reverse.pdf', format='Letter', print_background=True, prefer_css_page_size=True)
    rc = pg.evaluate(CARD)
    ok('reverse card: left arrowheads, no right ones, Lays values equal the planner values, no "Lays no hose"', 'Reverse lay' in pg.inner_text('#cardHead') and all(b['hl']==b['sections']==b['pumps'] and b['hr']==0 and b['lays']==b['plan'] and 'Lays no hose' not in b['text'] for b in rc), rc[0])
    ok('reverse card: the key line shows', pg.locator('#cardBody .key').count()==1)
    # ---- v0.8: six flows in the planner, three on the card ----
    cb = pg.evaluate(CARD)
    ok('card has exactly three blocks: 500, 1,250, 2,000 (1,000 was selected, so 1,250 is on the map)', [b['label'] for b in cb]==['500','1,250','2,000'] and pg.evaluate(CARDMAP)==['1,250'] and pg.evaluate('window.__relay.state.flow')==1250, [b['label'] for b in cb])
    ok('each block shows pumps + 1 engines, the card has no "Not needed", no "(on the map)", no "back to here"', all(len(b['engines'])==b['pumps']+1 for b in cb) and [len(b['engines']) for b in cb]==[b['pumps']+1 for b in cb] and 'Not needed' not in pg.inner_text('#cardBody') and '(on the map)' not in pg.inner_text('#cardBody') and 'to here' not in pg.inner_text('#cardBody'), [(b['label'], b['pumps']) for b in cb])
    ok('no block has "ft out" or "climb" text, and the layout line uses the planner words', all('ft out' not in b['text'] and 'climb' not in b['text'].lower() for b in cb) and all(b['layout']==('Source engine alone' if b['pumps']==1 else str(b['pumps']-1)+' relay engine'+('s' if b['pumps']>2 else '')) for b in cb), [b['layout'] for b in cb])
    cw = pg.evaluate("(() => { const e=document.getElementById('right'), c=getComputedStyle(e); return e.clientWidth - parseFloat(c.paddingLeft) - parseFloat(c.paddingRight); })()")
    ok('card preview content width is 7.6 in (729.6 CSS px), the width of the printed page', abs(cw-729.6)<=1, cw)
    mh = pg.evaluate("document.getElementById('map').getBoundingClientRect().height")
    ch = pg.evaluate("document.getElementById('right').scrollHeight - 57.6")
    print('CARD MAP HEIGHT (worst-case stand-in route, reverse lay):', mh, 'px =', round(mh/96, 2), 'in; card content', ch, 'px')
    ok('long card: the map gets shorter (measured 2.2 in; allowed 2.2 in to 2.5 in) and the card fits one page (10.1 in)', 211.2<=mh<=240 and ch<=969.6, (mh, ch))
    pg.locator('#right').screenshot(path='out/v08-card-preview.png')
    pg.pdf(path='out/v08-card.pdf', format='Letter', print_background=True, prefer_css_page_size=True)
    pg.hover('.em.A'); pg.wait_for_timeout(400)
    ok('no hover tooltip shows on the card with the mouse over A', pg.evaluate("[...document.querySelectorAll('.leaflet-tooltip')].filter(e => getComputedStyle(e).display !== 'none').length")==0)
    pg.mouse.move(5, 5)
    pg.click('#btnBack'); pg.wait_for_timeout(300)
    ok('Back to planner returns the selected flow (1,000)', pg.evaluate('window.__relay.state.flow')==1000)
    trows = pg.evaluate("[...document.querySelectorAll('#flowTable tbody tr')].map(r => [r.cells[0].innerText, r.cells[1].innerText])")
    ok('planner table has six rows with the right FL/100 values (5 inch chart, 1,250 by formula)', trows==[['500 GPM','2 PSI'],['750 GPM','5 PSI'],['1,000 GPM','10 PSI'],['1,250 GPM','12.5 PSI'],['1,500 GPM','20 PSI'],['2,000 GPM','30 PSI']], trows)
    pg.locator('#flowTable').screenshot(path='out/v08-table.png')
    pg.locator('#flowTable tbody tr').nth(4).click(); pg.wait_for_timeout(200)
    ok('a click on the 1,500 row selects it', pg.evaluate('window.__relay.state.flow')==1500 and 'sel' in (pg.locator('#flowTable tbody tr').nth(4).get_attribute('class') or ''))
    # 750 selected: drag a relay, open the card, go back. The drag must survive.
    pg.locator('#flowTable tbody tr').nth(1).click(); pg.wait_for_timeout(200)
    rel = pg.locator('.em.R').first; rb = rel.bounding_box(); pg.mouse.move(rb['x']+15, rb['y']+15); pg.mouse.down(); pg.mouse.move(rb['x']-20, rb['y']+30, steps=8); pg.mouse.up(); pg.wait_for_timeout(300)
    man = pg.evaluate('JSON.stringify(window.__relay.state.manual[750])')
    ok('a dragged relay at 750 GPM is kept as a manual position', man not in (None, 'null', 'undefined'), man)
    pg.click('#btnCard'); pg.wait_for_timeout(500)
    ok('750 selected: the card marks 1,250 as on the map', pg.evaluate(CARDMAP)==['1,250'] and pg.evaluate('window.__relay.state.flow')==1250, pg.evaluate(CARDMAP))
    pg.click('#btnBack'); pg.wait_for_timeout(300)
    ok('after Back to planner the selected flow is 750 again and the dragged relays are kept', pg.evaluate('window.__relay.state.flow')==750 and pg.evaluate('JSON.stringify(window.__relay.state.manual[750])')==man and pg.evaluate("document.querySelector('#flowTable tbody tr.sel').dataset.q")=='750', pg.evaluate('window.__relay.state.flow'))
    pg.click('#btnAuto'); pg.wait_for_timeout(200)
    pg.locator('#flowTable tbody tr').nth(5).click(); pg.wait_for_timeout(200); pg.click('#btnCard'); pg.wait_for_timeout(500)
    ok('2,000 selected: the card marks 2,000 as on the map', pg.evaluate(CARDMAP)==['2,000'] and pg.evaluate('window.__relay.state.flow')==2000, pg.evaluate(CARDMAP))
    pg.click('#btnBack'); pg.wait_for_timeout(200)
    ok('after Back to planner 2,000 is still selected', pg.evaluate('window.__relay.state.flow')==2000)
    # no lay selected: plain lines, hose length, no arrowheads, no key line
    pg.evaluate("window.__relay.state.settings.lay = null"); pg.click('#btnCard'); pg.wait_for_timeout(500); nl = pg.evaluate(CARD)
    ok('no lay selected: no arrowheads, plain hose lengths, no key line, no "Lays"', all(b['hl']==0 and b['hr']==0 and b['sections']==b['pumps'] and b['lays']==b['plan'] and 'Lays' not in b['text'] for b in nl) and pg.locator('#cardBody .key').count()==0, nl[0])
    pg.click('#btnBack'); pg.wait_for_timeout(200)
    pg.evaluate("window.__relay.state.settings.lay = 'reverse'")
    pg.locator('#flowTable tbody tr').nth(2).click(); pg.wait_for_timeout(200)
    pg.reload(); pg.wait_for_selector('#flowTable', timeout=8000); ok('reload keeps the route and its lay', pg.evaluate('window.__relay.state.settings.lay')=='reverse')
    # ---- clear: lay must be picked again ----
    pg.click('#btnClear'); pg.wait_for_timeout(150)
    ok('clear resets the lay and locks Trace by hand', pg.evaluate('window.__relay.state.settings.lay')==None and pg.is_disabled('#btnDraw'), pg.inner_text('#status'))
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
    pg.fill('#geoText', '100 Test Hill Rd'); pg.click('#geoForm button'); pg.wait_for_timeout(500); draft(pg)
    try: pg.wait_for_function('window.__relay.state.draft === true', timeout=8000); pg.wait_for_selector('#flowTable', timeout=8000); pg.wait_for_timeout(300)
    except Exception: pass
    dr = pg.evaluate("(() => { const s=window.__relay.state, st=document.getElementById('status'); return {draft:s.draft, n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, cls:st.className, text:st.textContent}; })()")
    print('DRAFT:', json.dumps(dr))
    ok('road draft with an empty route (hydrant T-102 by road): draft set, source hydrant, status ok', dr['draft'] is True and dr['n']>=3 and dr['hyd'] and dr['hyd']['num']=='T-102' and dr['cls']=='ok' and dr['text'].startswith('Draft route: hydrant'), dr['text'])
    ok('  first point is hydrant T-102 and last point is the address', dr['first'] and abs(dr['first']['lat']-(C[0]+0.001))<1e-9 and abs(dr['first']['lng']-(C[1]+0.002))<1e-9 and abs(dr['last']['lat']-ADDR2[0])<1e-9 and abs(dr['last']['lng']-ADDR2[1])<1e-9, (dr['first'], dr['last']))
    ok('  the results table appears for the draft', pg.locator('#flowTable').count()==1 and pg.is_visible('#flowTable'))
    dl = pg.evaluate("(() => { let d=0, y=0; window.__relay.map.eachLayer(l => { if (l.options && l.options.color==='#ffd21f') { y++; if (l.options.dashArray) d++; } }); return [y, d]; })()")
    ok('  a long driveway keeps the dashed last leg', dl==[2,1], dl)
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
    ok('the hose hint has no placeholder wording', 'placeholder' not in q.inner_text('#side').lower() and q.inner_text('#side').count('These are your defaults. Change them for this plan if necessary.')==1)
    setall(q); q.click('#btnSaveDefaults')
    ok('Save as my defaults: status says yours with the new summary', q.inner_text('#defaultsStatus')=='Saved in this browser. Defaults in use: yours ('+VSUM+').', q.inner_text('#defaultsStatus'))
    q.evaluate("localStorage.removeItem('yhfd-relay-pilot-v1')"); q.reload(); q.wait_for_timeout(900)  # no autosave: only the saved defaults can give these values
    ok('reload: the saved defaults give 200 PSI and 1,500 ft, and the status says yours', inputs(q)==['226','4','formula','200','50','5','1500'] and q.inner_text('#defaultsStatus')=='Defaults in use: yours ('+VSUM+').', (inputs(q), q.inner_text('#defaultsStatus')))
    GATE['roads'] = True; GATE['addr'] = ADDR2
    q.fill('#geoText', '100 Test Hill Rd'); q.click('#geoForm button'); q.wait_for_timeout(500); draft(q)
    try: q.wait_for_function('window.__relay.state.draft === true', timeout=8000); q.wait_for_selector('#flowTable', timeout=8000)
    except Exception: pass
    q.select_option('#setCap', '150'); q.wait_for_timeout(200); q.click('#btnClear'); q.wait_for_timeout(300)
    ok('Clear after a changed setting returns the settings to the saved defaults', inputs(q)==['226','4','formula','200','50','5','1500'] and q.evaluate('window.__relay.state.settings.cap')==200 and q.evaluate('window.__relay.state.settings.lay')==None, inputs(q))
    q.fill('#geoText', '100 Test Hill Rd'); q.click('#geoForm button'); q.wait_for_timeout(500); draft(q)  # a live route, so the copy check proves the route is left out
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
        v.fill('#geoText', '100 Test Hill Rd'); v.click('#geoForm button'); v.wait_for_timeout(500); draft(v)
        try: v.wait_for_function("document.getElementById('status').textContent.includes('No road draft')", timeout=8000)
        except Exception: pass
        GATE['road'] = None; return v.inner_text('#status')
    FAR = [[C[1], C[0]+0.05], [C[1]+0.002, C[0]+0.05]]   # a road about 3.4 miles from every stand-in hydrant
    t = why((C[0]+0.05, C[1]+0.001), FAR)
    ok('no hydrant in 1 mile by road: the status gives that reason', t=='Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. No road draft: the hydrant data has no hydrant in 1 mile by road. Trace the route by hand.', t)
    t = why((C[0]+0.01, C[1]), None)   # about 3,600 ft north of the stand-in road
    ok('no road within 500 ft: the status gives that reason', t=='Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. No road draft: no road is near this address. Trace the route by hand.', t)
    # ---- v0.6 phase: Town of Greenburgh hydrants (code TOG) ----
    def tog_page(rows):
        f = pathlib.Path('out/test_tog.html')
        f.write_text(re.sub(r'(id="hydrant-data">).*?(</script>)', lambda m: m.group(1) + json.dumps(fake + rows) + m.group(2), src, count=1, flags=re.S), encoding='utf-8')
        w = fresh(); w.goto(f.resolve().as_uri()); w.wait_for_timeout(700); return w
    TOG = [[C[1]+0.0005, C[0]+0.0005, '6001', 'TOG']] + [[C[1]+0.0005+i*0.0001, C[0]-0.0005, 'G-%d' % i, 'TOG'] for i in range(59)]
    w = tog_page(TOG[:1])
    ok('count line with 1 stand-in TOG row inside the district: Hydrant data prefix, warning sentence unchanged', (w.inner_text('#distCount'), w.get_attribute('#distCount', 'class'))==('Hydrant data: 4 hydrants in this district. ' + NOTE, 'note-box warn'), w.inner_text('#distCount'))
    w = tog_page(TOG)
    ok('count line with 60 stand-in TOG rows: Hydrant data prefix, county and town ending, no warning', (w.inner_text('#distCount'), w.get_attribute('#distCount', 'class'))==('Hydrant data: 63 hydrants in this district (county 2015, Town of Greenburgh 2026).', 'note-box'), (w.inner_text('#distCount'), w.get_attribute('#distCount', 'class')))
    ok('layer control names the hydrant layer "Hydrants (county and town data)"', 'Hydrants (county and town data)' in w.inner_text('.leaflet-control-layers') and 'county data, 2015' not in w.inner_text('.leaflet-control-layers'), w.inner_text('.leaflet-control-layers'))
    def pop(row):
        w.evaluate('window.__relay.map.setView([%f,%f],18,{animate:false})' % (row[1], row[0])); w.wait_for_timeout(300)
        w.evaluate('window.__relay.map.fire("click",{latlng:{lat:%f,lng:%f}})' % (row[1], row[0])); w.wait_for_timeout(300)
        return w.inner_text('.leaflet-popup-content')
    t = pop(TOG[0])
    ok('town hydrant popup gives the number, the town source, and no flow value', t=='Hydrant 6001\nTown of Greenburgh data, 2026.\nNo flow value.', t)
    t = pop(fake[0])
    ok('county hydrant popup is unchanged', t=='Hydrant T-101\nDistrict code: YKTWN\nCounty data, 2015. No flow value.', t)
    # ---- v0.7 phase: dual 3 inch lines, short driveway draft, drag S and A ----
    e7 = len(errors)
    x = fresh(); x.goto(test_html.resolve().as_uri()); x.wait_for_timeout(700)
    ok('hose list has Dual 3 inch lines after 4 inch, and the dual hint is hidden for 5 inch', x.evaluate("[...document.querySelectorAll('#setHose option')].map(o => o.value + ':' + o.textContent)")==['5:5 inch LDH','4:4 inch LDH','3:Dual 3 inch lines'] and not x.is_visible('#dualHint'))
    GATE['roads'] = True; GATE['addr'] = ADDR_SHORT; GATE['road'] = None
    x.fill('#geoText', '100 Test Hill Rd'); x.click('#geoForm button'); x.wait_for_timeout(500); draft(x)
    try: x.wait_for_function('window.__relay.state.draft === true', timeout=8000); x.wait_for_selector('#flowTable', timeout=8000); x.wait_for_timeout(300)
    except Exception: pass
    SHORT_TXT = 'Draft route: hydrant T-102 to 100 TEST HILL RD, YORKTOWN HEIGHTS. It follows Test Hill Rd. The driveway is shorter than 100 ft, so the draft stops on the road. Drag S or A to move them.'
    sd = x.evaluate("(() => { const s=window.__relay.state, m=window.__relay.map; let dash=0, yellow=0; m.eachLayer(l => { if (l.options && l.options.color==='#ffd21f') { yellow++; if (l.options.dashArray) dash++; } }); return {draft:s.draft, last:s.points[s.points.length-1], dash, yellow, text:document.getElementById('status').textContent}; })()")
    ok('short driveway: the draft ends at the road point, not the address', sd['draft'] is True and abs(sd['last']['lat']-(C[0]+0.003))<1e-6 and abs(sd['last']['lng']-ADDR_SHORT[1])<1e-6, sd['last'])
    ok('  the status says the draft stops on the road (with the low hydrant caution)', sd['text']==SHORT_TXT + ' The county hydrant list can be incomplete here. A nearer hydrant can exist.', sd['text'])
    ok('  no dashed leg is drawn', sd['yellow']==1 and sd['dash']==0, (sd['yellow'], sd['dash']))
    # dual 3 inch lines
    before = x.evaluate(SNAP)['res']; x.select_option('#setHose', '3'); x.wait_for_timeout(300)
    after = x.evaluate(SNAP)['res']; fl = x.evaluate('[500,750,1000,1250,1500,2000].map(q => window.__relay.state.results[q].fl100)')
    ok('Dual 3 inch lines: friction is 6, 11.25, 20, 31.25, 44, 80 PSI per 100 ft, the results change, and the hint shows', fl==[6,11.25,20,31.25,44,80] and after!=before and x.is_visible('#dualHint') and x.inner_text('#dualHint')=='For dual lines, enter the length of dual line that one engine lays.', (fl, before, after))
    x.click('#layRev'); x.click('#btnCard'); x.wait_for_timeout(500)
    foot = x.inner_text('#cardBody .foot')
    ok('card footer says dual 3" lines, not 3" LDH', foot.startswith('Rules: dual 3" lines, friction loss') and '3" LDH' not in foot, foot[:60])
    x.click('#btnBack'); x.wait_for_timeout(300)
    x.select_option('#setHose', '5'); x.wait_for_timeout(300)
    ok('the hint hides again for 5 inch', not x.is_visible('#dualHint'))
    x.select_option('#setHose', '3'); x.wait_for_timeout(200); x.click('#btnSaveDefaults'); x.evaluate("localStorage.removeItem('yhfd-relay-pilot-v1')"); x.reload(); x.wait_for_timeout(900)
    ok('saved defaults accept hose 3: the select, the hint, and the summary', x.input_value('#setHose')=='3' and x.is_visible('#dualHint') and x.inner_text('#defaultsStatus')=='Defaults in use: yours (Yorktown Hgts FD, dual 3 inch, chart, 185 PSI, 20 PSI, 10%, 1,000 ft).', x.inner_text('#defaultsStatus'))
    # drag S and A with the edit handles hidden
    x.select_option('#setHose', '5'); x.click('#btnResetDefaults')
    x.fill('#geoText', '100 Test Hill Rd'); x.click('#geoForm button'); x.wait_for_timeout(500); draft(x)
    try: x.wait_for_function('window.__relay.state.draft === true', timeout=8000); x.wait_for_selector('#flowTable', timeout=8000); x.wait_for_timeout(300)
    except Exception: pass
    x.uncheck('#showHandles'); x.wait_for_timeout(200)
    PT = "(() => { const s=window.__relay.state; return {n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], draft:s.draft, hyd:s.sourceHydrant, hose:s.profile.h[s.profile.n-1]}; })()"
    p0 = x.evaluate(PT)
    ok('before the drag: handles are hidden and S and A have the Drag to move tooltip', x.locator('.vx').count()==0 and x.locator('.em.S').count()==1 and x.locator('.em.A').count()==1 and p0['draft'] is True)
    def drag(sel, dx, dy):
        bb = x.locator(sel).bounding_box(); x0, y0 = bb['x']+bb['width']/2, bb['y']+bb['height']/2
        x.mouse.move(x0, y0); x.mouse.down(); x.mouse.move(x0+dx, y0+dy, steps=8); x.mouse.up(); x.wait_for_timeout(300)
        try: x.wait_for_function("document.getElementById('status').textContent.startsWith('Route calculated')", timeout=8000)
        except Exception: pass
    x.hover('.em.A'); x.wait_for_timeout(300)
    ok('hover on A shows the tooltip Drag to move', x.locator('.leaflet-tooltip').count()>=1 and x.inner_text('.leaflet-tooltip')=='Drag to move', x.locator('.leaflet-tooltip').count())
    x.mouse.move(5, 5)
    drag('.em.A', 70, -50); p1 = x.evaluate(PT)
    ok('drag A: the last point moves, the draft flag clears, the source stays, and the route is recalculated', abs(p1['last']['lat']-p0['last']['lat'])+abs(p1['last']['lng']-p0['last']['lng'])>0.0002 and p1['draft'] is False and p1['first']==p0['first'] and p1['hose']!=p0['hose'] and p1['n']==p0['n'], (p0['last'], p1['last'], p0['hose'], p1['hose']))
    drag('.em.S', -80, 60); p2 = x.evaluate(PT)
    ok('drag S: the first point moves, the last stays, and the route is recalculated', abs(p2['first']['lat']-p1['first']['lat'])+abs(p2['first']['lng']-p1['first']['lng'])>0.0002 and p2['last']==p1['last'] and p2['hose']!=p1['hose'], (p1['first'], p2['first'], p1['hose'], p2['hose']))
    ok('  the moved S no longer counts as a hydrant source', p2['hyd'] is None and x.inner_text('#sourceType')!='' , p2['hyd'])
    # ---- v0.9 phase: Go finds the address only. Step 2 holds the choices. The draft starts on a button. ----
    e9 = len(errors)
    FOUND = 'Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. Check step 2. Then select Draft route by road, or trace by hand.'
    GATE['roads'] = True; GATE['addr'] = ADDR2; GATE['road'] = None
    y = fresh(); y.set_viewport_size({'width':1280,'height':900}); road_calls = []
    y.on('request', lambda r: road_calls.append(r.url) if 'MapServer/11/query' in r.url else None)
    y.goto(test_html.resolve().as_uri()); y.wait_for_timeout(700)
    ok('the source type starts empty: first option is Select the type, the state is empty', y.evaluate("[...document.querySelectorAll('#sourceType option')].map(o => o.value + ':' + o.textContent)")==[':Select the type','Hydrant:Hydrant','Draft site:Draft site','Tanker dump site:Tanker dump site','Other:Other'] and y.input_value('#sourceType')=='' and y.evaluate('window.__relay.state.sourceType')=='')
    ok('the trace button idle label is Trace by hand and the draft button is first in the row and enabled', y.inner_text('#btnDraw')=='Trace by hand' and y.is_enabled('#btnDraft') and y.evaluate("document.querySelector('#btnDraft').nextElementSibling.id")=='btnDraw' and y.inner_text('#btnDraft')=='Draft route by road')
    y.click('#btnDraft')
    ok('draft button with no address: Find the address first.', y.inner_text('#status')=='Find the address first.', y.inner_text('#status'))
    y.fill('#geoText', '100 Test Hill Rd'); y.click('#geoForm button'); y.wait_for_function("document.getElementById('status').textContent.startsWith('Found')", timeout=8000); y.wait_for_timeout(700)
    ok('Go alone: no road request, no route, the status is the exact Found text', not road_calls and y.evaluate('window.__relay.state.points.length')==0 and not y.evaluate('window.__relay.state.draft') and y.inner_text('#status')==FOUND, (len(road_calls), y.inner_text('#status')))
    pin = y.evaluate("(() => { const m=window.__relay.map, e=document.querySelector('.pin'), r=e.getBoundingClientRect(), b=document.getElementById('map').getBoundingClientRect(); const c=m.latLngToContainerPoint([%f,%f]); return {n:document.querySelectorAll('.pin').length, dx:Math.abs(r.left+r.width/2-b.left-c.x), dy:Math.abs(r.top+r.height-b.top-c.y)}; })()" % ADDR2)
    ok('Go alone: one pin is on the map at the address, and the plan name is the address', pin['n']==1 and pin['dx']<14 and pin['dy']<30 and y.input_value('#planName')=='100 TEST HILL RD, YORKTOWN HEIGHTS', pin)
    y.set_viewport_size({'width':1280,'height':1900}); y.wait_for_timeout(300); y.locator('#side').screenshot(path='out/v09-sidebar.png'); y.set_viewport_size({'width':1280,'height':900}); y.wait_for_timeout(300)
    y.click('#btnDraft'); ok('draft button with no type: Select the water source type in step 2.', y.inner_text('#status')=='Select the water source type in step 2.', y.inner_text('#status'))
    y.select_option('#sourceType', 'Hydrant'); y.click('#btnDraft'); ok('draft button with no lay: Select Reverse lay or Forward lay in step 2.', y.inner_text('#status')=='Select Reverse lay or Forward lay in step 2.' and not road_calls, y.inner_text('#status'))
    y.click('#layRev'); y.click('#btnDraft')
    try: y.wait_for_function('window.__relay.state.draft === true', timeout=8000); y.wait_for_selector('#flowTable', timeout=8000); y.wait_for_timeout(300)
    except Exception: pass
    d9 = y.evaluate("(() => { const s=window.__relay.state; return {n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, type:s.sourceType, text:document.getElementById('status').textContent}; })()")
    ok('hydrant draft after the button equals the old draft: hydrant T-102 first, the address last, the same status text', d9['hyd'] and d9['hyd']['num']=='T-102' and d9['n']>=3 and abs(d9['first']['lat']-(C[0]+0.001))<1e-9 and abs(d9['first']['lng']-(C[1]+0.002))<1e-9 and abs(d9['last']['lat']-ADDR2[0])<1e-9 and abs(d9['last']['lng']-ADDR2[1])<1e-9 and d9['text']=='Draft route: hydrant T-102 to 100 TEST HILL RD, YORKTOWN HEIGHTS. It follows Test Hill Rd. Drag a point to match the driveway. Click the line to add a point. The county hydrant list can be incomplete here. A nearer hydrant can exist.', d9)
    y.screenshot(path='out/v09-after-draft.png')
    y.click('#btnDraft'); ok('draft button with a route: Clear the route first. The draft needs an empty route.', y.inner_text('#status')=='Clear the route first. The draft needs an empty route.' and y.evaluate('window.__relay.state.points.length')==d9['n'], y.inner_text('#status'))
    y.click('#btnClear'); y.wait_for_timeout(300)
    ok('Clear empties the source type, the lay, and the pin; the draft then asks for the address', y.input_value('#sourceType')=='' and y.evaluate('window.__relay.state.sourceType')=='' and y.evaluate('window.__relay.state.settings.lay')==None and y.locator('.pin').count()==0, y.input_value('#sourceType'))
    y.click('#btnDraft'); ok('after Clear the draft button says Find the address first.', y.inner_text('#status')=='Find the address first.', y.inner_text('#status'))
    # a non-hydrant type: the page asks for a click on the map, then drafts from the click
    y.fill('#geoText', '100 Test Hill Rd'); y.click('#geoForm button'); y.wait_for_function("document.getElementById('status').textContent.startsWith('Found')", timeout=8000)
    y.select_option('#sourceType', 'Draft site'); y.click('#layFwd'); road_calls.clear(); y.click('#btnDraft')
    ok('Draft site: the status asks for a click on the water source, and no road request is made yet', y.inner_text('#status')=='Click the water source on the map.' and not road_calls and y.evaluate('window.__relay.state.points.length')==0, y.inner_text('#status'))
    SRC = (C[0]+0.00005, C[1]+0.001)
    y.evaluate('window.__relay.map.fire("click",{latlng:{lat:%f,lng:%f}})' % SRC)
    try: y.wait_for_function('window.__relay.state.draft === true', timeout=8000); y.wait_for_selector('#flowTable', timeout=8000); y.wait_for_timeout(300)
    except Exception: pass
    d9 = y.evaluate("(() => { const s=window.__relay.state; return {n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, type:s.sourceType, text:document.getElementById('status').textContent}; })()")
    ok('Draft site: the click is the first point, the address is last, the source hydrant stays null, the type stays', d9['hyd'] is None and d9['type']=='Draft site' and d9['n']>=3 and abs(d9['first']['lat']-SRC[0])<1e-9 and abs(d9['first']['lng']-SRC[1])<1e-9 and abs(d9['last']['lat']-ADDR2[0])<1e-9, d9)
    ok('  the status starts: Draft route: draft site to <address>. It follows Test Hill Rd.', d9['text'].startswith('Draft route: draft site to 100 TEST HILL RD, YORKTOWN HEIGHTS. It follows Test Hill Rd.') and 'county hydrant list' not in d9['text'], d9['text'])
    # a far hydrant: a winding road of about 11,000 ft joins the only hydrant to the address
    KLAT = 20902260*3.141592653589793/180
    import math
    def LL9(xf, yf): return [C[1]+xf/(KLAT*math.cos(C[0]*math.pi/180)), C[0]+yf/KLAT]
    FARROAD = [LL9(0,0), LL9(4500,0), LL9(4500,2000), LL9(0,2000)]
    f9 = pathlib.Path('out/test_far.html')
    f9.write_text(re.sub(r'(id="hydrant-data">).*?(</script>)', lambda m: m.group(1) + json.dumps([[FARROAD[0][0], FARROAD[0][1], 'F-1', 'YKTWN']]) + m.group(2), src, count=1, flags=re.S), encoding='utf-8')
    w9 = fresh(); w9.goto(f9.resolve().as_uri()); w9.wait_for_timeout(700)
    GATE['addr'] = (FARROAD[3][1], FARROAD[3][0]); GATE['road'] = FARROAD
    w9.fill('#geoText', '100 Test Hill Rd'); w9.click('#geoForm button'); w9.wait_for_timeout(700); draft(w9)
    try: w9.wait_for_function("document.getElementById('status').textContent.startsWith('No road draft')", timeout=8000)
    except Exception: pass
    GATE['addr'] = ADDR2; GATE['road'] = None
    ok('a hydrant more than 1 mile away by road: the exact no-draft status and no route', w9.inner_text('#status')=='No road draft: the nearest hydrant by road is F-1, about 11,000 ft away. That is more than 1 mile. Select a different water source type, or trace the route by hand.' and w9.evaluate('window.__relay.state.points.length')==0 and not w9.evaluate('window.__relay.state.draft'), w9.inner_text('#status'))
    # a clicked source more than 1 mile away by road
    w9.select_option('#sourceType', 'Other'); w9.click('#btnDraft'); GATE['addr'] = (FARROAD[3][1], FARROAD[3][0]); GATE['road'] = FARROAD
    w9.evaluate('window.__relay.map.fire("click",{latlng:{lat:%f,lng:%f}})' % (FARROAD[0][1], FARROAD[0][0]))
    try: w9.wait_for_function("document.getElementById('status').textContent.startsWith('No road draft')", timeout=8000)
    except Exception: pass
    GATE['addr'] = ADDR2; GATE['road'] = None
    ok('a clicked source more than 1 mile away by road: the exact no-draft status and no route', w9.inner_text('#status')=='No road draft: the water source is about 11,000 ft away by road. That is more than 1 mile. Trace the route by hand.' and w9.evaluate('window.__relay.state.points.length')==0, w9.inner_text('#status'))
    # a card with no source type prints Not selected
    GATE['roads'] = False
    k9 = fresh(); k9.goto(test_html.resolve().as_uri()); k9.wait_for_timeout(700)
    kb = k9.locator('#map').bounding_box(); kx, ky = kb['x']+kb['width']/2, kb['y']+kb['height']/2
    k9.click('#layRev'); k9.click('#btnDraw')
    for dx,dy in ((220,120),(300,170)): k9.mouse.click(kx+dx, ky+dy); k9.wait_for_timeout(100)
    k9.click('#btnFinish'); k9.wait_for_selector('#flowTable', timeout=8000); k9.click('#btnCard'); k9.wait_for_timeout(500)
    ok('a card with no source type: the Water source fact reads Not selected', k9.evaluate('window.__relay.state.sourceType')=='' and k9.inner_text('#cardHead .facts4 div:nth-child(1) b')=='Not selected' and k9.inner_text('#cardHead .facts4 div:nth-child(1) span').lower()=='water source', k9.inner_text('#cardHead .facts4 div:nth-child(1)'))
    # order of the sidebar sections
    heads = y.evaluate("[...document.querySelectorAll('#side .sec h2')].map(h => h.textContent)")
    ok('sidebar sections are in the accepted order', heads==['Fire district','1. Find the address','2. Set up the lay','3. Make the route','4. Read the result','Keep the plan','My defaults'], heads)
    inside = y.evaluate("(() => { const sec = id => document.getElementById(id).closest('.sec').querySelector('h2').textContent; return {six:['sourceType','layRev','setHose','setHosePer','setCap','setRes','setBasis','setSlack'].map(sec), btns:['btnDraft','btnDraw','btnUndo','btnFinish','btnClear','status'].map(sec), res:sec('results'), defs:['btnSaveDefaults','btnResetDefaults','btnCopyDefaults','defaultsStatus'].map(sec), name:sec('planName')}; })()")
    ok('the settings are inside step 2 (before step 3), the buttons in step 3, the result in step 4, My defaults at the bottom', set(inside['six'])=={'2. Set up the lay'} and set(inside['btns'])=={'3. Make the route'} and inside['res']=='4. Read the result' and set(inside['defs'])=={'My defaults'} and inside['name']=='1. Find the address', inside)
    ok('the six settings sit in three two-column rows in the mockup order', y.evaluate("[...document.querySelectorAll('#setHose,#setHosePer,#setCap,#setRes,#setBasis,#setSlack')].map(e => e.id).join()")=='setHose,setHosePer,setCap,setRes,setBasis,setSlack' and y.evaluate("[...document.querySelectorAll('#side .sec')][2].querySelectorAll('.row').length")==3)
    ok('no page errors in the v0.9 phase', not [e for e in errors[e9:] if 'Failed to load resource' not in e], errors[e9:][:3])
    GATE['addr'] = C; GATE['roads'] = False
    ok('no page errors in the v0.4 phase', not [e for e in errors[e0:] if 'Failed to load resource' not in e], errors[e0:][:3])
    bad = [e for e in errors if 'Failed to load resource' not in e]
    ok('no console errors except the aborted requests', not bad, bad[:3])
    b.close()
for f in ('out/card_forward.pdf','out/card_reverse.pdf','out/v08-card.pdf'):
    n = len(re.findall(rb'/Type\s*/Page(?![a-zA-Z])', pathlib.Path(f).read_bytes()))
    ok(f+' prints on one page', n==1, n)
print('console errors:', errors[:6]); print('\nFAILED: '+str(fails) if fails else '\nALL UI CHECKS PASS')
sys.exit(1 if fails else 0)
