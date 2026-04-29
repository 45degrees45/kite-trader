# Architecture

Kite Trader is a local Streamlit dashboard for backtesting and live-trading Indian equities on Zerodha Kite using a **Drop & Rise** strategy: buy when price drops a configurable percentage from its recent high, sell when it rises a configurable percentage from the buy price.

```mermaid
flowchart TD
    User["User (Browser\nhttp://localhost:8501)"]

    subgraph Streamlit["app.py — Streamlit Dashboard"]
        Connect["🔐 Connect Page\nOAuth login flow"]
        Backtest["📊 Backtest Page\nHistorical simulation"]
        Paper["🤖 Paper Trade Page\nSimulated live trading"]
        Live["⚡ Live Trade Page\nReal order execution"]
        Settings["📋 Settings Page\nCredential management"]
    end

    subgraph Core["core/"]
        KiteMgr["kite_manager.py\nAuth & session\nget_kite / complete_login"]
        Data["data.py\nfetch_historical\nsearch_instruments / get_ltp"]
    end

    subgraph Strategy["strategies/"]
        DropRise["drop_rise.py\nDrop & Rise Strategy"]
        RunBacktest["run_backtest()\nIterates OHLC candles\nequity curve + trade log"]
        LiveStrat["LiveStrategy\ntick(price) per poll cycle\n5-second refresh loop"]
    end

    EnvFile[".env\nKITE_API_KEY\nKITE_API_SECRET\nKITE_ACCESS_TOKEN"]

    subgraph KiteAPI["Zerodha Kite API"]
        OAuth["OAuth 2.0\nrequest_token → access_token"]
        Historical["historical_data()\nOHLCV candles"]
        LTP["ltp()\nLast Traded Price"]
        Orders["place_order()\nMarket orders\n(live mode only)"]
        Instruments["instruments()\nSymbol search"]
    end

    User -->|"navigates pages"| Streamlit
    Connect -->|"generate_login_url\ncomplete_login"| KiteMgr
    Backtest -->|"search_instruments\nfetch_historical"| Data
    Backtest -->|"run_backtest(df)"| RunBacktest
    Paper -->|"get_ltp every 5s"| Data
    Paper -->|"tick(price)"| LiveStrat
    Live -->|"get_ltp every 5s"| Data
    Live -->|"tick(price)"| LiveStrat

    KiteMgr -->|"reads/writes tokens"| EnvFile
    KiteMgr -->|"KiteConnect session"| OAuth
    Data -->|"kite.historical_data"| Historical
    Data -->|"kite.ltp"| LTP
    Data -->|"kite.instruments"| Instruments

    LiveStrat -->|"mode=paper: log only"| Paper
    LiveStrat -->|"mode=live: _place_order"| Orders

    DropRise --> RunBacktest
    DropRise --> LiveStrat
```

## Component Summary

| Component | File | Role |
|-----------|------|------|
| Dashboard | `app.py` | Streamlit UI, page routing, session state, Plotly charts |
| Auth | `core/kite_manager.py` | KiteConnect OAuth, token persistence to `.env` |
| Data | `core/data.py` | Historical OHLCV fetch, instrument search, live LTP |
| Strategy | `strategies/drop_rise.py` | Drop & Rise logic for backtest, paper, and live modes |
| Kite API | external | Zerodha broker API (auth, data, order placement) |
