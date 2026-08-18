# CommercialInfraredSauna.com

GitHub Pages-ready commercial sauna economics, opportunity-index and facility-planning site.

## First deployment

1. Upload **all files**, including the hidden `.github` directory.
2. GitHub → **Settings → Pages → Source → GitHub Actions**.
3. Set the custom domain to `commercialinfraredsauna.com`.
4. Point the domain to GitHub Pages.
5. Add the optional-but-recommended repository secret `EIA_API_KEY` under **Settings → Secrets and variables → Actions**.
6. Run **Actions → Update commercial sauna index and deploy → Run workflow** once.

The Census ACS and County Business Patterns APIs do not require an API key for this workload. An EIA API key is needed to refresh the commercial electricity-rate component. If it is absent, the updater preserves the prior electricity-rate values and still refreshes Census data.

## Automatic freshness

The workflow runs every Monday. It refreshes:

- **EIA Electricity Retail Sales** — monthly commercial-sector electricity prices by state.
- **Census American Community Survey** — state population and median household income.
- **Census County Business Patterns** — Fitness and Recreational Sports Centers (NAICS 713940), used as a consistent market-density proxy.

It then recalculates the Opportunity Index, rebuilds all state pages, updates CSV/JSON downloads and regenerates the sitemap.

## Important methodology note

The Commercial Sauna Opportunity Index is a screening framework, not a business forecast. Fitness-center counts are a proxy for potential facility density and are not counts of sauna businesses. State-level commercial electricity prices do not capture every utility tariff, demand charge or local rate.

## Main public assets

- `/rankings/` — all-state Commercial Sauna Opportunity Index
- `/calculators/roi/` — scenario ROI calculator
- `/calculators/capacity/` — throughput calculator
- `/calculators/electrical/` — electricity-cost planner
- `/planning/ada/` — ADA planning reference
- `/data/commercial-sauna-index.csv` — downloadable dataset
- `/data/commercial-sauna-index.json` — JSON dataset

## Data sources

- U.S. Energy Information Administration: Electricity Retail Sales API
- U.S. Census Bureau: American Community Survey 5-Year API
- U.S. Census Bureau: County Business Patterns API
- U.S. Department of Justice: 2010 ADA Standards for Accessible Design
