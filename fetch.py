"""抓資料：證交所、櫃買中心、Yahoo Finance（皆免費、免金鑰）。

每個區塊各自 try/except：某一個來源掛掉，只會少一張卡，不會整份失敗。
"""
from __future__ import annotations

import datetime as dt
import statistics
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (stock-cards)"}
TIMEOUT = 20


def _get_json(url, params=None, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"抓取失敗 {url}: {last}")


def _num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("+", "").strip()
    if s in ("", "--", "X", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _roc_to_date(s):
    """'115/11/13' 或 '1151113' → date"""
    s = str(s).replace("/", "")
    y, m, d = int(s[:-4]) + 1911, int(s[-4:-2]), int(s[-2:])
    return dt.date(y, m, d)


# ---------------------------------------------------------------- 大盤 + 成交量
def fetch_market(day: dt.date):
    """證交所 FMTQIK：每日成交金額與加權指數（取本月＋上月，湊滿約 20 個交易日）。"""
    rows = []
    for months_back in (1, 0):
        ref = (day.replace(day=1) - dt.timedelta(days=1)) if months_back else day
        js = _get_json("https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK",
                       {"date": ref.strftime("%Y%m01"), "response": "json"})
        for r in js.get("data", []):
            # 欄位：日期, 成交股數, 成交金額, 成交筆數, 發行量加權股價指數, 漲跌點數
            d = _roc_to_date(r[0])
            if d <= day:
                rows.append({"date": d, "value_bn": _num(r[2]) / 1e8,
                             "taiex": _num(r[4]), "chg": _num(r[5])})
    rows.sort(key=lambda x: x["date"])
    rows = rows[-22:]
    last = rows[-1]
    prev = rows[-2]["taiex"]
    return {
        "date": last["date"].isoformat(),
        "taiex": last["taiex"],
        "chg": last["chg"],
        "chg_pct": last["chg"] / prev * 100,
        "value_bn": last["value_bn"],
        "history": [{"date": r["date"].strftime("%m/%d"), "value_bn": r["value_bn"],
                     "taiex": r["taiex"]} for r in rows],
    }


# ---------------------------------------------------------------- 三大法人
def fetch_institutional(day: dt.date, names_hint=None):
    ymd = day.strftime("%Y%m%d")
    # 各法人合計金額（億）
    js = _get_json("https://www.twse.com.tw/rwd/zh/fund/BFI82U",
                   {"dayDate": ymd, "type": "day", "response": "json"})
    totals = {"外資": 0.0, "投信": 0.0, "自營商": 0.0}
    for r in js.get("data", []):
        name, net = r[0], _num(r[3]) or 0
        if "外資" in name:
            totals["外資"] += net / 1e8
        elif "投信" in name:
            totals["投信"] += net / 1e8
        elif "自營商" in name:
            totals["自營商"] += net / 1e8

    # 個股買賣超（股數）
    js = _get_json("https://www.twse.com.tw/rwd/zh/fund/T86",
                   {"date": ymd, "selectType": "ALLBUT0999", "response": "json"})
    fields = js.get("fields", [])

    def col(*names):
        for n in names:  # 先找完全相同的欄名，再找開頭相同的
            if n in fields:
                return fields.index(n)
        for n in names:
            for i, f in enumerate(fields):
                if f.startswith(n):
                    return i
        raise KeyError(f"{names} 不在欄位中：{fields}")

    idx = {"外資": col("外陸資買賣超股數(不含外資自營商)", "外陸資買賣超股數"),
           "投信": col("投信買賣超股數"),
           "自營商": col("自營商買賣超股數")}
    top = {}
    for who, ci in idx.items():
        lst = [{"code": r[0].strip(), "name": r[1].strip(), "lots": (_num(r[ci]) or 0) / 1000}
               for r in js.get("data", [])]
        lst.sort(key=lambda x: x["lots"])
        top[who] = {"buy": lst[::-1][:3], "sell": lst[:3]}
    return {"totals_bn": totals, "top": top}


# ---------------------------------------------------------------- 融資融券
def fetch_margin(day: dt.date):
    ymd = day.strftime("%Y%m%d")
    out = {}
    # 上市：信用交易統計（融資金額 仟元）
    js = _get_json("https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN",
                   {"date": ymd, "selectType": "MS", "response": "json"})
    tables = js.get("tables") or [js]
    for t in tables:
        for r in t.get("data", []):
            if "融資金額" in r[0]:
                prev, today = _num(r[4]), _num(r[5])
                out["twse"] = {"margin_bal_bn": today / 1e5, "margin_chg_bn": (today - prev) / 1e5}
            if r[0].startswith("融券") and "交易單位" in r[0]:
                out.setdefault("twse_short", {})["short_chg_lots"] = _num(r[5]) - _num(r[4])

    # 個股融資減少前五（上市）
    js = _get_json("https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN",
                   {"date": ymd, "selectType": "ALL", "response": "json"})
    tables = js.get("tables") or [js]
    stock_tbl = max(tables, key=lambda t: len(t.get("data", [])))
    lst = []
    for r in stock_tbl.get("data", []):
        # 代號, 名稱, 融資買進, 融資賣出, 現金償還, 前日餘額, 今日餘額 ...
        prev, today = _num(r[5]), _num(r[6])
        if prev is not None and today is not None:
            lst.append({"code": r[0].strip(), "name": r[1].strip(), "lots": today - prev})
    lst.sort(key=lambda x: x["lots"])
    out["margin_decrease_top"] = lst[:5]

    # 上櫃：櫃買中心融資融券餘額
    try:
        roc = f"{day.year - 1911}/{day:%m/%d}"
        js = _get_json("https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php",
                       {"l": "zh-tw", "o": "json", "d": roc})
        tot = js.get("tfootData_one") or js.get("tables", [{}])[0].get("summary", [None])[0]
        # 欄位依櫃買格式：…資餘額(仟元)在倒數區段；抓不到就略過
        if tot:
            nums = [_num(x) for x in tot if _num(x) is not None]
            out["tpex"] = {"margin_bal_bn": None, "margin_chg_bn": None, "_raw": nums}
    except Exception:  # noqa: BLE001
        pass

    # 整戶擔保維持率：證交所沒有免費 API，交給 AI 從新聞補（見 analysis.py）
    out["maintenance_ratio"] = None
    return out


# ---------------------------------------------------------------- Yahoo 報價
def _yahoo(symbol, rng="1mo"):
    js = _get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                   {"range": rng, "interval": "1d"})
    res = js["chart"]["result"][0]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    if len(closes) < 2:
        raise RuntimeError(f"{symbol} 無資料")
    return closes


