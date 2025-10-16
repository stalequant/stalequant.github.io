# stalequant 2025-04-02

import json
import math
from typing import Any, cast
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, TypedDict

import ccxt
import numpy as np
import pandas as pd
import requests
from ccxt.base.exchange import Exchange

import datetime


### Types

type Coin = str
type ExchangeName = str
type Symbol = str
type CatLabel = str
type SpotFut = Literal["spot", "futures"]


class CutoffSpec(TypedDict):
    kind: Literal["exp", "linear", "reverse_linear"]
    start: float
    end: float
    steps: int


### Constants

STABLE_COINS: set[Coin] = {"USDC", "USDT", "USDH", "USDE", "USD"}

REFERENCE_EXCH: dict[ExchangeName, list[SpotFut]] = {
    "binance": ["spot", "futures"],
    "bybit": ["spot", "futures"],
    "okx": ["spot", "futures"],
    "gate": ["spot", "futures"],
    "kucoin": ["spot", "futures"],
    "mexc": ["spot", "futures"],
    "bitmex": ["futures"],
    "htx": ["futures"],
    "cryptocom": ["spot", "futures"],
    "coinbase": ["spot", "futures"],
    "kraken": ["spot"],
    "krakenfutures": ["futures"],
    "hyperliquid": ["spot", "futures"],
}

# EXCHANGE SPECIFIC COIN NAME VARIANTS
TOKEN_ALIASES: dict[Coin, Coin] = {
    "HPOS10I": "BITCOIN",
    "HPOS": "HPOS",
    "HPO": "HPOS",
    "BITCOIN": "HPOS",
    "NEIROCTO": "NEIRO",
    "1MCHEEMS": "CHEEMS",
    "1MBABYDOGE": "BABYDOGE",
    "JELLYJELLY": "JELLY",
    "UBTC": "BTC",
    "UETH": "ETH",
    "USOL": "SOL",
    "UFART": "FARTCOIN",
    "HPENGU": "PENGU",
    "UPUMP": "PUMP",
    "UUUSPX": "UUUSPX",
    "UBONK": "BONK",
    "UXPL": "XPL",
    "UWLD": "WLD",
    "LINK0": "LINK",
    "AVAX0": "AVAX",
    "AAVE0": "AAVE",
    "Neiro Ethereum": "NEIROETH",
    "HarryPotterObamaSonic10Inu (ERC-20)": "HPOS",
    "FRAX": "FXS",
    "Frax (prev. FXS)": "FXS",
    "XAUT0": "XAUT",
    "BabyDoge": "BabyDoge".upper(),
    "TSTBSC": "TST",
    "BEAMX": "BEAM",
    "RONIN": "RON",
}
EXCH_TOKEN_ALIASES: dict[tuple[Coin, ExchangeName], Coin] = {
    ("NEIRO", "bybit"): "NEIROETH",
    ("NEIRO", "gate"): "NEIROETH",
    ("NEIRO", "kucoin"): "NEIROETH",
}


OUTPUT_CORR_MAT_JSON: str = "hl_screen_corr.json"
OUTPUT_RAW_DATA_JSON: str = "hl_screen_main.json"
OUTPUT_META_JSON: str = "hl_meta.json"


