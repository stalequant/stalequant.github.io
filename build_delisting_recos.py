# stalequant 2025-04-02

import json
import math
import requests
import time

import ccxt
import numpy as np
import pandas as pd

STABLE_COINS = {"USDC", 'FDUSD', "USDT", 'DAI', 'USDB', 'USDE', 'TUSD', 'USR'}
DAYS_TO_CONSIDER = 30

OUTPUT_COLS = [
    'Symbol', 'Max Lev. on HL', 'Strict','Recommendation',
    'Market Cap Score', 'Spot Vol Score', 'Futures Vol Score',
    'HL Activity Score', 'HL Liquidity Score', 'Score',
    'MC $m', 'Spot Volume $m', 'Spot Vol Geomean $m',
    'Fut Volume $m', 'Fut Vol Geomean $m', 'OI on HL $m',
    'Volume on HL $m', 'HLP Vol Share %', 'HLP OI Share %',
    'HL Slip. $3k', 'HL Slip. $30k'
]
OUTPUT_CORR_MAT_JSON = 'hl_screen_corr.json'
OUTPUT_RAW_DATA_JSON = 'hl_screen_main.json'

SCORE_UB = {0: 62, 3: 75, 5: 85, 10: 101}
SCORE_LB = {0: 0, 3: 37, 5: 48, 10: 60}

REFERENCE_SPOT_EXCH = {
    'binance', 'bybit', 'okx', 'gate', 'kucoin', 'mexc',
    'cryptocom', 'coinbase', 'kraken', 'hyperliquid'
}
REFERENCE_FUT_EXCH = {
    'bybit', 'binance', 'gate', 'mexc', 'okx',
    'htx', 'krakenfutures', 'cryptocom', 'bitmex',
    'hyperliquid'
}
HL_STRICT = {'PURR','CATBAL','HFUN','PIP','JEFF','VAPOR','SOLV',
             'FARM','ATEHUN','SCHIZO','OMNIX','POINTS','RAGE'}

SCORE_CUTOFFS = {
    'Market Cap Score': {
        'MC $m': {'kind': 'exp', 'start': 1, 'end': 5000, 'steps': 20},
    },
    'Spot Vol Score': {
        'Spot Volume $m': {'kind': 'exp', 'start': 0.01, 'end': 1000, 'steps': 10},
        'Spot Vol Geomean $m': {'kind': 'exp', 'start': 0.01, 'end': 1000, 'steps': 10},
    },
    'Futures Vol Score': {
        'Fut Volume $m': {'kind': 'exp', 'start': 0.01, 'end': 1000, 'steps': 10},
        'Fut Vol Geomean $m': {'kind': 'exp', 'start': 0.01, 'end': 1000, 'steps': 10},
    },
    'HL Activity Score': {
        'Volume on HL $m': {'kind': 'exp', 'start': 0.001, 'end': 1000, 'steps': 10},
        'OI on HL $m': {'kind': 'exp', 'start': 0.001, 'end': 1000, 'steps': 10},
    },
    'HL Liquidity Score': {
        'HLP Vol Share %': {'kind': 'linear', 'start': 50, 'end': 0, 'steps': 5},
        'HLP OI Share %': {'kind': 'linear', 'start': 10, 'end': 0, 'steps': 5},
        'HL Slip. $3k': {'kind': 'linear', 'start': 5, 'end': 0, 'steps': 5},
        'HL Slip. $30k': {'kind': 'linear', 'start': 50, 'end': 0, 'steps': 5},
    }
}
HL_STRICT_BOOST = 5

earliest_ts_to_keep = time.time()-(DAYS_TO_CONSIDER+5)*24*60*60

def sig_figs(number, sig_figs=3):
    if np.isnan(number) or number <= 0:
        return 0
    return round(number, int(sig_figs - 1 - math.log10(number)))


def clean_symbol(symbol, exch=''):
    TOKEN_ALIASES = {
        'HPOS10I': 'BITCOIN', 'HPOS': 'HPOS', 'HPO': 'HPOS',
        'BITCOIN': 'HPOS', 'NEIROCTO': 'NEIRO', '1MCHEEMS': 'CHEEMS',
        '1MBABYDOGE': 'BABYDOGE', 'JELLYJELLY': 'JELLY'
    }
    EXCH_TOKEN_ALIASES = {
        ('NEIRO', 'bybit'): 'NEIROETH',
        ('NEIRO', 'gate'): 'NEIROETH',
        ('NEIRO', 'kucoin'): 'NEIROETH'
    }
    redone = symbol.split('/')[0]
    for suffix in ['10000000', '1000000', '1000', 'k']:
        redone = redone.replace(suffix, '')
    redone = EXCH_TOKEN_ALIASES.get((redone, exch), redone)
    return TOKEN_ALIASES.get(redone, redone)

