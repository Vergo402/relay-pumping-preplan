// Math test for the relay calculator. It runs the hydraulics code from the built page.
// Usage: node tests/test_core.js "dist/YHFD Relay Pumping Calculator.html"
// The expected values come from the YHFD chauffeur reference chart (PDF).
const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
const m=html.match(/<script id="core">([\s\S]*?)<\/script>/);
const mod={exports:{}}; new Function('module',m[1])(mod); const C=mod.exports;
let fails=0; const ok=(name,cond,info)=>{ console.log((cond?'PASS ':'FAIL ')+name+(info?'  -> '+info:'')); if(!cond) fails++; };
// straight synthetic route heading north; 1 deg lat = 364,812 ft approx by the same haversine
function route(lenFt, zf, step=25){ const n=Math.round(lenFt/step); const s=[],z=[]; const dLat=step/(20902260*Math.PI/180);
  for(let i=0;i<=n;i++){ s.push({lat:41.26+i*dLat,lng:-73.80}); z.push(zf(i*step)); } return C.buildProfile(s,z,0); }
const flat=L=>route(L,()=>500);
const S=(p,gpm,cap,res=20,hose=5,man)=>C.solve(p,{gpm,hose,cap,residual:res},man);
// friction loss is one formula for all flows: C x (GPM/100)^2 for each 100 ft. C is 0.08 (5 inch), 0.2 (4 inch), 0.2 on the total flow (dual 3 inch, 0.8 on half of the flow)
const FLOWS=[500,750,1000,1250,1500,2000], FL={5:[2,4.5,8,12.5,18,32],4:[5,11.25,20,31.25,45,80],3:[5,11.25,20,31.25,45,80]};
for(const h of [5,4,3]) ok(`FL formula hose ${h}: all six flows`, FLOWS.every((q,i)=>Math.abs(C.flPer100(h,q)-FL[h][i])<1e-9), FLOWS.map(q=>C.flPer100(h,q)).join(' '));
ok('FL dual 3in is 0.8 on half of the flow in one line', FLOWS.every(q=>Math.abs(C.flPer100(3,q)-0.8*Math.pow(q/2/100,2))<1e-9));
ok('FL ignores a third argument (old saved basis)', C.flPer100(5,750,'chart')===4.5&&C.flPer100(5,750,'formula')===4.5);
// PDP rounds up to the next 5 PSI. Flat 500 GPM, 5 inch: demand = 20 + 0.02 x ft. The minimum PDP is 50, so the checks sit at 50 and above.
{ const pd=ft=>{ const r=S(flat(ft),500,150); return [r.segs[0].req,r.maxPdp]; };
  let [rq,pp]=pd(1500); ok('PDP round up: demand 50.0 gives 50', Math.abs(rq-50)<1e-6&&pp===50, `req ${rq} pdp ${pp}`);
  [rq,pp]=pd(1525); ok('PDP round up: demand 50.5 gives 55', Math.abs(rq-50.5)<1e-6&&pp===55, `req ${rq} pdp ${pp}`);
  [rq,pp]=pd(1550); ok('PDP round up: demand 51 gives 55 (old 1 PSI tolerance gave 50)', Math.abs(rq-51)<1e-6&&pp===55, `req ${rq} pdp ${pp}`);
  [rq,pp]=pd(1750); ok('PDP round up: demand 55 with float noise gives 55', Math.abs(rq-55)<1e-6&&pp===55, `req ${rq} pdp ${pp}`);
  [rq,pp]=pd(1775); ok('PDP round up: demand 55.5 gives 60', Math.abs(rq-55.5)<1e-6&&pp===60, `req ${rq} pdp ${pp}`);
  [rq,pp]=pd(500); ok('PDP minimum stays 50: demand 30 gives 50', Math.abs(rq-30)<1e-6&&pp===50, `req ${rq} pdp ${pp}`); }
