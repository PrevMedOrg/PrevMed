from loguru import logger
from typing import Dict, Any


def execute_scoring_r(
    code: str, inputs: Dict[str, Any]
) -> tuple[str, list[list[str]], dict[str, bool]]:
    """
    Exécute le code de scoring R en utilisant rpy2.

    La fonction R doit retourner une liste avec 3 éléments :
    1. Une chaîne de caractères contenant le markdown à afficher
    2. Une liste de listes représentant une table (première liste = headers, suivantes = lignes de données)
    3. Une liste nommée avec include_md_in_pdf et include_data_in_pdf (booleans)

    Note : l'import de rpy2 est géré au moment de la création du questionnaire selon le langage de scoring.

    Paramètres
    ----------
    code : str
        Code R définissant une fonction 'scoring'
    inputs : Dict[str, Any]
        Variables d'entrée pour la fonction de scoring

    Retourne
    --------
    tuple[str, list[list[str]], dict[str, bool]]
        Tuple (markdown_string, table_data, pdf_options) où table_data[0] est la liste des headers,
        table_data[1:] sont les lignes de données, et pdf_options contrôle ce qui est inclus dans le PDF
    """
    logger.info("Début de l'exécution du scoring R")

    import rpy2.robjects as ro
    from rpy2.robjects import default_converter
    from rpy2.robjects.conversion import localconverter

    # Use localconverter to ensure conversion rules are available in threaded context
    # This fixes the ContextVar issue when running in Gradio's event handlers
    with localconverter(default_converter):
        logger.debug("Exécution du code R pour définir la fonction")
        # Execute the R code to define the function
        ro.r(code)

        logger.debug("Conversion des entrées Python en objets R")
        # Convert Python inputs to R arguments
        # Handle None values and type conversions
        r_inputs = {}
        for key, value in inputs.items():
            if value is None:
                r_inputs[key] = ro.NULL
            elif isinstance(value, bool):
                r_inputs[key] = ro.BoolVector([value])[0]
            elif isinstance(value, str):
                r_inputs[key] = ro.StrVector([value])[0]
            else:
                r_inputs[key] = value

        logger.debug("Appel de la fonction R 'scoring'")
        # Call the R function - expects it to return a named list
        result = ro.r["scoring"](**r_inputs)

        logger.debug("Conversion du résultat R en tuple Python")
        # R function should return a list with 3 elements:
        # 1. markdown string (character vector)
        # 2. list of lists representing table (first list = headers, rest = data rows)
        # 3. options list with include_md_in_pdf and include_data_in_pdf booleans
        if len(result) != 3:
            raise ValueError(
                f"R scoring function must return a list with 3 elements (markdown, table_data, options), got {len(result)}"
            )

        # Extract markdown string (first element)
        markdown_str = str(result[0][0])  # Convert R character vector to Python str

        # Extract table data (second element - list of character vectors)
        table_list = result[1]
        table_data = []
        for i in range(len(table_list)):
            # Each element is a character vector representing a row (or headers)
            row_vector = table_list[i]
            # Convert R character vector to Python list of strings
            row = [str(val) for val in row_vector]
            table_data.append(row)

        # Extract PDF options (third element - named list)
        options_list = result[2]
        pdf_options = {
            "include_md_in_pdf": bool(options_list.rx2("include_md_in_pdf")[0]),
            "include_data_in_pdf": bool(options_list.rx2("include_data_in_pdf")[0]),
        }

        logger.success(
            f"Scoring R terminé avec succès avec {len(table_data)} lignes de table (incluant headers)"
        )
        logger.debug(f"Longueur du markdown R: {len(markdown_str)} caractères")
        logger.debug(
            f"Options PDF: include_md_in_pdf={pdf_options['include_md_in_pdf']}, include_data_in_pdf={pdf_options['include_data_in_pdf']}"
        )
        return (markdown_str, table_data, pdf_options)


