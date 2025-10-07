"""
Utilitaires de génération de rapports PDF pour les applications de questionnaires.

Gère la création de rapports PDF formatés contenant les réponses au questionnaire et les résultats de scoring.
Utilise la bibliothèque ReportLab qui fournit un support Unicode natif et des capacités de formatage avancées.
"""

import time
import random
import string
import json
import gzip
import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, List
from filelock import FileLock, Timeout
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from loguru import logger

from PrevMed.utils.settings import settings
from PrevMed.utils.version import __VERSION__

# Character sets for generating human-readable reference codes
# Exclude ambiguous characters: no 0/O, no 1/I/l for easier human reading
UNAMBIGUOUS_LETTERS = "ABCDFGHJKLMNPQRSTUVWXY"  # 22 letters (no I, O, E, Z)
UNAMBIGUOUS_DIGITS = "23456789"  # 8 digits (no 0, 1)
UNAMBIGUOUS_CHARS = UNAMBIGUOUS_LETTERS + UNAMBIGUOUS_DIGITS  # 32 total chars

# Base directory to store compressed JSON data files (PDFs are temporary)
DATA_OUTPUT_DIR = "survey_data"

# Directory for temporary PDF files (cleaned up automatically)
TEMP_PDF_DIR = "temp_pdfs"


def cleanup_old_pdfs(temp_dir: str, max_age_seconds: int = 3600) -> None:
    """
    Supprime les fichiers PDF plus anciens que l'âge spécifié du répertoire temporaire.

    Cette fonction est appelée avant chaque génération de PDF pour s'assurer que les fichiers temporaires
    ne s'accumulent pas indéfiniment. L'âge par défaut est de 1 heure (3600 secondes).

    Paramètres
    ----------
    temp_dir : str
        Chemin vers le répertoire PDF temporaire
    max_age_seconds : int, optionnel
        Âge maximum en secondes avant qu'un fichier ne soit supprimé (par défaut : 3600 = 1 heure)
    """
    temp_path = Path(temp_dir)

    # Skip if directory doesn't exist yet
    if not temp_path.exists():
        logger.debug(f"Le répertoire PDF temporaire n'existe pas encore: {temp_dir}")
        return

    current_time = time.time()
    deleted_count = 0
    error_count = 0

    # Iterate over all PDF files in the directory
    for pdf_file in temp_path.glob("*.pdf"):
        try:
            # Get file modification time
            file_age = current_time - pdf_file.stat().st_mtime

            # Delete if older than max_age_seconds
            if file_age > max_age_seconds:
                pdf_file.unlink()
                deleted_count += 1
                logger.debug(
                    f"PDF temporaire ancien supprimé: {pdf_file.name} (âge: {file_age / 60:.1f} minutes)"
                )
        except Exception as e:
            error_count += 1
            logger.warning(
                f"Échec de la suppression du PDF temporaire {pdf_file.name}: {e}"
            )

    if deleted_count > 0:
        logger.info(
            f"Nettoyage de {deleted_count} PDF temporaire(s) plus ancien(s) que {max_age_seconds / 60:.1f} minutes"
        )
    if error_count > 0:
        logger.warning(f"Échec de la suppression de {error_count} PDF temporaire(s)")


