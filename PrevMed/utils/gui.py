import os
import time
import gradio as gr
from typing import Any, Dict
from loguru import logger

from PrevMed.utils.io import load_yaml
from PrevMed.utils.scoring import execute_scoring
from PrevMed.utils.logic import (
    find_next_valid_question,
    evaluate_skip_if,
    evaluate_valid_if,
)
from PrevMed.utils.pdf import generate_pdf_report
from PrevMed.utils.version import __VERSION__
from PrevMed.utils.css import CSS
from PrevMed.utils.js import JS_HEAD


def create_widget_for_question(question: Dict[str, Any]) -> gr.components.Component:
    """
    Crée le widget Gradio approprié basé sur la spécification du widget dans le YAML.

    Paramètres
    ----------
    question : Dict[str, Any]
        Configuration de la question depuis le YAML avec les champs 'widget' et 'widget_args'.

    Retourne
    --------
    gr.components.Component
        Composant Gradio configuré
    """
    widget_type = question["widget"].title()
    widget_args = question.get("widget_args", {})
    variable = question.get("variable", "unknown")

    logger.debug(
        f"Création du widget pour la variable '{variable}' de type '{widget_type}'"
    )
    logger.debug(f"  widget_args: {widget_args}")

    # Widgets are created as visible - visibility is controlled by their parent Row
    # Build kwargs dict from widget_args, excluding 'default' which maps to 'value'
    kwargs = {k: v for k, v in widget_args.items() if k != "default"}

    # Add common arguments for all widgets
    kwargs["interactive"] = True

    # Make widgets expand to fill their container (row) unless scale is explicitly set
    if "scale" not in kwargs:
        kwargs["scale"] = 1

    # Set label to question text if not explicitly provided in widget_args
    if "label" not in kwargs:
        kwargs["label"] = f"Q{question['order']}: {question['question']}"

    # Add centering class to widget to enable CSS-based centering
    kwargs["elem_classes"] = ["adjusted-widget"]

    logger.debug(f"  Widget kwargs (valeur exclue): {kwargs}")

    if widget_type == "Radio":
        widget = gr.Radio(**kwargs)
    elif widget_type == "Slider":
        widget = gr.Slider(**kwargs)
    elif widget_type == "Number":
        # Number widget always uses integer precision in this application
        kwargs["precision"] = 0
        widget = gr.Number(**kwargs)
    elif widget_type == "Checkbox":
        widget = gr.Checkbox(**kwargs)
    elif widget_type == "Textbox":
        widget = gr.Textbox(**kwargs)
    else:
        # Check if widget_type is a valid Gradio component we haven't explicitly handled
        if hasattr(gr, widget_type):
            logger.warning(
                f"Le type de widget '{widget_type}' pour la variable '{variable}' n'est pas explicitement supporté, "
                f"mais existe dans Gradio. Tentative d'utilisation quand même."
            )
            widget_class = getattr(gr, widget_type)
            widget = widget_class(**kwargs)
        else:
            # Fallback to Textbox for unknown widget types
            logger.warning(
                f"Type de widget inconnu '{widget_type}' pour la variable '{variable}', utilisation de Textbox"
            )
            widget = gr.Textbox(**kwargs)

    logger.debug(f"Widget {widget_type} créé avec succès pour la variable '{variable}'")
    return widget


