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
    const preProcessedSummary = tabSummary.replace(/[^a-zA-Z0-9 ]/g, "");
    getCategory(preProcessedSummary);
    // console.log(`Category: ${category}`);
  }
  
  async function summarizeContent(title) {
    let summarizer = await ai.summarizer.create();
    const summary = await summarizer.summarize(title);  // Summarize the tab
    return summary; // Replace with actual summary
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
            console.log("\nInput:", text);
            console.log("Category:", result.category);
            console.log("Confidence:", result.confidence);
            console.log("Explanation:", result.explanation);
        } else {
            console.error("Error:", response.statusText);
        }
    } catch (error) {
        console.error("Error:", error);
    }
}