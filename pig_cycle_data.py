#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猪周期五序列季度数据采集（2018Q1 → 2026Q3）
真实数据源：
  1. 能繁母猪存栏  —— akshare futures_hog_supply('生猪产能')  [玄田数据/中国养猪网，原始来源农业农村部]
  2. 猪肉价格      —— akshare index_hog_spot_price()          [生猪现货成交均价，日频→季度]
  3. 中证畜牧养殖指数 930707 —— 中证指数有限公司官网 API（官方源）
  4. 牧原股份 002714 —— akshare stock_zh_a_daily(前复权)
  5. 温氏股份 300498 —— akshare stock_zh_a_daily(前复权)
输出：data/pig_cycle/quarterly.json + .csv + 打印核对表
"""
import warnings, json, os, sys
warnings.filterwarnings('ignore')
import pandas as pd, requests

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'pig_cycle')
os.makedirs(OUT, exist_ok=True)

QEND = {1: '-03-31', 2: '-06-30', 3: '-09-30', 4: '-12-31'}


def quarter_label(ts):
    return f'{ts.year}Q{ts.quarter}'


def to_quarterly(daily: pd.Series, how='last'):
    """日频 → 季度（默认取季末值）"""
    s = daily.copy()
    if not isinstance(s.index, pd.DatetimeIndex):
        s.index = pd.to_datetime(s.index)
    g = s.groupby([s.index.year, s.index.quarter])
    out = g.last() if how == 'last' else g.mean()
    out.index = pd.MultiIndex.from_tuples(out.index, names=['year', 'quarter'])
    return out


print('=' * 78)
print('【1/5】能繁母猪存栏（农业农村部 / 玄田数据）')
print('=' * 78)
import akshare as ak
sow = ak.futures_hog_supply(symbol='生猪产能')
sow = sow[['周期', '能繁母猪存栏']].dropna()
sow['能繁母猪存栏'] = pd.to_numeric(sow['能繁母猪存栏'], errors='coerce')
print(f'  原始 {len(sow)} 行，周期范围 {sow["周期"].iloc[0]} → {sow["周期"].iloc[-1]}')
print('  完整原始数据（核对用）:')
print(sow.to_string(index=False))

print()
print('=' * 78)
print('【2/5】猪肉价格（生猪现货成交均价，元/公斤）')
print('=' * 78)
hog = ak.index_hog_spot_price()
hog['日期'] = pd.to_datetime(hog['日期'])
print(f'  原始 {len(hog)} 行，{hog["日期"].min():%Y-%m-%d} → {hog["日期"].max():%Y-%m-%d}')
print('  列:', list(hog.columns))
vcol = '成交均价' if '成交均价' in hog.columns else [c for c in hog.columns if c != '日期'][-1]
hog_s = hog.set_index('日期')[vcol].astype(float)
hog_q_last = to_quarterly(hog_s, 'last')
hog_q_mean = to_quarterly(hog_s, 'mean')
print(f'  最新值 {hog_s.index[-1]:%Y-%m-%d} = {hog_s.iloc[-1]} {vcol}')

print()
print('=' * 78)
print('【3/5】中证畜牧养殖指数 930707（中证指数公司官网）')
print('=' * 78)
r = requests.get('https://www.csindex.com.cn/csindex-home/perf/index-perf',
                 params={'indexCode': '930707', 'startDate': '20180101', 'endDate': '20261231'},
                 headers={'User-Agent': 'Mozilla/5.0'}, timeout=40)
idx = pd.DataFrame(r.json()['data'])
idx['tradeDate'] = pd.to_datetime(idx['tradeDate'], format='%Y%m%d')
idx['close'] = pd.to_numeric(idx['close'], errors='coerce')
idx = idx.dropna(subset=['close']).sort_values('tradeDate').set_index('tradeDate')
print(f'  官方日线 {len(idx)} 条，{idx.index.min():%Y-%m-%d} → {idx.index.max():%Y-%m-%d}')
print(f'  末值 {idx["close"].iloc[-1]}  ({idx["indexNameCnAll"].iloc[0]})')
idx_q = to_quarterly(idx['close'], 'last')

print()
print('=' * 78)
print('【4-5/5】牧原股份 002714 / 温氏股份 300498（前复权）')
print('=' * 78)
stocks = {}
for code, name in [('sz002714', '牧原股份'), ('sz300498', '温氏股份')]:
    d = ak.stock_zh_a_daily(symbol=code, start_date='20180101', end_date='20261231', adjust='qfq')
    d['date'] = pd.to_datetime(d['date'])
    c = d.set_index('date')['close'].astype(float)
    stocks[name] = c
    print(f'  {name} 日线 {len(c)} 条，{c.index.min():%Y-%m-%d} → {c.index.max():%Y-%m-%d}，末值 {c.iloc[-1]:.2f}')
    stocks[name + '_q'] = to_quarterly(c, 'last')

# ── 组装季度表 ────────────────────────────────────────────────
quarters = []
for y in range(2018, 2027):
    for q in range(1, 5):
        if y == 2026 and q > 3:
            continue
        quarters.append((y, q))

rows = []
for (y, q) in quarters:
    key = (y, q)
    rec = {
        'year': y, 'quarter': q, 'label': f'{y}Q{q}',
        'quarter_end': f'{y}{QEND[q]}',
    }
    rec['pork_price'] = round(float(hog_q_last[key]), 3) if key in hog_q_last.index else None
    rec['pork_price_mean'] = round(float(hog_q_mean[key]), 3) if key in hog_q_mean.index else None
    rec['index_930707'] = round(float(idx_q[key]), 2) if key in idx_q.index else None
    for nm in ['牧原股份', '温氏股份']:
        k = nm + '_q'
        rec[nm] = round(float(stocks[k][key]), 2) if key in stocks[k].index else None
    rows.append(rec)

df = pd.DataFrame(rows)

# 存栏单独处理（周期字段是中文，粒度不一：2018-2024 年值 + 2025 季度/月度）
sow_rows = []
for _, r0 in sow.iterrows():
    p = str(r0['周期']).strip()
    val = float(r0['能繁母猪存栏'])
    # "2025年一季度（末）" / "2025年7月" / "2018"
    if '季度' in p:
        yy = int(p[:4])
        qq = {'一': 1, '二': 2, '三': 3, '四': 4}.get(p[5], None)
        if qq:
            sow_rows.append({'year': yy, 'quarter': qq, 'sows': val, 'granularity': 'quarter'})
    elif p.endswith('月'):
        mm = int(''.join(ch for ch in p.split('年')[1] if ch.isdigit()))
        sow_rows.append({'year': int(p[:4]), 'quarter': (mm - 1) // 3 + 1, 'month': mm, 'sows': val, 'granularity': 'month'})
    elif p.isdigit() and len(p) == 4:
        sow_rows.append({'year': int(p), 'quarter': 4, 'sows': val, 'granularity': 'year-end'})
sow_df = pd.DataFrame(sow_rows)
print()
print('  存栏解析结果（核对）:')
print(sow_df.to_string(index=False))

# 合并：季度值优先，其次月度（取该季最后一个月），再次年末值
merged = {}
for _, r0 in sow_df.sort_values(['year', 'quarter']).iterrows():
    merged[(r0['year'], r0['quarter'])] = (r0['sows'], r0['granularity'])
df['sows'] = [merged.get((r.year, r.quarter), (None, None))[0] for r in df.itertuples()]
df['sows_granularity'] = [merged.get((r.year, r.quarter), (None, None))[1] for r in df.itertuples()]

print()
print('=' * 78)
print('最终季度表（2018Q1 → 2026Q3）')
print('=' * 78)
show = df[['label', 'sows', 'sows_granularity', 'pork_price', 'index_930707', '牧原股份', '温氏股份']].copy()
show.columns = ['季度', '能繁母猪存栏', '存栏粒度', '猪肉价(季末)', '中证畜牧', '牧原(qfq)', '温氏(qfq)']
print(show.to_string(index=False))

# 覆盖率核对
print()
print('--- 覆盖率核对 ---')
for c, nm in [('sows', '能繁母猪存栏'), ('pork_price', '猪肉价格'), ('index_930707', '中证畜牧指数'), ('牧原股份', '牧原'), ('温氏股份', '温氏')]:
    n = df[c].notna().sum()
    print(f'  {nm:12s} {n:2d}/35 季度有值  {"✅" if n >= 35 else ("⚠️ 缺 " + str(35 - n))}')

df.to_json(os.path.join(OUT, 'quarterly.json'), orient='records', force_ascii=False, indent=1)
df.to_csv(os.path.join(OUT, 'quarterly.csv'), index=False, encoding='utf-8-sig')
print(f'\n✅ 已保存: {OUT}/quarterly.json + quarterly.csv')
