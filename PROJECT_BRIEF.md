# PROJECT BRIEF — Kite Trader

## Problem Statement
Testing a price-drop buy / price-rise sell trading strategy on Zerodha requires either expensive backtesting software or manual spreadsheet work. There is no simple, local dashboard for this specific strategy with live trading integration.

## Solution Built
A Streamlit dashboard with 4 modes: OAuth login, historical backtest with equity curve, paper trading simulation, and live order execution via the Zerodha Kite API. Fully configurable drop % and rise % thresholds.

## Key Features
- Drop & Rise strategy: BUY on X% drop from recent high, SELL on Y% rise from buy
- Historical backtest with trade log and equity curve chart
- Paper trade mode (live prices, no real orders)
- Live trade mode (real Kite API orders)
- Kite OAuth login flow
- Configurable thresholds via Settings page

## Tech Stack
Python · Streamlit · Zerodha Kite Connect API · pandas · plotly

## Status
MVP Done

## Vibe Coding Effort
Sessions: ___ | Est. Hours: ___

## Users & Signups
Active Users: ___ | Live Trading: Yes / No

## Growth Tracking
_Track backtest performance, live trade P&L, strategy iterations._

## Last Updated
2026-03 (Mar 2026)

## Key Files
- `app.py` — Streamlit dashboard
- `core/kite_manager.py` — auth and session
- `core/data.py` — historical and live data
- `strategies/drop_rise.py` — strategy engine
