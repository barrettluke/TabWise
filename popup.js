// popup.js

// Function to create a card for a tab's data
function createTabCard(tabData) {
    return `
      <div class="tab-card">
        <div class="title">${tabData.title}</div>
        <div>
          <span class="category">${tabData.category}</span>
          <span class="confidence">${Math.round(tabData.confidence * 100)}% confidence</span>
        </div>
        <div class="explanation">${tabData.explanation}</div>
        <div class="summary">${tabData.summary}</div>
        <div class="timestamp">Analyzed: ${new Date(tabData.timestamp).toLocaleString()}</div>
      </div>
    `;
  }
  
  // Function to update the popup with current tab's data
  function updatePopup() {
    // Get data for current tab
    chrome.runtime.sendMessage({ type: 'GET_CURRENT_TAB_DATA' }, (response) => {
      const container = document.getElementById('current-tab');
      
      if (response.data) {
        container.innerHTML = createTabCard(response.data);
      } else {
        container.innerHTML = '<p>No data available for this tab yet.</p>';
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