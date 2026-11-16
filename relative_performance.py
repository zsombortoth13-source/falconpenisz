"""Relative performance of a strategy against its buy & hold benchmark: ONE chart, shown after every run in every app (the lean Monthly-high lab's Backtest, Optimizer and Walk-forward, and the Strategy
Lab's Backtest, Optimizer and Walk-forward). Both curves are rebased to 100 on the first day they both exist; 'relative' is strategy / buy & hold x 100, so above 100 the strategy is ahead of simply
holding the same markets, and a rising line means it is gaining on them. Under it, the strategy's lead over buy & hold in each trailing 12 months (green ahead, red behind).
The numbers (relative_frame, relative_summary) have no Streamlit in them and can be tested on their own; show() draws them."""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

GREEN, RED, GREY = "#2ca02c", "#d62728", "#7f7f7f"


def relative_frame(strategy, benchmark):
    """DataFrame indexed by date with 'Strategy' and 'Buy & hold' (both 100 on the first day both exist), 'Relative' (= strategy / buy & hold x 100) and 'Excess 12m' (the strategy's return over
    the trailing 365 days minus buy & hold's, in percentage points; NaN in the first year). None when either curve is missing or too short to compare."""
    if strategy is None or benchmark is None:
        return None
    s = pd.Series(strategy).astype(float).dropna()
    if len(s) < 3:
        return None
    b = pd.Series(benchmark).astype(float).sort_index()
    b = b[~b.index.duplicated(keep="last")].reindex(s.index.union(b.index)).ffill().reindex(s.index)          # buy & hold on the strategy's days (its own gaps carried forward)
    ok = (s > 0) & (b > 0)
    s, b = s[ok], b[ok]
    if len(s) < 3:
        return None
    frame = pd.DataFrame({"Strategy": s / s.iloc[0] * 100.0, "Buy & hold": b / b.iloc[0] * 100.0})
    frame["Relative"] = frame["Strategy"] / frame["Buy & hold"] * 100.0
    back = frame.index - pd.Timedelta(days=365)
    ret = {c: frame[c].to_numpy() / frame[c].asof(back).to_numpy() - 1.0 for c in ("Strategy", "Buy & hold")}
    frame["Excess 12m"] = (ret["Strategy"] - ret["Buy & hold"]) * 100.0
    return frame


def relative_summary(frame) -> dict:
    """{'relative_now': strategy / buy & hold at the end (1.0 = equal), 'edge_per_year': the strategy's compound yearly lead over buy & hold, 'years_ahead': calendar years the strategy beat buy & hold,
    'years': calendar years counted, 'worst_gap': the deepest fall of the relative line from its own best (negative, e.g. -0.45), 'days_ahead_12m': share of days the trailing 12 months were ahead}."""
    rel = frame["Relative"]
    years = max((frame.index[-1] - frame.index[0]).days / 365.25, 1e-9)
    year_end = frame[["Strategy", "Buy & hold"]].resample("YE").last()
    anchor = pd.concat([frame[["Strategy", "Buy & hold"]].iloc[[0]], year_end])
    anchor = anchor[~anchor.index.duplicated(keep="last")]
    yearly = anchor.pct_change().dropna()
    excess = frame["Excess 12m"].dropna()
    return {"relative_now": float(rel.iloc[-1] / 100.0),
            "edge_per_year": float((rel.iloc[-1] / 100.0) ** (1.0 / years) - 1.0),
            "years_ahead": int((yearly["Strategy"] > yearly["Buy & hold"]).sum()), "years": int(len(yearly)),
            "worst_gap": float((rel / rel.cummax() - 1.0).min()),
            "days_ahead_12m": float((excess > 0).mean()) if len(excess) else float("nan")}


def show(strategy, benchmark, key: str, title: str = "Relative performance vs buy & hold", csv_name: str = "relative_performance.csv"):
    """Draws the relative-performance block: four tiles, the relative line (log scale by default: a strategy that compounds far above buy & hold would flatten everything else), and the trailing
    12-month lead. `key` must be unique on the page (it names the widgets). Says so plainly when there is no benchmark to compare with."""
    st.markdown(f"**{title}**")
    frame = relative_frame(strategy, benchmark)
    if frame is None:
        st.caption("There is no buy & hold curve to compare with, so no relative performance chart.")
        return
    info = relative_summary(frame)
    st.caption("Strategy equity divided by equal-weight buy & hold of the same markets, both starting at 100 on the first day they share. Above 100 the strategy is ahead of just holding them; a rising "
               "line means it is gaining on them, a falling line that buy & hold is catching up.")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Now vs buy & hold", f"{info['relative_now']:,.2f}x", border=True, help="Strategy's final equity relative to buy & hold's, both rebased to the same start: 2.00x = twice as far.")
    t2.metric("Lead per year", f"{info['edge_per_year'] * 100:+.1f}%", border=True, help="The yearly compound growth of the relative line: the strategy's CAGR against buy & hold's, as a ratio.")
    t3.metric("Calendar years ahead", f"{info['years_ahead']} of {info['years']}", border=True, help="Calendar years (the first and last may be partial) in which the strategy returned more than buy & hold.")
    t4.metric("Worst stretch behind", f"{info['worst_gap'] * 100:.0f}%", border=True,
              help="The deepest fall of the relative line from its own highest point: how far the strategy slid back towards (or below) buy & hold at its worst.")
    log_scale = st.toggle("Log scale", value=True, key=f"{key}_log")
    weekly = frame.resample("W").last().dropna(subset=["Relative"])
    weekly.index.name = "date"
    data = weekly.reset_index()
    line = alt.Chart(data).mark_line(color="#1f77b4").encode(
        x=alt.X("date:T", title=None), y=alt.Y("Relative:Q", title="Strategy / buy & hold (100 = equal)", scale=alt.Scale(type="log" if log_scale else "linear", zero=False)),
        tooltip=["date:T", alt.Tooltip("Relative:Q", format=",.1f", title="Relative"), alt.Tooltip("Strategy:Q", format=",.1f"), alt.Tooltip("Buy & hold:Q", format=",.1f")])
    base = alt.Chart(pd.DataFrame({"y": [100.0]})).mark_rule(color=GREY, strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart(alt.layer(line, base).properties(height=300), width="stretch")
    lead = data.dropna(subset=["Excess 12m"]).copy()
    if len(lead):
        lead["Ahead"] = lead["Excess 12m"].clip(lower=0)
        lead["Behind"] = lead["Excess 12m"].clip(upper=0)
        st.caption("The strategy's return over the trailing 12 months minus buy & hold's (percentage points): green when it was ahead, red when behind.")
        tip = ["date:T", alt.Tooltip("Excess 12m:Q", format="+.1f", title="12-month lead, pts")]
        ahead = alt.Chart(lead).mark_area(color=GREEN, opacity=0.55).encode(x=alt.X("date:T", title=None), y=alt.Y("Ahead:Q", title=None), tooltip=tip)
        behind = alt.Chart(lead).mark_area(color=RED, opacity=0.55).encode(x="date:T", y="Behind:Q", tooltip=tip)
        st.altair_chart(alt.layer(ahead, behind).properties(height=150), width="stretch")
        if not np.isnan(info["days_ahead_12m"]):
            st.caption(f"Ahead of buy & hold over the trailing 12 months on {info['days_ahead_12m'] * 100:.0f}% of the days.")
    st.download_button("Download the relative performance (CSV)", frame.round(4).to_csv().encode(), csv_name, "text/csv", key=f"{key}_dl")
