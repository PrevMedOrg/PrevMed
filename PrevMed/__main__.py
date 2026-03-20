import argparse
from loguru import logger
from pathlib import Path

from PrevMed import enable_debug_console
from PrevMed.utils.settings import settings
from PrevMed.utils.io import load_scoring_script
from PrevMed.utils.gui import create_survey_interface  # gui is now a package


def parse_extra_launch_kwargs(unknown_args):
    """
    Parse unknown command-line arguments into kwargs for demo.launch().

    Supports formats like:
    - --key value (string/int/float)
    - --flag (boolean True)
    - --no-flag (boolean False)

    Parameters
    ----------
    unknown_args : list
        List of unknown command-line arguments

    Returns
    -------
    dict
        Dictionary of kwargs to pass to demo.launch()
    """
    kwargs = {}
    i = 0
    while i < len(unknown_args):
        arg = unknown_args[i]
        if arg.startswith("--"):
            key = arg[2:].replace("-", "_")

            # Check if this is a boolean flag (no value follows)
            if i + 1 >= len(unknown_args) or unknown_args[i + 1].startswith("--"):
                # It's a boolean flag
                if key.startswith("no_"):
                    kwargs[key[3:]] = False
                else:
                    kwargs[key] = True
                i += 1
            else:
                # It has a value
                value = unknown_args[i + 1]
                # Try to convert to appropriate type
                try:
                    # Try int first
                    kwargs[key] = int(value)
                except ValueError:
                    try:
                        # Try float
                        kwargs[key] = float(value)
                    except ValueError:
                        # Keep as string
                        kwargs[key] = value
                i += 2
        else:
            i += 1

    return kwargs


def cli_launcher():
    parser = argparse.ArgumentParser(
        description="Générateur dynamique de questionnaires à partir de configuration YAML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemple:\n"
            "  prevmed --survey-yaml specifications.yaml --scoring-script scoring.R\n\n"
            "Arguments supplémentaires:\n"
            "  Tous les arguments non reconnus seront passés à demo.launch().\n"
            "  Voir la documentation Gradio pour les arguments supportés:\n"
            "  https://www.gradio.app/docs/gradio/blocks"
        ),
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
        action="append",
        required=False,
        help="Pour les tests: utiliser une valeur séparée par une virgule sous la forme utilisateur,motdepasse. Peut être spécifié plusieurs fois pour définir plusieurs paires login/mot de passe",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Numéro de port pour le serveur Gradio (défaut: 7860)",
    )
    parser.add_argument(
        "--server-name",
        type=str,
        default="0.0.0.0",
        help="Nom du serveur pour le serveur Gradio (défaut: 0.0.0.0)",
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
    parser.add_argument(
        "--umami-ignore-dnt",
        action="store_false",
        dest="umami_do_not_track",
        default=True,
        help="Ignorer les préférences 'Do Not Track' du navigateur et effectuer le suivi même si DNT est activé (défaut: respecter DNT)",
    )
    parser.add_argument(
        "--terms-md",
        type=str,
        required=True,
        # Mandatory for GDPR compliance: users must be shown the legal notice
        # (data controller identity, processing purposes, retention period, etc.)
        # before submitting any health data. The app crashes at startup if missing
        # rather than silently running without legal cover.
        help="(OBLIGATOIRE) Chemin vers un fichier Markdown contenant les mentions légales RGPD (responsable du traitement, finalités, durée de conservation…) à afficher en bas de page. L'application refuse de démarrer sans ce fichier.",
    )

    args, unknown_args = parser.parse_known_args()

    # Parse extra kwargs for demo.launch()
    extra_launch_kwargs = parse_extra_launch_kwargs(unknown_args)
    if extra_launch_kwargs:
        logger.info(
            f"Arguments supplémentaires pour demo.launch(): {extra_launch_kwargs}"
        )

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

    # Load the mandatory GDPR legal terms file.
    # --terms-md is required; argparse already rejects missing values.
    # We still check file existence here to give a clear error message.
    terms_md_path = Path(args.terms_md)
    if not terms_md_path.exists():
        logger.error(f"Fichier de mentions légales introuvable: {args.terms_md}")
        raise SystemExit(f"Erreur: Fichier introuvable: {args.terms_md}")
    terms_md_content = terms_md_path.read_text(encoding="utf-8")
    logger.info(f"Mentions légales chargées depuis: {args.terms_md}")

    demo = create_survey_interface(
        yaml_path=survey_yaml_path,
        scoring_language=scoring_language,
        scoring_code=scoring_code,
        actual_url=args.actual_url,
        umami_url=args.umami_url,
        umami_website_id=args.umami_website_id,
        umami_do_not_track=args.umami_do_not_track,
        terms_md_content=terms_md_content,
    )

    # Process multiple auth pairs if provided
    auth_pairs = None
    if args.auth:
        auth_pairs = []
        for auth_str in args.auth:
            assert "," in auth_str, f"No comma found in auth argument: {auth_str}"
            authuser, authpass = auth_str.split(",", 1)
            auth_pairs.append((authuser, authpass))
        logger.info(
            f"Main: {len(auth_pairs)} paire(s) d'authentification configurée(s)"
        )

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
    demo.launch(
        footer_links=[],  # remove link to api / gradio / settings
        quiet=False,
        debug=args.debug,
        max_threads=args.max_threads,
        show_error=True,
        # width="100%",
        enable_monitoring=False,
        share=False,
        inbrowser=args.open_browser,
        pwa=False,
        mcp_server=False,
        # ssr_mode=True,  # server side rendering, experimental, trouble exiting at least
        auth=auth_pairs,
        auth_message="Please login" if auth_pairs else None,
        server_name=args.server_name,
        server_port=args.port,
        # /dev/shm is RAM-based tmpfs used for PDF downloads to avoid disk writes
        # Gradio needs explicit permission to serve files from this directory
        allowed_paths=["/dev/shm"],
        **extra_launch_kwargs,
    )

    logger.info("Main: Interface Gradio fermée")


if __name__ == "__main__":
    cli_launcher()
