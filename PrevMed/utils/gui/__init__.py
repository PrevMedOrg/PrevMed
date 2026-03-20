"""
GUI package for PrevMed.

Splits the Gradio interface into two pages:
- greetings: landing page with introductory markdown and legal terms
- survey: the actual questionnaire (questions, scoring, PDF download)

When ``greetings_md`` is present in the YAML, the greetings page is served
at ``/`` and the survey lives on a sub-route via ``Blocks.route()``
(configurable with the ``survey_route`` YAML key, default ``/survey``).
"""

from PrevMed.utils.gui.survey import create_survey_interface  # noqa: F401
