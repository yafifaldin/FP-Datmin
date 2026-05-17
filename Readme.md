# Earth's Threat Monitor — NASA NEO Dashboard

## Project overview
Multi-page Streamlit dashboard for visualising Near-Earth Object (NEO) data from the NASA NeoWs API. Covers live feed, risk analysis, orbital deep dive, and historical trends.

## Stack
- Python 3.10+
- Streamlit (multi-page)
- requests, pandas, numpy, plotly, scipy
- python-dotenv

## Running locally
```bash
pip install -r requirements.txt
cp .env.example .env          # add your NASA_API_KEY
streamlit run app.py
```

## Project structure
```
app.py                        # entry point, global CSS injection, sidebar
pages/
  1_overview.py               # live 7-day NEO feed, metric cards, bar chart
  2_risk_analysis.py          # scatter, top-15 bar, risk label donut
  3_orbital_deepdive.py       # violin, stacked bar, log-log scatter, K-W test
  4_historical_trend.py       # line, histogram, monthly bar, summary table
  5_ml_analysis.py
utils/
  fetch_data.py               # NASA API calls + pickle cache
  clean_data.py               # JSON → DataFrame parsers
  scoring.py                  # risk score formula + labels
assets/
  style.css                   # global dark-theme overrides
data/
  cache.pkl                   # auto-generated historical cache (git-ignored)
```

## Design system
| Token | Value |
|---|---|
| Background | `#0f0f1a` |
| Card / panel | `#1a1a2e` |
| Accent cyan | `#00d4ff` |
| Accent purple | `#7c3aed` |
| Accent magenta | `#e040fb` |
| Text primary | `#ffffff` |
| Text secondary | `#8892b0` |
| Border | `#2a2a4a` |

## API key
Get a free key at https://api.nasa.gov — without one the app falls back to `DEMO_KEY` (rate-limited). Set `NASA_API_KEY` in `.env`.

## Caching
Historical data is cached to `data/cache.pkl` for 24 h (`ttl=86400` in `st.cache_data`). Delete the file to force a refresh.