SCORE_CUTOFFS: dict[str, dict[CatLabel, CutoffSpec]] = {
    "Market Cap Score": {
        "MC $m": {"kind": "exp", "start": 1, "end": 5000, "steps": 15},
    },
    "Spot Volume Score": {
        "Spot Volume $m": {
            "kind": "exp",
            "start": 0.01,
            "end": 1000,
            "steps": 10,
        },
        "Spot Volume Geomean-3 $m": {
            "kind": "exp",
            "start": 0.01,
            "end": 1000,
            "steps": 10,
        },
    },
    "Futures Volume Score": {
        "Fut Volume $m": {
            "kind": "exp",
            "start": 0.01,
            "end": 1000,
            "steps": 10,
        },
        "Fut Volume Geomean-3 $m": {
            "kind": "exp",
            "start": 0.01,
            "end": 1000,
            "steps": 10,
        },
    },
    "Price Behavior Score": {
        "Spot Volatility (std)": {
            "kind": "reverse_linear",
            "start": 0.13,
            "end": 0.03,
            "steps": 5,
        },
        "Spot Intraday range (std)": {
            "kind": "reverse_linear",
            "start": 0.13,
            "end": 0.03,
            "steps": 5,
        },
    },
    "HL Activity Score": {
        "Volume on HL $m": {
            "kind": "exp",
            "start": 0.001,
            "end": 1000,
            "steps": 10,
        },
        "OI on HL $m": {
            "kind": "exp",
            "start": 0.001,
            "end": 1000,
            "steps": 5,
        },
    },
    "HL Liquidity Score": {
        "HLP Vol Share %": {
            "kind": "linear",
            "start": 50,
            "end": -0.5,
            "steps": 5,
        },
        "HLP OI Share %": {
            "kind": "linear",
            "start": 10,
            "end": -0.5,
            "steps": 5,
        },
        "HL Slip. $3k": {"kind": "linear", "start": 5, "end": 0, "steps": 5},
        "HL Slip. $30k": {"kind": "linear", "start": 50, "end": 0, "steps": 5},
    },
}

OUTPUT_COLS: list[str] = [
    "Symbol",
    "Max Lev. on HL",
    "Strict",
    "Recommendation",
    "Score",
]
for k, v in SCORE_CUTOFFS.items():
    OUTPUT_COLS.append(k)
    OUTPUT_COLS.extend(v)


HL_STRICT: set[Coin] = {
    "PURR",
    "CATBAL",
    "HFUN",
    "PIP",
    "JEFF",
    "VAPOR",
    "SOLV",
    "FARM",
    "ATEHUN",
    "SCHIZO",
    "OMNIX",
    "POINTS",
    "RAGE",
}
HL_STRICT_BOOST: float = 5
DAYS_TO_CONSIDER: float = 30

earliest_ts_to_keep: float = (
    time.time() - (DAYS_TO_CONSIDER + 5) * 24 * 60 * 60
)

SCORE_UB: dict[int, float] = {0: 62, 3: 75, 5: 85, 10: 101}
SCORE_LB: dict[int, float] = {0: 0, 3: 37, 5: 48, 10: 60}

MSR_INTERVAL: Literal["1d"] = "1d"


def sig_figs(number: float, sig_figs: int = 3):
    if np.isnan(number) or number <= 0:
        return 0
    return round(number, int(sig_figs - 1 - math.log10(number)))


def clean_symbol(symbol: Symbol, exch: ExchangeName | Literal[""] = ""):
    redone = symbol.split("/")[0]
    for suffix in ["10000000", "1000000", "1000", "k"]:
        redone = redone.replace(suffix, "")
    redone = EXCH_TOKEN_ALIASES.get((redone, exch), redone)
    return TOKEN_ALIASES.get(redone, redone)


def get_hot_ccxt_api(exch: ExchangeName) -> Exchange:
    api = getattr(ccxt, exch)()
    api.load_markets()
    return api


hl_markets: dict[Symbol, dict[str, Any]] = cast(
    dict[Symbol, dict[str, Any]], get_hot_ccxt_api("hyperliquid").markets
)


def print_message(message: str, level: int = 0) -> None:
    print("  " * level + message)


# %% REFERENCE EXCHANGE DATA
print_message("Building reference exchange data")


def get_fn(exch: ExchangeName, spot_fut: SpotFut) -> str:
    return f"exch_candles_{exch}_{spot_fut}_{MSR_INTERVAL}.json"


