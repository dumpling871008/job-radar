# job-radar

使用 Playwright 抓取 104 人力銀行公開搜尋頁，整理成 CSV 或 JSON。預設關鍵字為
`python工程師`，預設只抓一頁，避免對網站造成不必要的負載。

## 安裝

```powershell
uv sync
uv run playwright install chromium
```

## 使用

```powershell
# 預設輸出 data/jobs_104.csv
uv run python main.py "python工程師"

# 抓 3 頁、最多保留 50 筆
uv run python main.py "資料工程師" --pages 3 --max-jobs 50

# 輸出 JSON
uv run python main.py "後端工程師" --output data/backend_jobs.json

# 除錯時顯示瀏覽器
uv run python main.py "AI 工程師" --headed
```

CSV 使用 UTF-8 with BOM，能直接用 Excel 開啟。欄位包括職缺 ID、職稱、公司、
產業、地區、經歷、學歷、薪資、刊登日期、工作摘要、標籤、應徵人數與網址。

## 測試

```powershell
uv run python -m unittest -v
```

請遵守 104 的使用條款與 robots 規則，保留合理的翻頁間隔；程式不會繞過 CAPTCHA
或登入限制，也不應用於蒐集非公開或個人資料。
