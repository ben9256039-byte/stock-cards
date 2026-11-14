"""股票晨報字卡：抓資料 → 規則判斷 → AI 短評 → 畫字卡 → 寄信。

用法：
  python main.py --demo            # 用示範資料只畫卡（不連網）
  python main.py                   # 抓前一個交易日資料，畫卡
  python main.py --send            # 畫完寄到 Gmail（需設定環境變數）
  python main.py --date 2026-11-13 # 指定日期
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from analysis import ai_commentary, compute_checklist, merge
from cards import render_all
from demo import demo_data
from fetch import fetch_all, last_trading_day

HERE = Path(__file__).parent


def send_mail(paths, data):
    user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ.get("MAIL_TO", user)
    msg = EmailMessage()
    msg["Subject"] = f"股票每日晨報字卡 {data['date']}｜{(data.get('commentary') or {}).get('headline', '')}"
    msg["From"], msg["To"] = user, to
    cids = [f"card{i}" for i in range(len(paths))]
    html = "".join(f'<p><img src="cid:{c}" style="width:100%;max-width:540px"></p>' for c in cids)
    if data.get("errors"):
        html += "<p style='color:#999;font-size:12px'>未完成：" + "；".join(data["errors"]) + "</p>"
    msg.set_content("請用支援 HTML 的信箱開啟。")
    msg.add_alternative(f"<html><body>{html}</body></html>", subtype="html")
    body = msg.get_payload()[1]
    for c, p in zip(cids, paths):
        body.add_related(Path(p).read_bytes(), "image", "png", cid=f"<{c}>")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--date")
    ap.add_argument("--out", default=str(HERE / "out"))
    a = ap.parse_args()

    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    wl_file = HERE / "watchlist.json"  # 由「觀察名單管理」頁面複製過來；有這個檔就以它為準
    if wl_file.exists():
        cfg["watchlist"] = json.loads(wl_file.read_text(encoding="utf-8"))
    if a.demo:
        data = demo_data(cfg)
    else:
        day = dt.date.fromisoformat(a.date) if a.date else last_trading_day()
        data = fetch_all(cfg, day)
        data = merge(data, ai_commentary(data, cfg))
    data["checklist"] = compute_checklist(data, cfg["checklist_thresholds"])

    outdir = Path(a.out) / data["date"]
    paths = render_all(data, outdir)
    (outdir / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str),
                                      encoding="utf-8")
    print("產出：", *paths, sep="\n  ")
    if data.get("errors"):
        print("未完成：", *data["errors"], sep="\n  ")
    if a.send:
        if not os.environ.get("GMAIL_USER") or not os.environ.get("GMAIL_APP_PASSWORD"):
            print("尚未設定 Gmail，略過寄信（字卡可在 Actions 的 cards 附件下載）")
        else:
            send_mail(paths, data)
            print("已寄出")


if __name__ == "__main__":
    main()
