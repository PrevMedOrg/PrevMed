
CSS = """
.question-row {
    justify-content: center !important;
    display: flex !important;
    align-items: center !important;
}

.adjusted-widgets {
    max-width: 800px;
    width: 100%;
}
.adjusted-widget {
    max-width: 800px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    display: flex !important;
    justify-content: center !important;
}
/* Target Gradio's internal wrapper divs to ensure centering propagates */
.adjusted-widget > div,
.adjusted-widget > label,
.adjusted-widget > * {
    margin-left: auto !important;
    margin-right: auto !important;
}
/* Ensure Gradio components themselves are adjusted */
.adjusted-widget .wrap,
.adjusted-widget input,
.adjusted-widget textarea,
.adjusted-widget .svelte-1gfkn6j {
    margin-left: auto !important;
    margin-right: auto !important;
    text-align: center !important;
}

// Display the result table in the middle
.adjusted-results {
    display: flex;
    justify-content: center;
    width: 100%;
}
.adjusted-results table {
    margin-left: auto;
    margin-right: auto;
}

// hide the footer
footer {
    display: none !important;
}
"""
