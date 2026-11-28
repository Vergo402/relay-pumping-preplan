"""Page test for the relay calculator. It drives the built page in Chrome.

Usage: python3 tests/test_ui.py "dist/Relay Pumping Pre-plan.html"
Needs: pip install playwright, and Google Chrome.
Set CHROME_PATH to the Chrome program if Playwright cannot find Chrome.

The test does not use the internet. It answers map, address, and ground height
requests with stand-in data. The stand-in ground is a smooth slope.
"""
import datetime, json, os, re, sys, base64, urllib.parse, pathlib
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
def to_set(q):  # v0.17: show the Settings view (My defaults, the rules list). Safe to call twice.
    if not q.evaluate("document.getElementById('side').classList.contains('set')"): q.click('#btnSettings')
def to_plan(q):  # v0.17: go back to the planner view. Safe to call twice.
    if q.evaluate("document.getElementById('side').classList.contains('set')"): q.click('#btnSettingsBack')
ROWS20 = "[...document.querySelectorAll('#side .sec[data-k] .su')].map(b => [b.className.split(' ').slice(1).sort().join(' '), getComputedStyle(b).backgroundColor, getComputedStyle(b).color, getComputedStyle(b, '::before').width])"  # v0.20: the state of each setup row
def named(q):  # v0.21: the address is required before a route. With no address, type a plan name.
    q.evaluate("(() => { const r = window.__relay; if (!r.state.name && !r.found()) { const i = document.getElementById('planName'); i.value = 'Test plan'; i.dispatchEvent(new Event('input')); } })()")
def open_sec(q, key):  # v0.16: one setup section is open at a time. Click its line (if closed) before a check uses a control inside.
    to_plan(q)
    q.evaluate("k => { const s=document.querySelector('#side .sec[data-k=' + k + ']'); if (!s.querySelector('.bd').classList.contains('op')) s.firstElementChild.click(); }", key)
def pick(q, d='253'):  # v0.16: a new page has no district. Select one (default Yorktown Hgts FD).
    open_sec(q, 'dist'); q.select_option('#setDistrict', d); q.wait_for_timeout(300)
    q.evaluate("document.querySelector('#side .sec[data-k=dist] .su').click()"); q.wait_for_timeout(300)  # close it again
def load(q, f=None):  # goto + wait + select Yorktown Hgts FD
    q.goto((f or test_html).resolve().as_uri()); q.wait_for_timeout(700); pick(q)
def draft(q, kind='Hydrant', lay='#layRev'):  # v0.9: the draft needs the type and the lay, then the button
    open_sec(q, 'lay'); q.select_option('#sourceType', kind); q.click(lay); open_sec(q, 'route'); q.click('#btnDraft')
def clear(q):  # v0.14: Clear asks first. Confirm it.
    q.click('#btnClear'); q.click('#btnClearYes')
SNAP = '''() => { const s=window.__relay.state; return {lay:s.settings.lay, pts:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, hose:s.profile?s.profile.h[s.profile.n-1]:null,
  net:s.profile?s.profile.z[s.profile.n-1]-s.profile.z[0]:null, res:s.profile?[500,750,1000,1250,1500,2000].map(q=>({q, relays:s.results[q].relays.length, pdps:s.results[q].segs.map(x=>x.pdp), secs:s.results[q].segs.map(x=>Math.round(x.hose)), over:s.results[q].over, overHose:s.results[q].overHose})):null}; }'''
# The card blocks. Each block gives its label, mark, engine texts, arrowhead counts, "Lays" values, and the planner lay values for the same flow.
CARD = """() => { const up=n=>Math.ceil((n-0.5)/100)*100, st=window.__relay.state;
  return [...document.querySelectorAll('#cardBody .blk')].map(b => { const q=+b.querySelector('.fl b').textContent.replace(',',''), segs=st.results[q].segs;
    return { label:b.querySelector('.fl b').textContent, mark:b.querySelector('.fl').innerText.includes('On the map'), layout:b.querySelector('.fl small').textContent,
      engines:[...b.querySelectorAll('.e')].map(e=>e.innerText.replace(/\\n/g,' | ')), pumps:segs.length, hl:b.querySelectorAll('.hl').length, hr:b.querySelectorAll('.hr').length, sections:b.querySelectorAll('.s').length,
      lays:[...b.querySelectorAll('.s b')].map(e=>e.textContent), plan:segs.map(g=>up(g.hose).toLocaleString('en-US')+' ft'), text:b.innerText }; }); }"""
