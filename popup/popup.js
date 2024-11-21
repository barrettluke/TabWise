// popup.js

// function to handle tab navigation
function navigateToTab(tabId) {
    if (tabId) {
        chrome.tabs.update(parseInt(tabId), { active: true }, () => {
            // Optional: Also bring the window with this tab to the foreground
            chrome.tabs.get(parseInt(tabId), (tab) => {
                chrome.windows.update(tab.windowId, { focused: true });
            });
        });
    }
}

function createTabCard(tabData) {
    let summaryHtml = tabData.summary
        .split('\n')
        .map(line => {
            if (line.startsWith('*')) {
                const cleanContent = line.substring(1).trim().replace(/\*/g, '');
                return `<li>${cleanContent}</li>`;
            }
            return line.replace(/\*/g, '');
        })
        .filter(line => line.length > 0)
        .join('');

    summaryHtml = summaryHtml.includes('<li>') ? `<ul>${summaryHtml}</ul>` : summaryHtml;

    return `
        <div class="tab-card ${tabData.tab?.id ? 'clickable-tab' : ''}" data-tab-id="${tabData.tab?.id || ''}">
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

function handleTabCardClick(event) {
    const tabId = event.currentTarget.dataset.tabId;
    if (tabId) {
        navigateToTab(parseInt(tabId));
    }
}

function navigateToTab(tabId) {
    chrome.tabs.update(tabId, { active: true }, () => {
        // Bring the window with this tab to the foreground
        chrome.tabs.get(tabId, (tab) => {
            chrome.windows.update(tab.windowId, { focused: true });
        });
    });
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
    const isCollapsed = localStorage.getItem(`category-${category}-collapsed`) === 'true';
    const contentDisplay = isCollapsed ? 'none' : 'block';

    return `
        <div class="group-card" data-category="${category}">
            <div class="category-header">
                <svg class="collapse-icon ${isCollapsed ? 'collapsed' : ''}" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 6L8 11L13 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <h3>${category} (${groupTabs.length})</h3>
            </div>
            <div class="category-content" style="display: ${contentDisplay}">
                ${groupTabs.map(createTabCard).join('')}
            </div>
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
                container.innerHTML = Object.entries(groupedTabs)
                    .map(([category, groupTabs]) => createGroupCard(category, groupTabs))
                    .join('');
            } else {
                Object.entries(groupedTabs).forEach(([category, groupTabs]) => {
                    const existingGroup = container.querySelector(`[data-category="${category}"]`);
                    if (existingGroup) {
                        const content = existingGroup.querySelector('.category-content');
                        const isCollapsed = content.style.display === 'none';
                        existingGroup.outerHTML = createGroupCard(category, groupTabs);
                        if (isCollapsed) {
                            const newGroup = container.querySelector(`[data-category="${category}"]`);
                            const newContent = newGroup.querySelector('.category-content');
                            const newIcon = newGroup.querySelector('.collapse-icon');
                            newContent.style.display = 'none';
                            newIcon.classList.add('collapsed');
                        }
                    } else {
                        container.insertAdjacentHTML('beforeend', createGroupCard(category, groupTabs));
                    }
                });

                container.querySelectorAll('.group-card').forEach(groupEl => {
                    const category = groupEl.dataset.category;
                    if (!groupedTabs[category]) {
                        groupEl.remove();
                    }
                });
            }

            setupEventListeners();
        });
    });
}

function setupEventListeners() {
    // Category header click listeners
    document.querySelectorAll('.category-header').forEach(header => {
        header.removeEventListener('click', handleCategoryClick);
        header.addEventListener('click', handleCategoryClick);
    });

    // Tab navigation listeners
    document.querySelectorAll('.clickable-tab').forEach(tabCard => {
        tabCard.removeEventListener('click', handleTabCardClick);
        tabCard.addEventListener('click', handleTabCardClick);
    });
}

function handleCategoryClick(event) {
    const groupCard = event.currentTarget.closest('.group-card');
    const category = groupCard.dataset.category;
    const content = groupCard.querySelector('.category-content');
    const icon = groupCard.querySelector('.collapse-icon');
    
    const isCollapsed = content.style.display !== 'none';
    content.style.display = isCollapsed ? 'none' : 'block';
    icon.classList.toggle('collapsed');
    
    localStorage.setItem(`category-${category}-collapsed`, isCollapsed.toString());
}

// Initial load and event listeners
document.addEventListener('DOMContentLoaded', () => {
    updatePopup(true);
    
    const refreshInterval = setInterval(() => {
        updatePopup(false);
    }, 5000);

    window.addEventListener('unload', () => {
        clearInterval(refreshInterval);
    });
});