def get_hot_ccxt_api(exch):
    
        api = getattr(ccxt, exch)()
        try:
            api.fetch_ticker('BTC/USDT:USDT')
        except Exception as e:
            pass
        return api
    
hl_markets = get_hot_ccxt_api('hyperliquid').markets

# %% 
    
def dl_reference_exch_data():
    def download_exch(exch, spot):
        try:
            with open(f'exch_candles_{exch}_{"s" if spot else "f"}.json') as f:
                pass
            print(f'SKIPPING {exch} AS DOWNLOADED')

            return
        except Exception:
            print(f'DOWNLOADING {exch} TO TEMP')
            
        api= get_hot_ccxt_api(exch)

        exchange_data = {}
        for market in api.markets:
            try:
                if spot and ':' in market:
                    continue
                if not spot and ':USD' not in market:
                    continue
                if '/USD' not in market:
                    continue
                if '-' in market:
                    continue

                print(exch, market)
                exchange_data[market] = api.fetch_ohlcv(market, '1d')
            except Exception as e:
                print(e)
                time.sleep(1)

        with open(f'exch_candles_{exch}_{"fs"[spot]}.json', 'w') as f:
            json.dump(exchange_data, f)

    for exch in REFERENCE_SPOT_EXCH:
        download_exch(exch, True)

    for exch in REFERENCE_FUT_EXCH:
        download_exch(exch, False)

    raw_reference_exch_df = {}

    for spot, exchs in {True: REFERENCE_SPOT_EXCH,
                        False: REFERENCE_FUT_EXCH}.items():
        for exch in exchs:
            try:
                with open(f'exch_candles_{exch}_{"fs"[spot]}.json') as f:
                    loaded_json = json.load(f)
                    if loaded_json:
                        raw_reference_exch_df[spot, exch] = loaded_json
                    else:
                        raise Exception('Missing file')
            except Exception as e:
                print(exch, spot, e, 'fail')
                pass
    return raw_reference_exch_df


def geomean_three(series):
    return np.exp(np.log(series+1).sort_values()[-3:].sum()/3) - 1

def process_reference_exch_data(raw_reference_exch_df):
    all_candle_data = {}

    for (spot, exch), exch_data in raw_reference_exch_df.items():
        print('PROCESSING '+exch + ' ' + ('spot' if spot else 'futures'))
        api= get_hot_ccxt_api(exch)
        for symbol, market in exch_data.items():
            coin = clean_symbol(symbol, exch)
            if not len(market):
                continue
            market_df = (pd.DataFrame(market, columns=[*'tohlcv'])
                         .set_index('t').sort_index()
                         .loc[earliest_ts_to_keep*1000:]
                         .iloc[-DAYS_TO_CONSIDER-1:-1])
            if not len(market_df):
                continue
            contractsize = min(api.markets.get(
                symbol, {}).get('contractSize', None) or 1, 1)
            my_val = (np.minimum( market_df.l, market_df.c.iloc[-1]) 
                      * market_df.v).mean() * contractsize
            if my_val >= all_candle_data.get((exch, spot, coin), 0):
                all_candle_data[exch, spot, coin] = my_val

    df_coins = pd.Series(all_candle_data).sort_values(ascending=False)
    df_coins.index.names = ['exch', 'spot', 'coin']
    output_df = (df_coins.fillna(0)/1e6).groupby(['spot', 'coin']).agg(
        [geomean_three, 'sum']).unstack(0).fillna(0)
    output_df.columns = [
        f"{'Spot' if b else 'Fut'} "
        f"{dict(geomean_three='Vol Geomean $m', sum='Volume $m')[a]}" 
        for a, b in output_df.columns]

    return output_df


# %%

def dl_hl_data():
    response = requests.post("https://api.hyperliquid.xyz/info",
                             headers={"Content-Type": "application/json"},
                             json={"type": "metaAndAssetCtxs"})
    response.raise_for_status()
    return response.json()


def process_hl_data(raw_hl_data):
    universe, asset_ctxs = raw_hl_data[0]['universe'], raw_hl_data[1]
    merged_data = [u | a for u, a in zip(universe, asset_ctxs)]
    output_df = pd.DataFrame(merged_data)
    output_df = output_df[output_df.isDelisted != True]
    output_df.index = [name[1:] if name.startswith(
        'k') else name for name in output_df.name]
    output_df['Max Lev. on HL'] = output_df['maxLeverage']
    return output_df

