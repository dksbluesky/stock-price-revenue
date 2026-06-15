const API_BASE = "https://api.finmindtrade.com/api/v4/data";
const QUICK_TICKERS = [
  { id: "2330", name: "台積電" },
  { id: "2317", name: "鴻海" },
  { id: "2454", name: "聯發科" },
  { id: "2308", name: "台達電" },
  { id: "1301", name: "台塑" },
  { id: "2412", name: "中華電" },
];

let charts = {};

// ── Helpers ──────────────────────────────────────────────────────────────
function fmtMoney(n) {
  if (n == null || isNaN(n)) return "N/A";
  return `${(n / 1e8).toFixed(1)} 億`;
}
function fmtPct(n, digits = 1) {
  if (n == null || isNaN(n)) return "N/A";
  return `${n.toFixed(digits)}%`;
}
function fmtNum(n, digits = 2) {
  if (n == null || isNaN(n)) return "N/A";
  return n.toFixed(digits);
}
function setStatus(msg, cls) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = cls || "";
}
function normalizeTicker(raw) {
  let t = raw.trim().toUpperCase();
  t = t.replace(/\.TW$|\.TWO$/, "");
  return t;
}

async function fetchFinMind(dataset, dataId, startDate) {
  const url = `${API_BASE}?dataset=${dataset}&data_id=${encodeURIComponent(dataId)}&start_date=${startDate}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (json.status !== 200) throw new Error(json.msg || "FinMind error");
  return json.data || [];
}

function shiftDate(yearsAgo) {
  const d = new Date();
  d.setFullYear(d.getFullYear() - yearsAgo);
  return d.toISOString().slice(0, 10);
}

// ── Quarter pivot ────────────────────────────────────────────────────────
function pivotQuarters(rows) {
  const byDate = {};
  for (const r of rows) {
    if (!byDate[r.date]) byDate[r.date] = { date: r.date };
    byDate[r.date][r.type] = r.value;
  }
  return Object.values(byDate).sort((a, b) => (a.date < b.date ? -1 : 1));
}

function quarterLabel(dateStr) {
  const [y, m] = dateStr.split("-");
  const q = Math.ceil(parseInt(m, 10) / 3);
  return `${y}Q${q}`;
}

// ── Charts ───────────────────────────────────────────────────────────────
function destroyChart(key) {
  if (charts[key]) {
    charts[key].destroy();
    delete charts[key];
  }
}

function renderWaterfall(ttm) {
  const ctx = document.getElementById("waterfallCanvas").getContext("2d");
  destroyChart("waterfall");

  const rev = ttm.rev;
  const cost = ttm.cost;
  const gross = ttm.gross;
  const opExp = gross - ttm.opInc;
  const opInc = ttm.opInc;
  const taxInt = opInc - ttm.net;
  const net = ttm.net;

  const labels = ["總營收", "營業成本", "毛利", "營業費用", "營業利益", "稅/其他", "淨利"];
  // Floating-bar technique: [start, end] pairs for relative bars, [0, value] for totals
  let running = rev;
  const dataPairs = [
    [0, rev],
    [running - cost, running],
    [0, gross],
    [(running = gross) - opExp, running],
    [0, opInc],
    [(running = opInc) - taxInt, running],
    [0, net],
  ];
  const colors = ["#3498DB", "#E74C3C", "#3498DB", "#E74C3C", "#3498DB", "#E74C3C", "#3498DB"];
  const labelsText = [
    fmtMoney(rev),
    `-${fmtMoney(cost)}`,
    `${fmtMoney(gross)} (${fmtPct((gross / rev) * 100)})`,
    `-${fmtMoney(opExp)}`,
    fmtMoney(opInc),
    `-${fmtMoney(taxInt)}`,
    `${fmtMoney(net)} (${fmtPct((net / rev) * 100)})`,
  ];

  charts.waterfall = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: dataPairs,
        backgroundColor: colors,
        borderRadius: 4,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        title: { display: true, text: `${ttm.label} 獲利結構 (TTM 近四季)`, font: { size: 14 } },
        tooltip: {
          callbacks: {
            label: (item) => labelsText[item.dataIndex],
          },
        },
        datalabels: undefined,
      },
      scales: {
        y: { ticks: { callback: (v) => fmtMoney(v) } },
      },
    },
    plugins: [{
      id: "waterfallLabels",
      afterDatasetsDraw(chart) {
        const { ctx } = chart;
        const meta = chart.getDatasetMeta(0);
        ctx.save();
        ctx.font = "12px sans-serif";
        ctx.fillStyle = "#333";
        ctx.textAlign = "center";
        meta.data.forEach((bar, i) => {
          const pair = dataPairs[i];
          const topVal = Math.max(pair[0], pair[1]);
          const y = chart.scales.y.getPixelForValue(topVal) - 8;
          labelsText[i].split("\n").forEach((line, li) => {
            ctx.fillText(line, bar.x, y - li * 12);
          });
        });
        ctx.restore();
      },
    }],
  });
}

function renderQuarterlyTrend(quarters) {
  const ctx = document.getElementById("trendCanvas").getContext("2d");
  destroyChart("trend");
  const labels = quarters.map((q) => quarterLabel(q.date));
  charts.trend = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "營收", data: quarters.map((q) => (q.Revenue || 0) / 1e8), backgroundColor: "#2196F3" },
        { label: "淨利", data: quarters.map((q) => (q.IncomeAfterTaxes || 0) / 1e8), backgroundColor: "#4CAF50" },
      ],
    },
    options: {
      plugins: { title: { display: true, text: "近八季 營收 / 淨利 (億元)", font: { size: 14 } } },
      scales: { y: { title: { display: true, text: "億元" } } },
    },
  });
}

function renderMarginTrend(quarters) {
  const ctx = document.getElementById("marginCanvas").getContext("2d");
  destroyChart("margin");
  const labels = quarters.map((q) => quarterLabel(q.date));
  charts.margin = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "毛利率",
          data: quarters.map((q) => (q.Revenue ? (q.GrossProfit / q.Revenue) * 100 : null)),
          borderColor: "#2196F3", backgroundColor: "#2196F3", tension: 0.2,
        },
        {
          label: "營益率",
          data: quarters.map((q) => (q.Revenue ? (q.OperatingIncome / q.Revenue) * 100 : null)),
          borderColor: "#FF9800", backgroundColor: "#FF9800", tension: 0.2,
        },
        {
          label: "淨利率",
          data: quarters.map((q) => (q.Revenue ? (q.IncomeAfterTaxes / q.Revenue) * 100 : null)),
          borderColor: "#4CAF50", backgroundColor: "#4CAF50", tension: 0.2,
        },
      ],
    },
    options: {
      plugins: { title: { display: true, text: "近八季 利潤率趨勢 (%)", font: { size: 14 } } },
      scales: { y: { title: { display: true, text: "%" } } },
    },
  });
}

function renderEpsTrend(quarters) {
  const ctx = document.getElementById("epsCanvas").getContext("2d");
  destroyChart("eps");
  const labels = quarters.map((q) => quarterLabel(q.date));
  const ttmEps = quarters.map((_, i) => {
    if (i < 3) return null;
    let sum = 0;
    for (let j = i - 3; j <= i; j++) sum += quarters[j].EPS || 0;
    return sum;
  });
  charts.eps = new Chart(ctx, {
    data: {
      labels,
      datasets: [
        { type: "bar", label: "單季 EPS", data: quarters.map((q) => q.EPS ?? null), backgroundColor: "#9C27B0" },
        { type: "line", label: "TTM EPS", data: ttmEps, borderColor: "#E91E63", backgroundColor: "#E91E63", tension: 0.2, yAxisID: "y" },
      ],
    },
    options: {
      plugins: { title: { display: true, text: "每股盈餘 (EPS) 趨勢", font: { size: 14 } } },
      scales: { y: { title: { display: true, text: "元" } } },
    },
  });
}

function sma(values, period) {
  return values.map((_, i) => {
    if (i < period - 1) return null;
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += values[j];
    return sum / period;
  });
}

function renderPriceChart(prices) {
  const ctx = document.getElementById("priceCanvas").getContext("2d");
  destroyChart("price");
  const labels = prices.map((p) => p.date);
  const closes = prices.map((p) => p.close);
  charts.price = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "收盤價", data: closes, borderColor: "#1a3c5e", backgroundColor: "#1a3c5e", pointRadius: 0, borderWidth: 1.5 },
        { label: "20日均線", data: sma(closes, 20), borderColor: "#FF9800", pointRadius: 0, borderWidth: 1, tension: 0.1 },
        { label: "60日均線", data: sma(closes, 60), borderColor: "#2196F3", pointRadius: 0, borderWidth: 1, tension: 0.1 },
      ],
    },
    options: {
      plugins: { title: { display: true, text: "近一年股價走勢", font: { size: 14 } } },
      scales: { x: { ticks: { maxTicksLimit: 8 } } },
    },
  });
}

// ── Main ─────────────────────────────────────────────────────────────────
async function analyze(rawTicker) {
  const ticker = normalizeTicker(rawTicker || document.getElementById("tickerInput").value);
  if (!/^\d{4,6}$/.test(ticker)) {
    setStatus("⚠️ 請輸入有效的台股代號 (例如 2330)", "warn");
    return;
  }
  document.getElementById("tickerInput").value = ticker;
  localStorage.setItem("lastTicker", ticker);

  const runBtn = document.getElementById("runBtn");
  runBtn.disabled = true;
  setStatus("⏳ 讀取資料中...", "");
  document.getElementById("results").classList.add("hidden");

  try {
    const [info, finRaw, perRows, priceRows] = await Promise.all([
      fetchFinMind("TaiwanStockInfo", ticker, "2000-01-01"),
      fetchFinMind("TaiwanStockFinancialStatements", ticker, shiftDate(2.5)),
      fetchFinMind("TaiwanStockPER", ticker, shiftDate(0.05)),
      fetchFinMind("TaiwanStockPrice", ticker, shiftDate(1.3)),
    ]);

    if (!finRaw.length) throw new Error("找不到財報資料，請確認股票代號是否正確。");

    const quarters = pivotQuarters(finRaw).slice(-8);
    const latestQ = quarters[quarters.length - 1];
    const last4 = quarters.slice(-4);

    const ttm = {
      label: info[0]?.stock_name || ticker,
      rev: last4.reduce((s, q) => s + (q.Revenue || 0), 0),
      cost: last4.reduce((s, q) => s + (q.CostOfGoodsSold || 0), 0),
      gross: last4.reduce((s, q) => s + (q.GrossProfit || 0), 0),
      opInc: last4.reduce((s, q) => s + (q.OperatingIncome || 0), 0),
      net: last4.reduce((s, q) => s + (q.IncomeAfterTaxes || 0), 0),
      eps: last4.reduce((s, q) => s + (q.EPS || 0), 0),
    };

    const per = perRows.length ? perRows[perRows.length - 1] : null;
    const price = priceRows.length ? priceRows[priceRows.length - 1] : null;

    // Header
    document.getElementById("stockName").textContent = `${ttm.label} (${ticker}.TW)`;
    document.getElementById("stockMeta").textContent =
      `產業: ${info[0]?.industry_category || "N/A"} ｜ 最新財報季度: ${quarterLabel(latestQ.date)} (${latestQ.date})`;

    // KPI row
    const grossMargin = (ttm.gross / ttm.rev) * 100;
    const netMargin = (ttm.net / ttm.rev) * 100;
    document.getElementById("kpiPrice").textContent = price ? `${fmtNum(price.close)} TWD` : "N/A";
    document.getElementById("kpiPriceSub").textContent = price ? `收盤日: ${price.date}` : "";
    document.getElementById("kpiRev").textContent = fmtMoney(ttm.rev);
    document.getElementById("kpiGrossMargin").textContent = fmtPct(grossMargin);
    document.getElementById("kpiNetMargin").textContent = fmtPct(netMargin);
    document.getElementById("kpiEps").textContent = ttm.eps ? `${fmtNum(ttm.eps)} TWD` : "N/A";
    document.getElementById("kpiPe").textContent = per ? `${fmtNum(per.PER, 1)}x` : "N/A";
    document.getElementById("kpiDiv").textContent = per ? fmtPct(per.dividend_yield) : "N/A";
    document.getElementById("kpiPb").textContent = per ? `${fmtNum(per.PBR, 1)}x` : "N/A";

    // Run-rate forward P/E: annualize the latest quarter's EPS (not analyst consensus)
    const latestEps = latestQ.EPS;
    if (price && latestEps) {
      const fwdEps = latestEps * 4;
      const fwdPe = price.close / fwdEps;
      document.getElementById("kpiFwdPe").textContent = `${fmtNum(fwdPe, 1)}x`;
      document.getElementById("kpiFwdPeSub").textContent = `Fwd EPS ≈ ${fmtNum(fwdEps)} (${quarterLabel(latestQ.date)}×4)`;
    } else {
      document.getElementById("kpiFwdPe").textContent = "N/A";
      document.getElementById("kpiFwdPeSub").textContent = "";
    }

    // Charts
    renderWaterfall(ttm);
    renderQuarterlyTrend(quarters);
    renderMarginTrend(quarters);
    renderEpsTrend(quarters);
    if (priceRows.length) renderPriceChart(priceRows);

    document.getElementById("results").classList.remove("hidden");
    setStatus(`✅ ${ttm.label} (${ticker}) 資料更新完成`, "success");
  } catch (e) {
    setStatus(`❌ ${e.message}`, "error");
  } finally {
    runBtn.disabled = false;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("runBtn").addEventListener("click", () => analyze());
  document.getElementById("tickerInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") analyze();
  });

  const quickRow = document.getElementById("quickRow");
  for (const q of QUICK_TICKERS) {
    const btn = document.createElement("button");
    btn.className = "quick-btn";
    btn.textContent = `${q.id} ${q.name}`;
    btn.addEventListener("click", () => analyze(q.id));
    quickRow.appendChild(btn);
  }

  const last = localStorage.getItem("lastTicker") || "2330";
  document.getElementById("tickerInput").value = last;
  analyze(last);
});
