// This script adds additional layout control for Streamlit Cloud environment

// Check if we're in Streamlit Cloud environment
const isCloud = window.parent.location.href.includes('streamlitapp.com') || 
                window.parent.location.href.includes('streamlit.app') ||
                window.parent.location.href.includes('share.streamlit.io');

// Add fixed width wrappers to main content
function addFixedWidthContainers() {
    // Add a class to the main container
    const mainContainer = document.querySelector('[data-testid="stAppViewContainer"] > div:nth-child(2)');
    if (mainContainer) {
        mainContainer.classList.add('fixed-width-container');
        mainContainer.style.maxWidth = '1800px';
        mainContainer.style.margin = '0 auto';
        mainContainer.style.padding = '0';
    }
    
    // Add a class to all columns
    const columns = document.querySelectorAll('[data-testid="column"]');
    columns.forEach(col => {
        col.classList.add('fixed-width-column');
    });
    
    // Fix HTML elements
    const htmlElements = document.querySelectorAll('[data-testid="stHtml"]');
    htmlElements.forEach(el => {
        el.style.width = '100%';
        el.style.overflow = 'visible';
        el.style.margin = '0 0 1rem 0';
    });
}

// Wait for the DOM to be fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addFixedWidthContainers);
} else {
    addFixedWidthContainers();
}

// Also add a mutation observer to handle dynamic content changes
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.addedNodes.length) {
            addFixedWidthContainers();
        }
    });
});

// Start observing the document with the configured parameters
observer.observe(document.body, { childList: true, subtree: true });
