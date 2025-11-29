chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "sendText",
    title: "Send selected text",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId === "sendText") {
    const selectedText = info.selectionText;

    fetch("http://localhost:5000/api/receive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: selectedText })
    })
    .then(response => response.json())
    .then(data => console.log("Server response:", data))
    .catch(err => console.error(err));
  }
});

chrome.contextMenus.create({
  id: "trollText",
  title: "Troll me 😂",
  contexts: ["selection"]
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId === "trollText") {
    const selectedText = info.selectionText;

    fetch("http://localhost:5000/api/receiveToJudge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: selectedText })
    })
    .then(res => res.json())
    .then(data => console.log("Troll result:", data.judgment))
    .catch(err => console.error(err));
  }
});