# Every card block, with a count of its engine (.e), section (.s), and grid (.g) elements.
CARD_ALL = "[...document.querySelectorAll('#cardBody .blk')].map(b => ({label:b.querySelector('.fl b').textContent, text:b.innerText, np:!!b.querySelector('.np'), e:b.querySelectorAll('.e').length, s:b.querySelectorAll('.s').length, g:b.querySelectorAll('.g').length, relays:window.__relay.state.results[+b.querySelector('.fl b').textContent.replace(',','')].segs.length-1}))"
CARDMAP = "[...document.querySelectorAll('#cardBody .blk')].map(b => b.querySelector('.fl').innerText.includes('On the map') ? b.querySelector('.fl b').textContent : '').filter(Boolean)"
LAYROWS = "(() => { const t=[...document.querySelectorAll('#results table')].filter(t=>t.querySelector('th').textContent=='Lay')[0]; return {heads:[...t.querySelectorAll('th')].map(h=>h.textContent), rows:[...t.querySelectorAll('tbody tr')].map(r=>({cells:[...r.cells].map(c=>c.textContent), h:r.getBoundingClientRect().height}))}; })()"
UP = [(4,3),(120,-90),(160,-220),(60,-300)]   # source (hydrant at the centre) first, then uphill
with sync_playwright() as p:
    chrome = os.environ.get('CHROME_PATH')
    b = p.chromium.launch(executable_path=chrome, args=['--no-sandbox']) if chrome else p.chromium.launch(channel='chrome')
    pg = b.new_page(viewport={'width':1440,'height':900})
    pg.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR '+str(e)))
    pg.route('**/*', handle)
    pg.goto(test_html.resolve().as_uri()); pg.wait_for_timeout(700)
    ok('no default lay: Manually draw route stays enabled (v0.16: its click explains the missing choice) and the lay is empty at the start', pg.is_enabled('#btnDraw') and pg.evaluate('window.__relay.state.settings.lay')==None, pg.inner_text('#layHint'))
    pg.screenshot(path='out/v2_start.png')
    pick(pg); open_sec(pg, 'dist')
    opts = pg.evaluate("[...document.querySelectorAll('#setDistrict option')].map(o => o.textContent)")
    ok('district picker: Select district plus 60 districts, Yorktown Hgts FD (253) picked, hint right', len(opts)==61 and opts[0]=='Select district' and pg.input_value('#setDistrict')=='253' and 'Yorktown Hgts FD' in pg.evaluate("document.querySelector('#setDistrict').selectedOptions[0].textContent") and pg.evaluate('window.__relay.state.settings.district')==253 and pg.inner_text('#distHint')=='60 county districts. Hydraulic rules: chauffeur chart.', pg.inner_text('#distHint'))
    open_sec(pg, 'addr'); pg.fill('#geoText', '100 Test Hill Rd'); open_sec(pg, 'addr'); pg.click('#geoForm button'); pg.wait_for_timeout(600); draft(pg)
    try: pg.wait_for_function("document.getElementById('status').textContent.includes('No auto route')", timeout=5000)
    except Exception: pass
    ok('road query fails: no draft, the route stays empty and the status says so', pg.evaluate('window.__relay.state.points.length')==0 and not pg.evaluate('window.__relay.state.draft') and pg.inner_text('#status').startswith('Found: ') and 'No auto route: the road data did not answer. Draw the route manually.' in pg.inner_text('#status'), pg.inner_text('#status'))
    pg.evaluate('window.__relay.map.setZoom(16,{animate:false})'); pg.wait_for_timeout(400)
    box = pg.locator('#map').bounding_box(); cx, cy = box['x']+box['width']/2, box['y']+box['height']/2
    # ---- reverse lay: attack engine first ----
    open_sec(pg, 'lay'); pg.click('#layRev'); open_sec(pg, 'route'); ok('reverse selected: steps start at the attack engine', 'attack engine position first' in pg.inner_text('#steps') and pg.is_enabled('#btnDraw'), pg.inner_text('#status'))
    open_sec(pg, 'route'); named(pg); pg.click('#btnDraw'); ok('lay buttons lock during the trace', pg.is_disabled('#layFwd'))
    for dx,dy in reversed(UP): pg.mouse.click(cx+dx, cy+dy); pg.wait_for_timeout(100)
    ok('reverse status asks for the water source last', 'water source last' in pg.inner_text('#status'), pg.inner_text('#status'))
    pg.mouse.click(cx-200, cy+200); pg.wait_for_timeout(100); n5 = pg.evaluate('window.__relay.state.points.length')
    open_sec(pg, 'route'); pg.click('#btnUndo'); pg.wait_for_timeout(100); st = pg.evaluate('window.__relay.state.points.map(p=>[p.lat,p.lng])')
    ok('reverse undo removes the newest click (the source end)', n5==5 and len(st)==4 and abs(st[0][0]-C[0])<0.0002)
    open_sec(pg, 'route'); pg.click('#btnFinish'); pg.wait_for_selector('#flowTable', timeout=8000); pg.wait_for_timeout(300)
    rev = pg.evaluate(SNAP); print(json.dumps(rev))
    ok('reverse: water source ends as point 1 and snaps to hydrant T-101', rev['hyd'] and rev['hyd']['num']=='T-101' and abs(rev['first']['lat']-C[0])<1e-9 and abs(rev['first']['lng']-C[1])<1e-9)
    ok('reverse: route runs uphill in water order', rev['net']>100, round(rev['net']))
    ok('every section within 1,000 ft, no flags', all(max(r['secs'])<=1000 and not r['over'] and not r['overHose'] for r in rev['res']))
    txt = pg.inner_text('#results'); i = txt.find('Hose lay order'); print('LAY BLOCK (reverse):', txt[i:i+420].replace('\n',' | '))
    lo = pg.evaluate(LAYROWS); nr = len(lo['rows']); rr = lo['rows']  # v0.15: the lay order table has From, To, and Then pumps as columns
    ok('reverse lay order: first lay starts at the attack engine, last pumps as Source', 'reverse lay' in txt and rr[0]['cells'][1:3]==['Attack','Relay %d' % (nr-1)] and rr[-1]['cells'][4]=='Source' and rr[-1]['cells'][2]=='Water source')
    ok('v0.15: reverse lay table has 5 headers and one-line rows with short From, To, and Then cells', lo['heads']==['Lay','From','To','Hose','Then pumps as'] and nr>=2 and all(r['h']<34 for r in rr) and [r['cells'][0] for r in rr]==[str(i+1) for i in range(nr)] and all(rr[i]['cells'][2]==rr[i+1]['cells'][1] and rr[i]['cells'][4]==rr[i]['cells'][2].replace('Water source','Source') for i in range(nr-1)) and all(r['cells'][3].endswith(' ft') for r in rr), lo)
    pg.screenshot(path='out/v2_reverse.png')
    ov = pg.evaluate("(() => { const e=document.getElementById('side'); const t=[...e.querySelectorAll('table')].map(x=>x.scrollWidth); return {side:e.clientWidth, tables:t, inner:e.clientWidth-36}; })()")
    ok('sidebar tables fit the panel', all(w <= ov['inner']+1 for w in ov['tables']), ov)
    pg.locator('#side').evaluate('e => e.scrollTop = 520'); pg.wait_for_timeout(150); pg.screenshot(path='out/v2_reverse_scrolled.png')
    # ---- switch the same route to forward lay ----
    open_sec(pg, 'lay'); pg.click('#layFwd'); pg.wait_for_timeout(200); fw = pg.evaluate(SNAP); txt = pg.inner_text('#results'); i = txt.find('Hose lay order'); print('LAY BLOCK (forward):', txt[i:i+470].replace('\n',' | '))
    ok('switch to forward keeps the hydraulics', fw['res']==rev['res'] and fw['lay']=='forward')
    lf = pg.evaluate(LAYROWS); fr = lf['rows']; nf = len(fr)
    ok('forward lay order: first lay starts at the water source, last stops at the attack engine', fr[0]['cells'][1]=='Water source' and fr[-1]['cells'][2]=='Attack' and fr[-1]['cells'][4]=='Stops at Attack')
    ok('v0.15: forward lay rows carry the short From, To, and Then cells and stay on one line', lf['heads']==['Lay','From','To','Hose','Then pumps as'] and nf==nr and all(r['h']<34 for r in fr) and all(fr[i]['cells'][2]==fr[i+1]['cells'][1] and fr[i]['cells'][4]==fr[i]['cells'][2] for i in range(nf-1)) and [r['cells'][3] for r in fr]==[r['cells'][3] for r in reversed(rr)], lf)
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
    pg.click('#btnBack'); open_sec(pg, 'lay'); pg.click('#layRev'); pg.click('#btnCard'); pg.wait_for_timeout(600)
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
    ok('planner table has six rows with the right FL/100 values (5 inch formula, one decimal only when not whole)', trows==[['500 GPM','2 PSI'],['750 GPM','4.5 PSI'],['1,000 GPM','8 PSI'],['1,250 GPM','12.5 PSI'],['1,500 GPM','18 PSI'],['2,000 GPM','32 PSI']], trows)
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
    # ---- v0.11: a card flow that needs 6 or more relay engines is "Not practical as a relay" ----
    # At 150 PSI maximum PDP and 1,000 ft on each engine, the engine counts for 500, 1,250, and 2,000 GPM are 2, 3, and 7 relays.
    view = pg.evaluate('[window.__relay.map.getCenter(), window.__relay.map.getZoom()]')
    open_sec(pg, 'lay'); pg.select_option('#setCap', '150'); pg.wait_for_timeout(200)
    pg.click('#btnCard'); pg.wait_for_timeout(500); np_ = pg.evaluate(CARD_ALL)
    ok('card flow with 7 relay engines (2,000 GPM): "Not practical as a relay", the real count, no engine or section elements', [x['label'] for x in np_]==['500','1,250','2,000'] and np_[2]['np'] and 'Not practical as a relay' in np_[2]['text'] and 'needs 7 relay engines' in np_[2]['text'] and 'maximum of 5' in np_[2]['text'] and np_[2]['e']==0 and np_[2]['s']==0 and np_[2]['g']==0, np_[2]['text'])
    ok('card flows with 5 relay engines or fewer (500 and 1,250 GPM) still show PDPs and arrows', all(not x['np'] and x['e']==x['relays']+2 and x['s']==x['relays']+1 and 'Not practical' not in x['text'] for x in np_[:2]), [(x['label'], x['relays'], x['e'], x['s']) for x in np_[:2]])
    pg.click('#btnBack'); pg.wait_for_timeout(200)
    open_sec(pg, 'lay'); pg.select_option('#setCap', '185'); pg.evaluate('([c, z]) => window.__relay.map.setView(c, z, {animate:false})', view)
    pg.wait_for_timeout(400)
    # ---- v0.12: the card engine markers are smaller, and the card map fits the route with 20 px of padding ----
    EM_T = "() => [...document.querySelectorAll('#map .em')].map(e => getComputedStyle(e).transform)"
    # Each marker centre must be in the map box. The span along the longer axis must be wider than the map minus 90 px.
    EM_FIT = """() => { const m=document.getElementById('map').getBoundingClientRect(), c=[...document.querySelectorAll('#map .em')].map(e=>{const r=e.getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2];});
      const xs=c.map(p=>p[0]), ys=c.map(p=>p[1]), sx=Math.max(...xs)-Math.min(...xs), sy=Math.max(...ys)-Math.min(...ys), useX=sx/m.width>=sy/m.height;
      return {n:c.length, inside:c.every(p=>p[0]>=m.left&&p[0]<=m.right&&p[1]>=m.top&&p[1]<=m.bottom), span:useX?sx:sy, size:useX?m.width:m.height}; }"""
    off_t = pg.evaluate(EM_T)
    pg.click('#btnCard'); pg.wait_for_timeout(800)
    on_t = pg.evaluate(EM_T); fit = pg.evaluate(EM_FIT)
    ok('v0.12: card mode scales the engine markers to 0.7; the planner leaves them at none', len(on_t)>=2 and all(t=='matrix(0.7, 0, 0, 0.7, 0, 0)' for t in on_t) and len(off_t)>=2 and all(t=='none' for t in off_t), (off_t[:1], on_t[:1]))
    ok('v0.12: on the card, every engine marker is inside the map and the markers span more than the map size minus 90 px', fit['n']>=2 and fit['inside'] and fit['span'] > fit['size']-90, fit)
    # v0.18: the print step must not move the map or load new tiles. A print takes its picture before new tiles arrive.
    # proof: with the old fitBounds in beforeprint, the centre moves and this check fails.
    PV = "(()=>{const m=window.__relay.map,c=m.getCenter();return [m.getZoom(),c.lat.toFixed(6),c.lng.toFixed(6),document.querySelectorAll('#map .leaflet-tile-pane img').length,document.title]})()"
    pv0 = pg.evaluate(PV); pg.emulate_media(media='print')
    pg.evaluate("window.dispatchEvent(new Event('beforeprint'))"); pv1 = pg.evaluate(PV)
    pg.evaluate("window.dispatchEvent(new Event('afterprint'))"); pg.emulate_media(media='screen'); pg.wait_for_timeout(200)
    ok('v0.18: the print step keeps the card map view and tiles, and still sets the PDF file name', pv1[:4]==pv0[:4] and pv1[4]!=pv0[4] and pg.evaluate(PV)[4]==pv0[4], (pv0, pv1))
    pg.click('#btnBack'); pg.wait_for_timeout(200)
    # ---- clear: lay must be picked again ----
    open_sec(pg, 'route'); clear(pg); pg.wait_for_timeout(150)
    ok('clear resets the lay and the district; Manually draw route stays enabled', pg.evaluate('window.__relay.state.settings.lay')==None and pg.evaluate('window.__relay.state.settings.district')==None and pg.is_enabled('#btnDraw'), pg.inner_text('#status'))
    # ---- forward lay: source first ----
    pick(pg); open_sec(pg, 'lay'); pg.select_option('#sourceType', 'Hydrant')
    pg.evaluate('window.__relay.map.setView([%f,%f],16,{animate:false})' % C); pg.wait_for_timeout(400)
    open_sec(pg, 'lay'); pg.click('#layFwd'); open_sec(pg, 'route'); named(pg); pg.click('#btnDraw')
    for dx,dy in UP: pg.mouse.click(cx+dx, cy+dy); pg.wait_for_timeout(100)
    open_sec(pg, 'route'); pg.click('#btnFinish'); pg.wait_for_selector('#flowTable', timeout=8000); pg.wait_for_timeout(300)
    f2 = pg.evaluate(SNAP)
    ok('forward trace gives the same route as the reverse trace', abs(f2['hose']-rev['hose'])<1 and f2['hyd']['num']=='T-101' and f2['res']==rev['res'], (round(f2['hose']), round(rev['hose'])))
    open_sec(pg, 'lay'); pg.select_option('#setCap', '200'); open_sec(pg, 'lay'); pg.fill('#setHosePer', '1500'); open_sec(pg, 'lay'); pg.dispatch_event('#setHosePer', 'change'); pg.wait_for_timeout(200)
    r3 = pg.evaluate(SNAP)['res']; ok('1,500 ft per engine and 200 PSI lowers the engine count', sum(len(x['secs']) for x in r3) < sum(len(x['secs']) for x in rev['res']), [x['secs'] for x in r3])
    # ---- v0.3 phase: district picker, road draft, handles. It runs last so the old checks keep their state. ----
    open_sec(pg, 'route'); clear(pg); pg.wait_for_timeout(150)
    CEN = 'JSON.stringify(window.__relay.map.getCenter())'
    c0 = json.loads(pg.evaluate(CEN)); open_sec(pg, 'dist'); pg.select_option('#setDistrict', '226'); pg.wait_for_timeout(500); c1 = json.loads(pg.evaluate(CEN))
    nm = pg.evaluate("document.querySelector('#setDistrict').selectedOptions[0].textContent")
    ok('district change to ' + nm + ': map moves, placeholder, status, and layer label follow', abs(c1['lat']-c0['lat'])+abs(c1['lng']-c0['lng'])>0.01 and pg.get_attribute('#geoText','placeholder')=='Street address in '+nm and pg.inner_text('#status')=='District set to '+nm+'. Enter an address.' and (nm+' line') in pg.inner_text('.leaflet-control-layers-overlays'), (nm, c0, c1, pg.inner_text('#status')))
    open_sec(pg, 'dist'); pg.select_option('#setDistrict', '253'); pg.wait_for_timeout(500)
    ok('district set back to Yorktown Hgts FD (253)', pg.evaluate('window.__relay.state.settings.district')==253 and 'Yorktown Hgts FD' in pg.get_attribute('#geoText','placeholder'), pg.get_attribute('#geoText','placeholder'))
    # road draft: T-102 is the expected hydrant (T-101 is 2,050 ft by road, T-102 is 1,130 ft; X-9 is far from any road)
    GATE['roads'] = True; GATE['addr'] = ADDR2
    open_sec(pg, 'addr'); pg.fill('#geoText', '100 Test Hill Rd'); open_sec(pg, 'addr'); pg.click('#geoForm button'); pg.wait_for_timeout(500); draft(pg)
    try: pg.wait_for_function('window.__relay.state.draft === true', timeout=8000); pg.wait_for_selector('#flowTable', timeout=8000); pg.wait_for_timeout(300)
    except Exception: pass
    dr = pg.evaluate("(() => { const s=window.__relay.state, st=document.getElementById('status'); return {draft:s.draft, n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, cls:st.className, text:st.textContent}; })()")
    print('DRAFT:', json.dumps(dr))
    r20 = pg.evaluate(ROWS20)
    ok('v0.20: with a route, all four setup rows are done and no row is the next step', pg.evaluate('window.__relay.state.points.length') > 1 and [x[0] for x in r20]==['ok','ok','ok','ok'] and all(x[1]=='rgba(0, 0, 0, 0)' for x in r20), r20)
    ok('road draft with an empty route (hydrant T-102 by road): draft set, source hydrant, status ok', dr['draft'] is True and dr['n']>=3 and dr['hyd'] and dr['hyd']['num']=='T-102' and dr['cls']=='ok' and dr['text'].startswith('Auto route: hydrant'), dr['text'])
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
    open_sec(pg, 'route'); pg.uncheck('#showHandles'); pg.wait_for_timeout(200); hid = (pg.locator('.vx').count(), pg.locator('.mid').count())
    open_sec(pg, 'route'); pg.check('#showHandles'); pg.wait_for_timeout(200); shw = (pg.locator('.vx').count(), pg.locator('.mid').count())
    ok('Show handles off hides .vx and .mid, on shows them again', hid==(0,0) and shw==(n0, n0-1), (hid, shw))
    while pg.evaluate('window.__relay.state.points.length')>2: pg.locator('.vx').nth(1).click(button='right'); pg.wait_for_timeout(400)
    pg.locator('.vx').nth(0).dispatch_event('contextmenu'); pg.wait_for_timeout(400)  # the source engine icon covers this handle
    ok('with 2 points left, right-click removes nothing', pg.evaluate('window.__relay.state.points.length')==2)
    open_sec(pg, 'dist'); pg.select_option('#setDistrict', '226'); pg.wait_for_timeout(300); pg.reload(); pg.wait_for_timeout(1000)
    ok('reload keeps the fire district in the saved plan', pg.evaluate('window.__relay.state.settings.district')==226 and pg.input_value('#setDistrict')=='226', (pg.evaluate('window.__relay.state.settings.district'), pg.input_value('#setDistrict')))
    open_sec(pg, 'dist'); pg.select_option('#setDistrict', '253'); pg.wait_for_timeout(300)
    # ---- v0.4 phase: Maximum PDP 185, and "My defaults". Each part uses a new browser context, so storage starts empty. ----
    e0 = len(errors)
    def fresh():
        q = b.new_context(viewport={'width':1440,'height':900}).new_page()
        q.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
        q.on('pageerror', lambda e: errors.append('PAGEERROR '+str(e)))
        q.route('**/*', handle); return q
    LS = "k => localStorage.getItem(k)"
    VALS = {'hose':4, 'cap':200, 'residual':50, 'slack':5, 'hosePerEngine':1500}
    VSUM = '4 inch, 200 PSI, 50 PSI, 5%, 1,500 ft'
    def setall(q):
        open_sec(q, 'dist'); q.select_option('#setDistrict', '226'); open_sec(q, 'lay')
        for sel, v in (('#setHose','4'),('#setCap','200'),('#setRes','50'),('#setSlack','5')): q.select_option(sel, v)
        open_sec(q, 'lay'); q.fill('#setHosePer', '1500'); open_sec(q, 'lay'); q.dispatch_event('#setHosePer', 'change'); q.wait_for_timeout(300)
    def inputs(q): return q.evaluate("['#setDistrict','#setHose','#setCap','#setRes','#setSlack','#setHosePer'].map(s => document.querySelector(s).value)")
    q = fresh(); load(q)
    caps = q.evaluate("[...document.querySelectorAll('#setCap option')].map(o => o.value)")
    ok('Maximum PDP list is 150, 175, 185, 200', caps==['150','175','185','200'], caps)
    st = q.evaluate('window.__relay.state.settings')
    ok('a fresh page starts at 185 PSI and 1,000 ft', st['cap']==185 and st['hosePerEngine']==1000 and q.input_value('#setCap')=='185' and q.input_value('#setHosePer')=='1000', (st['cap'], st['hosePerEngine']))
    ok('status reads Defaults in use: built-in, with the summary', q.inner_text('#defaultsStatus')=='Defaults in use: built-in (5 inch, 185 PSI, 20 PSI, 10%, 1,000 ft).', q.inner_text('#defaultsStatus'))
    ok('the hose hint has no placeholder wording', 'placeholder' not in q.text_content('#side').lower() and q.text_content('#side').count('These are your defaults. Change them for this plan if necessary.')==1)
    setall(q); to_set(q); q.click('#btnSaveDefaults')
    ok('Save as my defaults: status says yours with the new summary', q.inner_text('#defaultsStatus')=='Saved in this browser. Defaults in use: yours ('+VSUM+').', q.inner_text('#defaultsStatus'))
    q.evaluate("localStorage.removeItem('yhfd-relay-pilot-v1')"); q.reload(); q.wait_for_timeout(900)  # no autosave: only the saved defaults can give these values
    ok('reload: the saved defaults give 200 PSI and 1,500 ft, and the status says yours', inputs(q)==['','4','200','50','5','1500'] and q.inner_text('#defaultsStatus')=='Defaults in use: yours ('+VSUM+').', (inputs(q), q.inner_text('#defaultsStatus')))
    GATE['roads'] = True; GATE['addr'] = ADDR2; pick(q)
    open_sec(q, 'addr'); q.fill('#geoText', '100 Test Hill Rd'); open_sec(q, 'addr'); q.click('#geoForm button'); q.wait_for_timeout(500); draft(q)
    try: q.wait_for_function('window.__relay.state.draft === true', timeout=8000); q.wait_for_selector('#flowTable', timeout=8000)
    except Exception: pass
    open_sec(q, 'lay'); q.select_option('#setCap', '150'); q.wait_for_timeout(200); open_sec(q, 'route'); clear(q); q.wait_for_timeout(300)
    ok('Clear after a changed setting returns the settings to the saved defaults', inputs(q)==['','4','200','50','5','1500'] and q.evaluate('window.__relay.state.settings.cap')==200 and q.evaluate('window.__relay.state.settings.lay')==None, inputs(q))
    pick(q); open_sec(q, 'addr'); q.fill('#geoText', '100 Test Hill Rd'); open_sec(q, 'addr'); q.click('#geoForm button'); q.wait_for_timeout(500); draft(q)  # a live route, so the copy check proves the route is left out
    try: q.wait_for_function('window.__relay.state.draft === true', timeout=8000)
    except Exception: pass
    to_set(q)
    with q.expect_download() as dl: q.click('#btnCopyDefaults')
    dl.value.save_as('out/copy.html'); cp = pathlib.Path('out/copy.html').read_text(encoding='utf-8')
    ok('Save a copy: file name and status', dl.value.suggested_filename=='Relay Pumping Pre-plan (my defaults).html' and q.inner_text('#defaultsStatus')=='Saved "Relay Pumping Pre-plan (my defaults).html". Look in your Downloads folder. That copy starts with: '+VSUM+'.', q.inner_text('#defaultsStatus'))
    blk = lambda t, i: re.search(r'id="' + i + r'">(.*?)</script>', t, re.S).group(1)
    ok('the copy holds the 6 chosen values in the user-defaults block', json.loads(blk(cp, 'user-defaults'))==VALS, blk(cp, 'user-defaults')[:120])
    ok('the copy keeps the hydrant-data and district-data blocks byte for byte', blk(cp, 'hydrant-data')==blk(src, 'hydrant-data') and blk(cp, 'district-data')==blk(src, 'district-data') and len(blk(cp, 'district-data'))>1000)
    ok('the copy has no map, route, or result markup', not re.search(r'class="[^"]*leaflet-container', cp) and '<div id="map"></div>' in cp and '<div id="results"><div class="empty">No route yet.</div></div>' in cp and q.evaluate('window.__relay.state.points.length')>1)
    q2 = fresh(); q2.goto(pathlib.Path('out/copy.html').resolve().as_uri()); q2.wait_for_timeout(900)
    ok('the copy opens in a new browser with the copied values and says this file', inputs(q2)==['','4','200','50','5','1500'] and q2.inner_text('#defaultsStatus')=='Defaults in use: this file ('+VSUM+').', (inputs(q2), q2.inner_text('#defaultsStatus')))
    ok('in the copy, the Reset button reads Reset to the file defaults', q2.inner_text('#btnResetDefaults')=='Reset to the file defaults', q2.inner_text('#btnResetDefaults'))
    to_set(q2)
    with q2.expect_download() as dl2: q2.click('#btnCopyDefaults')
    dl2.value.save_as('out/copy2.html')
    ok('the copy can make a further copy with the same values', json.loads(blk(pathlib.Path('out/copy2.html').read_text(encoding='utf-8'), 'user-defaults'))==VALS)
    to_set(q); q.click('#btnResetDefaults'); q.wait_for_timeout(400)
    ok('Reset removes the browser key, returns 185 PSI and 1,000 ft, and the status says built-in', q.evaluate(LS, 'yhfd-relay-defaults-v1') is None and inputs(q)==['253','5','185','20','10','1000'] and q.inner_text('#defaultsStatus')=='Defaults in use: built-in (5 inch, 185 PSI, 20 PSI, 10%, 1,000 ft).', (inputs(q), q.inner_text('#defaultsStatus')))
    # ---- v0.5 phase: hydrant count line and the reason for no draft ----
    v = fresh(); load(v)
    def cnt():
        open_sec(v, 'dist'); return (v.inner_text('#distCount'), v.get_attribute('#distCount', 'class'))
    NOTE = 'The county list is from 2015 and can be incomplete. Set the water source from a hydrant or a draft site that you know.'
    ok('count line, Yorktown Hgts FD with 3 stand-in hydrants: plural, warning form', cnt()==('County data: 3 hydrants in this district. ' + NOTE, 'note-box warn'), cnt())
    open_sec(v, 'dist'); v.select_option('#setDistrict', '226'); v.wait_for_timeout(500)
    ok('count line, a district with none of the stand-in hydrants: "no hydrants", warning form', cnt()==('County data: no hydrants in this district. ' + NOTE, 'note-box warn'), cnt())
    open_sec(v, 'dist'); v.select_option('#setDistrict', '253'); v.wait_for_timeout(500); GATE['roads'] = True
    def why(addr, road):
        GATE['addr'] = addr; GATE['road'] = road
        open_sec(v, 'addr'); v.fill('#geoText', '100 Test Hill Rd'); open_sec(v, 'addr'); v.click('#geoForm button'); v.wait_for_timeout(500); draft(v)
        try: v.wait_for_function("document.getElementById('status').textContent.includes('No auto route')", timeout=8000)
        except Exception: pass
        GATE['road'] = None; return v.inner_text('#status')
    FAR = [[C[1], C[0]+0.05], [C[1]+0.002, C[0]+0.05]]   # a road about 3.4 miles from every stand-in hydrant
    t = why((C[0]+0.05, C[1]+0.001), FAR)
    ok('no hydrant in 1 mile by road: the status gives that reason', t=='Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. No auto route: the hydrant data has no hydrant in 1 mile by road. Draw the route manually.', t)
    t = why((C[0]+0.01, C[1]), None)   # about 3,600 ft north of the stand-in road
    ok('no road within 500 ft: the status gives that reason', t=='Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. No auto route: no road is near this address. Draw the route manually.', t)
    # ---- v0.6 phase: Town of Greenburgh hydrants (code TOG) ----
    def tog_page(rows):
        f = pathlib.Path('out/test_tog.html')
        f.write_text(re.sub(r'(id="hydrant-data">).*?(</script>)', lambda m: m.group(1) + json.dumps(fake + rows) + m.group(2), src, count=1, flags=re.S), encoding='utf-8')
        w = fresh(); load(w, f); open_sec(w, 'dist'); return w
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
    x = fresh(); load(x)
    open_sec(x, 'lay')
    ok('hose list has Dual 3 inch lines after 4 inch, and the dual hint is hidden for 5 inch', x.evaluate("[...document.querySelectorAll('#setHose option')].map(o => o.value + ':' + o.textContent)")==['5:5 inch LDH','4:4 inch LDH','3:Dual 3 inch lines'] and not x.is_visible('#dualHint'))
    GATE['roads'] = True; GATE['addr'] = ADDR_SHORT; GATE['road'] = None
    open_sec(x, 'addr'); x.fill('#geoText', '100 Test Hill Rd'); open_sec(x, 'addr'); x.click('#geoForm button'); x.wait_for_timeout(500); draft(x)
    try: x.wait_for_function('window.__relay.state.draft === true', timeout=8000); x.wait_for_selector('#flowTable', timeout=8000); x.wait_for_timeout(300)
    except Exception: pass
    SHORT_TXT = 'Auto route: hydrant T-102 to 100 TEST HILL RD, YORKTOWN HEIGHTS. It follows Test Hill Rd. The driveway is shorter than 100 ft, so the auto route stops on the road. Drag S or A to move them.'
    sd = x.evaluate("(() => { const s=window.__relay.state, m=window.__relay.map; let dash=0, yellow=0; m.eachLayer(l => { if (l.options && l.options.color==='#ffd21f') { yellow++; if (l.options.dashArray) dash++; } }); return {draft:s.draft, last:s.points[s.points.length-1], dash, yellow, text:document.getElementById('status').textContent}; })()")
    ok('short driveway: the draft ends at the road point, not the address', sd['draft'] is True and abs(sd['last']['lat']-(C[0]+0.003))<1e-6 and abs(sd['last']['lng']-ADDR_SHORT[1])<1e-6, sd['last'])
    ok('  the status says the draft stops on the road (with the low hydrant caution)', sd['text']==SHORT_TXT + ' The county hydrant list can be incomplete here. A nearer hydrant can exist.', sd['text'])
    ok('  no dashed leg is drawn', sd['yellow']==1 and sd['dash']==0, (sd['yellow'], sd['dash']))
    # dual 3 inch lines
    before = x.evaluate(SNAP)['res']; open_sec(x, 'lay'); x.select_option('#setHose', '3'); x.wait_for_timeout(300)
    after = x.evaluate(SNAP)['res']; fl = x.evaluate('[500,750,1000,1250,1500,2000].map(q => window.__relay.state.results[q].fl100)')
    ok('Dual 3 inch lines: friction is 5, 11.25, 20, 31.25, 45, 80 PSI per 100 ft, the results change, and the hint shows', fl==[5,11.25,20,31.25,45,80] and after!=before and x.is_visible('#dualHint') and x.inner_text('#dualHint')=='For dual lines, enter the length of dual line that one engine lays.', (fl, before, after))
    open_sec(x, 'lay'); x.click('#layRev'); x.click('#btnCard'); x.wait_for_timeout(500)
    foot = x.inner_text('#cardBody .foot')
    ok('card footer says dual 3" lines, not 3" LDH', foot.startswith('Rules: dual 3" lines, friction loss from the chauffeur chart coefficients, 0.5 PSI') and '3" LDH' not in foot and 'chart table' not in foot and '(formula)' not in foot, foot[:60])
    x.click('#btnBack'); x.wait_for_timeout(300)
    open_sec(x, 'lay'); x.select_option('#setHose', '5'); x.wait_for_timeout(300)
    ok('the hint hides again for 5 inch', not x.is_visible('#dualHint'))
    open_sec(x, 'lay'); x.select_option('#setHose', '3'); x.wait_for_timeout(200); to_set(x); x.click('#btnSaveDefaults'); x.evaluate("localStorage.removeItem('yhfd-relay-pilot-v1')"); x.reload(); x.wait_for_timeout(900); open_sec(x, 'lay')
    ok('saved defaults accept hose 3: the select, the hint, and the summary', x.input_value('#setHose')=='3' and x.is_visible('#dualHint') and x.inner_text('#defaultsStatus')=='Defaults in use: yours (dual 3 inch, 185 PSI, 20 PSI, 10%, 1,000 ft).', x.inner_text('#defaultsStatus'))
    # drag S and A with the edit handles hidden
    open_sec(x, 'lay'); x.select_option('#setHose', '5'); to_set(x); x.click('#btnResetDefaults'); pick(x)
    open_sec(x, 'addr'); x.fill('#geoText', '100 Test Hill Rd'); open_sec(x, 'addr'); x.click('#geoForm button'); x.wait_for_timeout(500); draft(x)
    try: x.wait_for_function('window.__relay.state.draft === true', timeout=8000); x.wait_for_selector('#flowTable', timeout=8000); x.wait_for_timeout(300)
    except Exception: pass
    open_sec(x, 'route'); x.uncheck('#showHandles'); x.wait_for_timeout(200)
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
    FOUND = 'Found: 100 TEST HILL RD, YORKTOWN HEIGHTS. Check step 2. Then select Auto draw route, or Manually draw route.'
    GATE['roads'] = True; GATE['addr'] = ADDR2; GATE['road'] = None
    y = fresh(); y.set_viewport_size({'width':1280,'height':900}); road_calls = []
    y.on('request', lambda r: road_calls.append(r.url) if 'MapServer/11/query' in r.url else None)
    load(y)
    ok('the source type starts empty: first option is Select the type, the state is empty', y.evaluate("[...document.querySelectorAll('#sourceType option')].map(o => o.value + ':' + o.textContent)")==[':Select the type','Hydrant:Hydrant','Draft site:Draft site','Tanker dump site:Tanker dump site','Other:Other'] and y.input_value('#sourceType')=='' and y.evaluate('window.__relay.state.sourceType')=='')
    open_sec(y, 'route')
    ok('the trace button idle label is Manually draw route and the draft button is first in the row and enabled', y.inner_text('#btnDraw')=='Manually draw route' and y.is_enabled('#btnDraft') and y.evaluate("document.querySelector('#btnDraft').nextElementSibling.id")=='btnDraw' and y.inner_text('#btnDraft')=='Auto draw route to closest hydrant')
    open_sec(y, 'route'); y.click('#btnDraft')
    ok('draft button with no address and no type: the type message comes first (v0.16 order: district, type, lay, address)', y.inner_text('#status')=='Select the water source type in step 2.', y.inner_text('#status'))
    open_sec(y, 'addr'); y.fill('#geoText', '100 Test Hill Rd'); open_sec(y, 'addr'); y.click('#geoForm button'); y.wait_for_function("document.getElementById('status').textContent.startsWith('Found')", timeout=8000); y.wait_for_timeout(700)
    ok('Go alone: no road request, no route, the status is the exact Found text', not road_calls and y.evaluate('window.__relay.state.points.length')==0 and not y.evaluate('window.__relay.state.draft') and y.inner_text('#status')==FOUND, (len(road_calls), y.inner_text('#status')))
    pin = y.evaluate("(() => { const m=window.__relay.map, e=document.querySelector('.pin'), r=e.getBoundingClientRect(), b=document.getElementById('map').getBoundingClientRect(); const c=m.latLngToContainerPoint([%f,%f]); return {n:document.querySelectorAll('.pin').length, dx:Math.abs(r.left+r.width/2-b.left-c.x), dy:Math.abs(r.top+r.height-b.top-c.y)}; })()" % ADDR2)
    ok('Go alone: one pin is on the map at the address, and the plan name is the address', pin['n']==1 and pin['dx']<14 and pin['dy']<30 and y.input_value('#planName')=='100 TEST HILL RD, YORKTOWN HEIGHTS', pin)
    y.set_viewport_size({'width':1280,'height':1900}); y.wait_for_timeout(300); y.locator('#side').screenshot(path='out/v10-sidebar.png'); y.set_viewport_size({'width':1280,'height':900}); y.wait_for_timeout(300)
    open_sec(y, 'route'); y.click('#btnDraft'); ok('draft button with no type: Select the water source type in step 2.', y.inner_text('#status')=='Select the water source type in step 2.', y.inner_text('#status'))
    open_sec(y, 'lay'); y.select_option('#sourceType', 'Hydrant'); open_sec(y, 'route'); y.click('#btnDraft'); ok('draft button with no lay: Select Reverse lay or Forward lay in step 2.', y.inner_text('#status')=='Select Reverse lay or Forward lay in step 2.' and not road_calls, y.inner_text('#status'))
    open_sec(y, 'lay'); y.click('#layRev'); open_sec(y, 'route'); y.click('#btnDraft')
    try: y.wait_for_function('window.__relay.state.draft === true', timeout=8000); y.wait_for_selector('#flowTable', timeout=8000); y.wait_for_timeout(300)
    except Exception: pass
    d9 = y.evaluate("(() => { const s=window.__relay.state; return {n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, type:s.sourceType, text:document.getElementById('status').textContent}; })()")
    ok('hydrant draft after the button equals the old draft: hydrant T-102 first, the address last, the same status text', d9['hyd'] and d9['hyd']['num']=='T-102' and d9['n']>=3 and abs(d9['first']['lat']-(C[0]+0.001))<1e-9 and abs(d9['first']['lng']-(C[1]+0.002))<1e-9 and abs(d9['last']['lat']-ADDR2[0])<1e-9 and abs(d9['last']['lng']-ADDR2[1])<1e-9 and d9['text']=='Auto route: hydrant T-102 to 100 TEST HILL RD, YORKTOWN HEIGHTS. It follows Test Hill Rd. Drag a point to match the driveway. Click the line to add a point. The county hydrant list can be incomplete here. A nearer hydrant can exist.', d9)
    y.screenshot(path='out/v09-after-draft.png')
    open_sec(y, 'route'); y.click('#btnDraft'); ok('draft button with a route: Clear the route first. The auto route needs an empty route.', y.inner_text('#status')=='Clear the route first. The auto route needs an empty route.' and y.evaluate('window.__relay.state.points.length')==d9['n'], y.inner_text('#status'))
    open_sec(y, 'route'); clear(y); y.wait_for_timeout(300)
    ok('Clear empties the source type, the lay, and the pin; the draft then asks for the address', y.input_value('#sourceType')=='' and y.evaluate('window.__relay.state.sourceType')=='' and y.evaluate('window.__relay.state.settings.lay')==None and y.locator('.pin').count()==0, y.input_value('#sourceType'))
    open_sec(y, 'route'); y.click('#btnDraft'); ok('after Clear the draft button says Select the fire district first.', y.inner_text('#status')=='Select the fire district first.', y.inner_text('#status'))
    pick(y); open_sec(y, 'lay'); y.select_option('#sourceType', 'Hydrant'); y.click('#layRev'); open_sec(y, 'route'); y.click('#btnDraft')
    ok('draft button with no address (district, type, lay chosen): Find the address first.', y.inner_text('#status')=='Find the address first.', y.inner_text('#status'))
    # a non-hydrant type: the page asks for a click on the map, then drafts from the click
    open_sec(y, 'addr'); y.fill('#geoText', '100 Test Hill Rd'); open_sec(y, 'addr'); y.click('#geoForm button'); y.wait_for_function("document.getElementById('status').textContent.startsWith('Found')", timeout=8000)
    open_sec(y, 'lay'); y.select_option('#sourceType', 'Draft site'); open_sec(y, 'lay'); y.click('#layFwd'); road_calls.clear(); open_sec(y, 'route'); y.click('#btnDraft')
    ok('Draft site: the status asks for a click on the water source, and no road request is made yet', y.inner_text('#status')=='Click the water source on the map.' and not road_calls and y.evaluate('window.__relay.state.points.length')==0, y.inner_text('#status'))
    SRC = (C[0]+0.00005, C[1]+0.001)
    y.evaluate('window.__relay.map.fire("click",{latlng:{lat:%f,lng:%f}})' % SRC)
    try: y.wait_for_function('window.__relay.state.draft === true', timeout=8000); y.wait_for_selector('#flowTable', timeout=8000); y.wait_for_timeout(300)
    except Exception: pass
    d9 = y.evaluate("(() => { const s=window.__relay.state; return {n:s.points.length, first:s.points[0], last:s.points[s.points.length-1], hyd:s.sourceHydrant, type:s.sourceType, text:document.getElementById('status').textContent}; })()")
    ok('Draft site: the click is the first point, the address is last, the source hydrant stays null, the type stays', d9['hyd'] is None and d9['type']=='Draft site' and d9['n']>=3 and abs(d9['first']['lat']-SRC[0])<1e-9 and abs(d9['first']['lng']-SRC[1])<1e-9 and abs(d9['last']['lat']-ADDR2[0])<1e-9, d9)
    ok('  the status starts: Draft route: draft site to <address>. It follows Test Hill Rd.', d9['text'].startswith('Auto route: draft site to 100 TEST HILL RD, YORKTOWN HEIGHTS. It follows Test Hill Rd.') and 'county hydrant list' not in d9['text'], d9['text'])
    # a far hydrant: a winding road of about 11,000 ft joins the only hydrant to the address
    KLAT = 20902260*3.141592653589793/180
    import math
    def LL9(xf, yf): return [C[1]+xf/(KLAT*math.cos(C[0]*math.pi/180)), C[0]+yf/KLAT]
    FARROAD = [LL9(0,0), LL9(4500,0), LL9(4500,2000), LL9(0,2000)]
    f9 = pathlib.Path('out/test_far.html')
    f9.write_text(re.sub(r'(id="hydrant-data">).*?(</script>)', lambda m: m.group(1) + json.dumps([[FARROAD[0][0], FARROAD[0][1], 'F-1', 'YKTWN']]) + m.group(2), src, count=1, flags=re.S), encoding='utf-8')
    w9 = fresh(); load(w9, f9)
    GATE['addr'] = (FARROAD[3][1], FARROAD[3][0]); GATE['road'] = FARROAD
    open_sec(w9, 'addr'); w9.fill('#geoText', '100 Test Hill Rd'); open_sec(w9, 'addr'); w9.click('#geoForm button'); w9.wait_for_timeout(700); draft(w9)
    try: w9.wait_for_function("document.getElementById('status').textContent.startsWith('No auto route')", timeout=8000)
    except Exception: pass
    GATE['addr'] = ADDR2; GATE['road'] = None
    ok('a hydrant more than 1 mile away by road: the exact no-draft status and no route', w9.inner_text('#status')=='No auto route: the nearest hydrant by road is F-1, about 11,000 ft away. That is more than 1 mile. Select a different water source type, or draw the route manually.' and w9.evaluate('window.__relay.state.points.length')==0 and not w9.evaluate('window.__relay.state.draft'), w9.inner_text('#status'))
    # a clicked source more than 1 mile away by road
    open_sec(w9, 'lay'); w9.select_option('#sourceType', 'Other'); open_sec(w9, 'route'); w9.click('#btnDraft'); GATE['addr'] = (FARROAD[3][1], FARROAD[3][0]); GATE['road'] = FARROAD
    w9.evaluate('window.__relay.map.fire("click",{latlng:{lat:%f,lng:%f}})' % (FARROAD[0][1], FARROAD[0][0]))
    try: w9.wait_for_function("document.getElementById('status').textContent.startsWith('No auto route')", timeout=8000)
    except Exception: pass
    GATE['addr'] = ADDR2; GATE['road'] = None
    ok('a clicked source more than 1 mile away by road: the exact no-draft status and no route', w9.inner_text('#status')=='No auto route: the water source is about 11,000 ft away by road. That is more than 1 mile. Draw the route manually.' and w9.evaluate('window.__relay.state.points.length')==0, w9.inner_text('#status'))
    # a card with no source type prints Not selected
    GATE['roads'] = False
    k9 = fresh(); load(k9)
    kb = k9.locator('#map').bounding_box(); kx, ky = kb['x']+kb['width']/2, kb['y']+kb['height']/2
    open_sec(k9, 'lay'); k9.select_option('#sourceType', 'Other'); k9.click('#layRev'); open_sec(k9, 'route'); named(k9); k9.click('#btnDraw')
    for dx,dy in ((220,120),(300,170)): k9.mouse.click(kx+dx, ky+dy); k9.wait_for_timeout(100)
    open_sec(k9, 'route'); k9.click('#btnFinish'); k9.wait_for_selector('#flowTable', timeout=8000); open_sec(k9, 'lay'); k9.select_option('#sourceType', ''); k9.click('#btnCard'); k9.wait_for_timeout(500)
    ok('a card with no source type: the Water source fact reads Not selected', k9.evaluate('window.__relay.state.sourceType')=='' and k9.inner_text('#cardHead .facts4 div:nth-child(1) b')=='Not selected' and k9.inner_text('#cardHead .facts4 div:nth-child(1) span').lower()=='water source', k9.inner_text('#cardHead .facts4 div:nth-child(1)'))
    # order of the sidebar sections
    heads = y.evaluate("[...document.querySelectorAll('#side > .sec')].map(s => s.querySelector('h2, .su i').textContent)")
    ok('sidebar sections are in the accepted order (v0.16: the four setup sections show their line label)', heads==['District','1. Address','2. Lay','3. Route','4. Read the result','Keep the plan'], heads)
    inside = y.evaluate("(() => { const sec = id => document.getElementById(id).closest('.sec').querySelector('h2, .su i').textContent; return {six:['sourceType','layRev','setHose','setHosePer','setCap','setRes','setSlack'].map(sec), btns:['btnDraft','btnDraw','btnUndo','btnFinish','btnClear'].map(sec), status:document.getElementById('status').previousElementSibling.dataset.k + '>' + document.getElementById('status').nextElementSibling.querySelector('h2').textContent, res:sec('results'), defs:['btnSaveDefaults','btnResetDefaults','btnCopyDefaults','defaultsStatus'].map(sec), name:sec('planName')}; })()")
    ok('the settings are inside step 2 (before step 3), the buttons in step 3, the status block between step 3 and step 4, the result in step 4, My defaults in the Settings view', set(inside['six'])=={'2. Lay'} and set(inside['btns'])=={'3. Route'} and inside['status']=='route>4. Read the result' and inside['res']=='4. Read the result' and set(inside['defs'])=={'My defaults'} and inside['name']=='1. Address', inside)
    ok('the five settings sit in three rows in the mockup order', y.evaluate("[...document.querySelectorAll('#setHose,#setHosePer,#setCap,#setRes,#setSlack')].map(e => e.id).join()")=='setHose,setHosePer,setCap,setRes,setSlack' and y.evaluate("[...document.querySelectorAll('#side > .sec')][2].querySelectorAll('.row').length")==3)
    ok('no page errors in the v0.9 phase', not [e for e in errors[e9:] if 'Failed to load resource' not in e], errors[e9:][:3])
    # ---- v0.10 phase: one friction rule, PDP rounds up, six defaults. Old saved values with basis must load. ----
    e10 = len(errors)
    GATE['roads'] = False; GATE['addr'] = C
    t10 = fresh(); load(t10)
    ok('v0.10: the Friction loss values field is gone and the page says Pilot v0.15', t10.locator('#setBasis').count()==0 and 'Friction loss values' not in t10.text_content('#side') and 'Pilot v0.23' in t10.inner_text('.brand'))
    ok('v0.19: the name is Relay Pumping Pre-plan in the tab and the header, and the page text does not say YHFD', t10.title()=='Relay Pumping Pre-plan' and t10.inner_text('.brand h1')=='Relay Pumping Pre-plan' and 'YHFD' not in t10.evaluate("document.getElementById('side').textContent + document.getElementById('cardHead').textContent"), t10.title())
    ok('v0.16: the status line lists five values (no district)', t10.inner_text('#defaultsStatus')=='Defaults in use: built-in (5 inch, 185 PSI, 20 PSI, 10%, 1,000 ft).' and len(t10.inner_text('#defaultsStatus').split('(')[1].split(', '))==5, t10.inner_text('#defaultsStatus'))
    to_set(t10); rules = t10.inner_text('#setView ul')
    ok('v0.10: the rules list states the one friction rule and the round-up rule', 'one rule' in rules and '0.08' in rules and 'rounds up to the next 5 PSI' in rules and 'chart table' not in rules.lower() and 'formula option' not in rules.lower(), rules[:200])
    PLAN = {'name':'Old plan','notes':'','sourceType':'Hydrant','sourceHydrant':None,'flow':750,'manual':{},
            'points':[{'lat':C[0],'lng':C[1]},{'lat':C[0]+0.004,'lng':C[1]+0.002}],
            'settings':{'district':253,'hose':5,'basis':'chart','cap':185,'residual':20,'slack':10,'hosePerEngine':1000,'lay':'reverse'}}
    t10.set_input_files('#fileOpen', files=[{'name':'old.json','mimeType':'application/json','buffer':json.dumps(PLAN).encode()}])
    try: t10.wait_for_selector('#flowTable', timeout=8000)
    except Exception: pass
    ok('v0.10: an old plan file with basis chart loads and gives 4.5 PSI at 750 GPM', t10.evaluate('window.__relay.state.results[750].fl100')==4.5 and t10.evaluate('window.__relay.state.points.length')==2 and 'could not open' not in t10.inner_text('#status'), t10.inner_text('#status'))
    for bs in ('chart','formula'):
        PLAN['settings']['basis'] = bs
        t10.evaluate("p => localStorage.setItem('yhfd-relay-pilot-v1', JSON.stringify(p))", PLAN)
        t10.evaluate("""d => localStorage.setItem('yhfd-relay-defaults-v1', JSON.stringify(d))""", {'district':226,'hose':4,'basis':bs,'cap':200,'residual':50,'slack':5,'hosePerEngine':1500})
        t10.reload(); t10.wait_for_timeout(900)
        ok('v0.10: an old autosave and an old saved default with basis '+bs+' load and the five values apply (the old district in the default is ignored)', t10.evaluate('window.__relay.state.points.length')==2 and t10.input_value('#setCap')=='185' and t10.inner_text('#defaultsStatus')=='Defaults in use: yours (4 inch, 200 PSI, 50 PSI, 5%, 1,500 ft).' and t10.evaluate('window.__relay.state.settings.district')==253, t10.inner_text('#defaultsStatus'))
    # ---- v0.10 card file name: the browser takes the PDF name from the page title ----
    t11 = fresh(); load(t11)
    GATE['roads'] = False; GATE['addr'] = C
    today = datetime.date.today().strftime('%y-%m-%d'); NAME = 'window.__relay.cardFileName()'
    open_sec(t11, 'addr'); t11.fill('#geoText', '100 Test Hill Rd'); open_sec(t11, 'addr'); t11.click('#geoForm button'); t11.wait_for_timeout(600)
    nm = t11.evaluate(NAME)
    ok('card name: the date part is today as YY-MM-DD', re.match(r'^\d{2}-\d{2}-\d{2}_', nm) is not None and nm.startswith(today + '_'), nm)
    ok('card name: a plan name equal to the address shows one time', nm == today + '_100 TEST HILL RD, YORKTOWN HEIGHTS', nm)
    open_sec(t11, 'addr'); t11.fill('#planName', '  station 1 drill '); ok('card name: a different plan name comes first, then the address', t11.evaluate(NAME) == today + '_station 1 drill_100 TEST HILL RD, YORKTOWN HEIGHTS', t11.evaluate(NAME))
    open_sec(t11, 'addr'); t11.fill('#planName', '100 test hill rd, yorktown heights'); ok('card name: the equal check ignores case and spaces', t11.evaluate(NAME) == today + '_100 TEST HILL RD, YORKTOWN HEIGHTS', t11.evaluate(NAME))
    open_sec(t11, 'addr'); t11.fill('#planName', 'Drill A/B: *north?  "x" <y>|z'); nm = t11.evaluate(NAME)
    ok('card name: characters a file name cannot hold become one space', nm == today + '_Drill A B north x y z_100 TEST HILL RD, YORKTOWN HEIGHTS', nm)
    open_sec(t11, 'addr'); t11.fill('#planName', ''); ok('card name: an empty plan name gives the address only', t11.evaluate(NAME) == today + '_100 TEST HILL RD, YORKTOWN HEIGHTS', t11.evaluate(NAME))
    open_sec(t11, 'addr'); t11.fill('#planName', 'Drill A'); t11.evaluate("document.body.classList.add('card')")
    t11.evaluate("window.__t0 = document.title; window.dispatchEvent(new Event('beforeprint'))")
    ok('print title: beforeprint in card mode sets the card name', t11.evaluate('document.title') == today + '_Drill A_100 TEST HILL RD, YORKTOWN HEIGHTS', t11.evaluate('document.title'))
    t11.evaluate("window.dispatchEvent(new Event('afterprint'))")
    ok('print title: afterprint puts the old title back', t11.evaluate('document.title == window.__t0'), t11.evaluate('document.title'))
    t11.evaluate("document.body.classList.remove('card'); window.dispatchEvent(new Event('beforeprint'))")
    ok('print title: beforeprint outside card mode does not change the title', t11.evaluate('document.title == window.__t0'), t11.evaluate('document.title'))
    t11.evaluate("window.dispatchEvent(new Event('afterprint'))")
    PLAN2 = dict(PLAN, name='Drill A', settings=dict(PLAN['settings'], basis='chart'))  # Save needs a route, so open one, then search again
    t11.set_input_files('#fileOpen', files=[{'name':'r.json','mimeType':'application/json','buffer':json.dumps(PLAN2).encode()}]); t11.wait_for_timeout(600)
    open_sec(t11, 'addr'); t11.fill('#geoText', '100 Test Hill Rd'); open_sec(t11, 'addr'); t11.click('#geoForm button'); t11.wait_for_timeout(600)
    with t11.expect_download() as dl: t11.click('#btnSave')
    saved = json.loads(pathlib.Path(dl.value.path()).read_text())
    ok('plan file keeps the found address', saved.get('addr', {}).get('label') == '100 TEST HILL RD, YORKTOWN HEIGHTS' and abs(saved['addr']['lat'] - C[0]) < 1e-6, saved.get('addr'))
    open_sec(t11, 'route'); clear(t11); t11.wait_for_timeout(300)
    ok('card name: Clear forgets the address and its pin', t11.evaluate(NAME) == today + '_Drill A' and t11.evaluate('window.__relay.found()') is None and t11.locator('.pin').count() == 0, t11.evaluate(NAME))
    open_sec(t11, 'addr'); t11.fill('#planName', ''); ok('card name: with neither plan name nor address it is the date and Relay pre-plan', t11.evaluate(NAME) == today + '_Relay pre-plan', t11.evaluate(NAME))
    t11.set_input_files('#fileOpen', files=[{'name':'p.json','mimeType':'application/json','buffer':json.dumps(saved).encode()}]); t11.wait_for_timeout(600)
    ok('plan file round trip: the card name holds the address again and the pin shows', t11.evaluate(NAME) == today + '_Drill A_100 TEST HILL RD, YORKTOWN HEIGHTS' and t11.locator('.pin').count() == 1, t11.evaluate(NAME))
    t11.reload(); t11.wait_for_timeout(900)
    ok('autosave keeps the address after a reload', t11.evaluate(NAME).endswith('_100 TEST HILL RD, YORKTOWN HEIGHTS') and t11.locator('.pin').count() == 1, t11.evaluate(NAME))
    del saved['addr']; t11.set_input_files('#fileOpen', files=[{'name':'q.json','mimeType':'application/json','buffer':json.dumps(saved).encode()}]); t11.wait_for_timeout(600)
    ok('an old plan file without an address loads with no error and no pin', t11.evaluate(NAME) == today + '_Drill A' and t11.locator('.pin').count() == 0 and 'could not open' not in t11.inner_text('#status'), t11.inner_text('#status'))
    ok('no page errors in the v0.10 phase', not [e for e in errors[e10:] if 'Failed to load resource' not in e], errors[e10:][:3])
    GATE['addr'] = C; GATE['roads'] = False
    # ---- v0.13 phase: the setup folds when a result shows, the facts row, the engines list, the phone scroll ----
    e13 = len(errors)
    GATE['roads'] = True; GATE['addr'] = ADDR2; GATE['road'] = None
    f13 = fresh(); load(f13)
    SEC = "[...document.querySelectorAll('#side .sec[data-k]')]"
    ok('v0.16: before a route the four lines show and all four sections are closed (controls hidden)', f13.locator('#side .su:visible').count()==4 and f13.evaluate(SEC+".every(s => !s.querySelector('.bd').classList.contains('op'))") and not f13.is_visible('#setDistrict') and not f13.is_visible('#layRev'))
    open_sec(f13, 'addr'); f13.fill('#geoText', '100 Test Hill Rd'); f13.click('#geoForm button'); f13.wait_for_timeout(600); draft(f13); f13.wait_for_selector('#flowTable', timeout=8000); f13.wait_for_timeout(300)
    rows = f13.evaluate("[...document.querySelectorAll('#side .su')].map(b => [b.querySelector('i').textContent, b.querySelector('span').textContent, b.querySelector('u').textContent, b.getAttribute('aria-expanded'), b.offsetParent !== null])")
    ok('v0.13: after a draft four summary rows show with the expected texts', rows==[['District','Yorktown Hgts FD','Change','false',True],['1. Address','100 TEST HILL RD, YORKTOWN HEIGHTS','Change','false',True],['2. Lay','Hydrant \u00b7 Reverse \u00b7 5 inch \u00b7 185 PSI','Change','false',True],['3. Route','Auto route from hydrant T-102','Edit','false',True]], rows)
    ok('v0.13: the section controls are hidden after a draft', not any(f13.is_visible(c) for c in ('#setDistrict','#geoText','#layRev','#btnClear')))
    f13.click('#side .su >> nth=2')
    ok('v0.13: a click on a row opens that section, sets aria-expanded, and reads Close', f13.is_visible('#layRev') and f13.is_visible('#setCap') and not f13.is_visible('#setDistrict') and f13.locator('#side .su >> nth=2').get_attribute('aria-expanded')=='true' and f13.inner_text('#side .su >> nth=2 >> u')=='Close')
    f13.select_option('#setCap', '150'); f13.wait_for_timeout(300)
    ok('v0.13: a setting change keeps the section open and updates its summary', f13.is_visible('#setCap') and f13.inner_text('#side .su >> nth=2 >> span').endswith('150 PSI'))
    f13.click('#side .su >> nth=2'); f13.wait_for_timeout(300)
    ok('v0.13: a second click folds the section again', not f13.is_visible('#layRev') and f13.locator('#side .su >> nth=2').get_attribute('aria-expanded')=='false')
    f13.click('#side .su >> nth=3'); clear(f13); f13.wait_for_timeout(300)
    ok('v0.16: Clear closes all four sections, keeps the four lines, and the District line reads Select district', f13.locator('#side .su:visible').count()==4 and f13.evaluate(SEC+".every(s => !s.querySelector('.bd').classList.contains('op'))") and not f13.is_visible('#layRev') and f13.inner_text('#side .su >> nth=0 >> span')=='Select district')
    pick(f13); open_sec(f13, 'addr'); f13.fill('#geoText', '100 Test Hill Rd'); f13.click('#geoForm button'); f13.wait_for_timeout(600); draft(f13); f13.wait_for_selector('#flowTable', timeout=8000)
    en = f13.evaluate("""(() => { const r = window.__relay.state.results[window.__relay.state.flow], pd = [...document.querySelectorAll('#results .en .pd b')]; const sz = e => parseFloat(getComputedStyle(e).fontSize);
      const all = [...document.querySelectorAll('#side *')].filter(e => e.offsetParent !== null && e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(sz);
      return {rows: document.querySelectorAll('#results .en').length, engines: r.segs.length + 1, pdps: pd.slice(0, -1).map(e => +e.textContent), want: r.segs.map(g => g.pdp), sizes: pd.map(sz), weights: pd.map(e => getComputedStyle(e).fontWeight), max: Math.max(...all), intake: pd[pd.length-1].textContent, lines: [...document.querySelectorAll('#results .en small')].map(e => e.textContent)}; })()""")
    ok('v0.13: the engines list has one row per engine with its PDP', en['rows']==en['engines'] and en['pdps']==en['want'] and en['intake'].endswith(' PSI') and en['lines'][0].startswith('at the source') and ' lays ' in en['lines'][1], en)
    ok('v0.16: every PDP number and the Attack intake are 14 px bold', all(z==14 for z in en['sizes']) and en['weights']==['700']*len(en['sizes']), en)
    ph = fresh(); ph.set_viewport_size({'width':390,'height':800}); load(ph)
    GATE['addr'] = ADDR2; open_sec(ph, 'addr'); ph.fill('#geoText', '100 Test Hill Rd'); ph.click('#geoForm button'); ph.wait_for_timeout(600); draft(ph); ph.wait_for_selector('#flowTable', timeout=8000); ph.wait_for_timeout(500)
    box = ph.evaluate("(() => { const r = [...document.querySelectorAll('#side h2')].filter(h => h.textContent.startsWith('4.'))[0].getBoundingClientRect(); return [r.top, r.bottom, innerHeight]; })()")
    ok('v0.13: on a 390 px screen the result heading is in view after a draft', 0 <= box[0] and box[1] <= box[2], box)
    ph.close()
    # ---- v0.14 phase: Clear asks first, larger handles, click a point to remove it, flow rows from the keyboard ----
    e14 = len(errors)
    v = fresh(); v.set_viewport_size({'width':1280,'height':800}); load(v)
    GATE['addr'] = ADDR2; open_sec(v, 'addr'); v.fill('#geoText', '100 Test Hill Rd'); v.click('#geoForm button'); v.wait_for_timeout(600); draft(v); v.wait_for_selector('#flowTable', timeout=8000); v.wait_for_timeout(500)
    PTS = 'window.__relay.state.points.length'; BOX = "document.getElementById('clearBox').hidden"
    open_sec(v, 'route'); v.click('#btnClear')
    ok('v0.14: Clear shows the box and keeps the route; focus is on Keep route', v.evaluate(BOX) is False and v.evaluate(PTS)>=3 and v.evaluate('document.activeElement.id')=='btnClearNo' and v.get_attribute('#clearBox','role')=='group' and v.get_attribute('#clearBox','aria-label')=='Clear the route?' and v.inner_text('#clearBox').startswith('Clear the route? The settings go back to your defaults.'), v.inner_text('#clearBox'))
    v.click('#btnClearNo')
    ok('v0.14: Keep route hides the box, keeps the route, and returns focus to Clear', v.evaluate(BOX) is True and v.evaluate(PTS)>=3 and v.evaluate('document.activeElement.id')=='btnClear')
    v.click('#btnClear'); v.keyboard.press('Escape')
    ok('v0.14: Escape in the box acts as Keep route', v.evaluate(BOX) is True and v.evaluate(PTS)>=3 and v.evaluate('document.activeElement.id')=='btnClear')
    v.click('#btnClear'); v.click('#btnClearYes'); v.wait_for_timeout(300)
    ok('v0.14: Clear route clears the route and hides the box', v.evaluate(BOX) is True and v.evaluate(PTS)==0)
    pick(v); open_sec(v, 'addr'); v.fill('#geoText', '100 Test Hill Rd'); v.click('#geoForm button'); v.wait_for_timeout(600); draft(v); v.wait_for_selector('#flowTable', timeout=8000); v.wait_for_timeout(500)
    sz = v.evaluate("[getComputedStyle(document.querySelector('.vx')).width, getComputedStyle(document.querySelector('.vx')).height, getComputedStyle(document.querySelector('.mid')).width, getComputedStyle(document.querySelector('.mid')).height]")
    ok('v0.16: a point handle is 12 px and a middle handle is 14 px', sz==['12px','12px','14px','14px'], sz)
    cen = v.evaluate("(() => { const m = window.__relay.map, r = m.getContainer().getBoundingClientRect(); return window.__relay.state.points.map((p, i) => { const q = m.latLngToContainerPoint(p), b = document.querySelectorAll('.vx')[i].getBoundingClientRect(); return Math.hypot(b.x + b.width/2 - r.x - q.x, b.y + b.height/2 - r.y - q.y); }); })()")
    ok('v0.14: each point handle is centred on its route point within 1 px', len(cen)>=3 and max(cen)<1, cen)
    n = v.evaluate(PTS); v.locator('.vx').nth(1).click(); v.wait_for_timeout(300)
    pt = v.inner_text('.leaflet-popup-content')
    ok('v0.14: a click on a point opens a popup with the point number and Remove point; no point is added', pt.startswith('Point 2 of %d' % n) and 'Remove point' in pt and v.evaluate(PTS)==n, pt)
    v.click('.leaflet-popup-content button'); v.wait_for_timeout(600)
    ok('v0.14: Remove point removes that point, closes the popup, and the result recomputes', v.evaluate(PTS)==n-1 and v.locator('.leaflet-popup').count()==0 and v.evaluate('window.__relay.state.results[500].relays.length>=0') and v.is_visible('#flowTable'))
    v.locator('.vx').nth(1).click(button='right'); v.wait_for_timeout(500)
    ok('v0.14: right-click still removes a point', v.evaluate(PTS)==n-2, v.evaluate(PTS))
    bx = v.locator('.vx').nth(1).bounding_box(); v.mouse.move(bx['x']+9, bx['y']+9); v.mouse.down(); v.mouse.move(bx['x']+60, bx['y']+40, steps=8); v.mouse.up(); v.wait_for_timeout(500)
    ok('v0.14: a drag opens no popup', v.locator('.leaflet-popup').count()==0 and v.evaluate(PTS)==n-2)
    while v.evaluate(PTS)>2: v.locator('.vx').nth(1).click(button='right'); v.wait_for_timeout(400)
    v.locator('.vx').nth(1).dispatch_event('click'); v.wait_for_timeout(300)  # the attack engine icon covers this handle
    ok('v0.14: with 2 points the popup says A route keeps 2 points. and has no button', v.inner_text('.leaflet-popup-content')=='A route keeps 2 points.' and v.locator('.leaflet-popup-content button').count()==0 and v.evaluate(PTS)==2, v.inner_text('.leaflet-popup-content'))
    v.close()
    k14 = fresh(); k14.set_viewport_size({'width':1280,'height':800}); load(k14)
    GATE['addr'] = ADDR2; open_sec(k14, 'addr'); k14.fill('#geoText', '100 Test Hill Rd'); k14.click('#geoForm button'); k14.wait_for_timeout(600); draft(k14); k14.wait_for_selector('#flowTable', timeout=8000); k14.wait_for_timeout(500)
    ROWS = "[...document.querySelectorAll('#flowTable tbody tr')]"
    ok('v0.14: every flow row has tabindex 0 and the selected one has aria-selected true', k14.evaluate(ROWS+".every(r => r.tabIndex === 0)") and k14.evaluate(ROWS+".map(r => r.getAttribute('aria-selected')).join()")==('true,'+','.join(['false']*5) if k14.evaluate('window.__relay.state.flow')==500 else k14.evaluate(ROWS+".map(r => String(r.classList.contains('sel'))).join()")))
    for key, q in (('Enter', 1000), ('Space', 1500)):
        k14.focus('#flowTable tbody tr[data-q="%d"]' % q); y0 = k14.evaluate('scrollY'); k14.keyboard.press(key); k14.wait_for_timeout(200)
        st = k14.evaluate("({flow: window.__relay.state.flow, focus: document.activeElement.getAttribute('data-q'), aria: " + ROWS + ".map(r => r.getAttribute('aria-selected') + ':' + r.getAttribute('data-q')).filter(x => x.startsWith('true')), y: scrollY})")
        ok('v0.14: %s on a focused row selects it, keeps focus on it, and sets aria-selected' % key, st['flow']==q and st['focus']==str(q) and st['aria']==['true:%d' % q] and st['y']==y0, st)
    ok('v0.14: the result holds no pressure demand text', 'pressure demand' not in k14.inner_text('#results').lower() and k14.locator('#results .budget').count()==0)
    k14.close()
    # ---- v0.15 phase: the lay table is short, the sidebar starts at the top, the layer list is closed on a phone ----
    e15 = len(errors); GATE['addr'] = ADDR2
    w = fresh(); w.set_viewport_size({'width':1440,'height':900}); load(w)
    ok('v0.15: at 1440 px the layer control is open at load', 'leaflet-control-layers-expanded' in w.get_attribute('.leaflet-control-layers', 'class'))
    open_sec(w, 'addr'); w.fill('#geoText', '100 Test Hill Rd'); w.click('#geoForm button'); w.wait_for_timeout(600); draft(w); w.wait_for_selector('#flowTable', timeout=8000); w.wait_for_timeout(500)
    ok('v0.15: at 1440 px the sidebar scrollTop is 0 after a road draft', w.evaluate("document.getElementById('side').scrollTop")==0, w.evaluate("document.getElementById('side').scrollTop"))
    ok('v0.15: no element uses the class fact or facts', w.evaluate("document.querySelectorAll('.fact, .facts').length")==0)
    w.close()
    n15 = fresh(); n15.set_viewport_size({'width':390,'height':800}); load(n15)
    ok('v0.15: at 390 px the layer control starts collapsed', 'leaflet-control-layers-expanded' not in n15.get_attribute('.leaflet-control-layers', 'class'))
    n15.close()
    # ---- v0.16 phase: no district at the start, required choices, one open section, motion ----
    e16 = len(errors); GATE['roads'] = False; GATE['addr'] = ADDR2
    LINES = "[...document.querySelectorAll('#side .su')].map(b => ({k:b.parentNode.dataset.k, vis:b.getBoundingClientRect().height>0, label:b.children[0].textContent, text:b.children[1].textContent, act:b.children[2].textContent, req:b.classList.contains('req'), exp:b.getAttribute('aria-expanded')}))"
    OPEN = "[...document.querySelectorAll('#side .sec[data-k]')].filter(s => s.querySelector('.bd').classList.contains('op')).map(s => s.dataset.k)"
    FORCE = "({open:" + OPEN + ", focus:document.activeElement.id, status:document.getElementById('status').textContent, cls:document.getElementById('status').className})"
    COL = "id => { const c = getComputedStyle(document.getElementById(id)); return [c.borderTopColor, c.backgroundColor]; }"
    n16 = fresh(); n16.goto(test_html.resolve().as_uri()); n16.wait_for_timeout(700)
    ln = n16.evaluate(LINES)
    ok('v0.16 item 1: no district at the start (Select district, empty value, state none, count note hidden, map shows the whole county)', n16.input_value('#setDistrict')=='' and n16.evaluate("document.querySelector('#setDistrict').selectedOptions[0].textContent")=='Select district' and n16.evaluate('window.__relay.state.settings.district')==None and n16.evaluate("document.getElementById('distCount').hidden") and n16.evaluate('window.__relay.map.getZoom()')<=11, n16.evaluate('window.__relay.map.getZoom()'))
    ok('v0.16 items 2 and 5: four lines show with no route, all closed; all four are required (v0.21): District and Lay read Select, Address Enter, Route Make', [(l['label'], l['vis'], l['text'], l['act'], l['exp']) for l in ln]==[('District',True,'Select district','Select','false'),('1. Address',True,'Enter address','Enter','false'),('2. Lay',True,'Select source type and lay','Select','false'),('3. Route',True,'Make a route','Make','false')] and [l['req'] for l in ln]==[True,True,True,True], ln)
    ok('v0.16 item 5: a missing line has the light red background and red bold text', n16.evaluate("(() => { const b=document.querySelector('#side .su.req'), c=getComputedStyle(b), t=getComputedStyle(b.children[1]); return [c.backgroundColor, t.color, t.fontWeight]; })()")==['rgb(251, 236, 235)','rgb(179, 38, 30)','600'])
    st = n16.evaluate("(() => { const s=document.getElementById('status'), r=s.getBoundingClientRect(), l=[...document.querySelectorAll('#side .su')][3].getBoundingClientRect(); return {vis:r.height>0 && getComputedStyle(s).visibility=='visible', inSec:!!s.closest('.sec'), below:r.top>=l.bottom-1, text:s.textContent}; })()")
    ok('v0.16 item 8: the status block shows with every section closed, outside any section, under the fourth line', st['vis'] and not st['inSec'] and st['below'] and st['text']!='', st)
    n16.evaluate("document.activeElement.blur(); document.querySelectorAll('#side .su')[3].focus()")
    tabs = []
    for _ in range(8): n16.keyboard.press('Tab'); tabs.append(n16.evaluate("(() => { const a=document.activeElement; return a.closest('.bd') ? 'in-section:' + a.id : (a.id || a.tagName); })()"))
    ok('v0.16 item 3: with every section closed, Tab never lands on a control inside a section', not [t for t in tabs if t.startswith('in-section')] and len(tabs)==8, tabs)
    n16.keyboard.press('Shift+Tab'); n16.evaluate("document.activeElement.blur()")
    ok('v0.16 item 4: the open and close timing is 240 ms and 160 ms on grid rows with the accepted curve', n16.evaluate("(() => { const b=document.querySelector('#side .bd'), c=getComputedStyle(b), r=[c.transitionProperty, c.transitionDuration]; b.classList.add('op'); r.push(c.transitionDuration, c.transitionTimingFunction); b.classList.remove('op'); return r; })()")==['grid-template-rows','0.16s','0.24s','cubic-bezier(0.16, 1, 0.3, 1)'])
    n16.emulate_media(reduced_motion='reduce')
    rm = n16.evaluate("(() => { const b=document.querySelector('#side .bd'), c=getComputedStyle(b), i=getComputedStyle(b.firstElementChild); return [c.transitionProperty, c.transitionDuration, i.transitionProperty.includes('opacity'), Math.max(...i.transitionDuration.split(',').map(parseFloat))]; })()")
    ok('v0.16 item 4: with prefers-reduced-motion the section has no height transition and keeps a short fade', rm[0]=='none' and rm[1]=='0s' and rm[2] and 0<rm[3]<=0.1, rm)
    n16.emulate_media(reduced_motion='no-preference')
    # force: Go, Manually draw route, and Draft with a missing choice open that section, focus the control, and show the red message
    open_sec(n16, 'addr'); n16.click('#geoForm button'); n16.wait_for_timeout(100); f = n16.evaluate(FORCE)
    ok('v0.16 item 9: Go with no district closes the open section, opens District, focuses the select, and shows the red message', f=={'open':['dist'],'focus':'setDistrict','status':'Select the fire district first.','cls':'err'}, f)
    ok('v0.16 item 6: with the district missing, the select has a red border and the light red background', n16.evaluate(COL, 'setDistrict')==['rgb(179, 38, 30)','rgb(251, 236, 235)'])
    open_sec(n16, 'route'); n16.click('#btnDraft'); n16.wait_for_timeout(100); f = n16.evaluate(FORCE)
    ok('v0.16 item 9: Auto draw route to closest hydrant with no district: District opens, same message', f=={'open':['dist'],'focus':'setDistrict','status':'Select the fire district first.','cls':'err'}, f)
    open_sec(n16, 'route'); named(n16); n16.click('#btnDraw'); n16.wait_for_timeout(100); f = n16.evaluate(FORCE)
    ok('v0.16 item 9: Manually draw route with no district: District opens, same message, and no trace starts', f=={'open':['dist'],'focus':'setDistrict','status':'Select the fire district first.','cls':'err'} and not n16.evaluate('window.__relay.state.drawing'), f)
    n16.select_option('#setDistrict', '253'); n16.wait_for_timeout(300); ln = n16.evaluate(LINES)
    ok('v0.16 item 7: the District tint goes away when a district is picked, and the line reads the name and Close', not ln[0]['req'] and ln[0]['text']=='Yorktown Hgts FD' and ln[0]['act']=='Close' and 'req' not in (n16.get_attribute('#setDistrict','class') or ''), ln[0])
    open_sec(n16, 'addr'); n16.fill('#geoText', '100 Test Hill Rd'); n16.click('#geoForm button'); n16.wait_for_function("document.getElementById('status').textContent.startsWith('Found')", timeout=8000)
    ok('v0.16 item 9: Go with a district but no source type or lay is not blocked (the address search checks the district only)', n16.evaluate("document.getElementById('status').className")=='' and n16.evaluate('window.__relay.found()')!=None)
    open_sec(n16, 'route'); n16.click('#btnDraft'); n16.wait_for_timeout(100); f = n16.evaluate(FORCE); ln = n16.evaluate(LINES)
    ok('v0.16 item 9: Draft with no source type: Lay opens, the type select has focus, the step 2 message shows', f=={'open':['lay'],'focus':'sourceType','status':'Select the water source type in step 2.','cls':'err'} and ln[2]['text']=='Select source type and lay', f)
    ok('v0.16 item 6: both lay controls are red: the type select and the lay buttons', n16.evaluate(COL, 'sourceType')==['rgb(179, 38, 30)','rgb(251, 236, 235)'] and n16.evaluate("(() => { const b=getComputedStyle(document.getElementById('layRev')); return [b.borderTopColor, b.backgroundColor]; })()")==['rgb(179, 38, 30)','rgb(251, 236, 235)'])
    open_sec(n16, 'route'); named(n16); n16.click('#btnDraw'); n16.wait_for_timeout(100); f = n16.evaluate(FORCE)
    ok('v0.16 item 9: Manually draw route with no source type: same Lay message and focus', f=={'open':['lay'],'focus':'sourceType','status':'Select the water source type in step 2.','cls':'err'} and not n16.evaluate('window.__relay.state.drawing'), f)
    n16.select_option('#sourceType', 'Hydrant'); n16.wait_for_timeout(200); ln = n16.evaluate(LINES)
    ok('v0.16 item 7: picking the source type removes its tint; the line now reads Select lay', ln[2]['text']=='Select lay' and ln[2]['req'] and 'req' not in (n16.get_attribute('#sourceType','class') or '') and 'req' in n16.get_attribute('#layRev >> xpath=..', 'class'), ln[2])
    open_sec(n16, 'route'); n16.click('#btnDraft'); n16.wait_for_timeout(100); f = n16.evaluate(FORCE)
    ok('v0.16 item 9: Draft with no lay: Lay opens, the first lay button has focus, the lay message shows', f=={'open':['lay'],'focus':'layRev','status':'Select Reverse lay or Forward lay in step 2.','cls':'err'}, f)
    open_sec(n16, 'route'); named(n16); n16.click('#btnDraw'); n16.wait_for_timeout(100); f = n16.evaluate(FORCE)
    ok('v0.16 item 9: Manually draw route with no lay: same lay message and focus', f=={'open':['lay'],'focus':'layRev','status':'Select Reverse lay or Forward lay in step 2.','cls':'err'} and not n16.evaluate('window.__relay.state.drawing'), f)
    n16.click('#layRev'); n16.wait_for_timeout(200); ln = n16.evaluate(LINES)
    ok('v0.16 items 7 and 10: picking the lay removes the last tint; the line reads the full summary and Close', ln[2]['text']=='Hydrant · Reverse · 5 inch · 185 PSI' and not ln[2]['req'] and ln[2]['act']=='Close' and 'req' not in n16.get_attribute('#layRev >> xpath=..', 'class') and not any(l['req'] for l in ln[:3]) and ln[3]['req'], ln)
    n16.click('#side .su >> nth=1'); n16.wait_for_timeout(250)
    ok('v0.16 item 3: a click on a line opens it and closes the open one', n16.evaluate(OPEN)==['addr'] and not n16.is_visible('#layRev') and n16.is_visible('#geoText'), n16.evaluate(OPEN))
    n16.click('#side .su >> nth=1'); n16.wait_for_timeout(250)
    ok('v0.16 item 3: a click on the open line closes it, and none is open', n16.evaluate(OPEN)==[] and not n16.is_visible('#geoText') and n16.evaluate(LINES)[1]['act']=='Change')
    open_sec(n16, 'route'); named(n16); n16.click('#btnDraw'); n16.wait_for_timeout(100); n16.click('#side .su >> nth=1'); n16.wait_for_timeout(300)
    ok('v0.16: while a trace runs, section 3 stays open (a click on another line cannot close it)', n16.evaluate('window.__relay.state.drawing') and n16.evaluate(OPEN)==['route'] and n16.is_visible('#btnFinish'), n16.evaluate(OPEN))
    n16.close()
    # old saved defaults that hold a district: the district is ignored (browser storage, then a saved copy)
    d16 = fresh(); d16.goto(test_html.resolve().as_uri()); d16.wait_for_timeout(500)
    d16.evaluate("localStorage.setItem('yhfd-relay-defaults-v1', JSON.stringify({district:226, hose:4, cap:200}))"); d16.reload(); d16.wait_for_timeout(800)
    ok('v0.16: a stored old default with a district sets no district; its other values still apply', d16.input_value('#setDistrict')=='' and d16.evaluate('window.__relay.state.settings.district')==None and d16.input_value('#setHose')=='4' and d16.input_value('#setCap')=='200' and d16.inner_text('#defaultsStatus')=='Defaults in use: yours (4 inch, 200 PSI, 20 PSI, 10%, 1,000 ft).', d16.inner_text('#defaultsStatus'))
    d16.evaluate("localStorage.setItem('yhfd-relay-defaults-v1', JSON.stringify({district:226}))"); d16.reload(); d16.wait_for_timeout(800)
    ok('v0.16: a stored default that holds only a district counts as no saved default', d16.input_value('#setDistrict')=='' and d16.inner_text('#defaultsStatus')=='Defaults in use: built-in (5 inch, 185 PSI, 20 PSI, 10%, 1,000 ft).', d16.inner_text('#defaultsStatus'))
    d16.close()
    fd = pathlib.Path('out/test_fd.html'); fd.write_text(re.sub(r'(id="user-defaults">).*?(</script>)', lambda m: m.group(1) + '{"district":226,"hose":4}' + m.group(2), src, count=1, flags=re.S), encoding='utf-8')
    d16 = fresh(); d16.goto(fd.resolve().as_uri()); d16.wait_for_timeout(800)
    ok('v0.16: a saved copy whose file defaults hold a district sets no district; its hose value applies', d16.input_value('#setDistrict')=='' and d16.evaluate('window.__relay.state.settings.district')==None and d16.input_value('#setHose')=='4' and d16.inner_text('#defaultsStatus')=='Defaults in use: this file (4 inch, 185 PSI, 20 PSI, 10%, 1,000 ft).', d16.inner_text('#defaultsStatus'))
    d16.close()
    # ---- v0.16 phase, part F: map Undo (one level, six edit paths) ----
    e16u = len(errors); GATE['roads'] = True; GATE['addr'] = ADDR2; GATE['road'] = None
    u = fresh(); u.set_viewport_size({'width':1280,'height':800}); load(u)
    open_sec(u, 'addr'); u.fill('#geoText', '100 Test Hill Rd'); u.click('#geoForm button'); u.wait_for_timeout(600); draft(u); u.wait_for_selector('#flowTable', timeout=8000); u.wait_for_timeout(500)
    STATE = "(() => { const s=window.__relay.state; return JSON.stringify([s.points, s.manual, s.sourceHydrant, s.draft]); })()"
    HOSE = "(() => { const p=window.__relay.state.profile; return p.h[p.n-1]; })()"
    UDT = "(() => { const b=document.querySelector('.ud'); return b && !b.hidden && getComputedStyle(b).display!='none' ? b.querySelector('[role=status]').textContent : null; })()"
    def udrag(sel, dx, dy):
        bb = u.locator(sel).bounding_box(); x0, y0 = bb['x']+bb['width']/2, bb['y']+bb['height']/2
        u.mouse.move(x0, y0); u.mouse.down(); u.mouse.move(x0+dx, y0+dy, steps=8); u.mouse.up(); u.wait_for_timeout(900)
    def rclick(): u.locator('.vx').nth(1).dispatch_event('contextmenu'); u.wait_for_timeout(900)
    def line_click():  # a click on the dark line, 70 percent along the first section
        xy = u.evaluate("(() => { const m=window.__relay.map, r=m.getContainer().getBoundingClientRect(), p=window.__relay.state.points, a=m.latLngToContainerPoint(p[0]), b=m.latLngToContainerPoint(p[1]); return [r.x + a.x + (b.x-a.x)*0.7, r.y + a.y + (b.y-a.y)*0.7]; })()")
        u.mouse.click(xy[0], xy[1]); u.wait_for_timeout(900)
    def relay_drag():
        q = u.evaluate("[500,750,1000,1250,1500,2000].find(q => window.__relay.state.results[q].relays.length>0)")
        u.click('#flowTable tr[data-q="%d"]' % q); u.wait_for_timeout(300); udrag('.em.R >> nth=0', 40, 30)
    def try_undo(name, edit, text, relay=False):
        s0 = u.evaluate(STATE); h0 = u.evaluate(HOSE); edit(); t = u.evaluate(UDT); s1 = u.evaluate(STATE)
        u.click('.ud button'); u.wait_for_timeout(900)
        info = (t, s1 != s0, u.evaluate(STATE) == s0, u.evaluate(HOSE) == h0, u.evaluate(UDT), u.evaluate("document.activeElement === window.__relay.map.getContainer()"))
        ok(name, info == (text, True, True, True, None, True) and u.evaluate('window.__relay.state.results[500].segs.length>0'), info)
    try_undo('v0.16 F1: a middle handle click adds a point; Point added.; Undo restores points, manual, source, draft; recomputes; hides the box; focus on the map', lambda: (u.locator('.mid').first.click(), u.wait_for_timeout(900)), 'Point added.')
    try_undo('v0.16 F2: a drag of a point handle; Point moved.; Undo restores the snapshot taken at drag start', lambda: udrag('.vx >> nth=1', 60, 40), 'Point moved.')
    try_undo('v0.16 F3: a right-click remove; Point removed.; Undo restores it', rclick, 'Point removed.')
    try_undo('v0.16 F4: a click on the line inserts a point; Point added.; Undo restores it', line_click, 'Point added.')
    try_undo('v0.16 F5a: a drag of the S marker; Point moved.; Undo restores it', lambda: udrag('.em.S', -60, 40), 'Point moved.')
    try_undo('v0.16 F5b: a drag of the A marker; Point moved.; Undo restores it', lambda: udrag('.em.A', 60, -40), 'Point moved.')
    try_undo('v0.16 F6: a drag of a relay engine; Engine moved.; Undo restores state.manual', relay_drag, 'Engine moved.')
    u.locator('.vx').nth(1).click(); u.wait_for_timeout(300); u.click('.leaflet-popup-content button'); u.wait_for_timeout(900)
    ok('v0.16 F3b: Remove point in the popup shows Point removed.', u.evaluate(UDT) == 'Point removed.', u.evaluate(UDT))
    u.click('.ud button'); u.wait_for_timeout(900)
    s0 = u.evaluate(STATE); u.locator('.mid').first.dispatch_event('click'); u.wait_for_timeout(900); s1 = u.evaluate(STATE); udrag('.vx >> nth=1', 60, 40); s2 = u.evaluate(STATE)
    t2 = u.evaluate(UDT); u.click('.ud button'); u.wait_for_timeout(900)
    ok('v0.16 F: a second edit replaces the first (text and snapshot); Undo goes back one edit only, and there is no redo', t2 == 'Point moved.' and u.evaluate(STATE) == s1 != s0 and u.evaluate(UDT) is None, (t2, u.evaluate(UDT)))
    PTS_ = 'window.__relay.state.points.length'; n0 = u.evaluate(PTS_); u.locator('.mid').first.dispatch_event('click'); u.wait_for_timeout(900)
    u.click('.ud', position={'x': 3, 'y': 3}); u.wait_for_timeout(300)
    ok('v0.16 F: a click on the box (not on Undo) adds no route point and keeps the box', u.evaluate(PTS_) == n0 + 1 and u.evaluate(UDT) == 'Point added.', (n0, u.evaluate(PTS_)))
    q2 = u.evaluate("window.__relay.state.flow == 500 ? 750 : 500"); u.click('#flowTable tr[data-q="%d"]' % q2); u.wait_for_timeout(300)
    ok('v0.16 F: a change of flow hides the box', u.evaluate(UDT) is None)
    u.locator('.mid').first.dispatch_event('click'); u.wait_for_timeout(900); u.evaluate("(() => { const e=document.getElementById('setSlack'); e.value='15'; e.dispatchEvent(new Event('change')); })()"); u.wait_for_timeout(600)
    ok('v0.16 F: a setting that resets the relay positions hides the box', u.evaluate(UDT) is None)
    while u.evaluate(PTS_) > 2: rclick()
    u.click('#flowTable tr[data-q="%d"]' % (1000 if u.evaluate('window.__relay.state.flow') != 1000 else 500)); u.wait_for_timeout(300)
    u.locator('.vx').nth(1).dispatch_event('contextmenu'); u.wait_for_timeout(500)
    ok('v0.16 F: a refused remove (only 2 points) shows no box', u.evaluate(PTS_) == 2 and u.evaluate(UDT) is None)
    u.locator('.mid').first.dispatch_event('click'); u.wait_for_timeout(900); u.click('#flowTable tr[data-q="1250"]'); u.wait_for_timeout(300)
    u.locator('.mid').first.dispatch_event('click'); u.wait_for_timeout(900); u.click('#btnCard'); u.wait_for_timeout(600)
    ok('v0.16 F: in card mode the box is hidden by CSS (it is not hidden by script)', u.evaluate("(() => { const b=document.querySelector('.ud'); return !b.hidden && getComputedStyle(b).display; })()")=='none' and u.evaluate(UDT) is None)
    u.click('#btnBack'); u.wait_for_timeout(500)
    open_sec(u, 'route'); u.locator('.mid').first.dispatch_event('click'); u.wait_for_timeout(900); named(u); u.click('#btnDraw'); u.wait_for_timeout(300)
    ok('v0.16 F: entering trace mode hides the box', u.evaluate(UDT) is None)
    udrag('.vx >> nth=1', 60, 40)
    ok('v0.16 F: a point drag in trace mode shows no box', u.evaluate(UDT) is None)
    u.click('#btnFinish'); u.wait_for_timeout(900); u.locator('.mid').first.dispatch_event('click'); u.wait_for_timeout(900); clear(u); u.wait_for_timeout(500)
    ok('v0.16 F: Clear route hides the box', u.evaluate(UDT) is None)
    u.close()
    # ---- v0.17 phase: the Settings view behind the gear in the header ----
    e17 = len(errors); GATE['roads'] = True; GATE['addr'] = ADDR2; GATE['road'] = None
    g = fresh(); g.set_viewport_size({'width':1280,'height':800}); load(g)
    open_sec(g, 'addr'); g.fill('#geoText', '100 Test Hill Rd'); g.click('#geoForm button'); g.wait_for_timeout(600); draft(g); g.wait_for_selector('#flowTable', timeout=8000); g.wait_for_timeout(500)
    VIS = "s => !!document.querySelector(s) && getComputedStyle(document.querySelector(s)).display != 'none' && document.querySelector(s).getClientRects().length > 0"
    PRESS = "document.getElementById('btnSettings').getAttribute('aria-pressed')"
    ACT = "document.activeElement && document.activeElement.id"
    last = g.evaluate("[...document.querySelectorAll('#side > .sec')].pop().querySelector('h2').textContent")
    # proof: fails when the gear is missing or pressed, or when My defaults or the rules list stay in the planner
    ok('v0.17 a: planner view: the gear is in the header with aria-pressed false, My defaults and the rules list are not visible, the last planner section is Keep the plan', g.evaluate(VIS, '.brand #btnSettings') and g.evaluate(PRESS)=='false' and g.get_attribute('#btnSettings','aria-label')=='Settings' and not g.evaluate(VIS, '#btnSaveDefaults') and not g.evaluate(VIS, '#setView ul') and last=='Keep the plan', (last, g.evaluate(PRESS)))
    gb = g.evaluate("(() => { const b=document.getElementById('btnSettings'), r=b.getBoundingClientRect(), h=document.querySelector('.brand').getBoundingClientRect(); return [r.width, r.height, Math.abs((r.top+r.bottom)/2-(h.top+h.bottom)/2) < 1, r.right <= h.right]; })()")
    ok('v0.17: the gear is a 36 x 36 button, centred in the header, with an inline SVG icon', gb==[36,36,True,True] and g.evaluate("document.querySelectorAll('#btnSettings svg').length")==1 and g.evaluate("document.getElementById('btnSettings').tagName")=='BUTTON', gb)
    SNAP17 = "(() => { const s=document.getElementById('side'); return JSON.stringify([window.__relay.state.points, document.getElementById('results').innerHTML.length, [...document.querySelectorAll('#side .sec[data-k] .bd.op')].map(b=>b.parentNode.dataset.k), s.scrollTop, window.__relay.map.getCenter(), window.__relay.map.getZoom()]); })()"
    open_sec(g, 'lay'); g.evaluate("document.getElementById('side').scrollTop = 150"); g.wait_for_timeout(300)
    before = g.evaluate(SNAP17)
    ok('v0.17: the check has a real planner scroll to keep (the sidebar scrolls)', json.loads(before)[3] > 0, json.loads(before)[3])
    g.evaluate("document.getElementById('btnSettings').click()"); g.wait_for_timeout(200)  # a script click: the gear scrolls away with the sidebar, and a real click would scroll it back to 0
    boxes = g.evaluate("['btnSaveDefaults','btnResetDefaults','btnCopyDefaults'].map(i => { const r=document.getElementById(i).getBoundingClientRect(); return [r.left, r.width, r.top, r.bottom]; })")
    stacked = len({round(b[0]) for b in boxes})==1 and len({round(b[1]) for b in boxes})==1 and all(boxes[i][3] <= boxes[i+1][2] for i in range(2))
    # proof: fails when the buttons sit in one row (same top, different left), or when the rules list is closed or has a different count
    ok('v0.17 b: gear click: Settings view shows Back, My defaults (three buttons stacked, same left edge and width), the status line, and the open rules list of 12 items; planner sections are hidden; aria-pressed true; focus on Back',
       g.evaluate(VIS, '#btnSettingsBack') and g.text_content('#setView h2')=='My defaults' and stacked and g.evaluate(VIS, '#defaultsStatus') and g.evaluate(VIS, '#setView ul') and g.locator('#setView ul li').count()==12 and g.evaluate("document.querySelector('#setView details')")==None
       and not any(g.evaluate(VIS, x) for x in ('#side .sec[data-k=dist]', '#btnCard', '#status', '#results', '#planNotes')) and g.evaluate(PRESS)=='true' and g.evaluate(ACT)=='btnSettingsBack' and g.evaluate("document.getElementById('side').scrollTop")==0 and g.evaluate(VIS, '.brand'), (boxes, g.evaluate(ACT)))
    g.focus('#btnSettingsBack'); tabs = []
    for _ in range(8): g.keyboard.press('Tab'); tabs.append(g.evaluate("(() => { const a=document.activeElement, s=a.closest('#side'); return s ? (a.closest('#setView, .brand') ? 'ok' : 'planner:' + a.id) : 'outside'; })()"))
    # proof: fails when a hidden planner control stays focusable (it would show as planner:id)
    ok('v0.17: Tab in the Settings view never lands on a hidden planner control', not [t for t in tabs if t.startswith('planner')] and tabs[:3]==['ok','ok','ok'], tabs)
    def back_via(how):
        g.evaluate("document.getElementById('btnSettings').click()") if g.evaluate(PRESS)=='false' else None
        g.wait_for_timeout(150)
        if how=='back': g.click('#btnSettingsBack')
        elif how=='gear': g.evaluate("document.getElementById('btnSettings').click()")
        else: g.focus('#btnSettingsBack'); g.keyboard.press('Escape')
        g.wait_for_timeout(200)
        now = g.evaluate(SNAP17)
        if now != before: print('SNAP DIFF', how, before[-200:], now[-200:])
        return now==before and g.evaluate(PRESS)=='false' and g.evaluate(ACT)=='btnSettings' and g.evaluate(VIS, '#btnCard') and not g.evaluate(VIS, '#btnSaveDefaults')
    # proof: fails when a way back does not restore the same route, result, open section, scroll and map, or does not focus the gear
    r1 = back_via('back'); r2 = back_via('gear'); r3 = back_via('esc')
    ok('v0.17 c: Back, the gear, and Escape each return to the planner with the gear focused; route points, result, open section, scroll position, and map are the same as before', r1 and r2 and r3, (r1, r2, r3))
    # proof: fails when Escape pressed outside the Settings view (focus on the page) closes it, since the handler lives on the view only
    g.click('#btnSettings'); g.focus('#btnSettings'); g.keyboard.press('Escape'); g.wait_for_timeout(100)
    ok('v0.17: Escape with focus on the gear (outside the Settings view) does nothing', g.evaluate(PRESS)=='true')
    g.click('#btnSettings'); g.wait_for_timeout(100)
    # d: the defaults checks above run through to_set(). Here, Save and Reset from the Settings view show the same status text.
    to_set(g); g.click('#btnSaveDefaults'); sv = g.inner_text('#defaultsStatus'); g.click('#btnResetDefaults'); g.wait_for_timeout(300); rs = g.inner_text('#defaultsStatus')
    ok('v0.17 d: Save as my defaults and Reset work from the Settings view (status text, browser key)', sv.startswith('Saved in this browser. Defaults in use: yours (') and rs.startswith('Defaults in use: built-in (') and g.evaluate(LS, 'yhfd-relay-defaults-v1') is None, (sv, rs))
    to_plan(g)
    g.click('#btnSettings'); g.evaluate("document.getElementById('btnCard').click()"); g.wait_for_timeout(500)  # the button is hidden in Settings, so click it by script
    cardv = g.evaluate("document.body.classList.contains('card')") and g.evaluate(VIS, '#cardBody') and not g.evaluate(VIS, '#side')
    g.click('#btnBack'); g.wait_for_timeout(300)
    # proof: fails when Make card leaves the set class on #side (the planner view is then not shown after Back to planner)
    ok('v0.17 f: Make card while Settings is open shows the card; Back to planner shows the planner view (gear not pressed)', cardv and not g.evaluate("document.body.classList.contains('card')") and g.evaluate(VIS, '#btnCard') and not g.evaluate(VIS, '#btnSaveDefaults') and g.evaluate(PRESS)=='false')
    pd = g.evaluate("(() => { const c=getComputedStyle(document.querySelector('.en .pd')), bg=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim(); const t=document.createElement('i'); t.style.background=bg; document.body.appendChild(t); const want=getComputedStyle(t).backgroundColor; t.remove(); return [c.borderTopWidth, c.borderTopStyle, c.borderTopLeftRadius, c.backgroundColor==want]; })()")
    # proof: fails when the border, radius, or background of the PDP box changes
    ok('v0.17 g: .en .pd has a 1 px solid border, a 6 px radius, and the --bg background', pd==['1px','solid','6px',True], pd)
    g.close()
    m = fresh(); m.set_viewport_size({'width':390,'height':800}); load(m)
    inh = m.evaluate("(() => { const b=document.getElementById('btnSettings').getBoundingClientRect(), h=document.querySelector('.brand').getBoundingClientRect(); return b.left >= h.left && b.right <= h.right && b.top >= h.top && b.bottom <= h.bottom && document.documentElement.scrollWidth <= 390; })()")
    m.click('#btnSettings'); m.wait_for_timeout(200)
    sw = m.evaluate(VIS, '#btnSaveDefaults') and not m.evaluate(VIS, '#btnCard') and m.evaluate(ACT)=='btnSettingsBack' and m.evaluate(VIS, '#btnSettings')
    m.click('#btnSettingsBack'); m.wait_for_timeout(200)
    # proof: fails when the gear leaves the header or the page scrolls sideways at 390 px, or when the switch does not work on a phone
    ok('v0.17 e: at 390 px the gear is inside the header (no sideways scroll), the switch opens Settings with the gear still visible, and Back returns', inh and sw and m.evaluate(VIS, '#btnCard') and m.evaluate(ACT)=='btnSettings', (inh, sw))
    m.close()
    ok('no page errors in the v0.17 phase', not [e for e in errors[e17:] if 'Failed to load resource' not in e], errors[e17:][:3])
    ok('no page errors in the v0.16 Undo phase', not [e for e in errors[e16u:] if 'Failed to load resource' not in e], errors[e16u:][:3])
    ok('no page errors in the v0.16 phase', not [e for e in errors[e16:] if 'Failed to load resource' not in e], errors[e16:][:3])
    ok('no page errors in the v0.15 phase', not [e for e in errors[e15:] if 'Failed to load resource' not in e], errors[e15:][:3])
    # ---- v0.20 and v0.21 phase: each setup row shows done or required. All four steps are required. ----
    v20 = fresh(); v20.goto(test_html.resolve().as_uri()); v20.wait_for_timeout(700); r20 = v20.evaluate(ROWS20)
    ok('v0.21: a new page: all four setup rows are required and red; no row is done', [x[0] for x in r20]==['req','req','req','req'] and all(x[1]=='rgb(251, 236, 235)' for x in r20), r20)
    pick(v20); r20 = v20.evaluate(ROWS20)
    ok('v0.21: with a district: District is done; Address, Lay, and Route stay red', [x[0] for x in r20]==['ok','req','req','req'] and r20[0][1]=='rgba(0, 0, 0, 0)' and all(x[1]=='rgb(251, 236, 235)' for x in r20[1:]), r20)
    ok('v0.20: each setup row starts with a 16 px mark', all(x[3]=='16px' for x in r20), r20)
    ok('v0.21: the action word of a required row is a solid red button with white text', v20.evaluate("(() => { const c = getComputedStyle(document.querySelector('#side .sec[data-k=route] .su u')); return [c.backgroundColor, c.color]; })()")==['rgb(179, 38, 30)','rgb(255, 255, 255)'])
    open_sec(v20, 'route'); bb = v20.evaluate("['btnDraft','btnDraw'].map(i => { const r = document.getElementById(i).getBoundingClientRect(); return [document.getElementById(i).textContent, Math.round(r.width), Math.round(r.top)]; })")
    ok('v0.21: the two route buttons have the new names, full width, one above the other', bb[0][0]=='Auto draw route to closest hydrant' and bb[1][0]=='Manually draw route' and bb[0][1]==bb[1][1] and bb[0][1]>300 and bb[1][2]>bb[0][2], bb)
    open_sec(v20, 'lay'); v20.select_option('#sourceType', 'Draft site'); t1 = v20.text_content('#btnDraft'); v20.select_option('#sourceType', 'Hydrant'); t2 = v20.text_content('#btnDraft')
    ok('v0.21: the auto button names the water source for a source that is not a hydrant', (t1, t2)==('Auto draw route to water source','Auto draw route to closest hydrant'), (t1, t2))
    ok('v0.21: the setting label reads Intake pressure residual', v20.evaluate("document.getElementById('setRes').parentNode.firstChild.textContent")=='Intake pressure residual')
    # ---- v0.22: a "?" help mark on the Hose slack allowance label ----
    QV = "(() => { const c = getComputedStyle(document.querySelector('#side .q .tip')); return [c.visibility, c.opacity]; })()"
    q22 = v20.evaluate("(() => { const q = document.querySelector('#side .q'), s = document.getElementById('setSlack'); return [document.querySelectorAll('#side .q').length, q.parentNode === s.parentNode, q.getAttribute('role'), q.tabIndex, q.getAttribute('aria-label'), s.getAttribute('aria-label'), s.value, q.querySelector('.tip').textContent]; })()")
    ok('v0.22: the Hose slack allowance label has one "?" help button with a name; the select keeps its name and value', q22[:7]==[1, True, 'button', 0, 'What is the hose slack allowance?', 'Hose slack allowance', '10'] and '10% adds 100 ft to each 1,000 ft.' in q22[7], q22)
    ok('v0.22: the help text is hidden at the start', v20.evaluate(QV)==['hidden','0'], v20.evaluate(QV))
    v20.focus('#side .q'); v20.wait_for_timeout(400); f22 = v20.evaluate(QV)
    v20.evaluate("document.activeElement.blur()"); v20.wait_for_timeout(400); b22 = v20.evaluate(QV)
    v20.hover('#side .q'); v20.wait_for_timeout(400); h22 = v20.evaluate(QV)
    ok('v0.22: the help text shows on keyboard focus and on hover, and hides after', (f22, b22, h22)==(['visible','1'],['hidden','0'],['visible','1']), (f22, b22, h22))
    v20.click('#side .q'); v20.wait_for_timeout(200)
    ok('v0.22: a click on "?" keeps the help text open and does not change or focus the select', v20.evaluate(QV)==['visible','1'] and v20.evaluate("[document.getElementById('setSlack').value, document.activeElement.id]")==['10',''], v20.evaluate("[document.getElementById('setSlack').value, document.activeElement.id, document.activeElement.className]"))
    v20.evaluate("document.activeElement.blur()"); v20.mouse.move(700, 500)
    v20.click('#layRev'); open_sec(v20, 'route'); v20.click('#btnDraw'); v20.wait_for_timeout(300)
    ok('v0.21: Manually draw route with no address opens step 1, marks the address field red, and gives the message', not v20.evaluate('window.__relay.state.drawing') and v20.inner_text('#status')=='Find the address in step 1 first. With no match, type a plan name.' and v20.evaluate("document.querySelector('#side .sec[data-k=addr] .bd').classList.contains('op') && document.getElementById('geoText').classList.contains('req') && document.activeElement.id==='geoText'"), v20.inner_text('#status'))
    named(v20); open_sec(v20, 'route'); v20.click('#btnDraw'); v20.wait_for_timeout(300)
    ok('v0.21: with a plan name, the address row is done and Manually draw route starts; the button reads Drawing...', v20.evaluate('window.__relay.state.drawing') and v20.text_content('#btnDraw')=='Drawing...' and v20.evaluate(ROWS20)[1][0]=='ok')
    # ---- v0.23: the report form in Settings. A stand-in answers for the helper, so the test needs no internet. ----
    r23 = fresh(); sent23 = []; ans23 = ['{"ok":true,"number":14,"url":"https://github.com/Vergo402/relay-pumping-preplan/issues/14"}']
    def helper23(route):
        sent23.append(route.request.post_data)
        route.abort() if ans23[0] is None else route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=ans23[0])
    r23.route('https://script.google.com/**', helper23)
    r23.goto(test_html.resolve().as_uri()); r23.wait_for_timeout(700); r23.click('#btnSettings')
    REP = "(() => { const v = id => { const e = document.getElementById(id); return !!e && e.getClientRects().length > 0; }; return {form:v('repForm'), ok:v('repOk'), more:v('btnRepMore'), bad:v('repBad'), alt:v('repAlt'), ask:document.getElementById('repAsk').textContent, count:document.getElementById('repCount').textContent, send:document.getElementById('btnRepSend').textContent, text:document.getElementById('repText').value, trap:document.getElementById('repWeb').getBoundingClientRect().right < 0, h2:[...document.querySelectorAll('#setView h2')].map(h=>h.textContent)}; })()"
    s23 = r23.evaluate(REP)
    ok('v0.23: Settings has the section Problems and ideas after My defaults; the form shows, Problem is selected, the trap field is off the screen', s23['h2'][:2]==['My defaults','Problems and ideas'] and s23['form'] and not (s23['ok'] or s23['more'] or s23['bad'] or s23['alt']) and s23['ask']=='What happened? What did you expect?' and s23['count']=='0 of 1,000' and s23['send']=='Send report' and s23['trap'] and r23.get_attribute('#repProb','aria-pressed')=='true', s23)
    ok('v0.23: the form says that the report is public', 'This report is public on GitHub. Do not type an address or personal data.' in r23.inner_text('#rep'))
    r23.click('#btnRepSend'); r23.wait_for_timeout(200)
    ok('v0.23: Send with no text sends nothing and marks the text field red', sent23==[] and r23.evaluate("document.getElementById('repText').classList.contains('req') && document.activeElement.id==='repText'"))
    r23.click('#repIdea'); a23 = r23.evaluate(REP)['ask']; r23.click('#repProb')
    r23.fill('#repText', 'The auto route went to the wrong side of the road.'); r23.fill('#repName', 'Test Person')
    ok('v0.23: Idea changes the question; the count shows the typed characters', a23=='What do you want the page to do?' and r23.evaluate(REP)['count']=='50 of 1,000' and not r23.evaluate("document.getElementById('repText').classList.contains('req')"), (a23, r23.evaluate(REP)['count']))
    ans23[0] = None; r23.click('#btnRepSend'); r23.wait_for_timeout(400); f23 = r23.evaluate(REP)
    ok('v0.23: a failed send says Not sent, keeps the text, offers Send again and the GitHub link', f23['bad'] and f23['alt'] and f23['form'] and f23['send']=='Send again' and f23['text'].startswith('The auto route') and r23.inner_text('#repBad')=='Not sent.\nCheck the internet connection, then send again. Your text is still here.' and r23.get_attribute('#repAlt a','href')=='https://github.com/Vergo402/relay-pumping-preplan/issues/new', (f23, r23.inner_text('#repBad')))
    ans23[0] = '{"ok":false,"why":"limit"}'; r23.click('#btnRepSend'); r23.wait_for_timeout(400)
    ok('v0.23: at the daily limit the page says to send again tomorrow', 'maximum number of reports for today. Send again tomorrow. Your text is still here.' in r23.inner_text('#repBad'), r23.inner_text('#repBad'))
    ans23[0] = '{"ok":true,"number":14,"url":"https://github.com/Vergo402/relay-pumping-preplan/issues/14"}'; r23.click('#btnRepSend'); r23.wait_for_timeout(400); g23 = r23.evaluate(REP); body23 = json.loads(sent23[-1])
    ok('v0.23: the page sends the type, text, name, version, and browser, and no address or route', sorted(body23)==['browser','kind','name','text','version','website'] and (body23['kind'], body23['text'], body23['name'], body23['version'], body23['website'])==('problem','The auto route went to the wrong side of the road.','Test Person','v0.23','') and 'Chrome' in body23['browser'], body23)
    ok('v0.23: a good send shows the report number and the issue link, and hides the form', g23['ok'] and g23['more'] and not g23['form'] and r23.inner_text('#repOk').startswith('✓ Sent. Report number 14.') and r23.get_attribute('#repLink','href')=='https://github.com/Vergo402/relay-pumping-preplan/issues/14' and r23.evaluate("document.activeElement.id")=='btnRepMore', (g23, r23.inner_text('#repOk')))
    r23.click('#btnRepMore'); m23 = r23.evaluate(REP)
    ok('v0.23: Send one more gives an empty form again', m23['form'] and not (m23['ok'] or m23['bad'] or m23['alt']) and m23['text']=='' and m23['count']=='0 of 1,000' and m23['send']=='Send report', m23)
    src23 = test_html.read_text()
    ok('v0.23: the page holds no GitHub key', not re.search(r'github_pat_|gh[pousr]_[A-Za-z0-9]{20}|Bearer ', src23) and src23.count('script.google.com/macros/s/')==1)
    ok('no page errors in the v0.14 phase', not [e for e in errors[e14:] if 'Failed to load resource' not in e], errors[e14:][:3])
    ok('no page errors in the v0.13 phase', not [e for e in errors[e13:] if 'Failed to load resource' not in e], errors[e13:][:3])
    ok('no page errors in the v0.4 phase', not [e for e in errors[e0:] if 'Failed to load resource' not in e], errors[e0:][:3])
    bad = [e for e in errors if 'Failed to load resource' not in e]
    ok('no console errors except the aborted requests', not bad, bad[:3])
    b.close()
for f in ('out/card_forward.pdf','out/card_reverse.pdf','out/v08-card.pdf'):
    n = len(re.findall(rb'/Type\s*/Page(?![a-zA-Z])', pathlib.Path(f).read_bytes()))
    ok(f+' prints on one page', n==1, n)
print('console errors:', errors[:6]); print('\nFAILED: '+str(fails) if fails else '\nALL UI CHECKS PASS')
sys.exit(1 if fails else 0)