def create_survey_interface(
    yaml_path: str,
    scoring_language: str,
    scoring_code: str,
    actual_url: str = "NA",
    umami_url: str = None,
    umami_website_id: str = None,
) -> gr.Blocks:
    """
    Crée une interface Gradio Blocks à partir de la configuration YAML avec une question à la fois.

    Paramètres
    ----------
    yaml_path : str
        Chemin vers le fichier de configuration YAML
    scoring_language : str
        Langage du script de scoring ('r' ou 'python')
    scoring_code : str
        Code du script de scoring
    actual_url : str, optionnel
        URL réelle où cette enquête est hébergée (sera stockée dans les rapports PDF)
    umami_url : str, optionnel
        URL de l'instance Umami analytics (par ex., 'https://analytics.example.com')
    umami_website_id : str, optionnel
        ID du site web pour le suivi Umami analytics

    Retourne
    --------
    gr.Blocks
        Interface Gradio configurée
    """
    logger.info(f"Création de l'interface du questionnaire depuis le YAML: {yaml_path}")

    config = load_yaml(yaml_path)
    questions = sorted(config["questions"], key=lambda q: q["order"])

    logger.info(
        f"Questionnaire '{config['survey_name']}' chargé avec {len(questions)} questions"
    )

    logger.info(f"Langage de scoring: {scoring_language}")

    # Build analytics head content if parameters are provided
    # This allows optional Umami analytics integration for usage tracking
    analytics_head = ""

    if umami_url and umami_website_id:
        # Use custom Umami instance URL if provided, otherwise use cloud default
        script_url = f"{umami_url}/script.js"
        analytics_head = f'<script defer src="{script_url}" data-website-id="{umami_website_id}"></script>\n'
        logger.info(
            f"Umami analytics activé: {script_url} (ID du site web: {umami_website_id})"
        )
    elif umami_website_id:
        # Only website ID provided, use cloud.umami.is default
        analytics_head = f'<script defer src="https://cloud.umami.is/script.js" data-website-id="{umami_website_id}"></script>\n'
        logger.info(
            f"Umami analytics activé avec le point d'accès cloud (ID du site web: {umami_website_id})"
        )
    else:
        logger.debug("Umami analytics non configuré (aucun argument fourni)")

    with gr.Blocks(
        title=config["survey_name"],
        theme=gr.themes.Soft(
            primary_hue="green",
            secondary_hue="emerald",
            neutral_hue="gray",
        ),
        analytics_enabled=False,
        head=analytics_head + "\n\n" + JS_HEAD,
        css=CSS,
    ) as demo:
        gr.Markdown(
            f"# PrevMed - {config['survey_name']} (v{config['survey_version']})"
        )
        gr.Markdown("PrevMed version: " + __VERSION__)

        # Optional header text - rendered as markdown if present in YAML
        if config.get("header"):
            gr.Markdown(config["header"])

        # State to track current question index
        current_question_idx = gr.State(0)

        # Container for questions with accumulative display
        # All answered questions remain visible as user progresses
        with gr.Column(elem_classes=["question-container", "adjusted-widgets"]):
            # Create all widgets and store them
            # First question is visible by default, rest are hidden
            widgets = {}
            for i, q in enumerate(questions):
                # First question's row starts visible so users see something immediately
                initial_visible = i == 0
                with gr.Row(
                    visible=initial_visible, elem_classes=["question-row"]
                ) as row:
                    widget = create_widget_for_question(q)
                    widgets[q["variable"]] = {
                        "widget": widget,
                        "row": row,
                        "question": q,
                    }

        # Navigation buttons with fixed positioning class
        with gr.Row(elem_classes="nav-buttons", equal_height=True):
            prev_btn = gr.Button("← Précédent", visible=False, variant="stop", scale=1)
            next_btn = gr.Button(
                f"Suivant → (Question 1 / {len(questions)})",
                variant="primary",
                scale=2,
            )

        # Results section - positioned at bottom to appear after answering questions
        with gr.Column(elem_classes="adjusted-results"):
            result_output = gr.Markdown(label="Résultats du scoring", visible=False)
            pdf_download = gr.DownloadButton(
                label="📥 Télécharger le rapport PDF",
                visible=False,
                variant="primary",
                size="lg",
            )
        error_output = gr.Textbox(label="Erreur", visible=False, interactive=False)

        # Reload button - positioned at bottom to allow users to restart survey
        reload_btn = gr.Button(
            "🔄 Recharger le questionnaire", variant="secondary", size="sm"
        )

        def update_question_display(current_idx, *args):
            """
            Met à jour quelles questions sont visibles en fonction de l'index actuel.

            Cette fonction implémente un affichage cumulatif : toutes les questions répondues
            restent visibles si leurs conditions sont remplies, tandis que les questions futures sont cachées.
            Seule la question actuelle est interactive ; les précédentes sont en lecture seule.

            Scalabilité : Met à jour uniquement les questions de 0 à current_idx+1, pas toutes les questions.

            Paramètres
            ----------
            current_idx : int
                Index de la question actuelle à afficher
            *args : tuple
                Valeurs des widgets de toutes les questions dans l'ordre

            Retourne
            --------
            Dict[gr.components.Component, gr.update]
                Dictionnaire de mises à jour des composants Gradio
            """
            logger.debug(
                f"=== update_question_display DÉBUT === current_idx={current_idx}"
            )
            logger.debug(f"Réception de {len(args)} arguments")

            # Build context from current values
            context = {}
            for i, q in enumerate(questions):
                context[q["variable"]] = args[i]
                # Anonymity: Do not log actual answer values, only variable name and type
                logger.debug(
                    f"  Context[{i}] '{q['variable']}' (widget: {q['widget']}) type: {type(args[i]).__name__}"
                )

            logger.debug(f"Contexte construit avec {len(context)} variables")

            # Find the actual question to display (considering conditions)
            display_idx = current_idx
            while 0 <= display_idx < len(questions):
                condition = questions[display_idx].get("skip_if", None)
                if not condition:
                    break
                elif not evaluate_skip_if(condition, context):
                    break
                # If condition not met, skip to next question
                display_idx += 1

            # Build dictionary of component updates
            # Scalability: Only update components in a narrow range around current index
            # This avoids updating all previous questions, significantly improving performance
            # We only need to update:
            # - Previous question (to make it non-interactive)
            # - Current question (to make it visible and interactive)
            # - Next question (to ensure it stays hidden)
            updates = {}

            start_idx = max(0, display_idx - 1)
            end_idx = len(questions)  # Always update to end to hide future questions
            logger.debug(
                f"Mise à jour des questions {start_idx} à {end_idx - 1} (plage de {end_idx - start_idx}) sur {len(questions)} au total"
            )

            for i in range(start_idx, end_idx):
                q = questions[i]
                condition = q.get("skip_if", None)
                if not condition:
                    is_condition_met = True
                else:
                    is_condition_met = not evaluate_skip_if(condition, context)

                if i <= current_idx:
                    # Current and previous questions: show if condition is met
                    # This keeps all answered questions visible
                    is_visible = is_condition_met
                    # Only the current question is interactive, previous ones are read-only
                    is_interactive = (i == display_idx) and is_condition_met
                else:
                    # Future questions: always hide and non-interactive
                    is_visible = False
                    is_interactive = False

                # Update row visibility
                updates[widgets[q["variable"]]["row"]] = gr.update(visible=is_visible)
                # Update widget interactivity and value
                # Must include value when updating interactive to ensure proper state update
                updates[widgets[q["variable"]]["widget"]] = gr.update(
                    interactive=is_interactive, value=args[i]
                )

            # Update navigation buttons
            # Hide both buttons when showing results (past last question)
            prev_visible = display_idx > 0 and display_idx < len(questions)
            next_visible = display_idx < len(questions)

            # Calculate dynamic progress based on valid (non-skipped) questions
            # Count total questions with conditions met in current context
            # A question is valid (should be shown) if:
            # - It has no skip_if condition, OR
            # - It has skip_if but the condition evaluates to False (don't skip)
            total_valid = sum(
                1
                for q in questions
                if ("skip_if" not in q) or (not evaluate_skip_if(q["skip_if"], context))
            )

            # Count which valid question we're on (questions up to and including current)
            # Uses same logic as total_valid for consistency
            current_valid = sum(
                1
                for i, q in enumerate(questions[: display_idx + 1])
                if ("skip_if" not in q) or (not evaluate_skip_if(q["skip_if"], context))
            )

            # Calculate progress text for button label
            if display_idx < len(questions):
                if total_valid > 0:
                    next_btn_label = (
                        f"Suivant → (Question {current_valid} / {total_valid})"
                    )
                else:
                    next_btn_label = "Suivant →"
            else:
                next_btn_label = "✓ Terminé"

            logger.debug(
                f"Index d'affichage: {display_idx}, Progression: {current_valid}/{total_valid}"
            )

            # Add navigation button updates
            updates[prev_btn] = gr.update(visible=prev_visible)
            updates[next_btn] = gr.update(visible=next_visible, value=next_btn_label)
            # State update for current question index
            updates[current_question_idx] = display_idx

            logger.debug(
                f"=== update_question_display FIN === Retour de {len(updates)} mises à jour de composants"
            )

            return updates

        def go_next(request: gr.Request, current_idx, *args):
            """
            Navigue vers la question suivante, en sautant celles dont les conditions ne sont pas remplies.

            Paramètres
            ----------
            request : gr.Request
                Objet de requête Gradio contenant les informations client
            current_idx : int
                Index de la question actuelle
            *args : tuple
                Valeurs des widgets de toutes les questions dans l'ordre

            Retourne
            --------
            Dict[gr.components.Component, gr.update]
                Dictionnaire de mises à jour des composants Gradio incluant la navigation
                et potentiellement les résultats si c'est la dernière question
            """
            logger.info(
                f"=== go_next DÉBUT === depuis l'index de question {current_idx}"
            )
            logger.debug(f"go_next a reçu {len(args)} arguments")

            # Check if current question has been answered
            # Only enforce this if the question doesn't have a default value
            current_value = args[current_idx]
            current_question = questions[current_idx]
            widget_args = current_question.get("widget_args", {})
            has_default = "default" in widget_args

            # If no default is specified, require the user to provide a value
            if not has_default:
                # Check if value is None or empty (for text inputs)
                # Note: False and 0 are valid values, so we specifically check for None
                is_empty = current_value is None or (
                    isinstance(current_value, str) and current_value.strip() == ""
                )

                if is_empty:
                    warning_msg = f"Veuillez répondre à la question actuelle avant de continuer: {current_question['question']}"
                    logger.warning(
                        f"L'utilisateur a tenté de continuer sans répondre à la question {current_idx}: {current_question['variable']}"
                    )

                    # Display warning using Gradio's built-in Warning notification
                    gr.Warning(warning_msg)

                    # Return updates that don't change question
                    updates = update_question_display(current_idx, *args)
                    return updates

            # Check if answer meets validation criteria (valid_if condition)
            if "valid_if" in current_question:
                # Build context from current values for validation
                context = {}
                for i, q in enumerate(questions):
                    context[q["variable"]] = args[i]

                valid_if_condition = current_question["valid_if"]

                # Evaluate the valid_if condition
                try:
                    is_valid = evaluate_valid_if(valid_if_condition, context)
                except Exception as e:
                    logger.error(
                        f"Erreur lors de l'évaluation de la condition valid_if: {str(e)}",
                        exc_info=True,
                    )
                    gr.Warning(f"Erreur lors de la validation: {str(e)}")
                    updates = update_question_display(current_idx, *args)
                    return updates

                if not is_valid:
                    # Use custom invalid_message if provided, otherwise use default
                    if "invalid_message" in current_question:
                        warning_msg = current_question["invalid_message"]
                    else:
                        warning_msg = f"La réponse à la question actuelle n'est pas valide: {current_question['question']}"

                    logger.warning(
                        f"L'utilisateur a fourni une réponse invalide pour la question {current_idx}: {current_question['variable']} "
                        f"(la condition valid_if '{valid_if_condition}' a été évaluée à False)"
                    )

                    # Display warning using Gradio's built-in Warning notification
                    gr.Warning(warning_msg)

                    # Return updates that don't change question
                    updates = update_question_display(current_idx, *args)
                    return updates

            # Capture client info from request for privacy-preserving hash
            # This will be hashed with the patient reference code as salt
            # Gradio automatically injects the request parameter before other inputs
            client_info = None
            if request is not None:
                try:
                    client_info = {
                        "user_agent": request.headers.get("user-agent", "unknown"),
                        "ip_address": f"{request.client.host}:{request.client.port}",
                        "headers_count": len(request.headers),
                        "query_params": dict(request.query_params),
                        "session_hash": request.session_hash,
                    }
                    logger.info(
                        f"Informations client capturées pour le hachage: IP={client_info['ip_address']}, session_hash={client_info['session_hash']}"
                    )
                except Exception as e:
                    logger.warning(f"Échec de la capture des informations client: {e}")
                    client_info = None
            else:
                logger.warning(
                    "L'objet Request est None - le client_hash ne sera pas généré"
                )

            # Log argument metadata (anonymity: do not log actual values)
            for i, (q, val) in enumerate(zip(questions, args)):
                logger.debug(
                    f"  go_next entrée[{i}] '{q['variable']}' (widget:{q['widget']}) type: {type(val).__name__}"
                )

            # Build context from current values
            context = {}
            for i, q in enumerate(questions):
                context[q["variable"]] = args[i]

            logger.debug(
                f"Recherche de la prochaine question valide depuis {current_idx}"
            )
            try:
                new_idx = find_next_valid_question(
                    current_idx, questions, context, direction=1
                )
                logger.debug(f"Index de la prochaine question valide: {new_idx}")
            except Exception as e:
                logger.error(
                    f"Erreur lors de la recherche de la question suivante: {str(e)}",
                    exc_info=True,
                )
                raise

            logger.debug(f"Navigation de l'index {current_idx} vers {new_idx}")

            # Get display updates as dictionary
            logger.debug(f"Appel de update_question_display avec new_idx={new_idx}")
            try:
                updates = update_question_display(new_idx, *args)
                logger.debug(
                    f"Réception de {len(updates)} mises à jour de composants depuis update_question_display"
                )
            except Exception as e:
                logger.error(
                    f"ERREUR dans update_question_display: {str(e)}", exc_info=True
                )
                raise

            # If we've reached the end, automatically compute score
            if new_idx >= len(questions):
                logger.info("=== Fin du questionnaire atteinte, calcul du score ===")
                # Map values to inputs dict
                inputs = {}
                for i, q in enumerate(questions):
                    inputs[q["variable"]] = args[i]

                logger.debug("Exécution de la fonction de scoring")
                try:
                    scoring_start = time.perf_counter()
                    markdown_result, result_data, pdf_options = execute_scoring(
                        scoring_language, scoring_code, inputs
                    )
                    scoring_duration = time.perf_counter() - scoring_start
                    logger.success(
                        f"Scoring complété avec succès en {scoring_duration:.3f}s"
                    )

                    logger.debug("Génération du rapport PDF")
                    pdf_start = time.perf_counter()
                    # Generate PDF report with questions, answers, and results
                    # Pass client_info to be hashed with reference code as salt
                    # Pass both markdown and data dict to PDF generator
                    # Pass pdf_options to control what gets included in the PDF
                    pdf_path = generate_pdf_report(
                        survey_name=config["survey_name"],
                        survey_version=config.get("survey_version", "Unknown"),
                        questions=questions,
                        answers=inputs,
                        markdown_result=markdown_result,
                        results=result_data,
                        actual_url=actual_url,
                        client_info=client_info,
                        pdf_options=pdf_options,
                    )
                    pdf_duration = time.perf_counter() - pdf_start
                    logger.info(
                        f"Rapport PDF enregistré dans: {pdf_path} (durée {pdf_duration:.3f}s)"
                    )

                    # Add result component updates to the dictionary
                    updates[result_output] = gr.update(
                        value=markdown_result, visible=True
                    )
                    updates[pdf_download] = gr.update(value=pdf_path, visible=True)
                    # Clear any previous warnings on successful completion
                    updates[error_output] = gr.update(visible=False)

                    return updates
                except Exception as e:
                    logger.error(f"Erreur pendant le scoring: {str(e)}", exc_info=True)
                    # Add error updates to the dictionary
                    updates[result_output] = gr.update(visible=False)
                    updates[pdf_download] = gr.update(visible=False)
                    updates[error_output] = gr.update(value=str(e), visible=True)
                    return updates
            else:
                # Not at end yet, hide result components
                updates[result_output] = gr.update(visible=False)
                updates[pdf_download] = gr.update(visible=False)
                updates[error_output] = gr.update(visible=False)
                logger.debug(
                    f"=== go_next FIN === Retour de {len(updates)} mises à jour de composants (pas encore à la fin)"
                )
                return updates

        def go_prev(current_idx, *args):
            """
            Navigue vers la question précédente, en sautant celles dont les conditions ne sont pas remplies.

            Paramètres
            ----------
            current_idx : int
                Index de la question actuelle
            *args : tuple
                Valeurs des widgets de toutes les questions dans l'ordre

            Retourne
            --------
            Dict[gr.components.Component, gr.update]
                Dictionnaire de mises à jour des composants Gradio
            """
            logger.info(
                f"Navigation: Bouton Précédent cliqué depuis la question {current_idx}"
            )
            logger.debug(f"go_prev a reçu {len(args)} arguments")

            # Build context from current values
            context = {}
            for i, q in enumerate(questions):
                context[q["variable"]] = args[i]
                # Anonymity: Do not log actual answer values, only variable name and type
                logger.debug(
                    f"  go_prev arg[{i}] '{q['variable']}' type: {type(args[i]).__name__}"
                )

            new_idx = find_next_valid_question(
                current_idx, questions, context, direction=-1
            )

            logger.debug(f"Navigating from index {current_idx} to {new_idx}")

            # Get display updates as dictionary - widgets keep their current values
            return update_question_display(new_idx, *args)

        def compute_score(*args):
            """
            Calcule le score à partir des réponses du questionnaire.

            Paramètres
            ----------
            *args : tuple
                Index de la question actuelle suivi des valeurs des widgets de toutes les questions

            Retourne
            --------
            tuple
                Tuple contenant (markdown_result, gr.update, gr.update) pour les composants
                de résultats, visibilité du résultat et visibilité des erreurs
            """
            logger.info("Calcul de score manuel demandé")
            try:
                # Map args to inputs dict (skip the first arg which is current_idx)
                current_idx = args[0]
                values = args[1:]

                inputs = {}
                for i, q in enumerate(questions):
                    inputs[q["variable"]] = values[i]

                logger.debug("Exécution de la fonction de scoring")
                # Execute scoring - returns (markdown_str, data_dict, pdf_options)
                markdown_result, result_data, _pdf_options = execute_scoring(
                    scoring_language, scoring_code, inputs
                )
                logger.success("Scoring complété avec succès")

                return (
                    markdown_result,
                    gr.update(visible=True),
                    gr.update(visible=False),
                )
            except Exception as e:
                logger.error(
                    f"Erreur pendant le scoring manuel: {str(e)}", exc_info=True
                )
                return (
                    "",
                    gr.update(visible=True),
                    gr.update(value=str(e), visible=True),
                )

        # Wire up navigation
        logger.debug(
            "Connexion des boutons de navigation et des gestionnaires d'événements"
        )
        all_widget_inputs = [widgets[q["variable"]]["widget"] for q in questions]
        all_row_outputs = [widgets[q["variable"]]["row"] for q in questions]
        all_widget_outputs = [widgets[q["variable"]]["widget"] for q in questions]

        logger.debug("Attachement du gestionnaire de clic du bouton Suivant")
        next_btn.click(
            fn=go_next,
            inputs=[current_question_idx] + all_widget_inputs,
            outputs=all_row_outputs
            + all_widget_outputs
            + [prev_btn, next_btn, current_question_idx]
            + [result_output, pdf_download, error_output],
            show_progress="hidden",
        ).then(
            fn=None,
            js="""() => {
                setTimeout(() => {
                    // Find all question rows within the question container
                    const questionContainer = document.querySelector('.question-container');
                    if (!questionContainer) return;

                    const rows = questionContainer.querySelectorAll('.row');

                    // Find the last visible row (the current question after update)
                    let currentRow = null;
                    for (let i = rows.length - 1; i >= 0; i--) {
                        if (rows[i].offsetParent !== null) {  // Check if row is visible
                            currentRow = rows[i];
                            break;
                        }
                    }

                    // Scroll to the current question, centered in viewport
                    if (currentRow) {
                        currentRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }, 100);
            }""",
        )

        logger.debug("Attachement du gestionnaire de clic du bouton Précédent")
        prev_btn.click(
            fn=go_prev,
            inputs=[current_question_idx] + all_widget_inputs,
            outputs=all_row_outputs
            + all_widget_outputs
            + [prev_btn, next_btn, current_question_idx],
            show_progress="hidden",
        )

        logger.debug("Attachement du gestionnaire de chargement de la démo")
        # Initialize display on load
        demo.load(
            fn=update_question_display,
            inputs=[current_question_idx] + all_widget_inputs,
            outputs=all_row_outputs
            + all_widget_outputs
            + [prev_btn, next_btn, current_question_idx],
            show_progress="hidden",
        )

        logger.debug("Attachement du gestionnaire du bouton de rechargement")
        # Wire up reload button to refresh the page
        reload_btn.click(fn=None, js="() => location.reload()")

    logger.success("Interface du questionnaire créée avec succès")
    return demo
