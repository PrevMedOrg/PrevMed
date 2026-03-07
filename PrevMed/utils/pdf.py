"""
Utilitaires de génération de rapports PDF pour les applications de questionnaires.

Gère la création de rapports PDF formatés contenant les réponses au questionnaire et les résultats de scoring.
Utilise la bibliothèque ReportLab qui fournit un support Unicode natif et des capacités de formatage avancées.
"""

import io
import time
import random
import string
import json
import gzip
import csv
import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Union, Tuple
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
    PageBreak,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from loguru import logger

from PrevMed.utils.settings import settings
from PrevMed.utils.version import __VERSION__

# Character sets for generating human-readable reference codes
# Exclude ambiguous characters: no 0/O, no 1/I/l for easier human reading
UNAMBIGUOUS_LETTERS = "ABCDFGHJKLMNPQRSTUVWXY"  # 22 letters (no I, O, E, Z)
UNAMBIGUOUS_DIGITS = "23456789"  # 8 digits (no 0, 1)
UNAMBIGUOUS_CHARS = UNAMBIGUOUS_LETTERS + UNAMBIGUOUS_DIGITS  # 32 total chars

# Base directory to store compressed JSON data files and permanent PDFs
DATA_OUTPUT_DIR = "survey_data"

# Regex for parsing basic markdown elements in pdf_extra_content
import re

# Pre-compiled regex patterns for markdown parsing (compiled once for performance)
# These patterns handle: headers (arbitrary levels), bold (**text**), italic (*text*), links [text](url)
MD_HEADER_PATTERN = re.compile(r"^(#+)\s+(.+)$")
MD_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
MD_ITALIC_PATTERN = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
MD_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _md_to_reportlab(text: str) -> str:
    """
    Convert basic Markdown formatting to ReportLab XML tags.

    Handles bold (**text**), italic (*text*), and links [text](url).
    Note: Does NOT handle headers - those are detected separately in render_pdf_extra_content.

    Parameters
    ----------
    text : str
        Text with Markdown formatting

    Returns
    -------
    str
        Text with ReportLab XML tags (<b>, <i>, <a>)
    """
    # Convert bold **text** to <b>text</b>
    text = MD_BOLD_PATTERN.sub(r"<b>\1</b>", text)
    # Convert italic *text* to <i>text</i>
    text = MD_ITALIC_PATTERN.sub(r"<i>\1</i>", text)
    # Convert links [text](url) to <a href="url">text</a>
    # Skip links with empty URLs to prevent PDF rendering crashes
    def replace_link(match: re.Match) -> str:
        link_text = match.group(1)
        url = match.group(2).strip()
        if not url:
            # Empty URL - return just the text without link formatting
            logger.warning(f"Empty link URL detected for text: '{link_text}'. Link skipped.")
            return link_text
        return f'<a href="{url}" color="blue">{link_text}</a>'

    text = MD_LINK_PATTERN.sub(replace_link, text)
    return text