def download_one_exch(exch: ExchangeName, spot_fut: SpotFut) -> None:
    fn = get_fn(exch, spot_fut)
    try:
        with open(fn) as f:
            pass
        print_message(f"Skipping {exch} {spot_fut} as downloaded", level=2)

        return
    except Exception:
        print_message(f"Starting download of {exch} {spot_fut}", level=2)

    api = get_hot_ccxt_api(exch)
    if api.markets is None:
        raise RuntimeError(f"No markets found for exchange {exch}")

    exchange_data: dict[Symbol, list[list[float]]] = {}
    for market in api.markets:
        try:
            if spot_fut == "spot" and ":" in market:
                continue
            if spot_fut == "futures" and ":USD" not in market:
                continue
            if "/USD" not in market:
                continue
            if "-" in market:
                continue

            print_message(f"Downloading {exch} {market}...", level=3)
            exchange_data[market] = api.fetch_ohlcv(
                market, MSR_INTERVAL, limit=1000
            )
            time.sleep(2)

        except Exception as e:
            print_message(f"Error downloading {exch} {market}: {e}", level=3)
            time.sleep(5)

    with open(fn, "w") as f:
        json.dump(exchange_data, f)
    print_message(f"Completed download of {exch} {spot_fut}", level=2)


def dl_reference_exch_data() -> None:
    with ThreadPoolExecutor(max_workers=100) as ex:
        for exch, exch_spec in REFERENCE_EXCH.items():
            for spot_fut in exch_spec:
                _ = ex.submit(download_one_exch, exch, spot_fut)


print_message(
    "Downloading reference exchange data concurrently using CCXT", level=1
)
dl_reference_exch_data()


def geomean_three(series: pd.Series) -> float:
    return np.exp(np.log(series + 1).sort_values()[-3:].sum() / 3) - 1


def process_reference_exch_data() -> pd.DataFrame:
    all_candle_data: dict[
        tuple[ExchangeName, SpotFut, Coin], dict[str, float]
    ] = {}

    for exch, exch_spec in REFERENCE_EXCH.items():
        print_message(f"Processing {exch}", level=2)
        api = get_hot_ccxt_api(exch)
        if api.markets is None:
            raise RuntimeError(f"No markets found for exchange {exch}")

        for spot_fut in exch_spec:
            with open(get_fn(exch, spot_fut)) as f:
                exch_data = json.load(f)

            for symbol, market in exch_data.items():
                coin = clean_symbol(symbol, exch)
                if not len(market):
                    continue
                market_df = (
                    pd.DataFrame(market, columns=[*"tohlcv"])
                    .set_index("t")
                    .sort_index()
                    .loc[earliest_ts_to_keep * 1000 :]
                    .iloc[-DAYS_TO_CONSIDER - 1 : -1]
                )
                if not len(market_df):
                    continue
                contractsize = min(
                    api.markets.get(symbol, {}).get("contractSize", None) or 1,
                    1,
                )
                my_val = (
                    (
                        np.minimum(market_df.l, market_df.c.iloc[-1])
                        * market_df.v
                    ).mean()
                    * contractsize
                    / 1e6
                )
                if my_val >= all_candle_data.get(
                    (exch, spot_fut, coin), {}
                ).get("volume", 0):
                    all_candle_data[exch, spot_fut, coin] = {
                        "volume": my_val,
                        "std": (market_df.c / market_df.c.shift() - 1)
                        .iloc[-2:]
                        .dropna()
                        .std(),
                        "intra_day_range": (market_df.h / market_df.l - 1)
                        .iloc[-2:]
                        .dropna()
                        .std(),
                    }
            print_message(
                f"Loaded {len(exch_data)} symbols for {exch} {spot_fut}",
                level=3,
            )

    df_coins = pd.DataFrame(all_candle_data).T.sort_values(
        by="volume", ascending=False
    )
    df_coins.index.names = ["exch", "spot_fut", "coin"]
    output_df: pd.DataFrame = cast(
        pd.DataFrame,
        (
            (df_coins.fillna(0))
            .groupby(["spot_fut", "coin"])
            .agg(
                {
                    "volume": [geomean_three, "sum"],
                    "std": "median",
                    "intra_day_range": "median",
                }
            )
            .unstack(0)
            .fillna(0)
        ),
    )
    output_df.columns = [
        {"spot": "Spot", "futures": "Fut"}[spot_fut]
        + " "
        + {
            "volume": "Volume",
            "intra_day_range": "Intraday range",
            "std": "Volatility",
        }[item]
        + " "
        + {"geomean_three": "Geomean-3 $m", "sum": "$m", "median": "(std)"}[
            msr
        ]
        for item, msr, spot_fut in output_df.columns
    ]

    return output_df


