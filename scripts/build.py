#!/usr/bin/env python3
from pathlib import Path
import json, csv, math, statistics, html, re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SITE = 'https://commercialinfraredsauna.com'

STATE_NAMES = {
'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','DC':'District of Columbia','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}


def slug(s):
    return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')

def money(x, d=0):
    if x is None: return '—'
    return f"${x:,.{d}f}"

def num(x):
    if x is None: return '—'
    return f"{x:,.0f}"

def pct(x):
    if x is None: return '—'
    return f"{x:.1f}%"

def esc(x): return html.escape(str(x))

def norm(values, invert=False):
    vals=[v for v in values if v is not None]
    lo,hi=min(vals),max(vals)
    def f(v):
        if v is None: return 50.0
        if hi==lo: return 50.0
        z=(v-lo)/(hi-lo)*100
        return 100-z if invert else z
    return f

def compute_scores(rows):
    # Opportunity score: lower commercial rates are better, more fitness establishments per 100k is better,
    # higher household income is better, larger population provides more absolute market depth.
    ratef=norm([r.get('commercial_rate_cents') for r in rows], invert=True)
    densf=norm([r.get('fitness_establishments_per_100k') for r in rows])
    incf=norm([r.get('median_household_income') for r in rows])
    popf=norm([math.log10(max(r.get('population') or 1,1)) for r in rows])
    for r in rows:
        score=(0.35*ratef(r.get('commercial_rate_cents'))+
               0.30*densf(r.get('fitness_establishments_per_100k'))+
               0.20*incf(r.get('median_household_income'))+
               0.15*popf(math.log10(max(r.get('population') or 1,1))))
        r['opportunity_score']=round(score,1)
    for i,r in enumerate(sorted(rows,key=lambda x:x['opportunity_score'],reverse=True),1):
        r['rank']=i
    return rows

def head(title, desc, canonical, extra=''):
    return f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{canonical}">
<link rel="stylesheet" href="/assets/site.css"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">{extra}</head><body>'''

def nav():
    return '''<header class="topbar"><a class="brand" href="/"><span class="mark">CIS</span><span>CommercialInfraredSauna.com</span></a><nav><a href="/rankings/">Index</a><a href="/calculators/roi/">ROI</a><a href="/calculators/capacity/">Capacity</a><a href="/planning/ada/">ADA</a><a href="/methodology/">Methodology</a></nav></header>'''

def foot(meta):
    updated=meta.get('updated_at','Not yet refreshed')
    return f'''<footer><div><strong>Commercial Infrared Sauna Intelligence</strong><p>Independent planning data and scenario tools for commercial facilities.</p></div><div class="footmeta">Data build: {esc(updated[:10] if updated else 'pending')}<br><a href="/data/commercial-sauna-index.csv">Download CSV</a> · <a href="/methodology/">Methodology</a></div></footer></body></html>'''

def write(path, content):
    p=ROOT/path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content, encoding='utf-8')

def metric(label, value, sub=''):
    return f'<div class="metric"><span>{esc(label)}</span><strong>{esc(value)}</strong><small>{esc(sub)}</small></div>'

def status_banner(meta):
    if meta.get('live'):
        return ''
    return '<div class="notice">Starter planning dataset. Run the GitHub <strong>Update commercial sauna index</strong> workflow to replace preview values with current Census and EIA data.</div>'

