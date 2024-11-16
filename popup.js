// popup.js

// Function to create a card for a tab's data
function createTabCard(tabData) {
    // Convert summary into an unordered list if applicable
    let summaryHtml = tabData.summary
      .split('\n') // Split summary by newlines
      .filter(line => line.startsWith('*')) // Only keep lines starting with '*'
      .map(line => `<li>${line.substring(1).trim()}</li>`) // Remove '*' and wrap in <li>
      .join(''); // Combine all <li> items into a single string
  
    // Wrap in <ul> if there are any <li> items, otherwise use the raw summary
    summaryHtml = summaryHtml ? `<ul>${summaryHtml}</ul>` : tabData.summary;
  
    return `
      <div class="tab-card">
        <div class="title">${tabData.title}</div>
        <div>
          <span class="category">${tabData.category}</span>
          <span class="confidence">${tabData.confidence} confidence</span>
        </div>
        <div class="explanation">${tabData.explanation}</div>
        <div class="summary">${summaryHtml}</div>
        <div class="timestamp">Analyzed: ${new Date(tabData.timestamp).toLocaleString()}</div>
      </div>
    `;
  }
  
  function updatePopup() {
    // Get data for current tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.storage.local.get([tabs[0].id.toString()], (result) => {
          const container = document.getElementById('current-tab');
          if (result[tabs[0].id]) {
            container.innerHTML = createTabCard(result[tabs[0].id]);
          } else {
            container.innerHTML = '<p>No data available for this tab yet.</p>';
          }
        });
      }
    });
  }
  
  // Listen for updates from background script
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'TAB_CATEGORIZED') {
      // Update the popup if it's for the current tab
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0] && tabs[0].id === message.tabId) {
          updatePopup();
        }
      });
    }
  });
  
  // Initial update when popup opens
  document.addEventListener('DOMContentLoaded', updatePopup);