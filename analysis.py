"""規則判斷（衰退徵兆檢核表）＋ AI 短評。

數字類判斷全部用固定規則算，每天標準一致；
「為什麼買賣超」「新聞重點」這類需要判斷的內容才交給 Claude。
沒設定 ANTHROPIC_API_KEY 時，用簡單規則文字代替，程式照樣跑得完。
"""
from __future__ import annotations

import json
import os
import re
import statistics

import requests


def _g(data, name):
    for g in data.get("global", []):
        if g["name"].startswith(name):
            return g
    return None


def compute_checklist(data, th):
    items = []

    def add(item, value, rule, status):
        items.append({"item": item, "value": value, "rule": rule, "status": status})

    m = data.get("market")
    if m:
        hist = [h["taiex"] for h in m["history"]]
        ma20 = statistics.mean(hist[-20:])
        add("加權指數 vs 20日均線", f"{m['taiex']:,.0f} / {ma20:,.0f}", "跌破均線＝警示",
            "ok" if m["taiex"] >= ma20 else ("alert" if m["taiex"] < ma20 * 0.97 else "warn"))
        med = m.get("median_bn") or statistics.median(h["value_bn"] for h in m["history"])
        ratio = m["value_bn"] / med
        add("成交金額 vs 月中位數", f"{ratio:.0%}", "量縮<85%＝注意",
            "ok" if ratio >= 0.85 else ("warn" if ratio >= 0.7 else "alert"))

    inst = data.get("institutional")
    if inst:
        f = inst["totals_bn"]["外資"]
        add("外資買賣超", f"{f:+,.0f} 億",
            f"賣超>{th['foreign_sell_warn_bn']}億注意",
            "ok" if f > -th["foreign_sell_warn_bn"] else
            ("warn" if f > -th["foreign_sell_alert_bn"] else "alert"))

    mg = data.get("margin", {})
    if mg.get("twse") and m:
        chg = mg["twse"]["margin_chg_bn"]
        bad = chg > 0 and m["chg"] < 0
        add("融資增加但指數下跌", f"融資{chg:+.1f}億", "散戶接刀＝注意", "warn" if bad else "ok")
    if mg.get("maintenance_ratio"):
        r = mg["maintenance_ratio"]
        add("整戶擔保維持率", f"{r:.0f}%", f"<{th['maint_warn']}%注意",
            "ok" if r >= th["maint_warn"] else ("warn" if r >= th["maint_alert"] else "alert"))

    sox = _g(data, "費城")
    if sox:
        p = sox["chg_pct"]
        add("費半單日漲跌", f"{p:+.1f}%", f"跌>{-th['sox_drop_warn_pct']}%注意",
            "ok" if p > th["sox_drop_warn_pct"] else ("warn" if p > th["sox_drop_alert_pct"] else "alert"))
    vix = _g(data, "VIX")
    if vix:
        v = vix["value"]
        add("VIX 恐慌指數", f"{v:.1f}", f">{th['vix_warn']}注意",
            "ok" if v < th["vix_warn"] else ("warn" if v < th["vix_alert"] else "alert"))
    twd = _g(data, "美元/台幣")
    if twd:
        p = twd["chg_pct"]
        add("台幣匯率", f"{twd['value']:.2f}（{p:+.2f}%）", f"單日貶>{th['twd_weak_warn_pct']}%注意",
            "warn" if p > th["twd_weak_warn_pct"] else "ok")

    score = sum({"ok": 0, "warn": 0.5, "alert": 1}[i["status"]] for i in items)
    level = "綠燈" if score < 2 else ("黃燈" if score < 4 else "紅燈")
    return {"items": items, "score": score, "max": len(items), "level": level}


# ---------------------------------------------------------------- AI 短評
PROMPT = """你是台股晨報編輯。以下是 {date} 收盤後的數據（JSON）。請用繁體中文，回傳「只有 JSON」：
{{
 "headline": "一句話總結今天盤勢重點（30字內）",
 "volume": "成交量短評（40字內，跟月中位數比較）",
 "margin": "融資融券短評（40字內）",
 "maintenance_ratio": 整戶擔保維持率數字（查新聞，查不到填 null）,
 "reasons": {{"股票代號": "買賣超原因（14字內）", ...}},   ← 三大法人買賣超前三名每一檔都要
 "news": [{{"title": "標題（20字內）", "summary": "摘要（40字內）", "tag": "利多|利空|中性", "source": "媒體名"}}]  ← 4~5則，與台股/半導體/觀察名單相關
}}
觀察名單：{watch}
數據：
{data}
"""


def ai_commentary(data, cfg):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return fallback_commentary(data)
    slim = {k: data.get(k) for k in ("market", "institutional", "margin", "global")}
    body = {
        "model": cfg["ai"]["model"],
        "max_tokens": 3000,
        "messages": [{"role": "user", "content": PROMPT.format(
            date=data["date"], watch="、".join(w["name"] for w in cfg["watchlist"]),
            data=json.dumps(slim, ensure_ascii=False, default=str))}],
    }
    if cfg["ai"].get("use_web_search"):
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}]
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", json=body, timeout=180,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"] if b["type"] == "text")
        js = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        return js
    except Exception as e:  # noqa: BLE001
        data.setdefault("errors", []).append(f"AI 短評失敗：{e}")
        return fallback_commentary(data)


def fallback_commentary(data):
    m = data.get("market", {})
    out = {"reasons": {}, "news": []}
    if m:
        up = "上漲" if m["chg"] >= 0 else "下跌"
        out["headline"] = f"加權指數{up} {abs(m['chg']):.0f} 點，收 {m['taiex']:,.0f}"
        med = m.get("median_bn", m["value_bn"])
        out["volume"] = f"成交 {m['value_bn']:,.0f} 億，為月中位數的 {m['value_bn'] / med:.0%}"
    mg = data.get("margin", {}).get("twse")
    if mg:
        out["margin"] = f"上市融資餘額 {mg['margin_bal_bn']:,.0f} 億，單日 {mg['margin_chg_bn']:+.1f} 億"
    return out


def merge(data, ai):
    data["commentary"] = {k: ai.get(k) for k in ("headline", "volume", "margin")}
    if ai.get("maintenance_ratio") and not data.get("margin", {}).get("maintenance_ratio"):
        data.setdefault("margin", {})["maintenance_ratio"] = float(ai["maintenance_ratio"])
    reasons = ai.get("reasons") or {}
    for side in data.get("institutional", {}).get("top", {}).values():
        for lst in side.values():
            for s in lst:
                s.setdefault("reason", reasons.get(s["code"], ""))
    if ai.get("news"):
        data["news"] = ai["news"]
    return data
