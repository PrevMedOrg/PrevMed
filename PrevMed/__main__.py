import argparse
import shutil
from loguru import logger
from pathlib import Path

from PrevMed import enable_debug_console
from PrevMed.utils.settings import settings
from PrevMed.utils.io import load_scoring_script
from PrevMed.utils.gui import create_survey_interface
from PrevMed.utils.pdf import TEMP_PDF_DIR


def cli_launcher():
    # Clean up TEMP_PDF_DIR at startup if it exists and is non-empty
    # This ensures we start with a clean slate and don't accumulate old temporary PDFs
    temp_pdf_path = Path(TEMP_PDF_DIR)
    if temp_pdf_path.exists() and any(temp_pdf_path.iterdir()):
        logger.info(
            f"Nettoyage du répertoire PDF temporaire au démarrage: {TEMP_PDF_DIR}"
        )
        try:
            shutil.rmtree(temp_pdf_path)
            logger.success(f"Répertoire PDF temporaire supprimé: {TEMP_PDF_DIR}")
        except Exception as e:
            logger.warning(f"Échec de la suppression du répertoire PDF temporaire: {e}")

    parser = argparse.ArgumentParser(
        description="Générateur dynamique de questionnaires à partir de configuration YAML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exemple:\n  prevmed --survey-yaml specifications.yaml --scoring-script scoring.R",
    )
    parser.add_argument(
        "--survey-yaml",
        type=str,
        required=True,
        help="Chemin vers le fichier YAML de configuration du questionnaire",
    )
    parser.add_argument(
        "--scoring-script",
        type=str,
        required=True,
        help="Chemin vers le script de scoring (.R, .r pour R ou .py, .python pour Python)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activer le niveau de journalisation debug sur la console (la journalisation dans les fichiers est toujours au niveau debug)",
    )
    parser.add_argument(
        "--actual-url",
        type=str,
        default="NA",
        help="L'URL réelle où ce questionnaire est hébergé (sera stockée dans le rapport PDF)",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Ouvrir automatiquement le questionnaire dans un navigateur web (défaut: False)",
    )
    parser.add_argument(
        "--auth",
        type=str,
        required=False,
        help="Pour les tests: utiliser une valeur séparée par une virgule sous la forme utilisateur,motdepasse",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Numéro de port pour le serveur Gradio (défaut: 7860)",
    )
    parser.add_argument(
        "--save-user-data",
        action="store_true",
        help="Sauvegarder les données utilisateur de manière permanente (journaux CSV, données JSON et rapports PDF). Défaut: False - crée uniquement des PDF temporaires pour téléchargement sans enregistrer de données",
    )
    parser.add_argument(
        "--max-threads",
        type=int,
        default=40,
        help="Nombre maximum de threads pour le serveur Gradio (défaut: 40)",
    )
    parser.add_argument(
        "--no-queue",
        action="store_false",
        dest="queue",
        help="Désactiver la mise en file d'attente des requêtes dans Gradio (défaut: file d'attente activée)",
    )
    parser.add_argument(
        "--umami-url",
        type=str,
        required=False,
        help="URL de l'instance Umami analytics (ex: 'https://analytics.example.com')",
    )
    parser.add_argument(
        "--umami-website-id",
        type=str,
        required=False,
        help="ID du site web pour le suivi Umami analytics",
    )

    args = parser.parse_args()

    # Configure global settings
    settings.save_user_data = args.save_user_data
    if settings.save_user_data:
        logger.info(
            "Les données utilisateur seront sauvegardées de manière permanente (journaux CSV, données JSON et rapports PDF)"
        )
    else:
        logger.info(
            "Aucune donnée utilisateur ne sera sauvegardée - uniquement des PDF temporaires pour téléchargement"
        )

    # Enable debug console logging if requested
    if args.debug:
        enable_debug_console()
        logger.debug("Mode debug activé")
    survey_yaml_path = args.survey_yaml
    scoring_script_path = args.scoring_script

    if not Path(survey_yaml_path).exists():
        logger.error(f"Fichier YAML introuvable: {survey_yaml_path}")
        raise SystemExit(f"Erreur: Fichier introuvable: {survey_yaml_path}")

    if not Path(scoring_script_path).exists():
        logger.error(f"Script de scoring introuvable: {scoring_script_path}")
        raise SystemExit(f"Erreur: Fichier introuvable: {scoring_script_path}")

    logger.info(f"Main: Chargement du questionnaire depuis {survey_yaml_path}")

    # Load scoring script
    scoring_language, scoring_code = load_scoring_script(scoring_script_path)

    # fail early in case of R issue
    if scoring_language == "r":
        logger.debug("Vérification de la dépendance rpy2")
        try:
            import rpy2.robjects as ro  # noqa: F401
            from rpy2.robjects import default_converter  # noqa: F401
            from rpy2.robjects.conversion import localconverter  # noqa: F401

            logger.success("rpy2 importé avec succès")

        except ImportError as e:
            logger.error(
                f"Échec de l'import de rpy2. Assurez-vous qu'il est installé correctement. L'erreur était: '{e}'"
            )
            raise Exception(
                f"Échec de l'import de rpy2. Assurez-vous qu'il est installé correctement. L'erreur était: '{e}'"
            ) from e

    demo = create_survey_interface(
        yaml_path=survey_yaml_path,
        scoring_language=scoring_language,
        scoring_code=scoring_code,
        actual_url=args.actual_url,
        umami_url=args.umami_url,
        umami_website_id=args.umami_website_id,
    )
    if args.auth:
        assert "," in args.auth, "No comma found in auth argument"
        authuser, authpass = args.auth.split(",", 1)

    # Enable request queueing if requested (enabled by default for better performance)
    if args.queue:
        logger.info("Main: Activation de la file d'attente des requêtes")
        demo.queue(
            default_concurrency_limit=10,
        )
    else:
        logger.info("Main: File d'attente des requêtes désactivée")

    logger.info("Main: Lancement de l'interface Gradio")
    # relevant docs: https://www.gradio.app/docs/gradio/blocks
    try:
        demo.launch(
            show_api=False,
            quiet=False,
            debug=args.debug,
            max_threads=args.max_threads,
            show_error=True,
            width="100%",
            enable_monitoring=False,
            share=False,
            inbrowser=args.open_browser,
            pwa=False,
            mcp_server=False,
            # ssr_mode=True,  # server side rendering, experimental, trouble exiting at least
            auth=[(authuser, authpass)] if args.auth else None,
            auth_message="Please login" if args.auth else None,
            # server_name=server_name,
            server_port=args.port,
        )
    finally:
        # Clean up TEMP_PDF_DIR at shutdown if it exists
        # This ensures temporary PDFs don't persist after the application closes
        temp_pdf_path = Path(TEMP_PDF_DIR)
        if temp_pdf_path.exists():
            logger.info(
                f"Nettoyage du répertoire PDF temporaire à l'arrêt: {TEMP_PDF_DIR}"
            )
            try:
                shutil.rmtree(temp_pdf_path)
                logger.success(f"Répertoire PDF temporaire supprimé: {TEMP_PDF_DIR}")
            except Exception as e:
                logger.warning(
                    f"Échec de la suppression du répertoire PDF temporaire: {e}"
                )

    logger.info("Main: Interface Gradio fermée")


if __name__ == "__main__":
    cli_launcher()
