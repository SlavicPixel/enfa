document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("refreshBtn");
  if (!btn) return;

  btn.addEventListener("click", () => {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Refreshing...';

    fetch(btn.dataset.url, {
      method: "POST",
      headers: { "X-CSRFToken": btn.dataset.csrf },
    })
      .then(r => r.json())
      .then(data => {
        if (data.status === "ok") {
          location.reload();
        } else {
          alert("Error: " + data.message);
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i>Refresh data';
        }
      })
      .catch(() => {
        alert("Request failed.");
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i>Refresh data';
      });
  });
});