# %%


def dl_thunderhead_data():

    THUNDERHEAD_URL = "https://d2v1fiwobg9w6.cloudfront.net"
    THUNDERHEAD_HEADERS = {"accept": "*/*", }

    THUNDERHEAD_QUERIES = {'daily_usd_volume_by_coin',
                           'total_volume',
                           'asset_ctxs',
                           'hlp_positions',
                           'liquidity_by_coin'}

    raw_thunder_data = {}
    for query in THUNDERHEAD_QUERIES:
        response = requests.get(f"{THUNDERHEAD_URL}/{query}",
                                headers=THUNDERHEAD_HEADERS,
                                allow_redirects=True)
        response.raise_for_status()
        raw_thunder_data[query] = response.json().get('chart_data', [])
    return raw_thunder_data

def process_thunderhead_data(raw_thunder_data):
    dfs = []

    for key, records in raw_thunder_data.items():
        if key == 'liquidity_by_coin':
            dfs.append(pd.DataFrame({
                (entry['time'], coin): {**entry, 'time': 0}
                for coin, entries in records.items()
                for entry in entries
            }).T)
        else:
            dfs.append(pd.DataFrame(records).set_index(['time', 'coin']))

    coin_time_df = pd.concat(dfs, axis=1).unstack(0)
    spot_mapping = {d['info']['name']:symbol.split('/')[0] 
                    for symbol,d in  hl_markets.items() if ':' not in symbol}

    spot_data_df = (coin_time_df.loc[coin_time_df.index.isin(spot_mapping)]
                    .rename(spot_mapping).unstack().unstack(0))
    fut_data_df = (coin_time_df.loc[~coin_time_df.index.isin(spot_mapping)]
                   .unstack().unstack(0))
    fut_data_df['avg_notional_oi'] = (fut_data_df['avg_oracle_px'] *
                                       fut_data_df['avg_open_interest'])
    fut_s_df = fut_data_df.unstack(1).sort_index().iloc[-30:].mean().unstack(0)
    spot_s_df = spot_data_df.unstack(1).sort_index().iloc[-30:].mean().unstack(0)

    
    spot_s_df.index = [clean_symbol(sym) for sym in spot_s_df.index]
    fut_s_df.index = [clean_symbol(sym) for sym in fut_s_df.index]


    output_df = fut_s_df

    output_df['HLP Vol Share %'] = ((output_df['total_volume']
                                   - output_df['daily_usd_volume']/2)
                                  / output_df['total_volume'] * 100)
    output_df['HLP OI Share %'] = (output_df['daily_ntl_abs']
                                 / output_df['avg_notional_oi'] * 100)
    output_df['OI on HL $m'] = output_df['avg_notional_oi'] / 1e6
    output_df['Volume on HL $m'] = output_df['total_volume'] / 1e6
    output_df['HL Slip. $3k'] = output_df['median_slippage_3000'] * 100_00
    output_df['HL Slip. $30k'] = output_df['median_slippage_30000'] * 100_00
    

    return output_df


# %%

def dl_cmc_data():

    import keyring  # for cmc api key
    CMC_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    CMC_API_KEY = keyring.get_password('cmc', 'cmc')
    CMC_SYMBOL_OVERRIDES = {
        'Neiro Ethereum': 'NEIROETH',
        'HarryPotterObamaSonic10Inu (ERC-20)': 'HPOS'
    }

    response = requests.get(
        f"{CMC_API_URL}?CMC_PRO_API_KEY={CMC_API_KEY}&limit=5000",
        timeout=10
    )
    response.raise_for_status()
    data = response.json().get('data', [])

    for item in data:
        item['symbol'] = CMC_SYMBOL_OVERRIDES.get(item['name'], item['symbol'])

    return data


def process_cmc_data(cmc_data):
    output_df = pd.DataFrame([{
        'symbol':a['symbol'],
        'mc':a['quote']['USD']['market_cap'],
        'fd_mc':a['quote']['USD']['fully_diluted_market_cap'],}
    for a in cmc_data]).groupby('symbol')[['mc', 'fd_mc',]].max()

    output_df.loc[output_df['mc']==0,'mc'] = output_df['fd_mc']
    output_df = pd.concat([
        output_df, pd.Series({symbol.split('/')[0]:
                            float(data['info'].get('circulatingSupply',0))
                            *float(data['info'].get('markPx',0)) 
                            for symbol,data in hl_markets.items()
                                   if ':' not in symbol}, name='hl_mc')],
            
            axis = 1)
    output_df['MC $m'] = output_df[['mc','hl_mc']].max(axis=1)/1e6
     
    return output_df

