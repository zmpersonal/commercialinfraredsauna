#!/usr/bin/env python3
from pathlib import Path
import os, json, time, subprocess, sys
from datetime import datetime, timezone
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
STATE_FIPS={'01':'AL','02':'AK','04':'AZ','05':'AR','06':'CA','08':'CO','09':'CT','10':'DE','11':'DC','12':'FL','13':'GA','15':'HI','16':'ID','17':'IL','18':'IN','19':'IA','20':'KS','21':'KY','22':'LA','23':'ME','24':'MD','25':'MA','26':'MI','27':'MN','28':'MS','29':'MO','30':'MT','31':'NE','32':'NV','33':'NH','34':'NJ','35':'NM','36':'NY','37':'NC','38':'ND','39':'OH','40':'OK','41':'OR','42':'PA','44':'RI','45':'SC','46':'SD','47':'TN','48':'TX','49':'UT','50':'VT','51':'VA','53':'WA','54':'WV','55':'WI','56':'WY'}

session=requests.Session(); session.headers.update({'User-Agent':'CommercialInfraredSauna.com data updater/1.0'})

def get_json(url,params=None,timeout=60):
    r=session.get(url,params=params,timeout=timeout); r.raise_for_status(); return r.json()

def acs_latest():
    for year in (2024,2023):
        try:
            j=get_json(f'https://api.census.gov/data/{year}/acs/acs5',{'get':'NAME,B01003_001E,B19013_001E','for':'state:*'})
            head=j[0]; out={}
            for row in j[1:]:
                d=dict(zip(head,row)); code=STATE_FIPS.get(d.get('state'))
                if code:
                    out[code]={'population':int(d['B01003_001E']),'median_household_income':int(d['B19013_001E']),'acs_year':year}
            if len(out)>=50:return out,year
        except Exception as e: print('ACS',year,'failed:',e)
    return {},None

def cbp_latest():
    # CBP release lags ACS. Try newest plausible vintages and take the largest establishment count per state,
    # which captures the all-establishment total when employment-size/legal-form detail is returned.
    for year in (2024,2023,2022):
        for naics_var in ('NAICS2022','NAICS2017'):
            try:
                j=get_json(f'https://api.census.gov/data/{year}/cbp',{'get':f'NAME,ESTAB,{naics_var}','%s'%naics_var:'713940','for':'state:*'})
                head=j[0]; out={}
                for row in j[1:]:
                    d=dict(zip(head,row)); code=STATE_FIPS.get(d.get('state'))
                    if code:
                        est=int(d.get('ESTAB') or 0)
                        out[code]=max(est,out.get(code,0))
                if len(out)>=45:return out,year
            except Exception as e: print('CBP',year,naics_var,'failed:',e)
    return {},None

def eia_rates():
    key=os.getenv('EIA_API_KEY','').strip()
    if not key:
        print('EIA_API_KEY not set; preserving prior electricity rates.')
        return {},None
    params=[('api_key',key),('frequency','monthly'),('data[0]','price'),('facets[sectorid][]','COM'),('sort[0][column]','period'),('sort[0][direction]','desc'),('offset','0'),('length','5000')]
    try:
        j=get_json('https://api.eia.gov/v2/electricity/retail-sales/data/',params)
        data=j.get('response',{}).get('data',[]); out={}; periods={}
        for d in data:
            code=d.get('stateid') or d.get('stateId')
            if code not in set(STATE_FIPS.values()): continue
            period=d.get('period','')
            if code in periods and period<=periods[code]: continue
            try: price=float(d.get('price'))
            except: continue
            out[code]=price; periods[code]=period
        if len(out)>=45:return {c:{'commercial_rate_cents':v,'rate_period':periods[c]} for c,v in out.items()},max(periods.values()) if periods else None
    except Exception as e: print('EIA failed:',e)
    return {},None

def main():
    obj=json.loads((DATA/'state_index.json').read_text())
    rows={r['state_code']:r for r in obj['states']}
    acs,acs_year=acs_latest(); cbp,cbp_year=cbp_latest(); eia,eia_period=eia_rates()
    for code,r in rows.items():
        if code in acs:r.update(acs[code])
        if code in cbp:r['fitness_establishments']=cbp[code]; r['cbp_year']=cbp_year
        if code in eia:r.update(eia[code])
        pop=r.get('population') or 1
        r['fitness_establishments_per_100k']=round((r.get('fitness_establishments') or 0)/pop*100000,2)
    meta=obj.get('metadata',{})
    meta.update({'updated_at':datetime.now(timezone.utc).isoformat(),'live':bool(acs and cbp),'acs_year':acs_year,'cbp_year':cbp_year,'eia_period':eia_period,'sources':{'acs':'U.S. Census Bureau ACS 5-Year','cbp':'U.S. Census Bureau County Business Patterns','eia':'U.S. EIA Electricity Retail Sales'}})
    (DATA/'state_index.json').write_text(json.dumps({'metadata':meta,'states':list(rows.values())},indent=2))
    subprocess.run([sys.executable,str(ROOT/'scripts/build.py')],check=True)

if __name__=='__main__': main()
