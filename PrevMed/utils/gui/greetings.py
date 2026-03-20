"""
Greetings page for PrevMed.

Creates the landing page shown when the user first opens the app.
Contains introductory markdown (from the YAML ``greetings_md`` field)
and the mandatory GDPR legal terms in a collapsible section at the bottom.

A "Start" button toggles visibility to the survey page.
Must be called inside an active ``gr.Blocks`` context.
"""

import gradio as gr
from typing import Optional, Tuple
from loguru import logger


def create_greetings_section(
    greetings_md: str,
    terms_md_content: Optional[str] = None,
    legal_summary: str = "LEGAL",
) -> Tuple[gr.Column, gr.Button]:
    """
    Build the greetings landing page components.

    Must be called inside an active ``gr.Blocks()`` context because it creates
    Gradio components (Column, Markdown, Button) that need a parent.

    Parameters
    ----------
    greetings_md : str
        Markdown content for the greetings page, taken from the YAML
        ``greetings_md`` field.
    terms_md_content : str, optional
        GDPR legal terms markdown loaded from ``--terms-md``.
        Rendered in a collapsible ``<details>`` element at the bottom.
    legal_summary : str, optional
        Label for the collapsible legal section (default: ``"LEGAL"``).

    Returns
    -------
    tuple of (gr.Column, gr.Button)
        The greetings column (visible by default) and the start button,
        so the caller can wire the button to hide this section and show
        the survey section.
    """
    logger.debug("Création de la section d'accueil")

    with gr.Column(visible=True) as greetings_col:
        gr.Markdown(greetings_md)

        start_btn = gr.Button(
            "Commencer le questionnaire →",
            variant="primary",
            size="lg",
        )

        # Legal terms at the bottom of the greetings page, in a collapsible section
        if terms_md_content:
            gr.Markdown(
                f"<details><summary>{legal_summary}</summary>"
                f"\n\n{terms_md_content}\n\n</details>"
            )

    logger.debug("Section d'accueil créée avec succès")
    return greetings_col, start_btn