let p=flat(2600), r=S(p,750,150);
ok('flat 2600ft 750gpm cap150: no relay, PDP 140 (117 + 20 = 137)', r.relays.length===0&&r.maxPdp===140&&!r.over, `relays ${r.relays.length} pdp ${r.maxPdp} hose ${p.h[p.n-1].toFixed(1)}`);
r=S(flat(3000),750,150); ok('flat 3000ft 750gpm cap150: 1 relay', r.relays.length===1&&!r.over, `pdps ${r.segs.map(s=>s.pdp)} at ${r.segs.map(s=>Math.round(s.at))}`);
// chart Max Relay Distance table (20 PSI intake)
const tbl={150:{500:6500,750:2850,1000:1625,1500:700,2000:400},200:{500:9000,750:4000,1000:2250,1500:1000,2000:550}};
for(const cap of [150,200]) for(const q of [500,750,1000,1500,2000]){ const d=tbl[cap][q];
  const a=S(flat(Math.floor(d*0.97/25)*25),q,cap), b=S(flat(Math.ceil(d*1.04/25)*25),q,cap);
  ok(`chart max relay ${q}gpm @${cap}: ${d}ft is the edge`, a.relays.length===0 && b.relays.length===1, `below ${a.relays.length} (pdp ${a.maxPdp}), above ${b.relays.length}`); }
// worked example: 1500 ft, 120 ft climb
const hill=route(1500,x=>500+120*x/1500);
const hoseLen=hill.h[hill.n-1];
r=S(hill,750,200); ok('example 750gpm cap200: PDP 150 (147.7 needed), no relay', r.relays.length===0&&r.maxPdp===150, `pdp ${r.maxPdp} hose ${hoseLen.toFixed(1)} friction ${r.frictionAll.toFixed(1)} climb ${r.climbAll}`);
r=S(hill,750,150); ok('example 750gpm cap150: no relay, PDP 150 (147.7 needed)', r.relays.length===0&&r.maxPdp===150&&!r.over, `pdps ${r.segs.map(s=>s.pdp)}`);
r=S(hill,1000,200); ok('example 1000gpm cap200: 1 relay (200.4 needed)', r.relays.length===1&&!r.over, `pdps ${r.segs.map(s=>s.pdp)} demand ${(r.frictionAll+r.climbAll+20).toFixed(0)}`);
r=S(hill,500,150); ok('example 500gpm cap150: no relay, PDP 115 (110.1 needed, rounds up)', r.relays.length===0&&r.maxPdp===115, `pdp ${r.maxPdp}`);
// hose pressure limit: 250 PSI for dual 3 inch, 200 for 5 inch. A downhill run with the pump at idle (50 PSI) builds hose pressure from the drop.
{ const mid=route(1000,x=>900-0.45*x), steep=route(1000,x=>900-0.8*x), m3=S(mid,500,150,20,3), m5=S(mid,500,150,20,5), t3=S(steep,500,150,20,3);
  ok('hose limits: 250 for hose 3, 200 for hose 5 and 4', C.hoseMax(3)===250&&C.hoseMax(5)===200&&C.hoseMax(4)===200&&C.LDH_MAX===200);
  ok('hose limit: a run between 200 and 250 PSI flags hose 5 but not hose 3', m5.overLdh===true&&m3.overLdh===false&&m3.peak>201&&m3.peak<250, `hose5 peak ${Math.round(m5.peak)} hose3 peak ${Math.round(m3.peak)}`);
  ok('hose limit: a run above 250 PSI flags hose 3 too', t3.overLdh===true&&t3.peak>251, `peak ${Math.round(t3.peak)}`); }
