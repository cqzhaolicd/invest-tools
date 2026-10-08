#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猪周期「日频」数据导出 —— 供投资中心 pig_cycle.html 绘制猪价曲线 + 成本线

数据源（全部真实，实测可用）：
  猪价   akshare index_hog_spot_price()['成交均价']  —— 生猪现货成交均价(元/公斤)，周频，原始来源农业农村部/玄田
  股价   akshare stock_zh_a_daily(qfq)  —— 牧原/温氏/巨星/东瑞/兴业 前复权日线
  补充   /home/administrator/pig-monitor/history.json —— 监控脚本每日实采（比 akshare 更新）

成本线硬编码：牧原完全成本 11.6 元/kg、现金成本 10.1 元/kg（2026-07 披露 11.5，取 11.6 保守）

输出：data/pig_cycle/daily.json
"""
import warnings, json, os, sys
warnings.filterwarnings("ignore")
import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(REPO, "data", "pig_cycle")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "daily.json")
MONITOR_HIST = "/home/administrator/pig-monitor/history.json"

FULL_COST = 11.6
CASH_COST = 10.1

STOCKS = [
    ("牧原股份", "sz002714", "002714"),
    ("温氏股份", "sz300498", "300498"),
    ("巨星农牧", "sh603477", "603477"),
    ("东瑞股份", "sz001201", "001201"),
    ("兴业银行", "sh601166", "601166"),
]

KEEP_DAYS = 1900        # 保留约 7 年日线，够画完整周期


def main():
    import akshare as ak
    out = {"updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
           "cost": {"full": FULL_COST, "cash": CASH_COST},
           "stocks": {}, "hog": [], "hog_note": ""}

    # ── ① 猪价（周频）────────────────────────────────────────
    print("【1/3】猪价 index_hog_spot_price()")
    h = ak.index_hog_spot_price()
    h["日期"] = pd.to_datetime(h["日期"])
    h["成交均价"] = pd.to_numeric(h["成交均价"], errors="coerce")
    h = h.dropna(subset=["成交均价"]).sort_values("日期")
    h = h[h["日期"] >= pd.Timestamp.now() - pd.Timedelta(days=KEEP_DAYS)]
    out["hog"] = [{"date": d.strftime("%Y-%m-%d"), "price": round(float(p), 3)}
                  for d, p in zip(h["日期"], h["成交均价"])]
    print(f"  {len(out['hog'])} 条  {out['hog'][0]['date']} → {out['hog'][-1]['date']}"
          f"  末值 {out['hog'][-1]['price']}")
    out["hog_note"] = f"周频，akshare 最新 {out['hog'][-1]['date']}（官方源滞后约1周）"

    # ── ② 监控实采补充（比 akshare 新）───────────────────────
    print("【2/3】监控实采 history.json 补最新")
    try:
        with open(MONITOR_HIST, encoding="utf-8") as f:
            hist = json.load(f)
        series = hist.get("series") or []
        added = 0
        last_api = out["hog"][-1]["date"] if out["hog"] else "1970-01-01"
        for rec in series:
            d, p = rec.get("date"), rec.get("pig_price")
            if not d or p is None:
                continue
            if d > last_api and not any(x["date"] == d for x in out["hog"]):
                out["hog"].append({"date": d, "price": round(float(p), 3),
                                   "src": "monitor"})
                added += 1
        out["hog"].sort(key=lambda x: x["date"])
        print(f"  补入 {added} 条监控实采" if added else "  无新增（akshare 已最新）")
    except FileNotFoundError:
        print("  无 history.json，跳过")
    except Exception as e:
        print(f"  跳过: {e}")

    # ── ③ 5 只标的前复权日线 ─────────────────────────────────
    print("【3/3】5 只标的日线（qfq）")
    for name, sym, code in STOCKS:
        try:
            d = ak.stock_zh_a_daily(symbol=sym, adjust="qfq")
            d["date"] = pd.to_datetime(d["date"])
            d = d.dropna(subset=["close"]).sort_values("date")
            d = d[d["date"] >= pd.Timestamp.now() - pd.Timedelta(days=KEEP_DAYS)]
            out["stocks"][name] = {
                "code": code,
                "series": [{"date": x.strftime("%Y-%m-%d"), "close": round(float(c), 2)}
                           for x, c in zip(d["date"], d["close"])],
            }
            s = out["stocks"][name]["series"]
            print(f"  {name:8s} {len(s):5d} 条  {s[0]['date']} → {s[-1]['date']}  末值 {s[-1]['close']}")
        except Exception as e:
            print(f"  ❌ {name}: {type(e).__name__} {str(e)[:90]}")

    # ── 覆盖率核对（铁律：拉完必须回查）──────────────────────
    print()
    print("--- 覆盖率核对 ---")
    print(f"  猪价      {len(out['hog']):4d} 点  末值 {out['hog'][-1]['price']} 元/kg")
    for name, _, _ in STOCKS:
        st = out["stocks"].get(name)
        print(f"  {name:8s} {len(st['series']) if st else 0:4d} 点"
              f"  末值 {st['series'][-1]['close'] if st else '—'}")
    gap = out["hog"][-1]["price"] - FULL_COST
    print(f"  最新猪价 {out['hog'][-1]['price']} vs 完全成本 {FULL_COST} → {gap:+.2f} 元/kg")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n✅ 已保存 {OUT}  ({os.path.getsize(OUT)/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