def build_home(rows,meta):
    ranked=sorted(rows,key=lambda x:x['opportunity_score'],reverse=True)
    national_rate=statistics.mean([r['commercial_rate_cents'] for r in rows if r.get('commercial_rate_cents')])
    total_fit=sum(r.get('fitness_establishments') or 0 for r in rows)
    top=ranked[:8]
    rowshtml=''.join(f'''<tr><td class="rank">#{r['rank']}</td><td><a href="/states/{slug(r['state_name'])}/">{esc(r['state_name'])}</a></td><td><b>{r['opportunity_score']:.1f}</b></td><td>{r['commercial_rate_cents']:.1f}¢</td><td>{r['fitness_establishments_per_100k']:.1f}</td><td>{money(r['median_household_income'])}</td></tr>''' for r in top)
    schema=json.dumps({"@context":"https://schema.org","@type":"Dataset","name":"U.S. Commercial Sauna Opportunity Index","description":"State-level commercial sauna planning index combining electricity rates, fitness establishment density, household income and population.","url":SITE+"/","creator":{"@type":"Organization","name":"CommercialInfraredSauna.com"},"distribution":[{"@type":"DataDownload","encodingFormat":"text/csv","contentUrl":SITE+"/data/commercial-sauna-index.csv"}]})
    htmlx=head('Commercial Sauna Economics & Opportunity Index | CommercialInfraredSauna.com','Commercial sauna operating-cost benchmarks, market opportunity rankings, ROI calculators and facility planning references.',SITE+'/',f'<script type="application/ld+json">{schema}</script>')+nav()+status_banner(meta)+f'''
<main>
<section class="hero"><div class="eyebrow">COMMERCIAL HEAT-THERAPY INTELLIGENCE</div><h1>Plan the economics before you build the sauna.</h1><p class="lede">State-by-state commercial electricity costs, fitness-market density, ROI scenarios, throughput planning and accessibility references for gyms, spas, hotels, multifamily properties and recovery studios.</p><div class="hero-actions"><a class="btn" href="/calculators/roi/">Run ROI scenario</a><a class="btn ghost" href="/rankings/">Explore the index</a></div></section>
<section class="metric-grid">{metric('States + D.C.','51','indexed markets')}{metric('Avg. commercial power',f'{national_rate:.1f}¢/kWh','current/preview dataset')}{metric('Fitness establishments',f'{total_fit:,}','NAICS 713940 proxy')}{metric('Index leader',top[0]['state_name'],f"score {top[0]['opportunity_score']:.1f}/100")}</section>
<section class="split"><div><div class="eyebrow">THE INDEX</div><h2>Where do commercial sauna economics look most favorable?</h2><p>The Opportunity Index combines four public-data signals: commercial electricity affordability, fitness-center density, household income and population depth. It is a screening tool—not a forecast of business success.</p><a class="textlink" href="/methodology/">See weights, limitations and source definitions →</a></div><div class="formula-card"><div><b>35%</b><span>Commercial electricity affordability</span></div><div><b>30%</b><span>Fitness establishment density</span></div><div><b>20%</b><span>Median household income</span></div><div><b>15%</b><span>Population depth</span></div></div></section>
<section><div class="section-head"><div><div class="eyebrow">TOP MARKETS</div><h2>Commercial Sauna Opportunity Index</h2></div><a class="textlink" href="/rankings/">View all 51 →</a></div><div class="table-wrap"><table><thead><tr><th>Rank</th><th>State</th><th>Score</th><th>Commercial power</th><th>Fitness /100k</th><th>Median HH income</th></tr></thead><tbody>{rowshtml}</tbody></table></div></section>
<section class="tool-grid"><a class="tool" href="/calculators/roi/"><span>01</span><h3>ROI Scenario Calculator</h3><p>Model session pricing, utilization, power, labor and fixed investment without presenting the result as an earnings guarantee.</p></a><a class="tool" href="/calculators/capacity/"><span>02</span><h3>Capacity & Throughput</h3><p>Estimate theoretical and utilization-adjusted sessions per day from seats, session length and reset time.</p></a><a class="tool" href="/calculators/electrical/"><span>03</span><h3>Electrical Cost Planner</h3><p>Translate sauna kW, operating hours and state electricity rates into energy and cost scenarios.</p></a><a class="tool" href="/planning/ada/"><span>04</span><h3>ADA Planning Reference</h3><p>Plain-language orientation to federal sauna and steam-room accessibility provisions, with primary-source links.</p></a></section>
<section class="home-link"><div><div class="eyebrow">RESIDENTIAL PROJECT?</div><h2>This database is built for commercial facilities.</h2><p>If your project is for a private home rather than a gym, spa, hotel or multifamily amenity, browse residential sauna options separately.</p></div><a class="btn" href="https://inhousewellness.com/collections/saunas">Explore home saunas at InHouse Wellness</a></section>
</main>'''+foot(meta)
    write('index.html',htmlx)