print_message("Processing reference exchange data", level=1)
proc_ref_data = process_reference_exch_data()


# %%
print_message("Building Hyperliquid API sourced data")


def dl_hl_data():
    response = requests.post(
        "https://api.hyperliquid.xyz/info",
        headers={"Content-Type": "application/json"},
        json={"type": "metaAndAssetCtxs"},
    )
    response.raise_for_status()
    return response.json()


print_message("Downloading Hyperliquid API sourced data", level=1)
raw_hl_data: list[dict[str, Any]] = dl_hl_data()


def process_hl_data(raw_hl_data: list[dict[str, Any]]) -> pd.DataFrame:
    universe, asset_ctxs = raw_hl_data[0]["universe"], raw_hl_data[1]
    merged_data = [u | a for u, a in zip(universe, asset_ctxs)]
    output_df = pd.DataFrame(merged_data)
    output_df = output_df[True != output_df.isDelisted]
    output_df.index = [
        name[1:] if name.startswith("k") else name for name in output_df.name
    ]
    output_df["Max Lev. on HL"] = output_df["maxLeverage"]
    return output_df


print_message("Processing Hyperliquid API sourced data", level=1)
proc_hl_data: pd.DataFrame = process_hl_data(raw_hl_data)


# %%
print_message("Building Thunderhead API sourced data")


def dl_thunderhead_data() -> dict[str, list[dict[str, Any]]]:
    THUNDERHEAD_URL = "https://d2v1fiwobg9w6.cloudfront.net"
    THUNDERHEAD_HEADERS: dict[str, str] = {"accept": "*/*"}

    THUNDERHEAD_QUERIES: set[str] = {
        "daily_usd_volume_by_coin",
        "total_volume",
        "asset_ctxs",
        "hlp_positions",
        "liquidity_by_coin",
    }

    raw_thunder_data: dict[str, list[dict[str, Any]]] = {}
    for query in THUNDERHEAD_QUERIES:
        response = requests.get(
            f"{THUNDERHEAD_URL}/{query}",
            headers=THUNDERHEAD_HEADERS,
            allow_redirects=True,
        )
        response.raise_for_status()
        raw_thunder_data[query] = response.json().get("chart_data", [])
    return raw_thunder_data


print_message("Downloading Thunderhead API sourced data", level=1)
raw_thunder_data: dict[str, list[dict[str, Any]]] = dl_thunderhead_data()


def process_thunderhead_data(
    raw_thunder_data: dict[str, list[dict[str, Any]]]
) -> pd.DataFrame:
    dfs: list[pd.DataFrame] = []

    for key, records in raw_thunder_data.items():
        if key == "liquidity_by_coin":
            dd: dict[tuple[int, str], dict[str, Any]] = {}
            for coin, entries in records.items():
                for entry in entries:
                    dd[(entry["time"], coin)] = {**entry, "time": 0}

            dfs.append(pd.DataFrame(dd).T)
        else:
            dfs.append(pd.DataFrame(records).set_index(["time", "coin"]))

    coin_time_df = pd.concat(dfs, axis=1)
    coin_time_df = (
        coin_time_df.sort_values("daily_usd_volume", ascending=False)
        .groupby(level=[0, 1])
        .first()
    )

    coin_time_df = coin_time_df.unstack(0)

    fut_data_df = (
        coin_time_df.loc[~coin_time_df.index.str.contains("@")]
        .unstack()
        .unstack(0)
    )
    fut_data_df["avg_notional_oi"] = (
        fut_data_df["avg_oracle_px"] * fut_data_df["avg_open_interest"]
    )
    output_df: pd.DataFrame = (
        fut_data_df.unstack(1).sort_index().iloc[-30:].mean().unstack(0)
    )

    output_df.index = pd.Index([clean_symbol(sym) for sym in output_df.index])

    output_df["HLP Vol Share %"] = (
        (output_df["total_volume"] - output_df["daily_usd_volume"] / 2)
        / output_df["total_volume"]
        * 100
    )
    output_df.loc[output_df["HLP Vol Share %"] <= 0.001, "HLP Vol Share %"] = (
        0.0001
    )
    output_df["HLP OI Share %"] = (
        output_df["daily_ntl_abs"] / output_df["avg_notional_oi"] * 100
    )
    output_df.loc[output_df["HLP OI Share %"] <= 0.001, "HLP OI Share %"] = (
        0.0001
    )

    output_df["OI on HL $m"] = output_df["avg_notional_oi"] / 1e6
    output_df["Volume on HL $m"] = output_df["total_volume"] / 1e6
    output_df["HL Slip. $3k"] = output_df["median_slippage_3000"] * 100_00
    output_df["HL Slip. $30k"] = output_df["median_slippage_30000"] * 100_00

    return output_df.dropna(subset="time")


