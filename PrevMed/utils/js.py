JS_HEAD = """
<script>
// Add Enter key shortcut to click the "Suivant" button or PDF download button
document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('keydown', function(e) {
        // Check if Enter key was pressed (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            // Find the "Suivant →" button and click it if visible
            const buttons = Array.from(document.querySelectorAll('button'));
            const nextButton = buttons.find(btn => btn.textContent.includes('Suivant'));

            if (nextButton && nextButton.offsetParent !== null) {
                e.preventDefault();
                nextButton.click();
            } else {
                // If "Suivant" button is not visible, look for PDF download button
                const pdfButton = buttons.find(btn => btn.textContent.includes('Télécharger le rapport PDF'));

                if (pdfButton && pdfButton.offsetParent !== null) {
                    e.preventDefault();
                    pdfButton.click();
                }
            }
        }
    });
});

// Track PDF download clicks with Umami
document.addEventListener('click', function(e) {
    // Check if clicked element is a button containing the PDF download text
    if (e.target.tagName === 'BUTTON' &&
        e.target.textContent.includes('Télécharger le rapport PDF')) {

        // Only track if umami is available
        if (typeof umami !== 'undefined') {
            umami.track('PDF Download');
        }
    }
});

// Track reload button clicks with Umami
document.addEventListener('click', function(e) {
    // Check if clicked element is a button containing the reload text
    if (e.target.tagName === 'BUTTON' &&
        e.target.textContent.includes('Recharger')) {

        // Only track if umami is available
        if (typeof umami !== 'undefined') {
            umami.track('reload-survey-button');
        }
    }
});

// Track navigation button clicks with Umami
document.addEventListener('click', function(e) {
    // Check if clicked element is a button
    if (e.target.tagName === 'BUTTON') {
        // Track "Précédent" button clicks
        if (e.target.textContent.includes('Précédent')) {
            if (typeof umami !== 'undefined') {
                umami.track('back-question-button');
            }
        }
        // Track "Suivant" button clicks
        else if (e.target.textContent.includes('Suivant')) {
            if (typeof umami !== 'undefined') {
                umami.track('next-question-button');
            }
        }
    }
});

// add umami into all outbound url. Source: https://umami.is/docs/track-outbound-links
document.addEventListener('DOMContentLoaded', () => {
    // Only add tracking attributes if umami is available
    if (typeof umami !== 'undefined') {
        const name = 'outbound-link-click';
        document.querySelectorAll('a').forEach(a => {
            if (a.href && a.host && a.host !== window.location.host &&
                !a.getAttribute('data-umami-event')) {
                a.setAttribute('data-umami-event', name);
                a.setAttribute('data-umami-event-url', a.href);
            }
        });
    }
});
</script>
"""