def build_rankings(rows,meta):
    ranked=sorted(rows,key=lambda x:x['rank'])
    trs=''.join(f'<tr><td class="rank">#{r["rank"]}</td><td><a href="/states/{slug(r["state_name"])}/">{esc(r["state_name"])}</a></td><td><b>{r["opportunity_score"]:.1f}</b></td><td>{r["commercial_rate_cents"]:.1f}¢</td><td>{r["fitness_establishments_per_100k"]:.1f}</td><td>{num(r["fitness_establishments"])}</td><td>{money(r["median_household_income"])}</td><td>{num(r["population"])}</td></tr>' for r in ranked)
    h=head('U.S. Commercial Sauna Opportunity Index — State Rankings','Rank all 50 states and D.C. using commercial electricity, fitness-establishment density, household income and population.',SITE+'/rankings/')+nav()+status_banner(meta)+f'''<main><section class="pagehero"><div class="eyebrow">2026 DATA PRODUCT</div><h1>U.S. Commercial Sauna Opportunity Index</h1><p>Comparative state-level screening data for commercial sauna and recovery-facility planning.</p></section><section class="callout"><strong>How to use this:</strong> A higher score means the state currently combines lower commercial power costs, stronger fitness-business density, higher income and larger market depth. It does not measure local rent, competition, permitting, construction cost or customer demand.</section><section><div class="table-wrap"><table><thead><tr><th>Rank</th><th>State</th><th>Score</th><th>Power</th><th>Fitness /100k</th><th>Fitness est.</th><th>Median income</th><th>Population</th></tr></thead><tbody>{trs}</tbody></table></div><p class="download"><a class="btn ghost" href="/data/commercial-sauna-index.csv">Download CSV</a> <a class="btn ghost" href="/data/commercial-sauna-index.json">Download JSON</a></p></section></main>'''+foot(meta)
    write('rankings/index.html',h)

