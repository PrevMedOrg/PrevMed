from pathlib import Path
import yaml
from typing import Any, Dict, Literal
from loguru import logger

from PrevMed.utils.version import __VERSION__


_FILE_PATH_FIELDS = {"header", "body", "css"}


def _resolve_file_paths(config: Dict[str, Any], base_dir: Path) -> None:
    """Replace file-path references with file contents for known string fields."""
    for field in _FILE_PATH_FIELDS:
        value = config.get(field)
        if isinstance(value, str):
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = base_dir / candidate
            if candidate.exists():
                logger.debug(f"Chargement du contenu de '{field}' depuis: {candidate}")
                config[field] = candidate.read_text(encoding="utf-8")

    # Resolve file paths inside extra_pages entries
    for page in config.get("extra_pages", []):
        for field in _FILE_PATH_FIELDS:
            value = page.get(field)
            if isinstance(value, str):
                candidate = Path(value)
                if not candidate.is_absolute():
                    candidate = base_dir / candidate
                if candidate.exists():
                    logger.debug(f"Chargement du contenu de '{field}' (extra_page) depuis: {candidate}")
                    page[field] = candidate.read_text(encoding="utf-8")


def load_yaml(filepath: str) -> Dict[str, Any]:
    """Charge et parse le fichier de configuration YAML."""
    logger.info(f"Chargement de la configuration YAML depuis: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Check PrevMed version compatibility
        yaml_version = config.get("PrevMed_version")
        if yaml_version and yaml_version != __VERSION__:
            logger.warning(
                f"Le fichier YAML spécifie la version PrevMed {yaml_version} mais la version actuelle est {__VERSION__}. "
                "Veuillez vérifier la compatibilité et envisager de mettre à jour la configuration YAML."
            )

        # Validate question order values
        questions = config.get("questions", [])
        if questions:
            orders = [q.get("order") for q in questions]

            # Check for missing order fields
            if None in orders:
                raise ValueError("Certaines questions n'ont pas de champ 'order'")

            # Check for duplicates
            if len(orders) != len(set(orders)):
                duplicates = [x for x in orders if orders.count(x) > 1]
                raise ValueError(
                    f"Valeurs d'ordre dupliquées trouvées: {set(duplicates)}"
                )

            # Check that orders start at 1
            if min(orders) != 1:
                raise ValueError(
                    f"L'ordre des questions doit commencer à 1, mais l'ordre minimum trouvé est: {min(orders)}"
                )

            # Check that orders end at length
            if max(orders) != len(questions):
                raise ValueError(
                    f"L'ordre des questions doit se terminer à {len(questions)}, mais l'ordre maximum trouvé est: {max(orders)}"
                )

        # Resolve file-path references in string fields
        yaml_dir = Path(filepath).parent
        _resolve_file_paths(config, yaml_dir)

        logger.success(
            f"Configuration YAML chargée avec succès avec {len(config.get('questions', []))} questions"
        )
        return config
    except Exception as e:
        logger.error(f"Échec du chargement du fichier YAML {filepath}: {e}")
        raise


def load_scoring_script(filepath: str) -> tuple[Literal["r", "python"], str]:
    """
    Charge le script de scoring et détecte le langage depuis l'extension du fichier.

    Paramètres
    ----------
    filepath : str
        Chemin vers le fichier de script de scoring

    Retourne
    --------
    tuple[Literal["r", "python"], str]
        Tuple de (langage, contenu_du_code) où langage est 'r' ou 'python'

    Lève
    ----
    ValueError
        Si l'extension du fichier n'est pas reconnue
    """
    logger.info(f"Chargement du script de scoring depuis: {filepath}")

    path = Path(filepath)
    extension = path.suffix.lower()

    # Detect language from extension
    if extension in [".r", ".R"]:
        language = "r"
    elif extension in [".py", ".python"]:
        language = "python"
    else:
        error_msg = f"Extension de fichier non reconnue: '{extension}'. Utilisez .R/.r pour R ou .py/.python pour Python"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Read script content
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        logger.success(f"Script de scoring chargé avec succès (langage: {language})")
        return language, code
    except Exception as e:
        logger.error(f"Échec du chargement du script {filepath}: {e}")
        raise
