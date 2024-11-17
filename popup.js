// popup.js

// Function to create a card for a tab's data
function createTabCard(tabData) {
    // Convert summary into an unordered list if applicable
    let summaryHtml = tabData.summary
        .split('\n') // Split summary by newlines
        .map(line => {
            if (line.startsWith('*')) {
                // For lines starting with '*', remove the initial '*' and any other '*' in the line
                const cleanContent = line.substring(1).trim().replace(/\*/g, '');
                return `<li>${cleanContent}</li>`;
            }
            // For other lines, just remove any '*' characters
            return line.replace(/\*/g, '');
        })
        .filter(line => line.length > 0) // Remove empty lines
        .join('');

    // Wrap in <ul> if there are any <li> items
    summaryHtml = summaryHtml.includes('<li>') ? `<ul>${summaryHtml}</ul>` : summaryHtml;

    return `
        <div class="tab-card" data-tab-id="${tabData.tab?.id || ''}">
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
  
  function groupTabsByCategory(tabs, storedData) {
    const groups = {};
    tabs.forEach((tab) => {
      const tabId = tab.id.toString();
      if (storedData[tabId] && storedData[tabId].category) {
        const category = storedData[tabId].category;
        if (!groups[category]) {
          groups[category] = [];
        }
        groups[category].push({ ...storedData[tabId], tab });
      }
    });
    return groups;
  }
  
  function createGroupCard(category, groupTabs) {
    return `
      <div class="group-card" data-category="${category}">
        <h3>${category}</h3>
        ${groupTabs.map(createTabCard).join('')}
      </div>
    `;
  }
  
  function updatePopup(forceRefresh = false) {
    chrome.tabs.query({ currentWindow: true }, (tabs) => {
      const container = document.getElementById('current-tab');
      
      chrome.storage.local.get(null, (storedData) => {
        const groupedTabs = groupTabsByCategory(tabs, storedData);
        
        if (Object.keys(groupedTabs).length === 0) {
          container.innerHTML = '<p>No categorized tabs available.</p>';
          return;
        }
  
        if (forceRefresh) {
          // Complete refresh of all content
          container.innerHTML = Object.entries(groupedTabs)
            .map(([category, groupTabs]) => createGroupCard(category, groupTabs))
            .join('');
        } else {
          // Update existing cards or add new ones
          Object.entries(groupedTabs).forEach(([category, groupTabs]) => {
            const existingGroup = container.querySelector(`[data-category="${category}"]`);
            if (existingGroup) {
              // Update existing group
              existingGroup.innerHTML = createGroupCard(category, groupTabs)
                .replace(/<div class="group-card"[^>]*>/, '')
                .replace(/<\/div>$/, '');
            } else {
              // Add new group
              container.insertAdjacentHTML('beforeend', createGroupCard(category, groupTabs));
            }
          });
  
          // Remove empty categories
          container.querySelectorAll('.group-card').forEach(groupEl => {
            const category = groupEl.dataset.category;
            if (!groupedTabs[category]) {
              groupEl.remove();
            }
          });
        }
      });
    });
  }
  
  // Listen for live updates from background script
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'TAB_CATEGORIZED') {
      // Debounce the update to avoid too frequent refreshes
      if (window.updateTimeout) {
        clearTimeout(window.updateTimeout);
      }
      window.updateTimeout = setTimeout(() => {
        updatePopup(false);
      }, 100);
    }
    // Always send a response
    sendResponse({ received: true });
    return true;
  });
  
  // Initial update when popup opens
  document.addEventListener('DOMContentLoaded', () => {
    updatePopup(true);
    
    // Set up periodic refresh
    const refreshInterval = setInterval(() => {
      updatePopup(false);
    }, 5000);
  
    // Clear interval when popup closes
    window.addEventListener('unload', () => {
      clearInterval(refreshInterval);
    });
  });
  
  // Add error handling for the container
  window.addEventListener('error', (event) => {
    const container = document.getElementById('current-tab');
    container.innerHTML = `
      <div class="error-message">
        <p>An error occurred while updating the display.</p>
        <button onclick="updatePopup(true)">Retry</button>
      </div>
    `;
    console.error('Popup error:', event.error);
  });