def build_state(r,meta):
    # standardized 6 kW scenario
    daily_kwh=6*8
    monthly_cost=daily_kwh*30*r['commercial_rate_cents']/100
    session_cost=(6*0.5*r['commercial_rate_cents']/100)
    schema=json.dumps({"@context":"https://schema.org","@type":"Dataset","name":f"{r['state_name']} Commercial Sauna Economics","description":f"Commercial electricity and fitness-market planning indicators for {r['state_name']}.","url":SITE+f"/states/{slug(r['state_name'])}/"})
    content=head(f"Commercial Sauna Economics in {r['state_name']} | Cost & Market Data",f"Commercial sauna operating-cost estimates and market indicators for {r['state_name']}, including electricity rates and fitness establishment density.",SITE+f"/states/{slug(r['state_name'])}/",f'<script type="application/ld+json">{schema}</script>')+nav()+status_banner(meta)+f'''<main><section class="pagehero statehero"><div class="eyebrow">STATE PROFILE · RANK #{r['rank']}</div><h1>{esc(r['state_name'])} commercial sauna economics</h1><p>Current planning indicators for commercial infrared sauna installations and recovery facilities.</p></section><section class="metric-grid">{metric('Opportunity score',f"{r['opportunity_score']:.1f}/100",f"U.S. rank #{r['rank']}")}{metric('Commercial electricity',f"{r['commercial_rate_cents']:.1f}¢/kWh",'EIA commercial sector')}{metric('Fitness density',f"{r['fitness_establishments_per_100k']:.1f}/100k",'NAICS 713940 proxy')}{metric('Median household income',money(r['median_household_income']),'ACS')}</section>
<section class="split"><div><div class="eyebrow">STANDARDIZED COST CASE</div><h2>What does a 6 kW sauna cost to operate?</h2><p>Using a standardized 6 kW electrical load for 8 energized hours per day, 30 days per month. Actual infrared sauna power draw, duty cycle and operating schedule vary by equipment and facility.</p></div><div class="formula-card"><div><b>{daily_kwh:.0f} kWh</b><span>energy/day at full load</span></div><div><b>{money(monthly_cost,0)}</b><span>estimated monthly electricity</span></div><div><b>{money(session_cost,2)}</b><span>electricity for a 30-minute full-load session</span></div></div></section>
<section class="content-grid"><article><h2>Market context</h2><p>The Census County Business Patterns proxy currently shows <strong>{num(r['fitness_establishments'])}</strong> Fitness and Recreational Sports Centers (NAICS 713940) in {esc(r['state_name'])}, approximately <strong>{r['fitness_establishments_per_100k']:.1f} establishments per 100,000 residents</strong>.</p><p>This is not a count of sauna businesses. It is used as a consistent national proxy for the density of facilities likely to consider recovery amenities.</p></article><article><h2>Run your own scenario</h2><p>Replace the standardized assumptions with your actual sauna kW, session price, utilization, cleaning/reset time and staffing assumptions.</p><a class="btn" href="/calculators/roi/?state={r['state_code']}">Open ROI calculator</a></article></section></main>'''+foot(meta)
    write(f"states/{slug(r['state_name'])}/index.html",content)

def calc_shell(title,desc,slugpath,inner,script):
    return head(title,desc,SITE+slugpath)+nav()+f'<main><section class="pagehero"><div class="eyebrow">SCENARIO TOOL</div><h1>{esc(title.split(" | ")[0])}</h1><p>{esc(desc)}</p></section>{inner}</main><script>{script}</script>'+foot({'updated_at':'client-side calculator'})