print_message("Processing Thunderhead API sourced data", level=1)
proc_thunderhead_data: pd.DataFrame = process_thunderhead_data(
    raw_thunder_data
)


# %%
print_message("Building CoinMarketCap API sourced data")


def dl_cmc_data() -> list[dict[str, Any]]:
    import keyring  # for cmc api key

    CMC_API_URL = (
        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    )
    CMC_API_KEY = keyring.get_password("cmc", "cmc")

    response = requests.get(
        f"{CMC_API_URL}?CMC_PRO_API_KEY={CMC_API_KEY}&limit=5000", timeout=10
    )
    response.raise_for_status()
    data: list[dict[str, Any]] = response.json().get("data", [])

    for item in data:
        item["symbol"] = TOKEN_ALIASES.get(item["name"], item["symbol"])

    return data


print_message("Downloading CoinMarketCap API sourced data", level=1)
raw_cmc_data: list[dict[str, Any]] = dl_cmc_data()


def process_cmc_data(cmc_data: list[dict[str, Any]]) -> pd.DataFrame:
    output_df: pd.DataFrame = (
        pd.DataFrame(
            [
                {
                    "symbol": clean_symbol(a["symbol"]),
                    "mc": float(a["quote"]["USD"]["market_cap"]),
                    "fd_mc": float(
                        a["quote"]["USD"]["fully_diluted_market_cap"]
                    ),
                }
                for a in cmc_data
            ]
        )
        .groupby("symbol")[
            [
                "mc",
                "fd_mc",
            ]
        ]
        .max()
    )

    output_df.loc[output_df.mc <= 0, "mc"] = np.nan
    output_df["MC $m"] = output_df.mc.fillna(output_df.fd_mc) / 1e6

    return output_df


print_message("Processing CoinMarketCap API sourced data", level=1)
proc_cmc_data: pd.DataFrame = process_cmc_data(raw_cmc_data)