def fetch_quotes(items, tw=True):
    out = []
    for it in items:
        symbols = [it["symbol"]] if it.get("symbol") else [f"{it['code']}.TW", f"{it['code']}.TWO"]
        for sym in symbols:
            try:
                closes = _yahoo(sym)
                out.append({**it, "symbol": sym, "close": closes[-1],
                            "chg_pct": (closes[-1] / closes[-2] - 1) * 100,
                            "value": closes[-1], "history": closes[-20:]})
                break
            except Exception:  # noqa: BLE001
                continue
    return out


# ---------------------------------------------------------------- 全部
def fetch_all(cfg, day: dt.date):
    data = {"date": day.isoformat(), "errors": []}
    for key, fn in [("market", lambda: fetch_market(day)),
                    ("institutional", lambda: fetch_institutional(day)),
                    ("margin", lambda: fetch_margin(day)),
                    ("watchlist", lambda: fetch_quotes(cfg["watchlist"])),
                    ("global", lambda: fetch_quotes(cfg["global"]))]:
        try:
            data[key] = fn()
        except Exception as e:  # noqa: BLE001
            data["errors"].append(f"{key}: {e}")
    if "market" in data:
        data["date"] = data["market"]["date"]
        vals = [h["value_bn"] for h in data["market"]["history"]]
        data["market"]["median_bn"] = statistics.median(vals)
    return data


def last_trading_day(today=None):
    today = today or dt.date.today()
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d