def build_calculators(rows):
    opts=''.join(f'<option value="{r["state_code"]}" data-rate="{r["commercial_rate_cents"]}">{esc(r["state_name"])} — {r["commercial_rate_cents"]:.1f}¢/kWh</option>' for r in sorted(rows,key=lambda x:x['state_name']))
    roi_inner=f'''<section class="calculator"><div class="inputs"><label>State<select id="state">{opts}</select></label><label>Sauna electrical load (kW)<input id="kw" type="number" value="6" min="0.5" step="0.1"></label><label>Seats<input id="seats" type="number" value="4" min="1"></label><label>Session length (minutes)<input id="session" type="number" value="30" min="10"></label><label>Reset / cleaning time (minutes)<input id="reset" type="number" value="10" min="0"></label><label>Open hours / day<input id="hours" type="number" value="12" min="1"></label><label>Utilization<input id="util" type="range" value="45" min="5" max="100"><output id="utilout">45%</output></label><label>Revenue per occupied session<input id="price" type="number" value="25" min="0"></label><label>Monthly labor / cleaning cost<input id="labor" type="number" value="1200" min="0"></label><label>Initial equipment + install<input id="initial" type="number" value="30000" min="0"></label></div><div class="results"><div class="eyebrow">SCENARIO OUTPUT</div><div id="roiresults"></div><p class="fine">Scenario mathematics only. This is not a forecast, appraisal, financial advice or earnings representation. Real-world utilization, maintenance, rent, financing, taxes, insurance, downtime and other costs can materially change results.</p></div></section>'''
    roi_js='''const ids=['state','kw','seats','session','reset','hours','util','price','labor','initial'];ids.forEach(x=>document.getElementById(x).addEventListener('input',go));function go(){let st=document.getElementById('state');let rate=+st.selectedOptions[0].dataset.rate/100,kw=+v('kw'),seats=+v('seats'),session=+v('session'),reset=+v('reset'),hours=+v('hours'),util=+v('util')/100,price=+v('price'),labor=+v('labor'),initial=+v('initial');document.getElementById('utilout').textContent=Math.round(util*100)+'%';let cycles=hours*60/(session+reset),cap=cycles*seats,occupied=cap*util,rev=occupied*price*30,power=kw*hours*30*rate,contrib=rev-power-labor,pay=contrib>0?initial/contrib:null;document.getElementById('roiresults').innerHTML=`<div class="bigresult"><span>Occupied sessions / day</span><b>${occupied.toFixed(1)}</b></div><div class="resultgrid"><div><span>Monthly scenario revenue</span><b>$${rev.toLocaleString(undefined,{maximumFractionDigits:0})}</b></div><div><span>Electricity / month</span><b>$${power.toLocaleString(undefined,{maximumFractionDigits:0})}</b></div><div><span>Contribution before other costs</span><b>$${contrib.toLocaleString(undefined,{maximumFractionDigits:0})}</b></div><div><span>Simple payback</span><b>${pay?pay.toFixed(1)+' months':'Not reached'}</b></div></div>`}function v(id){return document.getElementById(id).value}const q=new URLSearchParams(location.search);if(q.get('state'))document.getElementById('state').value=q.get('state');go();'''
    write('calculators/roi/index.html',calc_shell('Commercial Sauna ROI Scenario Calculator | CommercialInfraredSauna.com','Model commercial sauna revenue, utilization, electricity, labor and simple payback assumptions.','/calculators/roi/',roi_inner,roi_js))

    cap_inner='''<section class="calculator"><div class="inputs"><label>Seats<input id="seats" type="number" value="4" min="1"></label><label>Session minutes<input id="session" type="number" value="30" min="5"></label><label>Reset minutes<input id="reset" type="number" value="10" min="0"></label><label>Open hours/day<input id="hours" type="number" value="12" min="1"></label><label>Utilization<input id="util" type="range" value="60" min="5" max="100"><output id="uout">60%</output></label><label>Operating days/month<input id="days" type="number" value="30" min="1" max="31"></label></div><div class="results"><div class="eyebrow">THROUGHPUT</div><div id="capresults"></div></div></section>'''
    cap_js='''['seats','session','reset','hours','util','days'].forEach(x=>document.getElementById(x).addEventListener('input',go));function n(i){return +document.getElementById(i).value}function go(){let cycles=n('hours')*60/(n('session')+n('reset')),theory=cycles*n('seats'),actual=theory*n('util')/100,month=actual*n('days');document.getElementById('uout').textContent=n('util')+'%';document.getElementById('capresults').innerHTML=`<div class="bigresult"><span>Utilization-adjusted sessions/day</span><b>${actual.toFixed(1)}</b></div><div class="resultgrid"><div><span>Theoretical max/day</span><b>${theory.toFixed(1)}</b></div><div><span>Adjusted/month</span><b>${month.toFixed(0)}</b></div><div><span>Cycles/day</span><b>${cycles.toFixed(1)}</b></div></div>`}go();'''
    write('calculators/capacity/index.html',calc_shell('Commercial Sauna Capacity & Throughput Calculator | CommercialInfraredSauna.com','Estimate sauna session throughput from capacity, session time, reset time, operating hours and utilization.','/calculators/capacity/',cap_inner,cap_js))

    elec_inner=f'''<section class="calculator"><div class="inputs"><label>State<select id="state">{opts}</select></label><label>Sauna load (kW)<input id="kw" type="number" value="6" step="0.1"></label><label>Energized hours/day<input id="hours" type="number" value="8" step="0.5"></label><label>Days/month<input id="days" type="number" value="30" min="1" max="31"></label><label>Average duty factor<input id="duty" type="range" value="75" min="10" max="100"><output id="dout">75%</output></label></div><div class="results"><div class="eyebrow">ENERGY MODEL</div><div id="eresults"></div><p class="fine">Electrical code compliance, circuit sizing and installation must be determined from the equipment documentation and applicable code by qualified professionals.</p></div></section>'''
    elec_js='''['state','kw','hours','days','duty'].forEach(x=>document.getElementById(x).addEventListener('input',go));function n(i){return +document.getElementById(i).value}function go(){let st=document.getElementById('state'),rate=+st.selectedOptions[0].dataset.rate/100,duty=n('duty')/100,kwh=n('kw')*n('hours')*n('days')*duty,cost=kwh*rate;document.getElementById('dout').textContent=n('duty')+'%';document.getElementById('eresults').innerHTML=`<div class="bigresult"><span>Estimated monthly electricity</span><b>$${cost.toFixed(0)}</b></div><div class="resultgrid"><div><span>Monthly energy</span><b>${kwh.toFixed(0)} kWh</b></div><div><span>Rate</span><b>${(rate*100).toFixed(1)}¢/kWh</b></div><div><span>Annualized cost</span><b>$${(cost*12).toFixed(0)}</b></div></div>`}go();'''
    write('calculators/electrical/index.html',calc_shell('Commercial Sauna Electricity Cost Calculator | CommercialInfraredSauna.com','Estimate commercial sauna electricity consumption and operating cost using state commercial power rates.','/calculators/electrical/',elec_inner,elec_js))

