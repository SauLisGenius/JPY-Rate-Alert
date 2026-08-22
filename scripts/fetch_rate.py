import json
import os
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup

FINDRATE_URL = "https://www.findrate.tw/JPY/"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RATE_FILE = os.path.join(DATA_DIR, "rate.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
TW_TZ = timezone(timedelta(hours=8))


def fetchHtml():
	resp = requests.get(
		FINDRATE_URL,
		headers={"User-Agent": "Mozilla/5.0 (compatible; RateBot/1.0)"},
		timeout=15,
	)
	resp.raise_for_status()
	resp.encoding = resp.apparent_encoding
	return resp.text


def toFloat(text):
	text = text.strip()
	if not text or text == "--":
		return None
	try:
		return float(text)
	except ValueError:
		return None


def parseBanks(html):
	soup = BeautifulSoup(html, "html.parser")
	targetTable = None
	for table in soup.find_all("table"):
		headerRow = table.find("tr")
		if headerRow and "銀行名稱" in headerRow.get_text():
			targetTable = table
			break
	if targetTable is None:
		raise RuntimeError("找不到匯率表格，網站版面可能改版了")

	banks = []
	for row in targetTable.find_all("tr")[1:]:
		cols = row.find_all("td")
		if len(cols) < 7:
			continue
		name = cols[0].get_text(strip=True)
		if not name:
			continue
		banks.append({
			"name": name,
			"cashBuy": toFloat(cols[1].get_text()),
			"cashSell": toFloat(cols[2].get_text()),
			"spotBuy": toFloat(cols[3].get_text()),
			"spotSell": toFloat(cols[4].get_text()),
			"updateTime": cols[5].get_text(strip=True),
			"feeNote": cols[6].get_text(strip=True),
		})
	return banks


def summarize(banks):
	sellCandidates = [b for b in banks if b["cashSell"] is not None]
	buyCandidates = [b for b in banks if b["cashBuy"] is not None]

	cheapestBuyJpy = min(sellCandidates, key=lambda b: b["cashSell"]) if sellCandidates else None
	bestSellJpy = max(buyCandidates, key=lambda b: b["cashBuy"]) if buyCandidates else None

	return {
		"cheapestBuyJPY": {"bank": cheapestBuyJpy["name"], "rate": cheapestBuyJpy["cashSell"]} if cheapestBuyJpy else None,
		"bestSellJPY": {"bank": bestSellJpy["name"], "rate": bestSellJpy["cashBuy"]} if bestSellJpy else None,
	}


def loadJson(path, default):
	if not os.path.exists(path):
		return default
	with open(path, "r", encoding="utf-8") as f:
		return json.load(f)


def saveJson(path, data):
	with open(path, "w", encoding="utf-8") as f:
		json.dump(data, f, ensure_ascii=False, indent=2)
		f.write("\n")


def sendLinePush(message):
	token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
	userId = os.environ.get("LINE_USER_ID")
	if not token or not userId:
		print("::warning::尚未設定 LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID，略過推播")
		return
	resp = requests.post(
		"https://api.line.me/v2/bot/message/push",
		headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
		json={"to": userId, "messages": [{"type": "text", "text": message}]},
		timeout=10,
	)
	if resp.status_code != 200:
		print(f"::error::LINE 推播失敗 {resp.status_code} {resp.text}")
	else:
		print("LINE 推播成功")


def main():
	html = fetchHtml()
	banks = parseBanks(html)
	summary = summarize(banks)
	now = datetime.now(TW_TZ).isoformat()

	rateData = {
		"fetchedAt": now,
		"source": FINDRATE_URL,
		"banks": banks,
		"summary": summary,
	}
	saveJson(RATE_FILE, rateData)

	config = loadJson(CONFIG_FILE, {"targetRate": None, "notified": False})
	target = config.get("targetRate")
	current = summary["cheapestBuyJPY"]["rate"] if summary["cheapestBuyJPY"] else None

	if target is not None and current is not None:
		alreadyNotified = config.get("notified", False)
		if current <= target and not alreadyNotified:
			bankName = summary["cheapestBuyJPY"]["bank"]
			message = (
				"🔔 日幣匯率到價通知\n"
				f"目前最低現鈔賣出價：{bankName} {current}\n"
				f"已達到目標 {target}\n"
				f"時間：{now[:16].replace('T', ' ')}"
			)
			sendLinePush(message)
			config["notified"] = True
			config["notifiedAt"] = now
			saveJson(CONFIG_FILE, config)
		elif current > target and alreadyNotified:
			# 匯率回升超過目標，解除警戒，之後再次跌破可再次通知
			config["notified"] = False
			config["notifiedAt"] = None
			saveJson(CONFIG_FILE, config)

	print(f"抓取完成：{len(banks)} 家銀行，目前最低現鈔賣出價 {current}，目標 {target}")


if __name__ == "__main__":
	main()
