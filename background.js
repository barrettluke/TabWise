// background.js

chrome.runtime.onInstalled.addListener(() => {
    console.log("TabWise Extension Installed");
  });
  
  // Listener for when a new tab is created or updated
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete') {
      // Initiate categorization or summarization for the new tab
      console.log(tab, "tab")
      console.log(tabId, "tabId")
      console.log(changeInfo, "changeInfo")
      categorizeTab(tab);
    }
  });
  
  async function categorizeTab(tab) {
    
    const tabSummary = await summarizeContent(tab.title);
    
    console.log(`Summary: ${tabSummary}`);
    // console.log(`Category: ${category}`);
  }
  
  async function summarizeContent(title) {
    let summarizer = await ai.summarizer.create();
    const summary = await summarizer.summarize(title);  // Summarize the tab
    return summary; // Replace with actual summary
  }