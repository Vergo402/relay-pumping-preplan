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
const S=(p,gpm,cap,basis='chart',res=20,hose=5,man)=>C.solve(p,{gpm,hose,basis,cap,residual:res},man);
ok('FL chart 5in', C.flPer100(5,500,'chart')===2&&C.flPer100(5,750,'chart')===5&&C.flPer100(5,1000,'chart')===10);
ok('FL formula 5in', Math.abs(C.flPer100(5,750,'formula')-4.5)<1e-9&&Math.abs(C.flPer100(5,1000,'formula')-8)<1e-9&&Math.abs(C.flPer100(5,500,'formula')-2)<1e-9);
ok('FL 4in', C.flPer100(4,1000,'chart')===20&&Math.abs(C.flPer100(4,750,'formula')-11.25)<1e-9);
let p=flat(2600), r=S(p,750,150);
ok('flat 2600ft 750gpm cap150 chart: no relay, PDP 150', r.relays.length===0&&r.maxPdp===150&&!r.over, `relays ${r.relays.length} pdp ${r.maxPdp} hose ${p.h[p.n-1].toFixed(1)}`);
r=S(flat(2700),750,150); ok('flat 2700ft 750gpm cap150: 1 relay', r.relays.length===1&&!r.over, `pdps ${r.segs.map(s=>s.pdp)} at ${r.segs.map(s=>Math.round(s.at))}`);
ok('  balanced: PDPs within 5 PSI', Math.abs(r.segs[0].pdp-r.segs[1].pdp)<=5, `${r.segs.map(s=>s.pdp)}`);
// chart Max Relay Distance table (formula basis, 20 PSI intake)
const tbl={150:{500:6500,750:2850,1000:1625},200:{500:9000,750:4000,1000:2250}};
for(const cap of [150,200]) for(const q of [500,750,1000]){ const d=tbl[cap][q];
  const a=S(flat(Math.floor(d*0.97/25)*25),q,cap,'formula'), b=S(flat(Math.ceil(d*1.04/25)*25),q,cap,'formula');
  ok(`chart max relay ${q}gpm @${cap}: ${d}ft is the edge`, a.relays.length===0 && b.relays.length===1, `below ${a.relays.length} (pdp ${a.maxPdp}), above ${b.relays.length}`); }
// worked example: 1500 ft, 120 ft climb
const hill=route(1500,x=>500+120*x/1500);
const hoseLen=hill.h[hill.n-1];
r=S(hill,750,200); ok('example 750gpm cap200: PDP ~155, no relay', r.relays.length===0&&r.maxPdp===155, `pdp ${r.maxPdp} hose ${hoseLen.toFixed(1)} friction ${r.frictionAll.toFixed(1)} climb ${r.climbAll}`);
r=S(hill,750,150); ok('example 750gpm cap150: 1 relay', r.relays.length===1&&!r.over, `pdps ${r.segs.map(s=>s.pdp)}`);
r=S(hill,1000,200); ok('example 1000gpm cap200: 1 relay (230 needed)', r.relays.length===1&&!r.over, `pdps ${r.segs.map(s=>s.pdp)} demand ${(r.frictionAll+r.climbAll+20).toFixed(0)}`);
r=S(hill,500,150); ok('example 500gpm cap150: no relay, PDP 110', r.relays.length===0&&r.maxPdp===110, `pdp ${r.maxPdp}`);
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
r=S(hill,1000,150,'chart',20,5,[2]); ok('manual relay near the source: flagged over the limit', r.over===true&&r.auto===false, `pdps ${r.segs.map(s=>s.pdp)}`);
// residual 50
r=S(flat(2000),750,150,'chart',50); ok('flat 2000ft 750 intake50: PDP 150', r.relays.length===0&&r.maxPdp===150, `pdp ${r.maxPdp}`);
// slack and densify
const pts=[{lat:41.26,lng:-73.80},{lat:41.262,lng:-73.80},{lat:41.262,lng:-73.797}];
const den=C.densify(pts,25,400); const len=C.routeFt(pts);
ok('densify keeps the ends and spacing <= 25ft', den.length>=len/25&&Math.abs(den[den.length-1].lng+73.797)<1e-12&&den.length<=400, `n ${den.length} len ${len.toFixed(0)}`);
const ps=C.buildProfile(den,den.map(()=>300),0.10); ok('10% slack on hose length', Math.abs(ps.h[ps.n-1]-len*1.1)<1, `${ps.h[ps.n-1].toFixed(1)} vs ${(len*1.1).toFixed(1)}`);
const long=C.densify([{lat:41.2,lng:-73.8},{lat:41.3,lng:-73.8}],25,400); ok('densify caps the sample count', long.length<=401, `n ${long.length}`);
// ---- hose load limit: one engine lays each section ----
const SM=(p,gpm,cap,maxSeg,man)=>C.solve(p,{gpm,hose:5,basis:'chart',cap,residual:20,maxSeg},man);
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
console.log(fails?`\n${fails} FAILED`:'\nALL PASS'); process.exit(fails?1:0);
