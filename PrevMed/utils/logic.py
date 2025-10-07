import gradio as gr
from loguru import logger
from typing import Any, Dict, List


def evaluate_skip_if(condition: str, context: Dict[str, Any]) -> bool:
    """
    Évalue de manière sécurisée une condition avec les valeurs de contexte données.
    Retourne True si la condition est remplie et qu'on doit sauter la question, False sinon (et on doit poser la question).
    Selon ce résultat, la question sera posée ou sautée.

    Si l'évaluation échoue, on lève RuntimeError.

    Paramètres
    ----------
    condition : str
        Expression Python à évaluer pour déterminer si la question doit être sautée
    context : Dict[str, Any]
        Dictionnaire des noms de variables et leurs valeurs actuelles

    Retourne
    --------
    bool
        True si la question doit être sautée, False si elle doit être posée

    Lève
    ----
    RuntimeError
        Si la condition ne peut pas être évaluée
    """
    try:
        # Use restricted eval with only the context variables available
        result = bool(eval(condition, {"__builtins__": {}}, context))
        return result
    except Exception as e:
        logger.warning(f"Échec de l'évaluation de la condition '{condition}': {e}")
        raise RuntimeError(
            f"Échec de l'évaluation de la condition '{condition}': {e}"
        ) from e


def evaluate_valid_if(condition: str, context: Dict[str, Any]) -> bool:
    """
    Évalue de manière sécurisée une condition de validation avec les valeurs de contexte données.
    Retourne True si la condition est remplie et la réponse est valide, False sinon (la réponse est invalide).

    Si l'évaluation échoue, on lève RuntimeError.

    Paramètres
    ----------
    condition : str
        Expression Python à évaluer pour la validation
    context : Dict[str, Any]
        Dictionnaire des noms de variables et leurs valeurs actuelles

    Retourne
    --------
    bool
        True si la réponse est valide, False si invalide

    Lève
    ----
    RuntimeError
        Si la condition ne peut pas être évaluée
    """
    try:
        # Use restricted eval with only the context variables available
        result = bool(eval(condition, {"__builtins__": {}}, context))
        return result
    except Exception as e:
        logger.warning(
            f"Échec de l'évaluation de la condition valid_if '{condition}': {e}"
        )
        raise RuntimeError(
            f"Échec de l'évaluation de la condition valid_if '{condition}': {e}"
        ) from e


def find_next_valid_question(
    current_idx: int, questions: List[Dict], context: Dict[str, Any], direction: int = 1
) -> int:
    """
    Trouve l'index de la prochaine question valide en fonction des conditions de saut.

    Paramètres
    ----------
    current_idx : int
        Index de la question actuelle
    questions : List[Dict]
        Liste de toutes les questions
    context : Dict[str, Any]
        Valeurs actuelles de toutes les variables
    direction : int
        1 pour suivant, -1 pour précédent

    Retourne
    --------
    int
        Index de la prochaine question valide, ou current_idx si aucune n'est trouvée
    """
    direction_str = "suivante" if direction == 1 else "précédente"
    logger.debug(
        f"Recherche de la {direction_str} question valide depuis l'index {current_idx}"
    )

    idx = current_idx + direction

    while 0 <= idx < len(questions):
        if "skip_if" not in questions[idx]:
            logger.debug(
                f"Question valide {direction_str} trouvée à l'index {idx} car clé 'skip_if' absente."
            )
            return idx

        condition = questions[idx]["skip_if"]
        if not evaluate_skip_if(condition, context):
            logger.debug(
                f"Question valide {direction_str} trouvée à l'index {idx}. 'skip_if' a retourné False."
            )
            return idx
        idx += direction

    # Return boundary index if no valid question found
    # For forward: return idx past end to trigger scoring
    # For backward: return 0 to go to first question
    final_idx = idx if idx >= len(questions) else 0
    logger.debug(
        f"Aucune question valide {direction_str} trouvée, retour de l'index {final_idx}"
    )
    return final_idx
