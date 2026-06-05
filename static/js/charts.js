// ── Helpers ───────────────────────────────────────────────────────────────

function filterDays(data, days) {
  if (days >= data.length) return data;
  return data.slice(-days);
}

function setActiveBtn(group, days) {
  group.querySelectorAll("button").forEach(b => {
    b.classList.toggle("active", parseInt(b.dataset.days) === days);
  });
}

// ── Price chart ───────────────────────────────────────────────────────────

function initPriceChart(allPrices) {
  const ctx        = document.getElementById("priceChart");
  const rangeGroup = document.getElementById("priceRange");
  if (!ctx || !rangeGroup) return;

  const initialDays = 180;

  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels:   filterDays(allPrices, initialDays).map(p => p.date),
      datasets: [{
        label:                    "Close ($)",
        data:                     filterDays(allPrices, initialDays).map(p => p.close),
        borderColor:              "#212529",
        backgroundColor:          "rgba(33,37,41,0.05)",
        borderWidth:              1.5,
        pointRadius:              0,
        pointHoverRadius:         5,
        pointHoverBackgroundColor:"#212529",
        fill:                     true,
        tension:                  0.3,
      }]
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8 } },
        y: { ticks: { callback: v => "$" + v.toFixed(0) } },
      }
    }
  });

  rangeGroup.addEventListener("click", e => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const days   = parseInt(btn.dataset.days);
    const sliced = filterDays(allPrices, days);
    chart.data.labels           = sliced.map(p => p.date);
    chart.data.datasets[0].data = sliced.map(p => p.close);
    chart.update();
    setActiveBtn(rangeGroup, days);
  });
}

// ── Sentiment chart ───────────────────────────────────────────────────────

function initSentimentChart(allSentiment) {
  const ctx        = document.getElementById("sentimentChart");
  const rangeGroup = document.getElementById("sentimentRange");
  if (!ctx || !rangeGroup) return;

  const initialDays = 180;

  function buildColors(data) {
    return data.map(s =>
      (s.net_sentiment || 0) > 0
        ? "rgba(25,135,84,0.6)"
        : "rgba(220,53,69,0.6)"
    );
  }

  const initial = filterDays(allSentiment, initialDays);

  const chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels:   initial.map(s => s.date),
      datasets: [{
        label:           "Net Sentiment",
        data:            initial.map(s => s.net_sentiment || 0),
        backgroundColor: buildColors(initial),
        borderWidth:     0,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8 } },
        y: { ticks: { maxTicksLimit: 5 } },
      }
    }
  });

  rangeGroup.addEventListener("click", e => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const days   = parseInt(btn.dataset.days);
    const sliced = filterDays(allSentiment, days);
    chart.data.labels                      = sliced.map(s => s.date);
    chart.data.datasets[0].data            = sliced.map(s => s.net_sentiment || 0);
    chart.data.datasets[0].backgroundColor = buildColors(sliced);
    chart.update();
    setActiveBtn(rangeGroup, days);
  });
}