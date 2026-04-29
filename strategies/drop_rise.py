"""
strategies/drop_rise.py

Strategy: Buy when price drops X% from recent high.
           Sell when price rises Y% from buy price.

Works in 3 modes:
  - backtest : run against historical OHLC data
  - paper    : simulate with live prices, no real orders
  - live     : place real Kite orders
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Trade:
    symbol: str
    buy_price: float
    buy_time: datetime
    sell_price: float | None = None
    sell_time: datetime | None = None
    qty: int = 1
    mode: str = "paper"

    @property
    def is_open(self) -> bool:
        return self.sell_price is None

    @property
    def pnl(self) -> float:
        if self.sell_price is None:
            return 0.0
        return (self.sell_price - self.buy_price) * self.qty

    @property
    def pnl_pct(self) -> float:
        if self.sell_price is None:
            return 0.0
        return ((self.sell_price - self.buy_price) / self.buy_price) * 100

    @property
    def duration(self) -> str:
        if not self.sell_time:
            return "Open"
        delta = self.sell_time - self.buy_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        return f"{h}h {m}m"


@dataclass
class StrategyResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def closed_trades(self):
        return [t for t in self.trades if not t.is_open]

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.closed_trades)

    @property
    def win_rate(self) -> float:
        ct = self.closed_trades
        if not ct:
            return 0.0
        wins = sum(1 for t in ct if t.pnl > 0)
        return (wins / len(ct)) * 100

    @property
    def max_drawdown(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        eq = self.equity_curve["equity"]
        peak = eq.cummax()
        dd = (eq - peak) / peak * 100
        return dd.min()

    @property
    def sharpe(self) -> float:
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return 0.0
        returns = self.equity_curve["equity"].pct_change().dropna()
        if returns.std() == 0:
            return 0.0
        return (returns.mean() / returns.std()) * np.sqrt(252)


def run_backtest(
    df: pd.DataFrame,
    symbol: str,
    drop_pct: float = 10.0,
    rise_pct: float = 5.0,
    qty: int = 1,
    capital: float = 100_000,
    lookback_candles: int = 20,
) -> StrategyResult:
    """
    Backtest the drop-buy / rise-sell strategy.

    df must have columns: [datetime, open, high, low, close, volume]
    """
    df = df.copy().reset_index(drop=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    trades: list[Trade] = []
    equity = capital
    equity_rows = []

    open_trade: Trade | None = None
    recent_high: float = df.iloc[0]["high"]

    for i, row in df.iterrows():
        price = row["close"]
        ts = row["datetime"]

        # Track rolling high over lookback window
        start = max(0, i - lookback_candles)
        recent_high = df.iloc[start:i + 1]["high"].max()

        # ── SELL signal ──────────────────────────────────────────
        if open_trade is not None:
            target = open_trade.buy_price * (1 + rise_pct / 100)
            if price >= target:
                open_trade.sell_price = price
                open_trade.sell_time = ts
                equity += open_trade.pnl
                trades.append(open_trade)
                open_trade = None

        # ── BUY signal ───────────────────────────────────────────
        if open_trade is None:
            drop_threshold = recent_high * (1 - drop_pct / 100)
            if price <= drop_threshold:
                cost = price * qty
                if equity >= cost:
                    open_trade = Trade(
                        symbol=symbol,
                        buy_price=price,
                        buy_time=ts,
                        qty=qty,
                        mode="backtest",
                    )
                    equity -= cost

        # Track equity
        unrealised = (price - open_trade.buy_price) * qty if open_trade else 0
        equity_rows.append({"datetime": ts, "equity": equity + unrealised})

    # Close any open trade at last price
    if open_trade is not None:
        last_price = df.iloc[-1]["close"]
        open_trade.sell_price = last_price
        open_trade.sell_time = df.iloc[-1]["datetime"]
        equity += open_trade.pnl
        trades.append(open_trade)

    equity_df = pd.DataFrame(equity_rows)

    return StrategyResult(trades=trades, equity_curve=equity_df)


# ── Paper / Live helpers ──────────────────────────────────────────────────────

class LiveStrategy:
    """
    Stateful strategy runner for paper and live trading.
    Feed it price ticks; it decides when to buy/sell.
    """

    def __init__(
        self,
        symbol: str,
        exchange: str,
        drop_pct: float = 10.0,
        rise_pct: float = 5.0,
        qty: int = 1,
        mode: Literal["paper", "live"] = "paper",
        kite=None,
    ):
        self.symbol = symbol
        self.exchange = exchange
        self.drop_pct = drop_pct
        self.rise_pct = rise_pct
        self.qty = qty
        self.mode = mode
        self.kite = kite

        self.open_trade: Trade | None = None
        self.trades: list[Trade] = []
        self.day_high: float | None = None
        self.log: list[str] = []

    def _tradingsymbol(self):
        return f"{self.exchange}:{self.symbol}"

    def tick(self, price: float, ts: datetime | None = None) -> str | None:
        """
        Feed a new price. Returns action string or None.
        """
        ts = ts or datetime.now()

        # Track intraday high
        if self.day_high is None or price > self.day_high:
            self.day_high = price

        action = None

        # ── SELL ─────────────────────────────────────────────────
        if self.open_trade is not None:
            target = self.open_trade.buy_price * (1 + self.rise_pct / 100)
            if price >= target:
                self.open_trade.sell_price = price
                self.open_trade.sell_time = ts
                self.trades.append(self.open_trade)
                msg = (
                    f"SELL {self.symbol} @ ₹{price:.2f} | "
                    f"PnL: ₹{self.open_trade.pnl:.2f} ({self.open_trade.pnl_pct:.1f}%)"
                )
                self.log.append(msg)
                if self.mode == "live" and self.kite:
                    self._place_order("SELL", price)
                self.open_trade = None
                action = msg

        # ── BUY ──────────────────────────────────────────────────
        if self.open_trade is None and self.day_high is not None:
            drop_threshold = self.day_high * (1 - self.drop_pct / 100)
            if price <= drop_threshold:
                self.open_trade = Trade(
                    symbol=self.symbol,
                    buy_price=price,
                    buy_time=ts,
                    qty=self.qty,
                    mode=self.mode,
                )
                msg = f"BUY  {self.symbol} @ ₹{price:.2f} | Day High: ₹{self.day_high:.2f}"
                self.log.append(msg)
                if self.mode == "live" and self.kite:
                    self._place_order("BUY", price)
                action = msg

        return action

    def _place_order(self, transaction_type: str, price: float):
        try:
            order_id = self.kite.place_order(
                tradingsymbol=self.symbol,
                exchange=self.exchange,
                transaction_type=transaction_type,
                quantity=self.qty,
                order_type=self.kite.ORDER_TYPE_MARKET,
                product=self.kite.PRODUCT_MIS,
                variety=self.kite.VARIETY_REGULAR,
            )
            self.log.append(f"  ↳ Order placed: {order_id}")
        except Exception as e:
            self.log.append(f"  ↳ Order FAILED: {e}")

    def reset_day(self):
        self.day_high = None
        self.open_trade = None

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades if not t.is_open)
