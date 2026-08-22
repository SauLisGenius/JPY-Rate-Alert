const GITHUB_OWNER = "your-github-username";
const GITHUB_REPO = "your-repo-name";
const GITHUB_BRANCH = "main";

const RATE_DATA_URL = "./data/rate.json";
const CONFIG_DATA_URL = "./data/config.json";
const CONFIG_API_PATH = "data/config.json";

const targetInput = document.getElementById("targetInput");
const targetStatus = document.getElementById("targetStatus");
const saveTargetBtn = document.getElementById("saveTargetBtn");
const clearTokenBtn = document.getElementById("clearTokenBtn");

function formatRate(value) {
	return value === null || value === undefined ? "--" : value;
}

async function loadRateData() {
	const res = await fetch(`${RATE_DATA_URL}?t=${Date.now()}`);
	const data = await res.json();
	renderSummary(data);
	renderTable(data.banks || []);
}

function renderSummary(data) {
	const summary = data.summary || {};
	document.getElementById("fetchedAt").textContent = data.fetchedAt || "--";

	if (summary.cheapestBuyJPY) {
		document.getElementById("cheapestBank").textContent = summary.cheapestBuyJPY.bank;
		document.getElementById("cheapestRate").textContent = summary.cheapestBuyJPY.rate;
	}
	if (summary.bestSellJPY) {
		document.getElementById("bestSellBank").textContent = summary.bestSellJPY.bank;
		document.getElementById("bestSellRate").textContent = summary.bestSellJPY.rate;
	}
}

function renderTable(banks) {
	const tbody = document.getElementById("rateTableBody");
	if (!banks.length) {
		tbody.innerHTML = "<tr><td colspan=\"7\">尚無資料，請等待排程第一次抓取</td></tr>";
		return;
	}
	tbody.innerHTML = banks.map(b => `
		<tr>
			<td class="bank">${b.name}</td>
			<td>${formatRate(b.cashBuy)}</td>
			<td>${formatRate(b.cashSell)}</td>
			<td>${formatRate(b.spotBuy)}</td>
			<td>${formatRate(b.spotSell)}</td>
			<td>${b.updateTime || "--"}</td>
			<td>${b.feeNote || ""}</td>
		</tr>
	`).join("");
}

async function loadConfig() {
	const res = await fetch(`${CONFIG_DATA_URL}?t=${Date.now()}`);
	const config = await res.json();
	if (config.targetRate !== null && config.targetRate !== undefined) {
		targetInput.value = config.targetRate;
	}
	const notifiedText = config.notified ? "（已通知，等匯率回升後才會再次通知）" : "";
	targetStatus.textContent = `目前設定：${config.targetRate ?? "尚未設定"} ${notifiedText}`;
}

function getToken() {
	let token = localStorage.getItem("ghToken");
	if (!token) {
		token = window.prompt("請輸入 GitHub Personal Access Token（僅需此 repo 的 Contents 讀寫權限）");
		if (token) {
			localStorage.setItem("ghToken", token);
		}
	}
	return token;
}

function toBase64Utf8(text) {
	return btoa(unescape(encodeURIComponent(text)));
}

async function saveTarget() {
	const value = parseFloat(targetInput.value);
	if (Number.isNaN(value)) {
		alert("請輸入有效的數字");
		return;
	}
	const token = getToken();
	if (!token) return;

	saveTargetBtn.disabled = true;
	saveTargetBtn.textContent = "儲存中...";

	try {
		const apiUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${CONFIG_API_PATH}`;
		const getRes = await fetch(`${apiUrl}?ref=${GITHUB_BRANCH}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		if (!getRes.ok) {
			throw new Error(`讀取設定檔失敗：${getRes.status}`);
		}
		const getData = await getRes.json();

		const newConfig = {
			targetRate: value,
			updatedAt: new Date().toISOString(),
			notified: false,
			notifiedAt: null,
		};

		const putRes = await fetch(apiUrl, {
			method: "PUT",
			headers: {
				Authorization: `Bearer ${token}`,
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				message: `chore: update target rate to ${value}`,
				content: toBase64Utf8(JSON.stringify(newConfig, null, 2) + "\n"),
				sha: getData.sha,
				branch: GITHUB_BRANCH,
			}),
		});

		if (!putRes.ok) {
			const errBody = await putRes.text();
			throw new Error(`寫入設定檔失敗：${putRes.status} ${errBody}`);
		}

		targetStatus.textContent = `已儲存目標值：${value}`;
	} catch (err) {
		alert(err.message);
	} finally {
		saveTargetBtn.disabled = false;
		saveTargetBtn.textContent = "儲存目標值";
	}
}

saveTargetBtn.addEventListener("click", saveTarget);
clearTokenBtn.addEventListener("click", () => {
	localStorage.removeItem("ghToken");
	alert("已清除本機儲存的 Token");
});

loadRateData().catch(err => console.error(err));
loadConfig().catch(err => console.error(err));