def build_ada(meta):
    h=head('Commercial Sauna ADA Planning Guide | Saunas & Steam Rooms','Plain-language planning reference to the 2010 ADA Standards provisions applicable to saunas and steam rooms.',SITE+'/planning/ada/')+nav()+'''<main><section class="pagehero"><div class="eyebrow">FACILITY PLANNING REFERENCE</div><h1>ADA planning for commercial saunas</h1><p>A primary-source-oriented overview of federal accessibility provisions for saunas and steam rooms. This is not legal, architectural or code-compliance advice.</p></section><section class="ada-grid"><article><span class="sectionno">241</span><h2>Scoping</h2><p>The 2010 ADA Standards include specific scoping provisions for saunas and steam rooms. In clusters, accessibility requirements apply according to the federal standard and its exceptions.</p><a class="textlink" href="https://www.ada.gov/law-and-regs/design-standards/2010-stds/">Read the official 2010 ADA Standards →</a></article><article><span class="sectionno">612.2</span><h2>Accessible bench</h2><p>Where seating is provided, at least one bench must comply with the referenced accessible-bench provisions. The standard also addresses the relationship between door swing and required clear floor space.</p></article><article><span class="sectionno">612.3</span><h2>Turning space</h2><p>A turning space complying with the applicable accessibility standard is required within saunas and steam rooms, subject to the stated removable-bench exception.</p></article><article><span class="sectionno">DESIGN</span><h2>Coordinate early</h2><p>Accessibility can affect room dimensions, bench configuration, doors and circulation. Resolve these requirements during architectural planning rather than after equipment selection.</p></article></section><section class="callout"><strong>Important:</strong> Federal ADA requirements are only one layer. State/local building codes, accessibility rules, electrical requirements, fire/life-safety requirements and health-department rules may also apply. Use qualified design and code professionals.</section></main>'''+foot(meta)
    write('planning/ada/index.html',h)

