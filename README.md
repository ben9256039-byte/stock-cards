# 股票晨報字卡

每天早上自動抓前一交易日資料，產出 8 張手機直式字卡（1080×1350），寄到 Gmail。

| # | 字卡 | 資料來源 | 誰產生 |
|---|------|---------|-------|
| 1 | 總覽（指數、成交額、三大法人合計、燈號、今日重點） | 證交所 | 程式＋AI一句話 |
| 2 | 成交量月線＋中位數＋指數對照 | 證交所 FMTQIK | 程式＋AI短評 |
| 3 | 三大法人買賣超前三名＋原因 | 證交所 T86/BFI82U | 程式＋AI原因 |
| 4 | 融資融券、維持率儀表、融資減少前五 | 證交所 MI_MARGN | 程式（維持率由AI查新聞） |
| 5 | 觀察名單熱度格＋20日走勢 | Yahoo Finance | 程式 |
| 6 | 衰退徵兆檢核表（紅黃綠燈） | 前面各項 | 程式（固定規則） |
| 7 | 國際市場：費半、那指、標普、VIX、美債、匯率 | Yahoo Finance | 程式 |
| 8 | 新聞重點（利多／利空／中性） | 網路新聞 | AI |

## 試跑
    pip install -r requirements.txt
    python main.py --demo     # 示範資料，不需連網
    python main.py            # 抓真資料
    python main.py --send     # 抓資料並寄信

## 放到 GitHub Actions 每天自動跑
1. 在 GitHub 建一個 **私人** repo，把這個資料夾全部上傳。
2. repo → Settings → Secrets and variables → Actions，新增：
   - `GMAIL_USER`：你的 Gmail
   - `GMAIL_APP_PASSWORD`：Gmail「應用程式密碼」（Google 帳戶 → 安全性 → 兩步驟驗證 → 應用程式密碼）
   - `MAIL_TO`：收件人（可省略，預設寄給自己）
   - `ANTHROPIC_API_KEY`：可省略；沒填就不產生 AI 短評、原因與新聞卡，其餘照常
3. Actions 分頁 → 「股票晨報字卡」→ Run workflow 先手動跑一次確認。

## 調整
- 觀察名單：在「觀察名單管理」頁面增刪，按「複製 watchlist.json」貼到 repo 的 `watchlist.json`
- 門檻值：改 `config.json`
- 檢核規則：`analysis.py` 的 `compute_checklist`
- 字卡版面：`cards.py`
