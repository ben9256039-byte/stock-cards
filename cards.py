"""把資料畫成手機直式字卡（1080×1350 PNG）。

配色依台股習慣：漲＝紅、跌＝綠。
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Wedge  # noqa: E402

# ---------------------------------------------------------------- 字型與配色
def _setup_font():
    for name in ("Noto Sans CJK TC", "Noto Sans TC", "Microsoft JhengHei", "PingFang TC", "Heiti TC"):
        if any(name == f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


_setup_font()

BG, PANEL, INK, MUTED = "#F4F1EA", "#FFFFFF", "#1C2430", "#7A808A"
NAVY, UP, DOWN, WARN, GRID = "#16324F", "#D7263D", "#169B5B", "#E3A008", "#E7E2D8"
W, H, DPI = 5.4, 6.75, 200  # → 1080 × 1350 px
WEEK = "一二三四五六日"


def pc(v):
    return UP if v > 0 else DOWN if v < 0 else MUTED


def arrow(v):
    return "▲" if v > 0 else "▼" if v < 0 else "－"


def wrap(s, width):
    """中英混排換行：中文算 1 格，英數算 0.55 格。"""
    import re as _re
    lines, cur, n = [], "", 0.0
    for tok in _re.findall(r"[A-Za-z0-9.,%+\-]+|.", s or ""):
        w = sum(1 if ord(ch) > 0x2E80 else 0.55 for ch in tok)
        if n + w > width and cur:
            lines.append(cur)
            cur, n = "", 0.0
        cur += tok
        n += w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- 共用框架
class Card:
    def __init__(self, title, sub, data, page, total):
        self.fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=BG)
        self.data = data
        f = self.fig
        f.patches.append(FancyBboxPatch((0, 0.885), 1, 0.115, boxstyle="square,pad=0",
                                        transform=f.transFigure, fc=NAVY, ec="none"))
        d = dt.date.fromisoformat(data["date"])
        self.t(0.06, 0.952, title, 17, "white", "bold")
        self.t(0.06, 0.912, sub or f"{d:%Y/%m/%d}（{WEEK[d.weekday()]}）收盤", 8.5, "#C9D6E3")
        self.t(0.94, 0.952, f"{page}/{total}", 9, "#C9D6E3", ha="right")
        self.t(0.94, 0.912, "股票每日晨報", 8, "#C9D6E3", ha="right")
        foot = "資料：證交所、櫃買中心、Yahoo Finance｜短評：Claude"
        self.t(0.5, 0.018, foot, 6, MUTED, ha="center")
        if data.get("demo"):
            self.fig.text(0.5, 0.45, "示範資料", fontsize=58, color="#000000", alpha=0.045,
                          ha="center", va="center", rotation=28, weight="bold")

    def t(self, x, y, s, size, color=INK, weight="normal", ha="left", va="center", **kw):
        return self.fig.text(x, y, s, fontsize=size, color=color, weight=weight, ha=ha, va=va, **kw)

    def panel(self, x, y, w, h, fc=PANEL):
        self.fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.018",
                                               transform=self.fig.transFigure, fc=fc, ec="#E2DDD2", lw=0.6,
                                               mutation_aspect=W / H))

    def ax(self, rect):
        a = self.fig.add_axes(rect)
        a.set_zorder(5)  # 疊在面板之上
        a.set_facecolor("none")
        for s in a.spines.values():
            s.set_visible(False)
        return a

    def spark(self, rect, ys, color):
        a = self.ax(rect)
        a.plot(range(len(ys)), ys, color=color, lw=1.2)
        a.fill_between(range(len(ys)), ys, min(ys), color=color, alpha=0.10, lw=0)
        a.scatter([len(ys) - 1], [ys[-1]], s=6, color=color, zorder=3)
        a.set_xticks([]), a.set_yticks([])
        a.set_ylim(min(ys) - (max(ys) - min(ys)) * 0.08, max(ys) + (max(ys) - min(ys)) * 0.08)
        return a

    def note(self, y, label, text, h=0.085, width=30):
        self.panel(0.05, y, 0.90, h, fc="#FBF8F1")
        self.t(0.08, y + h - 0.022, label, 7.5, NAVY, "bold")
        for i, line in enumerate(wrap(text, width)[:2]):
            self.t(0.08, y + h - 0.050 - i * 0.026, line, 8.5)

    def save(self, path):
        self.fig.savefig(path, dpi=DPI, facecolor=BG)
        plt.close(self.fig)


# ---------------------------------------------------------------- 1 總覽
def card_overview(c: Card):
    d = c.data
    m, inst = d.get("market"), d.get("institutional")
    if m:
        c.panel(0.05, 0.665, 0.90, 0.195)
        c.t(0.09, 0.830, "加權指數", 9, MUTED)
        c.t(0.09, 0.768, f"{m['taiex']:,.0f}", 30, INK, "bold")
        c.t(0.09, 0.700, f"{arrow(m['chg'])} {abs(m['chg']):,.0f} 點（{m['chg_pct']:+.2f}%）", 11,
            pc(m["chg"]), "bold")
        c.spark([0.56, 0.69, 0.36, 0.14], [h["taiex"] for h in m["history"]], pc(m["chg"]))
        c.t(0.92, 0.835, "近一月", 6.5, MUTED, ha="right")

    tiles = []
    if m:
        ratio = m["value_bn"] / m["median_bn"]
        tiles.append(("成交金額", f"{m['value_bn']:,.0f}億", f"月中位數的 {ratio:.0%}",
                      UP if ratio >= 1 else DOWN))
    if inst:
        for k in ("外資", "投信", "自營商"):
            v = inst["totals_bn"][k]
            tiles.append((k, f"{v:+,.1f}億", "買超" if v > 0 else "賣超", pc(v)))
    for i, (lab, val, sub, col) in enumerate(tiles):
        x = 0.05 + (i % 2) * 0.46
        y = 0.505 - (i // 2) * 0.150
        c.panel(x, y, 0.44, 0.140)
        c.t(x + 0.04, y + 0.110, lab, 8.5, MUTED)
        c.t(x + 0.04, y + 0.064, val, 17, col, "bold")
        c.t(x + 0.04, y + 0.024, sub, 7.5, MUTED)

    ck = d.get("checklist")
    if ck:
        col = {"綠燈": DOWN, "黃燈": WARN, "紅燈": UP}[ck["level"]]
        c.panel(0.05, 0.245, 0.90, 0.090)
        c.fig.patches.append(Circle((0.115, 0.290), 0.026, transform=c.fig.transFigure, fc=col, ec="none"))
        c.t(0.165, 0.302, f"衰退徵兆檢核：{ck['level']}", 11, INK, "bold")
        c.t(0.165, 0.270, f"警示分數 {ck['score']:g} / {ck['max']}（詳見第 6 張）", 8, MUTED)

    cm = d.get("commentary") or {}
    if cm.get("headline"):
        c.panel(0.05, 0.050, 0.90, 0.175, fc="#FBF8F1")
        c.t(0.08, 0.198, "今日重點", 8, NAVY, "bold")
        for i, line in enumerate(wrap(cm["headline"], 17)[:3]):
            c.t(0.08, 0.155 - i * 0.040, line, 13, INK, "bold")


# ---------------------------------------------------------------- 2 成交量
def card_volume(c: Card):
    m = c.data["market"]
    hist = m["history"]
    xs, ys = range(len(hist)), [h["value_bn"] for h in hist]
    med = m["median_bn"]
    c.panel(0.05, 0.40, 0.90, 0.46)
    c.t(0.09, 0.835, "上市成交金額（億元）", 9, INK, "bold")
    c.t(0.91, 0.835, f"中位數 {med:,.0f} 億", 8, MUTED, ha="right")
    a = c.ax([0.13, 0.46, 0.79, 0.34])
    a.fill_between(xs, ys, min(ys) * 0.9, color=NAVY, alpha=0.07, lw=0)
    a.plot(xs, ys, color=NAVY, lw=1.6, marker="o", ms=2.2)
    a.axhline(med, color=WARN, lw=1.1, ls="--")
    a.text(0, med, " 中位數", color=WARN, fontsize=6.5, va="bottom")
    a.scatter([xs[-1]], [ys[-1]], s=40, color=pc(ys[-1] - med), zorder=4)
    a.annotate(f"{ys[-1]:,.0f}", (xs[-1], ys[-1]), xytext=(-4, -14), textcoords="offset points",
               ha="right", fontsize=8.5, weight="bold", color=pc(ys[-1] - med))
    a.set_ylim(min(ys) * 0.9, max(ys) * 1.06)
    step = max(1, len(hist) // 6)
    a.set_xticks(list(xs)[::step])
    a.set_xticklabels([h["date"] for h in hist][::step], fontsize=6.5, color=MUTED)
    a.tick_params(axis="y", labelsize=6.5, colors=MUTED, length=0)
    a.tick_params(axis="x", length=0)
    a.grid(axis="y", color=GRID, lw=0.6)

    # 指數走勢對照
    c.panel(0.05, 0.215, 0.90, 0.170)
    c.t(0.09, 0.362, "加權指數（對照）", 8.5, INK, "bold")
    ti = [h["taiex"] for h in hist]
    c.t(0.91, 0.362, f"{ti[-1]:,.0f}", 8.5, pc(m["chg"]), "bold", ha="right")
    c.spark([0.09, 0.232, 0.82, 0.105], ti, pc(ti[-1] - ti[0]))

    above = sum(1 for v in ys if v > med)
    c.note(0.050, "短評", (c.data.get("commentary") or {}).get("volume")
           or f"近 {len(ys)} 日有 {above} 日高於中位數", h=0.150)


# ---------------------------------------------------------------- 3 三大法人
def card_institutional(c: Card):
    inst = c.data["institutional"]
    order = ("外資", "投信", "自營商")
    ph, gap, top = 0.262, 0.012, 0.865
    for k, who in enumerate(order):
        y0 = top - (k + 1) * ph - k * gap
        c.panel(0.05, y0, 0.90, ph)
        tot = inst["totals_bn"][who]
        c.t(0.08, y0 + ph - 0.025, who, 11, NAVY, "bold")
        c.t(0.92, y0 + ph - 0.025, f"合計 {tot:+,.1f} 億", 9, pc(tot), "bold", ha="right")
        rows = inst["top"][who]["buy"] + inst["top"][who]["sell"]
        mx = max(abs(r["lots"]) for r in rows) or 1
        rh = (ph - 0.055) / 6
        for i, r in enumerate(rows):
            y = y0 + ph - 0.058 - i * rh - rh / 2 + 0.006
            if i == 3:
                c.fig.add_artist(plt.Line2D([0.08, 0.92], [y + rh / 2 + 0.0, y + rh / 2],
                                            transform=c.fig.transFigure, color=GRID, lw=0.6))
            col = pc(r["lots"])
            c.t(0.08, y, ("買" if i < 3 else "賣"), 6.5, "white", "bold",
                bbox=dict(boxstyle="round,pad=0.25", fc=col, ec="none"))
            c.t(0.125, y, r["name"], 9, INK, "bold")
            c.t(0.255, y, (r.get("reason") or "")[:14], 7, MUTED)
            bw = 0.20 * abs(r["lots"]) / mx
            c.fig.patches.append(FancyBboxPatch((0.60, y - 0.008), bw, 0.016, boxstyle="square,pad=0",
                                                transform=c.fig.transFigure, fc=col, ec="none", alpha=0.85))
            c.t(0.60 + bw + 0.012, y, f"{r['lots']:+,.0f}", 7.5, col, "bold")
    c.t(0.95, 0.042, "單位：張", 6.5, MUTED, ha="right")


# ---------------------------------------------------------------- 4 融資融券
def card_margin(c: Card):
    mg = c.data["margin"]
    kp = []
    if mg.get("twse"):
        kp.append(("上市融資餘額", f"{mg['twse']['margin_bal_bn']:,.0f}億", mg["twse"]["margin_chg_bn"], "億"))
    if mg.get("tpex") and mg["tpex"].get("margin_bal_bn"):
        kp.append(("上櫃融資餘額", f"{mg['tpex']['margin_bal_bn']:,.0f}億", mg["tpex"]["margin_chg_bn"], "億"))
    if mg.get("twse_short"):
        v = mg["twse_short"]["short_chg_lots"]
        kp.append(("上市融券增減", f"{v:+,.0f}張", None, ""))
    n = max(len(kp), 1)
    w = (0.90 - 0.02 * (n - 1)) / n
    for i, (lab, val, chg, u) in enumerate(kp):
        x = 0.05 + i * (w + 0.02)
        c.panel(x, 0.725, w, 0.135)
        c.t(x + 0.03, 0.833, lab, 7.5, MUTED)
        c.t(x + 0.03, 0.790, val, 13.5, INK, "bold")
        if chg is not None:
            c.t(x + 0.03, 0.748, f"{arrow(chg)} {abs(chg):,.1f}{u}", 8, pc(chg), "bold")

    # 維持率儀表
    r = mg.get("maintenance_ratio")
    c.panel(0.05, 0.445, 0.90, 0.265)
    c.t(0.09, 0.685, "整戶擔保維持率", 9, INK, "bold")
    c.t(0.91, 0.685, "<140% 危險｜140–160% 注意｜>160% 安全", 6.3, MUTED, ha="right")
    a = c.ax([0.25, 0.455, 0.50, 0.215])
    a.set_xlim(-1.15, 1.15), a.set_ylim(-0.25, 1.1), a.set_aspect("equal"), a.axis("off")
    lo, hi = 120, 200

    def ang(v):
        return 180 - (min(max(v, lo), hi) - lo) / (hi - lo) * 180

    for s, e, col in ((lo, 140, UP), (140, 160, WARN), (160, hi, DOWN)):
        a.add_patch(Wedge((0, 0), 1, ang(e), ang(s), width=0.22, fc=col, alpha=0.85, ec="white", lw=1))
    if r:
        import math
        th = math.radians(ang(r))
        a.plot([0, 0.78 * math.cos(th)], [0, 0.78 * math.sin(th)], color=INK, lw=2.2, solid_capstyle="round")
        a.add_patch(Circle((0, 0), 0.06, fc=INK))
        a.text(0, -0.2, f"{r:.1f}%", ha="center", fontsize=15, weight="bold", color=INK)
    else:
        a.text(0, 0.2, "今日無資料", ha="center", fontsize=9, color=MUTED)
    for v in (lo, 140, 160, hi):
        import math
        th = math.radians(ang(v))
        a.text(1.13 * math.cos(th), 1.13 * math.sin(th), str(v), ha="center", va="center", fontsize=6, color=MUTED)

    # 融資減少前五
    top5 = mg.get("margin_decrease_top") or []
    c.panel(0.05, 0.165, 0.90, 0.265)
    c.t(0.09, 0.405, "融資減少前五名（張）", 9, INK, "bold")
    if top5:
        mx = max(abs(x["lots"]) for x in top5)
        for i, s in enumerate(top5):
            y = 0.365 - i * 0.040
            c.t(0.09, y, f"{s['name']}", 8.5, INK, "bold")
            c.t(0.21, y, s["code"], 7, MUTED)
            bw = 0.45 * abs(s["lots"]) / mx
            c.fig.patches.append(FancyBboxPatch((0.30, y - 0.009), bw, 0.018, boxstyle="square,pad=0",
                                                transform=c.fig.transFigure, fc=DOWN, ec="none", alpha=0.8))
            c.t(0.30 + bw + 0.012, y, f"{s['lots']:,.0f}", 7.5, DOWN, "bold")
    cm = (c.data.get("commentary") or {}).get("margin")
    if cm:
        c.note(0.050, "短評", cm, h=0.100)


# ---------------------------------------------------------------- 5 觀察名單
def card_watchlist(c: Card):
    wl = c.items
    cols, tw, th = 3, 0.287, 0.185
    allw = c.data["watchlist"]
    up = sum(1 for s in allw if s["chg_pct"] > 0)
    c.t(0.06, 0.862, f"共 {len(allw)} 檔：上漲 {up}・下跌 {len(allw) - up}（依產業分組，組內依漲跌幅）", 7.5, MUTED)
    for i, s in enumerate(wl):
        x = 0.05 + (i % cols) * (tw + 0.0165)
        y = 0.655 - (i // cols) * (th + 0.012)
        col = pc(s["chg_pct"])
        alpha = min(abs(s["chg_pct"]) / 5, 1) * 0.22 + 0.04
        c.panel(x, y, tw, th)
        c.fig.patches.append(FancyBboxPatch((x, y), tw, th, boxstyle="round,pad=0,rounding_size=0.018",
                                            transform=c.fig.transFigure, fc=col, alpha=alpha, ec="none",
                                            mutation_aspect=W / H))
        c.t(x + 0.025, y + th - 0.028, s["name"], 9.5, INK, "bold")
        c.t(x + tw - 0.02, y + th - 0.028, s.get("code", ""), 6.5, MUTED, ha="right")
        tag = (s.get("theme") or s.get("industry") or "")[:9]
        if tag:
            c.t(x + tw - 0.02, y + th - 0.068, tag, 6, NAVY, ha="right")
        c.t(x + 0.025, y + th - 0.068, f"{s['close']:,.1f}" if s["close"] < 1000 else f"{s['close']:,.0f}",
            10, INK)
        c.t(x + 0.025, y + th - 0.103, f"{arrow(s['chg_pct'])}{abs(s['chg_pct']):.2f}%", 10.5, col, "bold")
        if s.get("history"):
            c.spark([x + 0.02, y + 0.012, tw - 0.04, 0.052], s["history"], col)


# ---------------------------------------------------------------- 6 衰退徵兆
def card_checklist(c: Card):
    ck = c.data["checklist"]
    col = {"綠燈": DOWN, "黃燈": WARN, "紅燈": UP}[ck["level"]]
    c.panel(0.05, 0.700, 0.90, 0.160)
    for k, (lv, cc) in enumerate((("綠", DOWN), ("黃", WARN), ("紅", UP))):
        on = ck["level"].startswith(lv)
        c.fig.patches.append(Circle((0.13 + k * 0.085, 0.780), 0.030, transform=c.fig.transFigure,
                                    fc=cc if on else "#E4E0D6", ec="none"))
    c.t(0.43, 0.805, f"今日：{ck['level']}", 15, col, "bold")
    c.t(0.43, 0.760, f"警示分數 {ck['score']:g} / {ck['max']}", 9, MUTED)
    c.t(0.43, 0.728, "紅=1分　黃=0.5分；<2 綠燈、2–3.5 黃燈、≥4 紅燈", 6.3, MUTED)

    items = ck["items"]
    rh = 0.072
    c.panel(0.05, 0.860 - 0.175 - len(items) * rh - 0.02, 0.90, len(items) * rh + 0.02)
    sc = {"ok": DOWN, "warn": WARN, "alert": UP}
    st = {"ok": "正常", "warn": "注意", "alert": "警示"}
    for i, it in enumerate(items):
        y = 0.655 - i * rh
        c.fig.patches.append(Circle((0.10, y), 0.014, transform=c.fig.transFigure,
                                    fc=sc[it["status"]], ec="none"))
        c.t(0.135, y + 0.012, it["item"], 9, INK, "bold")
        c.t(0.135, y - 0.016, it["rule"], 6.5, MUTED)
        c.t(0.80, y + 0.012, it["value"], 8.5, INK, ha="right")
        c.t(0.91, y + 0.012, st[it["status"]], 7.5, sc[it["status"]], "bold", ha="right")
        if i < len(items) - 1:
            c.fig.add_artist(plt.Line2D([0.08, 0.92], [y - rh / 2, y - rh / 2],
                                        transform=c.fig.transFigure, color=GRID, lw=0.6))


# ---------------------------------------------------------------- 7 國際市場
def card_global(c: Card):
    gl = c.data["global"][:6]
    tw, th = 0.44, 0.255
    for i, g in enumerate(gl):
        x = 0.05 + (i % 2) * (tw + 0.02)
        y = 0.597 - (i // 2) * (th + 0.012)
        col = pc(g["chg_pct"])
        if g["symbol"] in ("^VIX", "TWD=X", "^TNX"):  # 這三個上升是偏空訊號 → 用中性色
            col = WARN if g["chg_pct"] > 0 else NAVY
        c.panel(x, y, tw, th)
        c.t(x + 0.035, y + th - 0.032, g["name"], 9, MUTED)
        v = g["value"]
        c.t(x + 0.035, y + th - 0.080, f"{v:,.2f}" if v < 100 else f"{v:,.0f}", 16, INK, "bold")
        c.t(x + 0.035, y + th - 0.120, f"{arrow(g['chg_pct'])} {abs(g['chg_pct']):.2f}%", 9.5, col, "bold")
        if g.get("history"):
            c.spark([x + 0.03, y + 0.018, tw - 0.06, 0.085], g["history"], col)
    c.t(0.95, 0.042, "VIX、殖利率、美元上升以橘色標示（對股市偏空）", 6.3, MUTED, ha="right")


# ---------------------------------------------------------------- 8 新聞
def card_news(c: Card):
    news = c.data.get("news", [])[:5]
    tagc = {"利多": UP, "利空": DOWN, "中性": MUTED}
    ph, gap = 0.150, 0.012
    for i, n in enumerate(news):
        y = 0.865 - (i + 1) * ph - i * gap
        c.panel(0.05, y, 0.90, ph)
        c.fig.patches.append(FancyBboxPatch((0.05, y), 0.012, ph, boxstyle="square,pad=0",
                                            transform=c.fig.transFigure, fc=tagc.get(n["tag"], MUTED), ec="none"))
        c.t(0.09, y + ph - 0.030, n["tag"], 7, "white", "bold",
            bbox=dict(boxstyle="round,pad=0.3", fc=tagc.get(n["tag"], MUTED), ec="none"))
        c.t(0.17, y + ph - 0.030, n["title"], 10.5, INK, "bold")
        for k, line in enumerate(wrap(n["summary"], 26)[:2]):
            c.t(0.09, y + ph - 0.068 - k * 0.028, line, 8.2)
        c.t(0.92, y + 0.018, n.get("source", ""), 6.5, MUTED, ha="right")


# ---------------------------------------------------------------- 產出
PLAN = [
    ("overview", "台股晨報總覽", None, card_overview, lambda d: "market" in d),
    ("volume", "成交量｜近一個月", None, card_volume, lambda d: "market" in d),
    ("institutional", "三大法人買賣超", "買超／賣超前三名・原因", card_institutional, lambda d: "institutional" in d),
    ("margin", "融資融券", None, card_margin, lambda d: "margin" in d),
    ("watchlist", "觀察名單", None, card_watchlist, lambda d: d.get("watchlist")),
    ("checklist", "衰退徵兆檢核表", None, card_checklist, lambda d: d.get("checklist")),
    ("global", "國際市場", "美股收盤・匯率・利率", card_global, lambda d: d.get("global")),
    ("news", "新聞重點", None, card_news, lambda d: d.get("news")),
]


def render_all(data, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    plan = []
    for key, title, sub, fn, ok in PLAN:
        if not ok(data):
            continue
        if key == "watchlist":  # 依產業分組排序，每 12 檔一張
            wl = sorted(data["watchlist"], key=lambda s: (s.get("industry") or "~", -s["chg_pct"]))
            pages = [wl[i:i + 12] for i in range(0, len(wl), 12)]
            for k, chunk in enumerate(pages):
                t = title if len(pages) == 1 else f"{title}（{k + 1}/{len(pages)}）"
                plan.append((f"{key}{k + 1}" if len(pages) > 1 else key, t, sub, fn, chunk))
        else:
            plan.append((key, title, sub, fn, None))
    paths = []
    for i, (key, title, sub, fn, items) in enumerate(plan, 1):
        c = Card(title, sub, data, i, len(plan))
        c.items = items
        try:
            fn(c)
        except Exception as e:  # noqa: BLE001
            c.t(0.5, 0.5, f"本卡產生失敗：{e}"[:40], 9, UP, ha="center")
        p = outdir / f"{i:02d}_{key}.png"
        c.save(p)
        paths.append(str(p))
    return paths
