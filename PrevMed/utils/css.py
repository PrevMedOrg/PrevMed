CSS = """
/* Constrain the entire app to a readable width, centered */
.gradio-container {
    max-width: 1024px !important;
    margin: 0 auto !important;
}

/* Hide the Gradio footer */
footer {
    display: none !important;
}

.question-row {
    justify-content: center !important;
    display: flex !important;
    align-items: center !important;
}

/* Center question widget content (labels, radio buttons, etc.) */
.question-row .adjusted-widget {
    justify-content: center !important;
    text-align: center !important;
}
.question-row .adjusted-widget > * {
    text-align: center !important;
    justify-content: center !important;
}
.question-row .adjusted-widget input {
    text-align: center !important;
}

/* Center result tables */
.adjusted-results {
    display: flex;
    justify-content: center;
    width: 100%;
}
.adjusted-results table {
    margin-left: auto;
    margin-right: auto;
}

/* Force text justification in header content */
.force_justify_text, .force_justify_text * {
    text-align: justify !important;
}

/* Prevent unwanted scrollbars on Markdown and content containers */
.gradio-container .md,
.gradio-container .prose,
.gradio-container .svelte-1ed2p3z,
.gradio-container .block,
.gradio-container .wrap {
    overflow: visible !important;
    max-height: none !important;
}
/* Ensure long headings wrap properly */
.gradio-container h1, .gradio-container h2,
.gradio-container h3, .gradio-container h4 {
    overflow-wrap: break-word !important;
    word-wrap: break-word !important;
}

/* Hide the Gradio multipage navigation bar */
.nav-holder {
    display: none !important;
}
"""
