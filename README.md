# Monthly-high lab

Backtest and walk-forward of the monthly-high breakout strategy (entry above its EMA on the first close over a monthly high that is min..max days old, pyramiding on every further signal, an ATR stop that moves up with every add, an ATR take-profit per unit), with Monte Carlo and a chart of every position.

Run locally:

    pip install -r requirements.txt
    streamlit run mh_walkforward_ui.py

Main file for Streamlit Community Cloud: `mh_walkforward_ui.py`.

`cache_prices/` holds saved daily prices so the app starts without downloading; the app refreshes them from Yahoo Finance when they are older than 12 hours and falls back to the saved copy if Yahoo refuses the download.
