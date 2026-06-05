document.addEventListener("DOMContentLoaded", () => {
  const importance = JSON.parse(
    document.getElementById("importance-data").textContent
  );

  const labels = importance.map(f => f.feature);
  const values = importance.map(f => f.coefficient);
  const colors = values.map(v =>
    v > 0 ? "rgba(220,53,69,0.7)" : "rgba(13,110,253,0.7)"
  );

  new Chart(document.getElementById("importanceChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label:           "Coefficient",
        data:            values,
        backgroundColor: colors,
        borderWidth:     0,
      }]
    },
    options: {
      indexAxis:  "y",
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` Coefficient: ${ctx.raw.toFixed(4)}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(0,0,0,0.05)" },
          ticks: { maxTicksLimit: 6 }
        },
        y: { ticks: { font: { family: "monospace", size: 11 } } }
      }
    }
  });
});