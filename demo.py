"""示範資料：只用來看字卡排版，數字皆為虛構。"""
import random
import statistics


def _walk(start, n, vol, seed, drift=0.0):
    rnd = random.Random(seed)
    v, out = start, []
    for _ in range(n):
        v *= 1 + rnd.gauss(drift, vol)
        out.append(v)
    return out


def demo_data(cfg):
    dates = ["10/15", "10/16", "10/17", "10/20", "10/21", "10/22", "10/23", "10/24", "10/27", "10/28",
             "10/29", "10/30", "10/31", "11/03", "11/04", "11/05", "11/06", "11/07", "11/10", "11/11",
             "11/12", "11/13"]
    taiex = _walk(27200, len(dates), 0.009, 1, 0.0008)
    vol = [5200, 5650, 4980, 5120, 6030, 5480, 5310, 4870, 5260, 5900, 6420, 6110, 5580, 5020,
           4760, 5340, 5810, 4690, 4550, 4920, 5180, 4380]
    hist = [{"date": d, "value_bn": v, "taiex": t} for d, v, t in zip(dates, vol, taiex)]
    chg = taiex[-1] - taiex[-2]
    data = {
        "date": "2026-11-13",
        "demo": True,
        "errors": [],
        "market": {"taiex": taiex[-1], "chg": chg, "chg_pct": chg / taiex[-2] * 100,
                   "value_bn": vol[-1], "history": hist, "median_bn": statistics.median(vol)},
        "institutional": {
            "totals_bn": {"外資": -186.4, "投信": 42.7, "自營商": -15.3},
            "top": {
                "外資": {"buy": [{"code": "2317", "name": "鴻海", "lots": 18240, "reason": "AI伺服器出貨上修"},
                                {"code": "2382", "name": "廣達", "lots": 9310, "reason": "GB300拉貨加速"},
                                {"code": "2383", "name": "台光電", "lots": 4120, "reason": "高階CCL報價調漲"}],
                        "sell": [{"code": "2330", "name": "台積電", "lots": -21560, "reason": "權值股提款、匯率因素"},
                                 {"code": "2303", "name": "聯電", "lots": -15240, "reason": "成熟製程價格壓力"},
                                 {"code": "3481", "name": "群創", "lots": -12080, "reason": "面板報價走弱"}]},
                "投信": {"buy": [{"code": "3105", "name": "穩懋", "lots": 3820, "reason": "低軌衛星PA需求"},
                                {"code": "2049", "name": "上銀", "lots": 2950, "reason": "機器人題材、訂單回溫"},
                                {"code": "6510", "name": "精測", "lots": 1240, "reason": "AI探針卡接單滿"}],
                        "sell": [{"code": "2603", "name": "長榮", "lots": -2860, "reason": "運價回落"},
                                 {"code": "2409", "name": "友達", "lots": -2210, "reason": "季底作帳結束"},
                                 {"code": "3037", "name": "欣興", "lots": -1730, "reason": "漲多獲利了結"}]},
                "自營商": {"buy": [{"code": "4576", "name": "大銀微", "lots": 1680, "reason": "人形機器人概念"},
                                  {"code": "2308", "name": "台達電", "lots": 1210, "reason": "資料中心電源"},
                                  {"code": "1597", "name": "直得", "lots": 980, "reason": "滾柱螺桿題材"}],
                          "sell": [{"code": "2330", "name": "台積電", "lots": -3420, "reason": "避險部位調節"},
                                   {"code": "2454", "name": "聯發科", "lots": -1860, "reason": "手機晶片庫存"},
                                   {"code": "2881", "name": "富邦金", "lots": -1290, "reason": "權證避險賣出"}]},
            }},
        "margin": {
            "twse": {"margin_bal_bn": 3462.5, "margin_chg_bn": 28.6},
            "tpex": {"margin_bal_bn": 1186.2, "margin_chg_bn": -6.4},
            "twse_short": {"short_chg_lots": 5230},
            "maintenance_ratio": 166.8,
            "margin_decrease_top": [{"code": "2409", "name": "友達", "lots": -8120},
                                    {"code": "3481", "name": "群創", "lots": -6340},
                                    {"code": "2344", "name": "華邦電", "lots": -4210},
                                    {"code": "2618", "name": "長榮航", "lots": -3060},
                                    {"code": "2303", "name": "聯電", "lots": -2780}]},
        "commentary": {
            "headline": "外資賣超台積電拖累指數，機器人與AI伺服器族群逆勢有撐",
            "volume": "成交金額4,380億，僅月中位數約8成，量縮整理、追價意願低",
            "margin": "指數跌但上市融資增28.6億，散戶逢低承接，籌碼稍亂",
        },
        "news": [
            {"title": "輝達GB300出貨上修", "summary": "供應鏈傳Q1拉貨量較原預估增一成，鴻海、廣達受惠", "tag": "利多", "source": "工商時報"},
            {"title": "台積電2奈米良率傳佳", "summary": "法人估明年2奈米營收占比可望達一成，但短線外資提款", "tag": "中性", "source": "經濟日報"},
            {"title": "人形機器人零組件需求升溫", "summary": "國際大廠擴大採購減速機與線性滑軌，上銀、直得受關注", "tag": "利多", "source": "MoneyDJ"},
            {"title": "美元走強、台幣貶破32", "summary": "Fed官員偏鷹發言，熱錢外流壓抑權值股", "tag": "利空", "source": "中央社"},
            {"title": "面板報價11月下旬續跌", "summary": "電視面板需求疲弱，群創、友達營運承壓", "tag": "利空", "source": "TrendForce"},
        ],
    }

    wl = []
    for i, w in enumerate(cfg["watchlist"]):
        base = [1085, 1180, 690, 1520, 168, 395, 74, 840, 268, 412, 236, 182][i % 12]
        h = _walk(base, 20, 0.022, 100 + i)
        wl.append({**w, "close": h[-1], "chg_pct": (h[-1] / h[-2] - 1) * 100, "history": h})
    data["watchlist"] = wl

    g_base = {"^SOX": (5820, 0.018), "^IXIC": (19850, 0.011), "^GSPC": (6120, 0.008),
              "^VIX": (18.5, 0.06), "^TNX": (4.32, 0.012), "TWD=X": (31.85, 0.003)}
    gl = []
    for i, g in enumerate(cfg["global"]):
        b, v = g_base.get(g["symbol"], (100, 0.01))
        h = _walk(b, 20, v, 200 + i)
        gl.append({**g, "value": h[-1], "chg_pct": (h[-1] / h[-2] - 1) * 100, "history": h})
    data["global"] = gl
    return data