def execute_scoring_python(
    code: str, inputs: Dict[str, Any]
) -> tuple[str, list[list[str]], dict[str, bool]]:
    """
    Exécute le code de scoring Python.

    La fonction Python doit retourner un tuple avec 3 éléments :
    1. Une chaîne contenant le markdown à afficher
    2. Une liste de listes représentant une table (première liste = headers, suivantes = lignes de données)
    3. Un dictionnaire d'options avec include_md_in_pdf et include_data_in_pdf (booleans)

    Paramètres
    ----------
    code : str
        Code Python définissant une fonction 'scoring'
    inputs : Dict[str, Any]
        Variables d'entrée pour la fonction de scoring

    Retourne
    --------
    tuple[str, list[list[str]], dict[str, bool]]
        Tuple (markdown_string, table_data, pdf_options) où table_data[0] est la liste des headers,
        table_data[1:] sont les lignes de données, et pdf_options contrôle ce qui est inclus dans le PDF
    """
    logger.info("Début de l'exécution du scoring Python")

    try:
        logger.debug("Exécution du code Python pour définir la fonction")
        # Create namespace and execute code
        namespace = {}
        exec(code, namespace)

        # Find the scoring function (must be named 'scoring')
        func_name = "scoring"
        if func_name not in namespace:
            logger.error(f"Fonction '{func_name}' introuvable dans le code de scoring")
            raise ValueError(
                f"Fonction '{func_name}' introuvable dans le code de scoring"
            )

        logger.debug(f"Appel de la fonction Python {func_name}")
        # Call the function with inputs
        result = namespace[func_name](**inputs)

        # Ensure result is a 3-tuple
        if not isinstance(result, tuple) or len(result) != 3:
            raise ValueError(
                f"Python scoring function must return a tuple with 3 elements (markdown, table_data, options), got {type(result)}"
            )

        markdown_str, table_data, pdf_options = result

        # Validate types
        if not isinstance(markdown_str, str):
            raise ValueError(
                f"First element of return tuple must be a string (markdown), got {type(markdown_str)}"
            )
        if not isinstance(table_data, list):
            raise ValueError(
                f"Second element of return tuple must be a list (table_data), got {type(table_data)}"
            )
        if not isinstance(pdf_options, dict):
            raise ValueError(
                f"Third element of return tuple must be a dict (pdf_options), got {type(pdf_options)}"
            )

        # Validate table structure: should be list of lists where all rows have same length
        if len(table_data) == 0:
            raise ValueError("Table data must have at least one row (headers)")

        # Convert all values to strings
        table_data = [[str(val) for val in row] for row in table_data]

        # Validate all rows have same length as headers
        header_len = len(table_data[0])
        for i, row in enumerate(table_data[1:], start=1):
            if len(row) != header_len:
                raise ValueError(
                    f"Row {i} has {len(row)} columns but headers have {header_len} columns"
                )

        logger.success(
            f"Scoring Python terminé avec succès avec {len(table_data)} lignes de table (incluant headers)"
        )
        logger.debug(f"Longueur du markdown Python: {len(markdown_str)} caractères")
        logger.debug(
            f"Options PDF: include_md_in_pdf={pdf_options.get('include_md_in_pdf', True)}, include_data_in_pdf={pdf_options.get('include_data_in_pdf', True)}"
        )
        return (markdown_str, table_data, pdf_options)
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du scoring Python: {str(e)}")
        raise RuntimeError(
            f"Erreur lors de l'exécution du scoring Python: {str(e)}"
        ) from e


def execute_scoring(
    language: str, code: str, inputs: Dict[str, Any]
) -> tuple[str, list[list[str]], dict[str, bool]]:
    """
    Exécute le scoring selon le langage spécifié.

    Paramètres
    ----------
    language : str
        'r' ou 'python'
    code : str
        Code du script de scoring
    inputs : Dict[str, Any]
        Variables d'entrée pour la fonction de scoring

    Retourne
    --------
    tuple[str, list[list[str]], dict[str, bool]]
        Tuple (markdown_string, table_data, pdf_options) où markdown_string est le résultat formaté
        à afficher, table_data est une liste de listes (headers puis lignes de données),
        et pdf_options contrôle ce qui est inclus dans le PDF
    """
    logger.info(f"Exécution du scoring avec le langage: {language}")

    if language == "r":
        return execute_scoring_r(code, inputs)
    elif language == "python":
        return execute_scoring_python(code, inputs)
    else:
        logger.error(f"Langage de scoring non supporté: {language}")
        raise ValueError(f"Langage de scoring non supporté: {language}")