def build_method(meta):
    h=head('Methodology | Commercial Sauna Opportunity Index','Sources, formulas, weights and limitations behind the Commercial Sauna Opportunity Index.',SITE+'/methodology/')+nav()+f'''<main><section class="pagehero"><div class="eyebrow">METHODOLOGY</div><h1>How the index is built</h1><p>The index is designed to be reproducible, transparent and useful for screening—not to predict business success.</p></section><section class="method"><h2>Data sources</h2><div class="source"><b>U.S. Energy Information Administration</b><p>Monthly average retail electricity price for the commercial sector by state. The updater uses EIA's electricity retail-sales API.</p><a href="https://www.eia.gov/opendata/browser/electricity/retail-sales">Primary source</a></div><div class="source"><b>U.S. Census Bureau — County Business Patterns</b><p>State counts of Fitness and Recreational Sports Centers (NAICS 713940). This is a proxy for the density of facilities that may consider recovery amenities; it is not a count of sauna businesses.</p><a href="https://www.census.gov/data/developers/data-sets/cbp-zbp/cbp-api.html">Primary source</a></div><div class="source"><b>U.S. Census Bureau — American Community Survey</b><p>Population and median household income, using the latest configured ACS 5-year release.</p><a href="https://www.census.gov/data/developers/data-sets/acs-5year.html">Primary source</a></div><h2>Opportunity Score</h2><p>Each input is min-max normalized across the 50 states and D.C. Lower electricity prices score higher. The weighted score is:</p><div class="equation">35% electricity affordability + 30% fitness density + 20% median household income + 15% population depth</div><p>Population depth uses the logarithm of population so very large states do not overwhelm the other factors.</p><h2>What the score does not include</h2><p>Local rent, construction cost, commercial lease terms, sales taxes, permitting, competition, customer acquisition, hotel occupancy, gym membership trends, insurance, equipment reliability and actual local demand are not included. These can be decisive.</p><h2>Operating-cost scenarios</h2><p>Electricity estimates are arithmetic scenarios based on entered or standardized kW, energized hours, duty factor and the applicable commercial electricity rate. They are not utility bills and do not account for demand charges or tariff structures.</p><h2>Update cadence</h2><p>The GitHub Action runs weekly. EIA data can change monthly; ACS and CBP update on slower annual schedules. The workflow preserves the previous value when a source is temporarily unavailable.</p></section></main>'''+foot(meta)
    write('methodology/index.html',h)

def build_data(rows,meta):
    # public json/csv
    payload={'metadata':meta,'states':sorted(rows,key=lambda x:x['rank'])}
    (DATA/'commercial-sauna-index.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    fields=['rank','state_code','state_name','opportunity_score','commercial_rate_cents','fitness_establishments','fitness_establishments_per_100k','median_household_income','population','rate_period','acs_year','cbp_year']
    with (DATA/'commercial-sauna-index.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader();
        for r in sorted(rows,key=lambda x:x['rank']): w.writerow({k:r.get(k,'') for k in fields})

def build_sitemap(rows):
    paths=['/','/rankings/','/methodology/','/calculators/roi/','/calculators/capacity/','/calculators/electrical/','/planning/ada/']+[f"/states/{slug(r['state_name'])}/" for r in rows]
    now=datetime.now(timezone.utc).date().isoformat()
    xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{SITE}{p}</loc><lastmod>{now}</lastmod></url>\n' for p in paths)+'</urlset>'
    write('sitemap.xml',xml)

def main():
    obj=json.loads((DATA/'state_index.json').read_text())
    rows=compute_scores(obj['states']); meta=obj.get('metadata',{})
    build_data(rows,meta); build_home(rows,meta); build_rankings(rows,meta)
    for r in rows: build_state(r,meta)
    build_calculators(rows); build_ada(meta); build_method(meta); build_sitemap(rows)
    write('robots.txt','User-agent: *\nAllow: /\nSitemap: https://commercialinfraredsauna.com/sitemap.xml\n')
    write('404.html',head('Page not found | CommercialInfraredSauna.com','Page not found.',SITE+'/404.html')+nav()+'<main><section class="pagehero"><h1>404</h1><p>That facility-planning page does not exist.</p><a class="btn" href="/">Return to the index</a></section></main>'+foot(meta))

if __name__=='__main__': main()