def append_to_csv_log(
    csv_file_path: str,
    reference_code: str,
    timestamp: int,
    results: Dict[str, str],
    json_data: Dict[str, Any],
    client_info: Dict[str, Any] = None,
) -> None:
    """
    Ajoute de manière atomique les données de soumission du questionnaire au fichier journal CSV.

    Utilise filelock pour le verrouillage de fichiers multiplateforme et les écritures atomiques afin d'éviter
    la corruption des données en cas d'accès concurrent. Crée le CSV avec les en-têtes s'il n'existe pas.

    Paramètres
    ----------
    csv_file_path : str
        Chemin complet vers le fichier journal CSV
    reference_code : str
        Code de référence lisible par l'humain (par exemple, "ABC-XYZ")
    timestamp : int
        Horodatage Unix au moment de la soumission du questionnaire
    results : Dict[str, str]
        Dictionnaire contenant les résultats de scoring (converti depuis table_data)
    json_data : Dict[str, Any]
        Données JSON complètes (doit contenir la clé 'answers' pour le calcul du hash)
    client_info : Dict[str, Any], optionnel
        Dictionnaire d'informations client (chaque clé sera hachée individuellement pour la confidentialité)
    """
    logger.debug(
        f"Ajout de la soumission {reference_code} au journal CSV à {csv_file_path}"
    )

    # Create lock file for atomic access
    csv_lock_file = csv_file_path + ".lock"
    lock = FileLock(csv_lock_file, timeout=10)

    # Define temp file path early so exception handler can always reference it
    temp_csv = csv_file_path + ".tmp"

    try:
        with lock:
            # Check if CSV exists to determine if we need to write headers
            file_exists = Path(csv_file_path).exists()

            if file_exists:
                # Read existing CSV to get row count and verify headers
                with open(csv_file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)
                    existing_headers = reader.fieldnames or []

                # Check if rotation is needed (CSV has grown too large)
                # Rotation keeps lock hold time bounded by limiting CSV size to 1000 rows
                # This ensures performance remains acceptable under high concurrent load
                if len(existing_rows) >= 1000:
                    # Move current CSV to archive with timestamp for permanent storage
                    csv_dir = Path(csv_file_path).parent
                    archive_filename = f"survey_submissions_{timestamp}.csv"
                    archive_path = csv_dir / archive_filename
                    Path(csv_file_path).rename(archive_path)
                    logger.info(
                        f"CSV pivoté: déplacé {len(existing_rows)} lignes vers {archive_path}"
                    )

                    # Start fresh with new CSV file
                    # Reset rows but keep headers to maintain schema consistency
                    existing_rows = []
                    row_number = 1
                else:
                    row_number = len(existing_rows) + 1
            else:
                row_number = 1
                existing_headers = []

            # Compute cropped hash of answers only for duplicate detection
            # Use first 12 characters of SHA256 hash (sufficient for duplicate detection)
            # Hash only answers to detect identical survey responses regardless of metadata
            answers_str = json.dumps(json_data["answers"], sort_keys=True)
            full_hash = hashlib.sha256(answers_str.encode("utf-8")).hexdigest()
            cropped_hash = full_hash[:12]

            # Human-readable datetime
            datetime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

            # Build row data
            row_data = {
                "reference_code": reference_code,
                "row_number": row_number,
                "timestamp_unix": timestamp,
                "datetime": datetime_str,
            }

            # Add scoring results (dynamic columns based on results dict)
            # Results dict is created from table data by combining row labels with column headers
            for key, value in results.items():
                # Values are already strings from table data, store as-is
                row_data[key] = str(value)

            # Compute individual hashes for each client_info key for finer-grained duplicate detection
            # Each client attribute gets its own hash column to allow targeted analysis
            client_hashes = {}
            if client_info:
                for key, value in client_info.items():
                    try:
                        # Create deterministic string and hash with reference code as salt
                        value_str = (
                            json.dumps(value, sort_keys=True)
                            if not isinstance(value, str)
                            else value
                        )
                        salted_data = f"{reference_code}:{value_str}"
                        hash_value = hashlib.sha256(
                            salted_data.encode("utf-8")
                        ).hexdigest()[:12]
                        client_hashes[f"{key}_hash"] = hash_value
                    except Exception as e:
                        logger.warning(
                            f"Échec du hachage de la clé client_info '{key}': {e}"
                        )
                        client_hashes[f"{key}_hash"] = "NA"

                logger.debug(
                    f"Generated {len(client_hashes)} individual client hashes for reference {reference_code}"
                )

            # Add answers_hash
            row_data["answers_hash"] = cropped_hash

            # Add all individual client hashes
            for hash_key, hash_value in client_hashes.items():
                row_data[hash_key] = hash_value

            logger.debug(
                f"Données de ligne CSV pour {reference_code}: answers_hash={cropped_hash}, client_hashes={list(client_hashes.keys())}"
            )

            # Determine headers - must include all columns
            if file_exists and existing_headers:
                # Use existing headers but ensure new result keys are appended
                fieldnames = list(existing_headers)
                for key in row_data.keys():
                    if key not in fieldnames:
                        # Hash keys (answers_hash and client_*_hash) should go at the end
                        # Scoring result keys should go before answers_hash
                        if key == "answers_hash" or key.endswith("_hash"):
                            # Hash keys go at the end
                            fieldnames.append(key)
                        elif "answers_hash" in fieldnames:
                            # Scoring result keys go before answers_hash
                            hash_idx = fieldnames.index("answers_hash")
                            fieldnames.insert(hash_idx, key)
                        else:
                            # No answers_hash yet, append at end
                            fieldnames.append(key)
            else:
                # First time - create header order
                # Fixed columns first, then scoring results, then hashes
                fixed_cols = [
                    "reference_code",
                    "row_number",
                    "timestamp_unix",
                    "datetime",
                ]
                scoring_cols = [k for k in results.keys()]
                hash_cols = ["answers_hash"] + [
                    k
                    for k in row_data.keys()
                    if k.endswith("_hash") and k != "answers_hash"
                ]
                fieldnames = fixed_cols + scoring_cols + hash_cols

            # Write to temporary file atomically
            write_mode = "w"  # Always write mode for atomic operation

            # If we have existing rows, copy them first; otherwise start fresh
            # This handles both normal appends and post-rotation scenarios
            if len(existing_rows) > 0:
                logger.debug(f"Writing {len(existing_rows)} existing rows to CSV")
                with open(temp_csv, write_mode, encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    # Write existing rows (ensuring all fields exist)
                    for existing_row in existing_rows:
                        # Fill in missing fields with empty string
                        complete_row = {
                            field: existing_row.get(field, "") for field in fieldnames
                        }
                        writer.writerow(complete_row)
                    # Write new row
                    writer.writerow(row_data)
            else:
                # New file or post-rotation - just write header and new row
                logger.debug("Creating new CSV log file")
                with open(temp_csv, write_mode, encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerow(row_data)

            # Atomic rename - replaces old file with new one
            Path(temp_csv).replace(csv_file_path)
            logger.success(
                f"Journal CSV mis à jour: ajout de la ligne {row_number} pour la référence {reference_code}"
            )

    except Timeout:
        # Lock timeout - save to fallback file to avoid data loss
        # This ensures we never lose data even under high concurrent load
        logger.warning(
            f"Délai d'expiration du verrou pour le journal CSV {csv_file_path} - sauvegarde dans le fichier de secours"
        )

        # Generate fallback filename with timestamp and random suffix for uniqueness
        # Format: survey_submissions_fallback_{timestamp}_{random}.csv
        # Random suffix prevents conflicts if multiple timeouts occur at same timestamp
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=6)
        )
        csv_dir = Path(csv_file_path).parent
        fallback_filename = (
            f"survey_submissions_fallback_{timestamp}_{random_suffix}.csv"
        )
        fallback_path = csv_dir / fallback_filename

        try:
            # Compute cropped hash of answers only for duplicate detection
            answers_str = json.dumps(json_data["answers"], sort_keys=True)
            full_hash = hashlib.sha256(answers_str.encode("utf-8")).hexdigest()
            cropped_hash = full_hash[:12]

            # Human-readable datetime
            datetime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

            # Build row data (same as main path)
            row_data = {
                "reference_code": reference_code,
                "row_number": 1,  # Always 1 for fallback files
                "timestamp_unix": timestamp,
                "datetime": datetime_str,
            }

            # Add scoring results
            # Values are already strings from table data, store as-is
            for key, value in results.items():
                row_data[key] = str(value)

            # Compute individual client hashes
            client_hashes = {}
            if client_info:
                for key, value in client_info.items():
                    try:
                        value_str = (
                            json.dumps(value, sort_keys=True)
                            if not isinstance(value, str)
                            else value
                        )
                        salted_data = f"{reference_code}:{value_str}"
                        hash_value = hashlib.sha256(
                            salted_data.encode("utf-8")
                        ).hexdigest()[:12]
                        client_hashes[f"{key}_hash"] = hash_value
                    except Exception as e:
                        logger.warning(f"Failed to hash client_info key '{key}': {e}")
                        client_hashes[f"{key}_hash"] = "NA"

            # Add answers_hash
            row_data["answers_hash"] = cropped_hash

            # Add all individual client hashes
            for hash_key, hash_value in client_hashes.items():
                row_data[hash_key] = hash_value

            # Create fieldnames in consistent order
            fixed_cols = [
                "reference_code",
                "row_number",
                "timestamp_unix",
                "datetime",
            ]
            scoring_cols = [k for k in results.keys()]
            hash_cols = ["answers_hash"] + [
                k
                for k in row_data.keys()
                if k.endswith("_hash") and k != "answers_hash"
            ]
            fieldnames = fixed_cols + scoring_cols + hash_cols

            # Write fallback CSV with just this row
            with open(fallback_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row_data)

            logger.success(
                f"Données sauvegardées dans le CSV de secours: {fallback_path} (référence: {reference_code})"
            )

        except Exception as fallback_error:
            logger.error(
                f"Échec de la sauvegarde dans le CSV de secours: {str(fallback_error)}",
                exc_info=True,
            )
            raise

    except Exception as e:
        logger.error(f"Échec de la mise à jour du journal CSV: {str(e)}")
        # Clean up temp file if it exists
        if Path(temp_csv).exists():
            try:
                Path(temp_csv).unlink()
            except:
                pass
        raise


