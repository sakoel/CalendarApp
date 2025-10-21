// popup.js (MVP)
const tokenEl = document.getElementById("token");
const saveBtn = document.getElementById("saveToken");

saveBtn.onclick = async () => {
  const t = tokenEl.value.trim();
  if (!t) return;
  await chrome.storage.sync.set({ apiToken: t });
  alert("Saved.");
};

async function getToken() {
  return new Promise(r => chrome.storage.sync.get("apiToken", x => r(x.apiToken)));
}

async function createEvent(payload) {
  const token = await getToken();
  const res = await fetch("https://calendarapp-9jvu.onrender.com/api/create_event", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
  return res.json();
}

document.getElementById("signIn").onclick = () => {
  window.open("https://calendarapp-9jvu.onrender.com/api/authenticate", "_blank");
};
