# 匯率查詢

每 30 分鐘自動抓取 [findrate.tw 日幣匯率](https://www.findrate.tw/JPY/)，展示各銀行牌告匯率，並在「全銀行最低現鈔賣出價」跌到你設定的目標值時，用 LINE 推播通知。

## 架構

- `.github/workflows/fetch-rate.yml`：GitHub Actions 排程（每 30 分鐘），執行抓取 + 比對 + LINE 推播，並把結果寫回 `data/rate.json` / `data/config.json`
- `scripts/fetch_rate.py`：爬蟲 + 通知邏輯
- `data/rate.json`：最新匯率資料（自動產生，不用手動編輯）
- `data/config.json`：目標值與通知狀態
- `index.html` / `app.js` / `style.css`：展示頁面，含目標值輸入框（透過 GitHub API 直接把新目標值寫回 `data/config.json`）

## 建置步驟

1. 在 GitHub 建立一個新 repo（建議設為 **Private**，因為瀏覽器會存取你的 GitHub Token），把這個資料夾內容 push 上去
2. **設定 LINE 推播密鑰**：進 repo Settings → Secrets and variables → Actions，新增：
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_USER_ID`
3. **開啟 GitHub Pages**：Settings → Pages → Source 選 `main` branch / root，儲存後會拿到一個網址
4. 編輯 `app.js` 最上方三個常數，改成你自己的：
   ```js
   const GITHUB_OWNER = "你的GitHub帳號";
   const GITHUB_REPO = "repo名稱";
   const GITHUB_BRANCH = "main";
   ```
5. 打開部署好的網頁，在「目標值設定」輸入目標匯率並按「儲存目標值」，第一次會跳出視窗要求輸入 **GitHub Personal Access Token**：
   - 到 GitHub → Settings → Developer settings → Fine-grained personal access tokens 建立
   - Repository access 選「Only select repositories」→ 選這個 repo
   - Permissions 只給 **Contents: Read and write**
   - Token 會存在瀏覽器 localStorage，之後不用再輸入（可按「清除已存Token」移除）

## 通知邏輯

- 每次排程抓完資料後，比較「全銀行最低現鈔賣出價」與 `targetRate`
- 跌到目標值（含）以下且尚未通知過 → 發送 LINE 推播，並標記 `notified: true`
- 之後匯率回升超過目標值 → 自動解除標記，下次再跌破會再通知一次

## 已知限制

- 網頁存 Token 的方式僅適合單人使用的私有 repo，不要用在公開專案或多人共用情境
- 若網頁儲存目標值與排程同時寫入 `data/config.json`，極少數情況下可能發生寫入衝突（GitHub API 回傳 409），重新整理頁面再存一次即可
- GitHub Actions 排程時間非絕對精準，尖峰時段可能延遲數分鐘到數十分鐘
