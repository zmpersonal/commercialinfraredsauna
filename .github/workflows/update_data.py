#!/usr/bin/env python3
from pathlib import Path
import os, json, subprocess, sys
from datetime import datetime, timezone
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
STATE_FIPS = {
    '01':'AL','02':'AK','04':'AZ','05':'AR','06':'CA','08':'CO','09':'CT','10':'DE','11':'DC','12':'FL','13':'GA','15':'HI','16':'ID','17':'IL','18':'IN','19':'IA','20':'KS','21':'KY','22':'LA','23':'ME','24':'MD','25':'MA','26':'MI','27':'MN','28':'MS','29':'MO','30':'MT','31':'NE','32':'NV','33':'NH','34':'NJ','35':'NM','36':'NY','37':'NC','38':'ND','39':'OH','40':'OK','41':'OR','42':'PA','44':'RI','45':'SC','46':'SD','47':'TN','48':'TX','49':'UT','50':'VT','51':'VA','53':'WA','54':'WV','55':'WI','56':'WY'
}
STATE_CODES = set(STATE_FIPS.values())

session = requests.Session()
session.headers.update({'User-Agent':'CommercialInfraredSauna.com data updater/1.1 (public-data refresh)'})

def get_json(url, params=None, timeout=75):
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

def require_secret(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError(f'{name} is not set. Add it under Settings > Secrets and variables > Actions.')
    return value

def acs_latest(census_key):
    errors=[]
    for year in (2024, 2023):
        try:
            j = get_json(
                f'https://api.census.gov/data/{year}/acs/acs5',
                {'get':'NAME,B01003_001E,B19013_001E','for':'state:*','key':census_key}
            )
            head=j[0]; out={}
            for row in j[1:]:
                d=dict(zip(head,row)); code=STATE_FIPS.get(d.get('state'))
                if not code: continue
                pop=int(d['B01003_001E']); income=int(d['B19013_001E'])
                if pop <= 0 or income <= 0: continue
                out[code]={'population':pop,'median_household_income':income,'acs_year':year}
            if len(out) >= 51:
                return out, year
            errors.append(f'{year}: only {len(out)} states/DC returned')
        except Exception as e:
            errors.append(f'{year}: {e}')
    raise RuntimeError('ACS refresh failed. ' + ' | '.join(errors))

def cbp_latest(census_key):
    # 2023 is the latest published CBP vintage as of this build. The API example for 2023 uses NAICS2017.
    errors=[]
    for year, naics_var in ((2023,'NAICS2017'), (2022,'NAICS2017')):
        try:
            j = get_json(
                f'https://api.census.gov/data/{year}/cbp',
                {'get':f'NAME,ESTAB,{naics_var},LFO','for':'state:*',naics_var:'713940','key':census_key}
            )
            head=j[0]; by_state={}
            for row in j[1:]:
                d=dict(zip(head,row)); code=STATE_FIPS.get(d.get('state'))
                if not code: continue
                try: est=int(d.get('ESTAB') or 0)
                except ValueError: continue
                # State CBP can include legal-form detail. The LFO=001 row is total for all legal forms;
                # when not present, retain the largest establishment count as a defensive fallback.
                lfo=str(d.get('LFO',''))
                if lfo == '001':
                    by_state[code]=est
                elif code not in by_state:
                    by_state[code]=est
                else:
                    by_state[code]=max(by_state[code],est)
            if len(by_state) >= 51:
                return by_state, year
            errors.append(f'{year}: only {len(by_state)} states/DC returned')
        except Exception as e:
            errors.append(f'{year}: {e}')
    raise RuntimeError('CBP refresh failed. ' + ' | '.join(errors))

def eia_rates(eia_key):
    params=[
        ('api_key',eia_key),('frequency','monthly'),('data[0]','price'),
        ('facets[sectorid][]','COM'),('sort[0][column]','period'),('sort[0][direction]','desc'),
        ('offset','0'),('length','5000')
    ]
    j=get_json('https://api.eia.gov/v2/electricity/retail-sales/data/', params)
    data=j.get('response',{}).get('data',[])
    out={}; periods={}
    for d in data:
        code=d.get('stateid')
        if code not in STATE_CODES: continue
        period=str(d.get('period',''))
        if code in periods and period <= periods[code]: continue
        try: price=float(d.get('price'))
        except (TypeError, ValueError): continue
        if price <= 0: continue
        out[code]={'commercial_rate_cents':price,'rate_period':period}
        periods[code]=period
    if len(out) < 51:
        raise RuntimeError(f'EIA refresh failed: only {len(out)} states/DC returned. Verify EIA_API_KEY and API response.')
    return out, max(periods.values())

def main():
    census_key=require_secret('CENSUS_API_KEY')
    eia_key=require_secret('EIA_API_KEY')

    obj=json.loads((DATA/'state_index.json').read_text())
    rows={r['state_code']:r for r in obj['states']}

    print('Refreshing ACS...')
    acs,acs_year=acs_latest(census_key)
    print(f'ACS OK: {len(acs)} jurisdictions, vintage {acs_year}')

    print('Refreshing County Business Patterns...')
    cbp,cbp_year=cbp_latest(census_key)
    print(f'CBP OK: {len(cbp)} jurisdictions, vintage {cbp_year}')

    print('Refreshing EIA commercial electricity rates...')
    eia,eia_period=eia_rates(eia_key)
    print(f'EIA OK: {len(eia)} jurisdictions, latest period {eia_period}')

    for code,r in rows.items():
        r.update(acs[code])
        r['fitness_establishments']=cbp[code]
        r['cbp_year']=cbp_year
        r.update(eia[code])
        pop=r['population']
        r['fitness_establishments_per_100k']=round(r['fitness_establishments']/pop*100000,2)

    meta=obj.get('metadata',{})
    meta.update({
        'updated_at':datetime.now(timezone.utc).isoformat(),
        'live':True,
        'acs_year':acs_year,
        'cbp_year':cbp_year,
        'eia_period':eia_period,
        'source_status':{'acs':'live','cbp':'live','eia':'live'},
        'sources':{
            'acs':'U.S. Census Bureau ACS 5-Year',
            'cbp':'U.S. Census Bureau County Business Patterns',
            'eia':'U.S. EIA Electricity Retail Sales'
        }
    })
    (DATA/'state_index.json').write_text(json.dumps({'metadata':meta,'states':list(rows.values())},indent=2))
    subprocess.run([sys.executable,str(ROOT/'scripts/build.py')],check=True)

    print('Refresh complete. Site rebuilt from live government data.')

if __name__=='__main__':
    main()
