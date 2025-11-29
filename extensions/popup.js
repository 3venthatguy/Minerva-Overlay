// popup.js
document.getElementById("send").addEventListener("click", () => {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    chrome.scripting.executeScript({
      target: {tabId: tabs[0].id},
      func: () => window.getSelection().toString()
    }, (results) => {
      const text = results[0].result;
      fetch("http://localhost:5000/api/receive", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ text })
      });
    });
  });
});