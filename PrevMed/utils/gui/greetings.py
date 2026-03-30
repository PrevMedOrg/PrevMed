"""
Extra pages for PrevMed.

Creates additional pages (e.g. landing / greetings pages) defined via
the ``extra_pages`` list in the YAML configuration.  Each extra page is
served on its own route via Gradio's native ``Blocks.route()`` multipage
routing.

Must be called inside an active ``gr.Blocks`` context.
"""

import gradio as gr
from typing import Any, Dict, List, Optional
from loguru import logger


def create_extra_page(
    page_config: Dict[str, Any],
    terms_md_content: Optional[str] = None,
    default_legal_summary: str = "LEGAL",
) -> gr.Column:
    """
    Build an extra page from its configuration dict.

    Must be called inside an active ``gr.Blocks()`` or route context.

    Parameters
    ----------
    page_config : dict
        Configuration for this extra page.  Supports keys such as
        ``body``, ``page_title``, ``legal_summary``, etc.
    terms_md_content : str, optional
        GDPR legal terms markdown loaded from ``--terms-md``.
        Rendered in a collapsible ``<details>`` element at the bottom.
    default_legal_summary : str, optional
        Fallback label for the collapsible legal section.

    Returns
    -------
    gr.Column
        The page column.
    """
    route = page_config.get("route", "page")
    logger.debug(f"Création de la page supplémentaire: /{route}")

    with gr.Column(visible=True) as page_col:
        if page_config.get("page_title"):
            title = page_config["page_title"]
            if not title.startswith("#") and not title.startswith("<"):
                gr.Markdown(f"# {title}")
            else:
                gr.Markdown(title)

        if page_config.get("body"):
            gr.Markdown(page_config["body"])

        # Legal terms at the bottom, in a collapsible section
        legal_summary = page_config.get("legal_summary", default_legal_summary)
        if terms_md_content:
            gr.Markdown(
                f"<details><summary>{legal_summary}</summary>"
                f"\n\n{terms_md_content}\n\n</details>"
            )

    logger.debug(f"Page supplémentaire /{route} créée avec succès")
    return page_col