def generate_pdf_report(
    survey_name: str,
    survey_version: str,
    questions: List[Dict],
    answers: Dict[str, Any],
    markdown_result: str,
    results: List[List[str]],
    actual_url: str = "NA",
    client_info: Dict[str, Any] = None,
    pdf_options: Dict[str, bool] = None,
) -> str:
    """
    Génère un rapport PDF contenant les questions du questionnaire, les réponses et les résultats de scoring.

    Enregistre un fichier JSON compressé avec toutes les données du rapport sur le disque de manière permanente.
    Crée le PDF en tant que fichier temporaire pour le téléchargement patient (non sauvegardé de manière permanente).

    Paramètres
    ----------
    survey_name : str
        Nom du questionnaire
    survey_version : str
        Version du questionnaire
    questions : List[Dict]
        Liste de toutes les configurations de questions
    answers : Dict[str, Any]
        Dictionnaire associant les noms de variables aux réponses de l'utilisateur
    markdown_result : str
        Résultats de scoring formatés en Markdown provenant de la fonction de scoring
    results : List[List[str]]
        Données de table de résultats (première liste = headers, suivantes = lignes de données)
    actual_url : str, optionnel
        L'URL réelle où ce questionnaire est hébergé
    client_info : Dict[str, Any], optionnel
        Dictionnaire d'informations client (sera haché avec le code de référence comme sel pour la confidentialité)
    pdf_options : Dict[str, bool], optionnel
        Options contrôlant ce qui est inclus dans le PDF (include_md_in_pdf, include_data_in_pdf).
        Par défaut, les deux sont True si non spécifiés.

    Retourne
    --------
    str
        Chemin vers le fichier PDF temporaire pour téléchargement
    """
    logger.info("Début de la génération du rapport PDF")
    logger.debug(f"Questionnaire: {survey_name} v{survey_version}")

    # Default to including both markdown and data if not specified
    # This allows R/Python scoring functions to control PDF content granularly
    if pdf_options is None:
        pdf_options = {"include_md_in_pdf": True, "include_data_in_pdf": True}

    include_md = pdf_options.get("include_md_in_pdf", True)
    include_data = pdf_options.get("include_data_in_pdf", True)

    logger.debug(
        f"Options PDF: include_md_in_pdf={include_md}, include_data_in_pdf={include_data}"
    )

    try:
        # Clean up old temporary PDFs before generating new one
        # This ensures temp directory doesn't accumulate files indefinitely
        cleanup_old_pdfs(TEMP_PDF_DIR, max_age_seconds=3600)

        # Only create directories and setup logging if user data saving is enabled
        if settings.save_user_data:
            # Create hierarchical directory structure for CSV:
            # survey_data/csv/{__VERSION__}/{survey_name}_{survey_version}/
            csv_dir = (
                Path(DATA_OUTPUT_DIR)
                / "csv"
                / __VERSION__
                / f"{survey_name}_{survey_version}"
            )
            csv_dir.mkdir(parents=True, exist_ok=True)
            csv_file_path = csv_dir / "survey_submissions.csv"
            logger.debug(f"Chemin du fichier journal CSV: {csv_file_path}")

            # Create data output directory for JSON files if it doesn't exist
            Path(DATA_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Répertoire de sortie des données JSON: {DATA_OUTPUT_DIR}")
        else:
            logger.debug(
                "Sauvegarde des données utilisateur désactivée - omission de la création du répertoire"
            )

        # Generate human-readable reference code in format XXX-YYY (like boarding pass)
        # Using unambiguous characters to avoid confusion when memorizing/reading
        # Each 3-character group must contain at least one letter and one number
        # This ensures variety and reduces likelihood of inappropriate word patterns

        def generate_valid_code_part() -> str:
            """Génère une partie de code de 3 caractères avec au moins une lettre et un chiffre."""
            while True:
                part = "".join(random.choices(UNAMBIGUOUS_CHARS, k=3))
                # Check if part contains at least one letter and one number
                has_letter = any(c in UNAMBIGUOUS_LETTERS for c in part)
                has_number = any(c in UNAMBIGUOUS_DIGITS for c in part)
                if has_letter and has_number:
                    return part

        # Generate both parts of the reference code
        ref_code_part1 = generate_valid_code_part()
        ref_code_part2 = generate_valid_code_part()
        reference_code = f"{ref_code_part1}-{ref_code_part2}"

        # Include timestamp for uniqueness and reference code for human readability
        timestamp = int(time.time())

        # Compute individual hashes for each client_info key for privacy-preserving duplicate detection
        # Each attribute is hashed separately to allow finer-grained analysis
        client_hashes = {}
        if client_info:
            for key, value in client_info.items():
                try:
                    # Create deterministic string and hash with reference code as salt
                    value_str = (
                        json.dumps(value, sort_keys=True)
                        if not isinstance(value, str)
                        else value
                    )
                    salted_data = f"{reference_code}:{value_str}"
                    hash_value = hashlib.sha256(
                        salted_data.encode("utf-8")
                    ).hexdigest()[:12]
                    client_hashes[f"{key}_hash"] = hash_value
                except Exception as e:
                    logger.warning(
                        f"Échec du hachage de la clé client_info '{key}': {e}"
                    )
                    client_hashes[f"{key}_hash"] = "NA"

                logger.info(
                    f"Généré {len(client_hashes)} hachages client individuels pour la référence {reference_code}"
                )
        else:
            logger.info(
                f"Aucun client_info fourni - aucun hachage client ne sera généré pour la référence {reference_code}"
            )

        # Convert table data to dict for CSV logging
        # Table format: [["Header1", "Header2"], ["Row1Col1", "Row1Col2"], ...]
        # Dict format: {"Row1Col1_Header2": "Row1Col2", ...}
        results_dict = {}
        if len(results) > 0:
            headers = results[0]
            for row in results[1:]:
                # Create composite keys combining row label (first column) with column headers
                row_label = (
                    row[0]
                    .replace("/", "_")
                    .replace(" ", "_")
                    .replace("é", "e")
                    .replace("è", "e")
                    .replace("à", "a")
                    .replace("ô", "o")
                )
                for i in range(1, len(row)):
                    col_header = (
                        headers[i]
                        .replace("/", "_")
                        .replace(" ", "_")
                        .replace("é", "e")
                        .replace("è", "e")
                        .replace("à", "a")
                        .replace("ô", "o")
                    )
                    key = f"{row_label}_{col_header}"
                    results_dict[key] = row[i]

        logger.debug(
            f"Converted table data to dict with {len(results_dict)} keys for CSV logging"
        )

        # Only save JSON and CSV if user data saving is enabled
        if settings.save_user_data:
            # Save compressed JSON with survey data permanently
            json_filename = f"{timestamp}_{reference_code}.json.gz"
            json_filepath = Path(DATA_OUTPUT_DIR) / json_filename

            logger.debug(
                f"Sauvegarde des données JSON compressées dans: {json_filepath}"
            )

            # Create data dictionary with survey responses and results
            # Questions are not saved to reduce storage size (they can be retrieved from YAML)
            # Individual client hashes are stored (not raw client info) for privacy-preserving duplicate detection
            # Store both table format (for PDF) and dict format (for CSV compatibility)
            data = {
                "survey_name": survey_name,
                "survey_version": survey_version,
                "prevmed_version": __VERSION__,
                "answers": answers,
                "results_table": results,  # Table format for PDF
                "results_dict": results_dict,  # Dict format for CSV
                "actual_url": actual_url,
                "reference_code": reference_code,
                "timestamp": timestamp,
                "client_hashes": client_hashes,
            }

            # Save as compressed JSON
            with gzip.open(json_filepath, "wt", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            logger.success(
                f"Données JSON compressées sauvegardées dans: {json_filepath}"
            )

            # Update CSV log with submission data
            # This is done after JSON save to ensure we have the data file
            try:
                append_to_csv_log(
                    csv_file_path=csv_file_path,
                    reference_code=reference_code,
                    timestamp=timestamp,
                    results=results_dict,  # Use dict format for CSV
                    json_data=data,
                    client_info=client_info,
                )
            except Exception as e:
                # Log error but don't fail PDF generation
                logger.error(
                    f"Échec de la mise à jour du journal CSV, poursuite avec le PDF: {str(e)}"
                )
        else:
            logger.debug(
                "Sauvegarde des données utilisateur désactivée - omission de la journalisation JSON et CSV"
            )

        # Create PDF file - either permanent or temporary based on settings
        if settings.save_user_data:
            # Save PDF permanently alongside JSON data
            pdf_filename = f"{timestamp}_{reference_code}.pdf"
            pdf_filepath = Path(DATA_OUTPUT_DIR) / pdf_filename
            logger.debug(
                f"Génération du PDF permanent: {pdf_filepath} avec le code de référence: {reference_code}"
            )
        else:
            # Create temporary PDF in local directory for download only (not permanently saved)
            # Old PDFs are cleaned up automatically (see cleanup_old_pdfs above)
            temp_dir = Path(TEMP_PDF_DIR)
            temp_dir.mkdir(parents=True, exist_ok=True)

            pdf_filename = f"survey_{reference_code}_{timestamp}.pdf"
            pdf_filepath = temp_dir / pdf_filename
            logger.debug(
                f"Génération du PDF temporaire: {pdf_filepath} avec le code de référence: {reference_code}"
            )

        # Create PDF using ReportLab with explicit compression enabled
        pdf = SimpleDocTemplate(str(pdf_filepath), pagesize=A4)
        pdf.pageCompression = 1  # Explicitly enable PDF compression
        story = []  # Container for PDF elements
        styles = getSampleStyleSheet()

        # Create custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#000000"),
            spaceAfter=12,
            alignment=TA_CENTER,
        )
        reference_style = ParagraphStyle(
            "ReferenceCode",
            parent=styles["Normal"],
            fontSize=14,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#006400"),  # Dark green for emphasis
            spaceAfter=10,
            alignment=TA_CENTER,
        )
        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#666666"),
            spaceAfter=6,
            fontName="Helvetica-Oblique",
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceAfter=10,
        )
        question_style = ParagraphStyle(
            "Question",
            parent=styles["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            spaceAfter=4,
        )
        answer_style = ParagraphStyle(
            "Answer",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=8,
        )

        # Title
        story.append(Paragraph(survey_name, title_style))
        story.append(Spacer(1, 3 * mm))

        # Reference Code - displayed prominently for patient to memorize
        story.append(
            Paragraph(f"<b>Code de référence : {reference_code}</b>", reference_style)
        )
        story.append(Spacer(1, 5 * mm))

        # Version information
        story.append(
            Paragraph(f"Version du questionnaire : {survey_version}", subtitle_style)
        )
        story.append(
            Paragraph(
                f"Version PrevMed : {__VERSION__}",
                subtitle_style,
            )
        )
        story.append(Spacer(1, 3 * mm))

        # Survey URL if provided
        if actual_url:
            story.append(
                Paragraph(f"URL du questionnaire : {actual_url}", subtitle_style)
            )
            story.append(Spacer(1, 3 * mm))

        # Timestamp
        story.append(
            Paragraph(
                f"Généré le : {time.strftime('%d/%m/%Y à %H:%M:%S')}", subtitle_style
            )
        )
        story.append(Spacer(1, 10 * mm))

        # Scoring Results section - conditionally include based on pdf_options
        # Only add section heading if at least one of markdown or data will be shown
        if include_md or include_data:
            story.append(Paragraph("Résultats du questionnaire", heading_style))
            story.append(Spacer(1, 5 * mm))

        # Conditionally include markdown results based on include_md_in_pdf
        if include_md:
            # Create a custom style for the markdown text
            # Using Paragraph instead of Preformatted for better cross-viewer compatibility
            markdown_style = ParagraphStyle(
                "MarkdownResults",
                parent=styles["Normal"],
                fontSize=10,
                fontName="Courier",
                textColor=colors.black,
                backColor=None,  # Explicitly no background
                leftIndent=10 * mm,
                spaceAfter=2 * mm,
            )

            # Render markdown line by line using Paragraph for robust rendering
            # This avoids Preformatted which can have viewer-specific rendering issues
            # Wrap text in explicit color tags to ensure black text in all PDF viewers (including Okular)
            for line in markdown_result.split("\n"):
                if line.strip():
                    # Escape HTML special characters manually
                    safe_line = (
                        line.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    # Wrap in explicit font color tag for maximum PDF viewer compatibility
                    # This ensures text renders as black even in viewers like Okular that may ignore style textColor
                    colored_line = f'<font color="black">{safe_line}</font>'
                    story.append(Paragraph(colored_line, markdown_style))
                else:
                    # Empty line - add small spacer to preserve structure
                    story.append(Spacer(1, 2 * mm))

            story.append(Spacer(1, 3 * mm))

        # Conditionally include data table based on include_data_in_pdf
        if include_data:
            # Create table from results data for structured data display
            # Results is already in table format: [[headers], [row1], [row2], ...]
            # This provides a machine-readable format alongside the markdown
            results_data = results  # Use table data directly

            # Calculate column widths dynamically based on number of columns
            num_cols = len(results_data[0]) if len(results_data) > 0 else 2
            available_width = 180 * mm  # Total available width
            col_width = available_width / num_cols
            col_widths = [col_width] * num_cols

            # Create and style the results table
            results_table = Table(results_data, colWidths=col_widths)
            results_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ]
                )
            )
            story.append(results_table)

        # Questions and Answers section
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph("Réponses au questionnaire", heading_style))
        story.append(Spacer(1, 5 * mm))

        for iq, q in enumerate(questions):
            var_name = q["variable"]
            answer = answers.get(var_name)

            # Question text - show ALL questions regardless of whether they were answered
            question_text = f"Q{iq + 1}: {q['question']}"
            story.append(Paragraph(question_text, question_style))

            # Answer formatting - handle all value types including None
            if isinstance(answer, bool):
                answer_text = f"R : {'Oui' if answer else 'Non'}"
            elif answer is None:
                answer_text = "R : Non répondu"
            else:
                answer_text = f"R : {answer}"

            story.append(Paragraph(answer_text, answer_style))
            story.append(Spacer(1, 3 * mm))

        # Build the PDF
        logger.debug("Construction du document PDF")
        pdf_build_start = time.perf_counter()
        pdf.build(story)
        pdf_build_duration = time.perf_counter() - pdf_build_start
        logger.debug(f"Document PDF construit en {pdf_build_duration:.3f}s")

        if settings.save_user_data:
            logger.success(f"Rapport PDF permanent sauvegardé: {pdf_filepath}")
            logger.info(
                f"Données permanentes sauvegardées en JSON compressé: {json_filepath}"
            )
        else:
            logger.success(f"Rapport PDF temporaire généré: {pdf_filepath}")
            logger.info(
                "Aucune donnée utilisateur n'a été sauvegardée de manière permanente"
            )
        return pdf_filepath

    except Exception as e:
        # If PDF generation fails, raise a clear error message
        logger.error(f"Échec de la génération du rapport PDF: {str(e)}")
        raise RuntimeError(
            f"Failed to generate PDF report: {str(e)}. "
            "This may be due to unsupported characters in the survey text."
        ) from e
