const form = document.getElementById("eventForm");
const statusEl = document.getElementById("status");
const authBtn = document.getElementById("authBtn");

// Handle authentication
authBtn.addEventListener("click", () => {
  // Redirect to your backend's authentication endpoint
  window.open("https://calendarapp-9jvu.onrender.com/api/authenticate", "_blank");
});

// Optional: remember last-used values
function saveDraft(data) {
  chrome.storage.sync.set({ draft: data });
}
function loadDraft() {
  chrome.storage.sync.get("draft", ({ draft }) => {
    if (!draft) return;
    for (const [k, v] of Object.entries(draft)) {
      const el = form.elements[k];
      if (el) el.value = v;
    }
  });
}
loadDraft();

form.addEventListener("input", () => {
  const data = Object.fromEntries(new FormData(form).entries());
  saveDraft(data);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusEl.textContent = "Creating…";

  const data = Object.fromEntries(new FormData(form).entries());
  // Build ISO datetimes in your server’s expected timezone (adjust if needed)
  const { title, date, start, end, description } = data;
  const startISO = new Date(`${date}T${start}:00`).toISOString();
  const endISO   = new Date(`${date}T${end}:00`).toISOString();

  try {
    const res = await fetch("https://calendarapp-9jvu.onrender.com/api/create_event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Send only what your Flask route expects
      body: JSON.stringify({
        title,
        description,
        start: startISO,
        end: endISO
      }),
      credentials: "include" // if your backend uses cookies/session
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json(); // e.g., {id: "...", htmlLink: "..."}
    statusEl.innerHTML = `✔ Event created ${json.htmlLink ? `— <a href="${json.htmlLink}" target="_blank">open</a>` : ""}`;
    // Clear draft if you like
    chrome.storage.sync.remove("draft");
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Failed to create event. Check login/server.";
  }
});