def render_pdf_extra_content(
    pdf_extra_content: str, styles: Dict[str, ParagraphStyle]
) -> List:
    """
    Render Markdown content from pdf_extra_content YAML field into ReportLab flowables.

    Supports:
    - Headers: #, ##, ###, etc. (arbitrary levels, rendered as Heading1, Heading2, etc.)
    - Bold: **text**
    - Italic: *text*
    - Links: [text](url) - empty URLs are safely skipped
    - Tables: pipe-separated tables with | header | header | format

    Parameters
    ----------
    pdf_extra_content : str
        Markdown content from the YAML file
    styles : Dict[str, ParagraphStyle]
        Dictionary of ReportLab paragraph styles to use

    Returns
    -------
    List
        List of ReportLab flowables (Paragraph, Spacer, Table) ready to be added to the PDF story
    """
    flowables = []
    lines = pdf_extra_content.split("\n")
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if not stripped:
            # Empty line - add small spacer
            flowables.append(Spacer(1, 3 * mm))
            i += 1
            continue

        # Check for headers
        header_match = MD_HEADER_PATTERN.match(stripped)
        if header_match:
            level = len(header_match.group(1))  # 1, 2, 3, ... (arbitrary)
            header_text = header_match.group(2)
            # Map header level to style (use Heading1, Heading2, Heading3, fallback to Heading3 for deeper)
            style_name = f"Heading{min(level, 3)}"
            if style_name in styles:
                flowables.append(Paragraph(header_text, styles[style_name]))
            else:
                # Fallback to Heading2 if style not found
                flowables.append(Paragraph(header_text, styles["Heading2"]))
            flowables.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # Check for markdown table (starts with |)
        if stripped.startswith("|") and stripped.endswith("|"):
            # Collect all table rows
            table_rows = []
            while i < len(lines):
                row_stripped = lines[i].strip()
                if not row_stripped.startswith("|"):
                    break
                # Skip separator rows (e.g., |---|---|)
                if re.match(r"^\|[\s\-:]+\|$", row_stripped.replace("|", "| |")):
                    i += 1
                    continue
                # Parse table row: split by | and strip each cell
                cells = [cell.strip() for cell in row_stripped.split("|")]
                # Remove empty first/last elements from leading/trailing |
                cells = [c for c in cells if c]
                if cells:
                    # Apply markdown formatting to each cell
                    cells = [_md_to_reportlab(c) for c in cells]
                    table_rows.append(cells)
                i += 1

            if table_rows:
                # Create ReportLab table from parsed markdown table
                # Calculate column widths dynamically
                num_cols = max(len(row) for row in table_rows)
                available_width = 180 * mm
                col_width = available_width / num_cols
                col_widths = [col_width] * num_cols

                # Normalize rows to have same number of columns
                for row in table_rows:
                    while len(row) < num_cols:
                        row.append("")

                # Create table with styling
                md_table = Table(table_rows, colWidths=col_widths)
                md_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 1), (-1, -1), 10),
                        ]
                    )
                )
                flowables.append(md_table)
                flowables.append(Spacer(1, 3 * mm))
            continue

        # Regular paragraph - convert markdown formatting to ReportLab tags
        converted = _md_to_reportlab(stripped)
        flowables.append(Paragraph(converted, styles["Normal"]))
        flowables.append(Spacer(1, 1 * mm))
        i += 1

    return flowables


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

    # Define temp file path immediately to ensure exception handler can always reference it
    # This prevents NameError if exception occurs before temp file creation
    temp_csv = csv_file_path + ".tmp"

    # Create lock file for atomic access
    csv_lock_file = csv_file_path + ".lock"
    lock = FileLock(csv_lock_file, timeout=10)

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

        # Generate fallback filename with timestamp and UUID for guaranteed uniqueness
        # Format: survey_submissions_fallback_{timestamp}_{uuid}.csv
        # UUID ensures absolute uniqueness even under high concurrent load
        unique_id = str(uuid.uuid4())[:8]
        csv_dir = Path(csv_file_path).parent
        fallback_filename = f"survey_submissions_fallback_{timestamp}_{unique_id}.csv"
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
    pdf_extra_content: str = None,
    show_survey_version: bool = True,
    show_webapp_version: bool = True,
) -> Union[str, Tuple[bytes, str]]:
    """
    Génère un rapport PDF contenant les questions du questionnaire, les réponses et les résultats de scoring.

    Enregistre un fichier JSON compressé avec toutes les données du rapport sur le disque de manière permanente
    si save_user_data est True. Sinon, génère uniquement un PDF en mémoire (BytesIO).

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
    pdf_extra_content : str, optionnel
        Contenu Markdown supplémentaire à inclure dans le PDF. Supporte le formatage Markdown
        basique: gras (**text**), italique (*text*), titres (# à tout niveau), liens [text](url),
        et tables (format pipe: | col1 | col2 |). Les liens vides sont ignorés pour éviter les erreurs.
    show_survey_version : bool, optionnel
        Afficher la version du questionnaire dans le PDF. Par défaut True.
    show_webapp_version : bool, optionnel
        Afficher la version de la webapp dans le PDF. Par défaut True.

    Retourne
    --------
    Union[str, Tuple[bytes, str]]
        Si save_user_data=True: chemin vers le fichier PDF permanent (str)
        Si save_user_data=False: tuple de (bytes PDF, nom de fichier suggéré)
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

        # Generate UUID to guarantee absolute uniqueness even if timestamp and reference code collide
        # Using first 8 characters provides 4 billion+ unique values while keeping filenames readable
        unique_id = str(uuid.uuid4())[:8]

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
            # Save compressed JSON with survey data permanently using atomic write
            json_filename = f"{timestamp}_{reference_code}_{unique_id}.json.gz"
            json_filepath = Path(DATA_OUTPUT_DIR) / json_filename
            json_temp_filepath = Path(DATA_OUTPUT_DIR) / f".{json_filename}.tmp"

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

            # Save as compressed JSON to temp file first, then atomic rename
            # This ensures the file is either complete or doesn't exist (no partial writes)
            try:
                with gzip.open(json_temp_filepath, "wt", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)

                # Atomic rename - replaces old file with new one in single operation
                json_temp_filepath.replace(json_filepath)

                logger.success(
                    f"Données JSON compressées sauvegardées dans: {json_filepath}"
                )
            except Exception as e:
                # Clean up temp file if atomic write failed
                if json_temp_filepath.exists():
                    try:
                        json_temp_filepath.unlink()
                    except:
                        pass
                raise

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

        # Determine PDF output method based on settings
        # BytesIO is used to generate PDF in memory when not saving user data
        # This avoids creating temporary files on disk that need cleanup
        if settings.save_user_data:
            # Save PDF permanently alongside JSON data using atomic write pattern
            pdf_filename = f"{timestamp}_{reference_code}_{unique_id}.pdf"
            pdf_filepath = Path(DATA_OUTPUT_DIR) / pdf_filename
            pdf_temp_filepath = Path(DATA_OUTPUT_DIR) / f".{pdf_filename}.tmp"
            logger.debug(
                f"Génération du PDF permanent: {pdf_filepath} avec le code de référence: {reference_code}"
            )
            # Write to temp file first for atomic operation
            pdf_output = str(pdf_temp_filepath)
            pdf_buffer = None
        else:
            # Use BytesIO for in-memory PDF generation (no disk files)
            logger.debug(
                f"Génération du PDF en mémoire avec le code de référence: {reference_code}"
            )
            pdf_buffer = io.BytesIO()
            pdf_output = pdf_buffer
            pdf_filepath = None
            pdf_temp_filepath = None

        # Create PDF using ReportLab with explicit compression enabled
        pdf = SimpleDocTemplate(pdf_output, pagesize=A4)
        pdf.pageCompression = 1  # Explicitly enable PDF compression
        story = []  # Container for PDF elements
        styles = getSampleStyleSheet()
        styles["Normal"].alignment = TA_JUSTIFY

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
        # Only show reference code when data is actually saved (otherwise it's meaningless)
        if settings.save_user_data:
            story.append(
                Paragraph(f"<b>Code de référence : {reference_code}</b>", reference_style)
            )
            story.append(Spacer(1, 5 * mm))

        # Version information (can be hidden via YAML show_survey_version / show_webapp_version)
        if show_survey_version:
            story.append(
                Paragraph(f"Version du questionnaire : {survey_version}", subtitle_style)
            )
        if show_webapp_version:
            story.append(
                Paragraph(
                    f"Webapp version : {__VERSION__}",
                    subtitle_style,
                )
            )
        # Survey URL if provided
        if actual_url:
            story.append(
                Paragraph(f'URL du questionnaire : <a href="{actual_url}" color="blue">{actual_url}</a>', subtitle_style)
            )

        # GitHub repository link
        story.append(
            Paragraph(
                'Code source disponible sur : <a href="https://github.com/PrevMedOrg/" color="blue">https://github.com/PrevMedOrg/</a>',
                subtitle_style,
            )
        )

        # Timestamp
        story.append(
            Paragraph(
                f"Généré le : {time.strftime('%d/%m/%Y à %H:%M:%S')}", subtitle_style
            )
        )
        story.append(Spacer(1, 8 * mm))

        # Scoring Results section - conditionally include based on pdf_options
        # Only add section heading if at least one of markdown or data will be shown
        if include_md or include_data:
            story.append(Paragraph("Résultats du questionnaire", heading_style))
            story.append(Spacer(1, 5 * mm))

        # Conditionally include markdown results based on include_md_in_pdf
        if include_md:
            # Render markdown content using the same parser as pdf_extra_content
            # This properly converts headers, bold, italic, links, and tables to PDF flowables
            md_flowables = render_pdf_extra_content(markdown_result, styles)
            story.extend(md_flowables)
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

        # Render pdf_extra_content if provided (Markdown from YAML)
        # This section appears after scoring results and before the Q&A listing
        if pdf_extra_content:
            story.append(Spacer(1, 5 * mm))
            # Render markdown content using the standard styles
            # Uses Heading1/2/3 for headers, Normal for paragraphs
            extra_flowables = render_pdf_extra_content(pdf_extra_content, styles)
            story.extend(extra_flowables)

        # Questions and Answers section - start on a new page
        story.append(PageBreak())
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

        # Return appropriate result based on settings
        if settings.save_user_data:
            # Complete atomic write: rename temp file to final destination
            # This ensures PDF is either complete or doesn't exist (no partial writes)
            try:
                pdf_temp_filepath.replace(pdf_filepath)
                logger.success(f"Rapport PDF permanent sauvegardé: {pdf_filepath}")
                logger.info(
                    f"Données permanentes sauvegardées en JSON compressé: {json_filepath}"
                )
                return str(pdf_filepath)
            except Exception as e:
                # Clean up temp file if atomic write failed
                if pdf_temp_filepath.exists():
                    try:
                        pdf_temp_filepath.unlink()
                    except:
                        pass
                raise
        else:
            # Extract bytes from BytesIO buffer and return with suggested filename for Gradio
            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer.close()
            suggested_filename = f"survey_{reference_code}.pdf"
            logger.success(
                f"Rapport PDF généré en mémoire ({len(pdf_bytes)} bytes, nom suggéré: {suggested_filename})"
            )
            logger.info(
                "Aucune donnée utilisateur n'a été sauvegardée de manière permanente"
            )
            return (pdf_bytes, suggested_filename)

    except Exception as e:
        # If PDF generation fails, raise a clear error message
        logger.error(f"Échec de la génération du rapport PDF: {str(e)}")
        raise RuntimeError(
            f"Failed to generate PDF report: {str(e)}. "
            "This may be due to unsupported characters in the survey text."
        ) from e
