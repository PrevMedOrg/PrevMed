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
</script>
"""
