// background.js

chrome.runtime.onInstalled.addListener(() => {
  console.log("TabWise Extension Installed");
});

// Store tab states and categorized data
let tabStates = new Map();
let categorizedTabs = new Map();  // New: Store categorization results

class TabState {
  constructor() {
    this.lastTitle = null;
    this.lastUrl = null;
    this.lastProcessedTime = 0;
    this.changes = 0;
    this.lastProcessedTitle = null;
  }
}

function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!tabStates.has(tabId)) {
    tabStates.set(tabId, new TabState());
  }
  
  const state = tabStates.get(tabId);
  const currentTime = Date.now();
  
  if (currentTime - state.lastProcessedTime < 1000) {
    state.changes++;
  } else {
    state.changes = 0;
  }
  
  const shouldProcess = determineIfShouldProcess(changeInfo, tab, state);
  if (shouldProcess) {
    debouncedProcessTab(tabId, tab, state);
  }
  
  state.lastProcessedTime = currentTime;
  if (tab.url) state.lastUrl = tab.url;
  if (changeInfo.title) state.lastTitle = changeInfo.title;
});

function determineIfShouldProcess(changeInfo, tab, state) {
  if (!state.lastUrl) return true;
  
  const hasNewTitle = changeInfo.title && changeInfo.title !== state.lastTitle;
  const hasNewUrl = tab.url !== state.lastUrl;
  const isComplete = changeInfo.status === 'complete';
  const isSPABehavior = state.changes >= 2;
  
  if (changeInfo.title && changeInfo.title === state.lastProcessedTitle) {
    return false;
  }
  
  return hasNewTitle || 
         hasNewUrl || 
         (isComplete && Date.now() - state.lastProcessedTime > 1000) ||
         (isSPABehavior && hasNewTitle);
}

const debouncedProcessTab = debounce(async (tabId, tab, state) => {
  try {
    if (tab.title && tab.title !== state.lastProcessedTitle) {
      state.lastProcessedTitle = tab.title;
      await categorizeTab(tabId, tab);
    }
  } catch (error) {
    console.error('Error processing tab:', error);
  }
}, 500);

async function categorizeTab(tabId, tab) {
  if (!tab.title || tab.title.length < 2) return;
  
  try {
    const tabSummary = await summarizeContent(tab.title);
    const preProcessedSummary = tabSummary.replace(/[^a-zA-Z0-9 ]/g, "");
    const categoryResult = await getCategory(preProcessedSummary);
    
    // Store the categorization results
    const tabData = {
      url: tab.url,
      title: tab.title,
      summary: tabSummary,
      category: categoryResult.category,
      confidence: categoryResult.confidence,
      explanation: categoryResult.explanation,
      timestamp: new Date().toISOString()
    };
    
    // Update categorizedTabs Map
    categorizedTabs.set(tabId, tabData);
    
    // Store in chrome.storage
    chrome.storage.local.set({ [tabId]: tabData });
    
    // Notify popup if it's open
    chrome.runtime.sendMessage({
      type: 'TAB_CATEGORIZED',
      data: tabData,
      tabId: tabId
    }).catch((error) => {
      console.error("Message sending failed:", error);
    });
    
  } catch (error) {
    console.error('Error in categorizeTab:', error);
  }
}

async function summarizeContent(title) {
  let summarizer = await ai.summarizer.create();
  const summary = await summarizer.summarize(title);
  return summary;
}

async function getCategory(text) {
  try {
    const response = await fetch("http://localhost:8000/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prompt: text })
    });

    if (response.ok) {
      return await response.json();
    }
    throw new Error(response.statusText);
  } catch (error) {
    console.error("Error in getCategory:", error);
    return {
      category: 'Error',
      confidence: 0,
      explanation: error.message
    };
  }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_CURRENT_TAB_DATA') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        const tabData = categorizedTabs.get(tabs[0].id);
        sendResponse({ data: tabData || null });
      }
    });
    return true; // Will respond asynchronously
  }
});

// Clean up when tabs are closed
chrome.tabs.onRemoved.addListener((tabId) => {
  categorizedTabs.delete(tabId);
  tabStates.delete(tabId);
});