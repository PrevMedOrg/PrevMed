"""
GUI package for PrevMed.

Splits the Gradio interface into two pages:
- greetings: landing page with introductory markdown and legal terms
- survey: the actual questionnaire (questions, scoring, PDF download)

Both pages live inside a single gr.Blocks app; visibility toggling
switches between them so that auth, queue, and launch options keep working.
"""

from PrevMed.utils.gui.survey import create_survey_interface  # noqa: F401