# %%
def build_scores(df: pd.DataFrame) -> pd.DataFrame:
    output: dict[str, pd.Series] = {}
    for score_category, category_details in SCORE_CUTOFFS.items():
        output[score_category] = pd.Series(0, index=df.index)
        for score_var, thresholds in category_details.items():
            score_name = "Partial_Score_" + score_var
            output[score_name] = pd.Series(0, index=df.index)

            if thresholds["kind"] == "exp":
                point_thresholds = {
                    thresholds["start"]
                    * (thresholds["end"] / thresholds["start"])
                    ** (k / thresholds["steps"]): k
                    for k in range(0, thresholds["steps"] + 1)
                }
                for lb, value in sorted(point_thresholds.items()):
                    output[score_name].loc[df[score_var] >= lb] = value
            elif thresholds["kind"] == "linear":
                point_thresholds = {
                    thresholds["start"]
                    + (thresholds["end"] - thresholds["start"])
                    * (k / thresholds["steps"]): k
                    for k in range(0, thresholds["steps"] + 1)
                }
                for lb, value in sorted(point_thresholds.items()):
                    output[score_name].loc[df[score_var] >= lb] = value

            elif thresholds["kind"] == "reverse_linear":
                point_thresholds = {
                    thresholds["start"]
                    + (thresholds["end"] - thresholds["start"])
                    * (k / thresholds["steps"]): k
                    for k in range(0, thresholds["steps"] + 1)
                }
                for lb, value in reversed(sorted(point_thresholds.items())):
                    output[score_name].loc[df[score_var] <= lb] = value

            else:
                raise ValueError("thresholds['kind']")

            output[score_category] += output[score_name]

    output_df = pd.concat(output, axis=1)
    output_df.loc[
        df["Max Lev. on HL"] < 1, [c for c in output_df if "HL" in str(c)]
    ] = 0
    output_df["NON_HL_SCORE_BOOST"] = (
        0.5
        * (df["Max Lev. on HL"] < 1)
        * output_df[
            ["Market Cap Score", "Spot Volume Score", "Futures Volume Score"]
        ].sum(axis=1)
    ).astype(int)

    output_df["Strict"] = output_df.index.isin(HL_STRICT)
    output_df["Score"] = (
        output_df[[*SCORE_CUTOFFS, "NON_HL_SCORE_BOOST"]].sum(axis=1)
        + output_df["Strict"] * HL_STRICT_BOOST
    )

    return output_df


print_message("Building recommendations", level=0)
print_message("Merging data", level=1)
processed_data: list[pd.DataFrame] = [
    proc_cmc_data,
    proc_ref_data,
    proc_hl_data,
    proc_thunderhead_data,
]
df: pd.DataFrame = pd.concat(processed_data, axis=1)
df = df.loc[~df.index.isin(STABLE_COINS)]

df["Symbol"] = df.index
df["Max Lev. on HL"] = df["Max Lev. on HL"].fillna(0)

df = pd.concat([df, build_scores(df)], axis=1)


def generate_recommendation(row: pd.Series) -> str:
    high_lev = (
        row["Score"] < SCORE_LB[min(max(SCORE_LB), int(row["Max Lev. on HL"]))]
    )
    low_lev = (
        row["Score"]
        >= SCORE_UB[min(max(SCORE_UB), int(row["Max Lev. on HL"]))]
    )

    if row["Max Lev. on HL"] > 3 and high_lev:
        return "Dec. Lev."
    if row["Max Lev. on HL"] == 3 and high_lev:
        return "Delist"
    if row["Max Lev. on HL"] == 0 and low_lev:
        return "List"
    if row["Max Lev. on HL"] > 0 and low_lev:
        return "Inc. Lev."
    return ""


print_message("Generating recommendations", level=1)
df["Recommendation"] = df.apply(generate_recommendation, axis=1)

df_for_main_data = df[OUTPUT_COLS].sort_values("Score", ascending=False).copy()

for c in df_for_main_data.columns:
    if str(df_for_main_data[c].dtype) in [
        "int64",
        "float64",
    ]:
        df_for_main_data[c] = df_for_main_data[c].map(sig_figs)


# %%


import plotly.express as px
import pandas as pd

lev_map = {
    0: "Not listed",
    3: "3x",
    5: "5x",
    10: "10x",
    20: "20x+",
    25: "20x+",
    40: "20x+",
}
lev_list = list(lev_map.values())

# Map each "Max Lev. on HL " value to its index in lev_list
df2 = df.copy()
df2["x_bucket"] = df2["Max Lev. on HL"].map(lev_map)
df2["x_index"] = df2["x_bucket"].apply(
    lambda v: lev_list.index(v) if v in lev_list else None
)
df2["show"] = df2.index
df2["coin"] = df2.index

df2["offset_o"] = 0
df2["max_offset_o"] = 0

for _, group in df2.groupby(["x_index", "Score"], sort=False):
    df2.loc[group.index, "offset_o"] = range(len(group))
    df2.loc[group.index, "max_offset_o"] = len(group)

