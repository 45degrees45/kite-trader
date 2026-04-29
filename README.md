# 📈 Kite Trader

A local Streamlit dashboard for backtesting and live-trading on Zerodha Kite.

## Strategy: Drop & Rise
- **BUY** when price drops X% from the recent high
- **SELL** when price rises Y% from your buy price
- Default: 10% drop → buy, 5% rise → sell (fully configurable)

## Quick Start (Ubuntu)

```bash
# 1. Clone / copy this folder, then:
chmod +x setup.sh
./setup.sh

# 2. Add your credentials
nano .env
# Set KITE_API_KEY and KITE_API_SECRET

# 3. Run
source venv/bin/activate
streamlit run app.py
```

Open **http://localhost:8501**

## Pages

| Page | What it does |
|------|-------------|
| 🔐 Connect | Kite OAuth login |
| 📊 Backtest | Historical backtest with equity curve, trade log, charts |
| 🤖 Paper Trade | Live simulation — no real orders |
| ⚡ Live Trade | Real orders via Kite API |
| 📋 Settings | Update credentials |

## Getting Kite API Credentials

1. Go to https://developers.kite.trade/
2. Create an app → get API Key + Secret
3. Set redirect URL to `http://127.0.0.1/` (for local login)

## File Structure

```
kite-trader/
├── app.py               # Main Streamlit app
├── requirements.txt
├── setup.sh
├── .env                 # Your credentials (never commit this)
├── core/
│   ├── kite_manager.py  # Auth / session
│   └── data.py          # Historical + live data fetchers
└── strategies/
    └── drop_rise.py     # Backtest engine + live strategy runner
```