// intake at each receiving engine >= residual, every hose point >= 10
function check(p,r,res){ let good=true; r.segs.forEach(s=>{ if(s.intake<res-1.01) good=false; }); r.line.forEach(pt=>{ if(pt[1]<C.LINE_MIN-1.01) good=false; }); return good; }
ok('pressures hold on example', check(hill,S(hill,1000,200),20)&&check(hill,S(hill,750,150),20));
// crest: up 150 ft over 1000 ft then down 150 ft over 1000 ft, net zero
const crest=route(2000,x=>x<=1000?500+0.15*x:650-0.15*(x-1000));
r=S(crest,750,150); ok('crest route: PDP covers the high point', check(crest,r,20)&&r.maxPdp>=135, `relays ${r.relays.length} pdps ${r.segs.map(s=>s.pdp)} intakes ${r.segs.map(s=>Math.round(s.intake))}`);
const st=C.stats(crest); ok('stats crest', Math.abs(st.net)<0.5&&Math.abs(st.highAbove-150)<1&&Math.abs(st.grade-0.15)<0.01||Math.abs(st.grade+0.15)<0.01, JSON.stringify({net:st.net,high:st.highAbove,grade:st.grade}));
// downhill 400 ft drop over 2000 ft: static head > 200
const down=route(2000,x=>900-0.2*x);
r=S(down,500,150); ok('downhill: LDH warning raised', r.overLdh===true&&r.segs[0].pdp===50, `peak ${Math.round(r.peak)} at ${Math.round(r.peakAt)} pdp ${r.segs[0].pdp}`);
// long steep: 4000 ft, 300 ft climb, 1000 gpm cap150 -> several relays; all within cap
const big=route(4000,x=>400+300*x/4000);
r=S(big,1000,150); ok('long steep 1000gpm cap150: multiple relays inside the cap', r.relays.length>=3&&!r.over&&check(big,r,20)&&r.segs.every(s=>s.pdp<=150), `relays ${r.relays.length} pdps ${r.segs.map(s=>s.pdp)}`);
const demand=r.frictionAll+r.climbAll; ok('  engine count is the minimum', r.segs.length===Math.ceil((demand)/(150-20)-1e-6)|| r.segs.length===Math.ceil(demand/130)+0, `demand ${demand.toFixed(0)} segs ${r.segs.length}`);
// manual placement: a bad hand position reports over the limit
r=S(hill,1000,150,20,5,[2]); ok('manual relay near the source: flagged over the limit', r.over===true&&r.auto===false, `pdps ${r.segs.map(s=>s.pdp)}`);
// residual 50
r=S(flat(2000),750,150,50); ok('flat 2000ft 750 intake50: PDP 140 (90 + 50)', r.relays.length===0&&r.maxPdp===140, `pdp ${r.maxPdp}`);
// slack and densify
const pts=[{lat:41.26,lng:-73.80},{lat:41.262,lng:-73.80},{lat:41.262,lng:-73.797}];
const den=C.densify(pts,25,400); const len=C.routeFt(pts);
ok('densify keeps the ends and spacing <= 25ft', den.length>=len/25&&Math.abs(den[den.length-1].lng+73.797)<1e-12&&den.length<=400, `n ${den.length} len ${len.toFixed(0)}`);
const ps=C.buildProfile(den,den.map(()=>300),0.10); ok('10% slack on hose length', Math.abs(ps.h[ps.n-1]-len*1.1)<1, `${ps.h[ps.n-1].toFixed(1)} vs ${(len*1.1).toFixed(1)}`);
const long=C.densify([{lat:41.2,lng:-73.8},{lat:41.3,lng:-73.8}],25,400); ok('densify caps the sample count', long.length<=401, `n ${long.length}`);
// ---- hose load limit: one engine lays each section ----
const SM=(p,gpm,cap,maxSeg,man)=>C.solve(p,{gpm,hose:5,cap,residual:20,maxSeg},man);
const segLens=r=>r.segs.map(s=>Math.round(s.hose));
r=SM(flat(2500),500,150,1000); ok('hose limit: flat 2500ft 500gpm, 1000 ft per engine -> 2 relays', r.relays.length===2&&r.segs.every(s=>s.hose<=1000.01)&&!r.overHose, `sections ${segLens(r)} pdps ${r.segs.map(s=>s.pdp)}`);
ok('  sections balanced within 60 ft', Math.max(...segLens(r))-Math.min(...segLens(r))<=60, `${segLens(r)}`);
r=SM(flat(2500),500,150,0); ok('no hose limit: same route, source engine alone', r.relays.length===0);
r=SM(flat(1000),750,150,1000); ok('hose limit: 1000 ft route fits one engine', r.relays.length===0&&!r.overHose, `sections ${segLens(r)}`);
r=SM(flat(1025),750,150,1000); ok('hose limit: 1025 ft route needs a second section', r.relays.length===1, `sections ${segLens(r)}`);
r=SM(hill,1000,200,1000); ok('hose limit: example 1000gpm cap200 keeps 1 relay, both sections under 1000', r.relays.length===1&&r.segs.every(s=>s.hose<=1000.01), `sections ${segLens(r)} pdps ${r.segs.map(s=>s.pdp)}`);
r=SM(big,500,200,1000); ok('hose limit drives the count: 4000ft at 500gpm -> 4+ sections, pressure still inside the cap', r.segs.length>=5&&!r.over&&r.segs.every(s=>s.hose<=1000.01)&&check(big,r,20), `sections ${segLens(r)} pdps ${r.segs.map(s=>s.pdp)}`);
r=SM(flat(2500),500,150,1000,[8]); ok('hand placement that breaks the hose limit is flagged', r.overHose===true&&r.segs[1].overHose===true&&!r.segs[0].overHose, `sections ${segLens(r)}`);
r=SM(flat(2500),500,150,600); ok('600 ft per engine -> every section <= 600', r.segs.every(s=>s.hose<=600.01)&&r.segs.length===5, `sections ${segLens(r)}`);
// ---- v0.3 road draft: nearest road point, simplify, district polygon, draft route ----
// ft east and north of a fixed corner near YHFD; 1 deg lat = 364,812 ft by the same sphere
const KLAT=20902260*Math.PI/180, LAT0=41.27, LNG0=-73.79, KLNG=KLAT*Math.cos(LAT0*Math.PI/180);
const P=(x,y)=>({lat:LAT0+y/KLAT,lng:LNG0+x/KLNG}), LL=(x,y)=>[LNG0+x/KLNG,LAT0+y/KLAT], HY=(x,y,n)=>[LNG0+x/KLNG,LAT0+y/KLAT,n,'YKTWN'];
// nearest point on a path: 50 ft north of a segment that runs 1,000 ft east
let nn=C.nearestOnPaths(P(400,50),[[LL(0,0),LL(1000,0)],[LL(0,500),LL(1000,500)]]);
ok('nearestOnPaths: distance and position on a segment', nn&&nn.path===0&&nn.seg===0&&Math.abs(nn.ft-50)<1&&Math.abs(nn.t-0.4)<0.01&&C.distFt(nn,P(400,0))<1, JSON.stringify(nn));
ok('nearestOnPaths: no paths gives null, a point past the end clamps to the end', C.nearestOnPaths(P(0,0),[])===null&&C.distFt(C.nearestOnPaths(P(1200,0),[[LL(0,0),LL(1000,0)]]),P(1000,0))<1);
// simplify: collinear points go, a corner stays
const sq=[P(0,0),P(0,100),P(0,200),P(0,203),P(100,203)], sp=C.simplify(sq,8);
ok('simplify drops collinear points and keeps the corner', sp.length===3&&sp[0]===sq[0]&&sp[1]===sq[3]&&sp[2]===sq[4]&&C.simplify([sq[0],sq[4]],8).length===2, `kept ${sp.length}`);
// point in polygon: a hole, and the second part of a MultiPolygon
const ring=(a,b)=>[[a,a],[b,a],[b,b],[a,b],[a,a]], poly={type:'Polygon',coordinates:[ring(0,10),ring(4,6)]}, multi={type:'MultiPolygon',coordinates:[[ring(0,10),ring(4,6)],[ring(20,30)]]};
ok('pointInPolygon: inside, outside, and inside a hole', C.pointInPolygon(2,2,poly)&&!C.pointInPolygon(15,5,poly)&&!C.pointInPolygon(5,5,poly));
ok('pointInPolygon: second part of a MultiPolygon', C.pointInPolygon(25,25,multi)&&C.pointInPolygon(2,2,multi)&&!C.pointInPolygon(5,5,multi)&&!C.pointInPolygon(15,15,multi));
// road grid: a narrow U. H1 is the nearest hydrant in a straight line (120 ft) but 800 ft by road. H2 is 200 ft by road.
const roads=[{name:'Left Rd',path:[LL(500,400),LL(500,0)]},{name:'Bottom Rd',path:[LL(500,0),LL(600,0)]},{name:'Right Rd',path:[LL(600,0),LL(600,300)]},{name:'Island Rd',path:[LL(700,300),LL(700,200)]}];
const AD=P(620,300), H1=HY(500,400,'H-1'), H2=HY(610,100,'H-2'), H3=HY(700,300,'H-3'), H5=HY(330,100,'H-5');
let d=C.draftRoute(AD,[H1,H2,H3],roads,{});
ok('draftRoute: picks the hydrant that is shortest by road, not by straight line', d&&d.hydrant[2]==='H-2'&&Math.abs(d.roadFt-200)<2, d&&`${d.hydrant[2]} roadFt ${d.roadFt.toFixed(1)}`);
ok('  water order: first point is the hydrant, last point is the road point near the address (20 ft, short driveway)', d&&d.points[0].lat===H2[1]&&d.points[0].lng===H2[0]&&C.distFt(d.points[d.points.length-1],P(600,300))<1&&d.points.length>=3, d&&`${d.points.length} points`);
ok('  the hydrant on a disconnected road is not selected', d&&d.hydrant[2]!=='H-3'&&C.draftRoute(AD,[H3],roads,{})===null);
ok('  a hydrant more than 150 ft from a road is ignored', C.draftRoute(AD,[H5],roads,{})===null&&C.draftRoute(AD,[H2,H5],roads,{}).hydrant[2]==='H-2'&&C.draftRoute(AD,[H5],roads,{hydMaxFt:200})!==null);
ok('  an address more than 500 ft from a road gives null', C.draftRoute(P(620,1200),[H1,H2],roads,{})===null&&C.draftRoute(P(620,1200),[H1,H2],roads,{addrMaxFt:1000})!==null);
d=C.draftRoute(AD,[H1],roads,{}); const want=C.routeFt([P(500,400),P(500,0),P(600,0),P(600,300)]);
ok('  streets lists the road names used, longest run first', d&&d.hydrant[2]==='H-1'&&d.streets.join()==='Left Rd,Right Rd,Bottom Rd'&&Math.abs(d.roadFt-want)/want<0.01, d&&`${d.streets} roadFt ${d.roadFt.toFixed(1)} want ${want.toFixed(1)}`);
let o={}; C.draftRoute(P(620,1200),[H1,H2],roads,o);
ok('  the reason is road when no road is near the address', o.why==='road', o.why);
o={}; C.draftRoute(AD,[H3],roads,o);
ok('  the reason is hydrant when no hydrant joins by road', o.why==='hydrant', o.why);
// short driveway: an address closer than 100 ft to the road gives a draft that ends on the road
d=C.draftRoute(AD,[H1,H2,H3],roads,{});
ok('draftRoute: address 20 ft from the road ends on the road, shortDrive is true', d&&d.shortDrive===true&&C.distFt(d.points[d.points.length-1],P(600,300))<1&&C.distFt(d.points[d.points.length-1],AD)>15, d&&JSON.stringify(d.points[d.points.length-1]));
const AD99=P(699.5,150), AD100=P(702,150), AD150=P(750,50);
const R2=[{name:'Right Rd',path:[LL(600,0),LL(600,300)]},{name:'Bottom Rd',path:[LL(500,0),LL(600,0)]}];
d=C.draftRoute(P(698.5,150),[H2],R2,{});
ok('  98.5 ft from the road: shortDrive is true', d&&d.shortDrive===true&&C.distFt(d.points[d.points.length-1],P(600,150))<1, d&&`${d.shortDrive}`);
d=C.draftRoute(P(702,150),[H2],R2,{});
ok('  102 ft from the road: the address point stays, shortDrive is false', d&&d.shortDrive===false&&C.distFt(d.points[d.points.length-1],P(702,150))<0.5, d&&`${d.shortDrive}`);
d=C.draftRoute(AD150,[H2],roads,{});
ok('  150 ft from the road: the address point stays', d&&d.shortDrive===false&&C.distFt(d.points[d.points.length-1],AD150)<0.5, d&&`${d.shortDrive} ${d.points.length} points`);
// 1 mile limit: the road path of the chosen draft. A straight road of 5,270 ft drafts, one of 5,290 ft gives null with why far and the feet.
const LONG=ft=>[{name:'Long Rd',path:[LL(0,0),LL(ft,0)]}], HL=HY(0,0,'H-L');
ok('draftRoute: MAX_DRAFT_FT is 5,280', C.MAX_DRAFT_FT===5280);
o={}; d=C.draftRoute(P(5270,0),[HL],LONG(5270),o);
ok('  a road path of 5,270 ft drafts', d&&Math.abs(d.roadFt-5270)<5&&o.why===undefined, d&&d.roadFt);
o={}; d=C.draftRoute(P(5290,0),[HL],LONG(5290),o);
ok('  a road path of 5,290 ft gives null, why far, the hydrant, and the feet', d===null&&o.why==='far'&&o.hydrant[2]==='H-L'&&Math.abs(o.roadFt-5290)<5, JSON.stringify([o.why,o.roadFt]));
console.log(fails?`\n${fails} FAILED`:'\nALL PASS'); process.exit(fails?1:0);