for _, group in df2.groupby(["x_index"], sort=False):
    score_orders = group.Score.sort_values()
    if len(score_orders) > 10:
        scores_to_hide = score_orders.loc[
            score_orders.gt(score_orders.iloc[5])
            & score_orders.lt(score_orders.iloc[-5])
        ]

        df2.loc[scores_to_hide.index, "show"] = ""

df2 = df2.loc[df2.Score.gt(55) | df2.x_index.gt(0)]
df2["x_offset"] = (
    df2["x_index"]
    + (0.5 + df2.offset_o % 5 - np.minimum(df2.max_offset_o, 5) / 2) / 6
)
df2["y_offset"] = df2["Score"] + df2.offset_o // 5 / 2

# Create scatter plot
fig = px.scatter(
    df2,
    x="x_offset",
    y="y_offset",
    text=df2.show,
    labels={"x_index": "Leverage Index", "y_offset": "Score"},
    title="Score vs. Max Leverage Index on HL",
    hover_name=df2.index,
    template="plotly_dark",  # <--- dark mode template
)


def make_hover_template(item):
    z = f"<b> {item['coin']}</b><br>"
    if item["Max Lev. on HL"] == 0:
        z += "Not listed on Hyperliquid<br>"
    else:
        z += f"Current HL Leverage Limit: {item['Max Lev. on HL']}<br>"
    z += f"Score: {item['Score']}<br>"
    for k, v in SCORE_CUTOFFS.items():
        z += f"{k}: {item[k]}<br>"
        for v1 in v:
            z += f" {v1}: {sig_figs(item[v1],3)}<br>"
    return z


fig.update_traces(
    mode="markers+text",
    textfont=dict(size=8),
    hovertemplate=[make_hover_template(a) for n, a in df2.iterrows()],
    marker=dict(size=8, opacity=0.75),
    textposition="middle center",
)

fig.update_layout(
    xaxis=dict(
        tickvals=list(range(len(lev_list[:4]))),
        ticktext=[str(x) for x in lev_list],
        title="Max Leverage on Hyperliquid",
    )
)
import plotly.graph_objects as go

lev_to_idx = {lev: i for i, lev in enumerate(lev_map)}

bars = []
for lev, x_min in SCORE_UB.items():
    if lev not in lev_map:
        continue
    xi = lev_to_idx[lev]
    height = max(0.0, 100.0 - float(x_min))
    bars.append(
        go.Bar(
            x=[xi],
            y=[height],  # bar height
            base=[x_min],  # start at x_min, extend to 100
            width=0.8,
            marker=dict(color="rgba(0,200,0,0.25)"),  # transparent green
            showlegend=False,
            hoverinfo="skip",
        )
    )
for lev, x_min in SCORE_LB.items():
    if lev not in lev_map:
        continue
    xi = lev_to_idx[lev]
    bars.append(
        go.Bar(
            x=[xi],
            y=[x_min],  # bar height
            base=[0],  # start at x_min, extend to 100
            width=0.8,
            marker=dict(color="rgba(200,0,0,0.25)"),  # transparent green
            showlegend=False,
            hoverinfo="skip",
        )
    )

# 1) Add bar traces (currently they’ll be on TOP)
for bar in bars:
    fig.add_trace(bar)

# 2) Reorder traces so bars are at the BACK
k = len(bars)
if k:
    n = len(fig.data)
    # bars are the last k traces; move them to the front
    new_order = list(range(n - k, n)) + list(range(0, n - k))
    fig.data = tuple(fig.data[i] for i in new_order)  # permutation -> allowed

# style/layout for overlayed bars
fig.update_layout(barmode="overlay")
fig.update_yaxes(range=[30, 101])
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",  # outer background
    plot_bgcolor="rgba(0,0,0,0)",  # inner plotting area
)
fig.show(renderer="browser")
fig_json = fig.to_json()
with open("hl_delisting_data.json", "w") as f:
    json.dump(
        {
            "data": df_for_main_data.to_dict(orient="records"),
            "meta": {
                "time": datetime.datetime.now().isoformat()[:10],
                "version": 1.1,
            },
            "fig": json.loads(fig_json),
        },
        f,
    )


print_message("Completed recommendation data build", level=0)