# %%
def build_scores(df):
    output = {}
    for score_category, category_details in SCORE_CUTOFFS.items():
        output[score_category] = pd.Series(0, index=df.index)
        for score_var, thresholds in category_details.items():
            if thresholds['kind'] =='exp':
                point_thresholds = {
                    thresholds['start'] 
                    * (thresholds['end']/thresholds['start']) 
                    ** (k/thresholds['steps']):
                        k for k in range(0, thresholds['steps']+1)}
            elif thresholds['kind'] =='linear':
                point_thresholds = {
                    thresholds['start']
                    + (thresholds['end']  - thresholds['start'] )
                    * (k/thresholds['steps'] ):
                        k for k in range(0, thresholds['steps'] +1)}
            else: 
                raise ValueError("thresholds['kind']")
                
            score_name = 'Partial_Score_'+score_var
            output[score_name] = pd.Series(0, index=df.index)
            for lb, value in sorted(point_thresholds.items()):
                output[score_name].loc[df[score_var] >= lb] = value
            output[score_category] += output[score_name]

    output_df = pd.concat(output, axis=1)
    output_df.loc[df['Max Lev. on HL'] < 1,
                  [c for c in output_df if 'HL' in c]] = 0
    output_df['NON_HL_SCORE_BOOST'] = (
        0.5
        * (df['Max Lev. on HL'] < 1)
        * output_df[['Market Cap Score', 'Spot Vol Score', 'Futures Vol Score']]
        .sum(axis=1)
    ).astype(int)

    output_df['Strict'] = output_df.index.isin(HL_STRICT)
    output_df['Score'] = (
        output_df[[*SCORE_CUTOFFS, 'NON_HL_SCORE_BOOST'] ].sum(axis=1)  
        + output_df['Strict']*HL_STRICT_BOOST)

    return output_df

# %%

def generate_recommendation(row):
    high_lev = row['Score'] < SCORE_LB[min(max(SCORE_LB),
                                           int(row['Max Lev. on HL']))]
    low_lev = row['Score'] >= SCORE_UB[min(max(SCORE_UB), 
                                           int(row['Max Lev. on HL']))]

    if row['Max Lev. on HL'] > 3 and high_lev:
        return 'Dec. Lev.'
    if row['Max Lev. on HL'] == 3 and high_lev:
        return 'Delist'
    if row['Max Lev. on HL'] == 0 and low_lev:
        return 'List'
    if row['Max Lev. on HL'] > 0 and low_lev:
        return 'Inc. Lev.'
    return ''

# %%
processed_data = [
    process_cmc_data(dl_cmc_data()),
    process_reference_exch_data(dl_reference_exch_data()),
    process_hl_data(dl_hl_data()),
    process_thunderhead_data(dl_thunderhead_data())
]

# %%
df = pd.concat(processed_data, axis=1)
df = df.loc[~df.index.isin(STABLE_COINS)]

df['Symbol'] = df.index
df['Max Lev. on HL'] = df['Max Lev. on HL'].fillna(0)

df = pd.concat([df, build_scores(df)], axis=1)

df['Recommendation'] = df.apply(generate_recommendation, axis=1)

df_for_main_data = df[OUTPUT_COLS].sort_values('Score', ascending=False).copy()

for c in df_for_main_data.columns:
    if str(df_for_main_data[c].dtype) in ['int64', 'float64',]:
        df_for_main_data[c] = df_for_main_data[c].map(sig_figs)

with open(OUTPUT_RAW_DATA_JSON, 'w') as f:
    json.dump(df_for_main_data.to_dict(orient='records'),f)

df_for_corr = df[['Max Lev. on HL'] + [c for c in df if "Score" in c]] .copy()
df_for_corr.loc[df_for_corr['Max Lev. on HL'] < 1,
                [c for c in df_for_corr if 'HL' in c]] = np.nan
df_for_corr = df_for_corr.rename(
    {c: c.replace('Partial_Score_', '..') for c in df_for_corr}, axis=1)
corr_mat = (df_for_corr.corr()*100).astype(int)
corr_mat = corr_mat.reset_index().rename({'index': 'Symbol'}, axis=1)
with open(OUTPUT_CORR_MAT_JSON, 'w') as f:
    json.dump(corr_mat.to_dict(orient='records'),f) 