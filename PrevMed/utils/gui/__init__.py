"""
GUI package for PrevMed.

The survey questionnaire is served at ``/``.  Additional pages defined
in the ``extra_pages`` YAML list are served on their own routes via
``Blocks.route()``.
"""

from PrevMed.utils.gui.survey import create_survey_interface  # noqa: F401
