"""
Greetings page for PrevMed.

Creates the landing page shown when the user first opens the app.
Contains introductory markdown (from the YAML ``greetings_md`` field)
and the mandatory GDPR legal terms in a collapsible section at the bottom.

The "Start" button uses ``gr.Button(link=...)`` to navigate to the survey
route via Gradio's native ``Blocks.route()`` multipage routing.
Must be called inside an active ``gr.Blocks`` context.
"""

import gradio as gr
from typing import Optional
from loguru import logger


def create_greetings_section(
    greetings_md: str,
    survey_route: str = "survey",
    terms_md_content: Optional[str] = None,
    legal_summary: str = "LEGAL",
) -> gr.Column:
    """
    Build the greetings landing page components.

    Must be called inside an active ``gr.Blocks()`` context because it creates
    Gradio components (Column, Markdown, Button) that need a parent.

    Parameters
    ----------
    greetings_md : str
        Markdown content for the greetings page, taken from the YAML
        ``greetings_md`` field.
    survey_route : str, optional
        Route path for the survey page (default: ``"survey"``).
        The start button links to this route.
    terms_md_content : str, optional
        GDPR legal terms markdown loaded from ``--terms-md``.
        Rendered in a collapsible ``<details>`` element at the bottom.
    legal_summary : str, optional
        Label for the collapsible legal section (default: ``"LEGAL"``).

    Returns
    -------
    gr.Column
        The greetings column.
    """
    logger.debug("Création de la section d'accueil")

    with gr.Column(visible=True) as greetings_col:
        gr.Markdown(greetings_md)

        # gr.Button(
        #     "Commencer le questionnaire →",
        #     variant="primary",
        #     size="lg",
        #     link=survey_route,
        # )

        # Legal terms at the bottom of the greetings page, in a collapsible section
        if terms_md_content:
            gr.Markdown(
                f"<details><summary>{legal_summary}</summary>"
                f"\n\n{terms_md_content}\n\n</details>"
            )

    logger.debug("Section d'accueil créée avec succès")
    return greetings_col
