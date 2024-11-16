// background.js

chrome.runtime.onInstalled.addListener(() => {
  console.log("TabWise Extension Installed");
});

// Store tab states
let tabStates = new Map();

class TabState {
  constructor() {
    this.lastTitle = null;
    this.lastUrl = null;
    this.lastProcessedTime = 0;
    this.changes = 0;
    this.lastProcessedTitle = null; // Track the last processed title
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
  
  // Check if we've already processed this title
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
    // Only process if the title is different from the last processed title
    if (tab.title && tab.title !== state.lastProcessedTitle) {
      state.lastProcessedTitle = tab.title; // Update the last processed title
      await categorizeTab(tab);
    }
  } catch (error) {
    console.error('Error processing tab:', error);
  }
}, 500);

chrome.tabs.onRemoved.addListener((tabId) => {
  tabStates.delete(tabId);
});

async function categorizeTab(tab) {
  if (!tab.title || tab.title.length < 2) return;
  
  try {
    const tabSummary = await summarizeContent(tab.title);
    console.log(`\nNew page detected:`);
    console.log(`URL: ${tab.url}`);
    console.log(`Title: ${tab.title}`);
    console.log(`Summary: ${tabSummary}`);
    
    const preProcessedSummary = tabSummary.replace(/[^a-zA-Z0-9 ]/g, "");
    await getCategory(preProcessedSummary);
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
      const result = await response.json();
      console.log("Category:", result.category);
      console.log("Confidence:", result.confidence);
      console.log("Explanation:", result.explanation);
    } else {
      console.error("Error:", response.statusText);
    }
  } catch (error) {
    console.error("Error in getCategory:", error);
  }
}