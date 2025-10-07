"""PREMM5 Scoring Function for PrevMed (Python implementation).

This script implements the PREMM5 (Prediction Model for MLH1, MSH2, MSH6, PMS2)
risk assessment for Lynch syndrome mutations.

Expected to be called by PrevMed via the execute_scoring_python function.
The main entry point is the 'scoring' function which is called with keyword arguments
matching the variables defined in premm5.yaml.

Design decisions:
- None values are handled for conditional parameters (questions only shown when conditions are met)
- Returns a tuple (markdown_str, table_data, pdf_options) for PrevMed compatibility
- Follows the PREMM5 model specification with linear predictors and softmax transformation
- Uses type hints and NumPy-style docstrings per project conventions
"""

import math
from typing import Optional, Dict, List, Tuple, Any


def compute_premm5_from_data(
    sex: str,
    personal_crc_count: int,
    personal_ec: Optional[str],
    personal_other_ls: Optional[str],
    current_age: int,
    fdr_crc_count: int,
    sdr_crc_count: int,
    fdr_ec_count: int,
    sdr_ec_count: int,
    fdr_other_ls_count: int,
    sdr_other_ls_count: int,
    age_crc_proband: Optional[int] = None,
    age_crc_fdr: Optional[int] = None,
    age_crc_sdr: Optional[int] = None,
    age_ec_proband: Optional[int] = None,
    age_ec_fdr: Optional[int] = None,
    age_ec_sdr: Optional[int] = None,
) -> Dict[str, float]:
    """Compute PREMM5 probabilities from patient and family history data.

    Parameters
    ----------
    sex : str
        Patient sex ("M"/"F" or "Male"/"Female" or "Homme"/"Femme")
    personal_crc_count : int
        Number of colorectal cancers (0, 1, >=2)
    personal_ec : Optional[str]
        "Oui" if endometrial cancer, "Non" otherwise, None if not answered
    personal_other_ls : Optional[str]
        "Oui" if other Lynch syndrome cancer, "Non" otherwise, None if not answered
    current_age : int
        Current age (15-100)
    fdr_crc_count : int
        First degree relative CRC count
    sdr_crc_count : int
        Second degree relative CRC count
    fdr_ec_count : int
        First degree relative EC count
    sdr_ec_count : int
        Second degree relative EC count
    fdr_other_ls_count : int
        First degree relative other LS cancer count
    sdr_other_ls_count : int
        Second degree relative other LS cancer count
    age_crc_proband : Optional[int], default=None
        Age at CRC diagnosis for patient
    age_crc_fdr : Optional[int], default=None
        Age at CRC diagnosis for first degree relative
    age_crc_sdr : Optional[int], default=None
        Age at CRC diagnosis for second degree relative
    age_ec_proband : Optional[int], default=None
        Age at EC diagnosis for patient
    age_ec_fdr : Optional[int], default=None
        Age at EC diagnosis for first degree relative
    age_ec_sdr : Optional[int], default=None
        Age at EC diagnosis for second degree relative

    Returns
    -------
    Dict[str, float]
        Dictionary with keys: p_MLH1, p_MSH2_EPCAM, p_MSH6, p_PMS2, p_any, p_none
        containing probability estimates for each gene mutation
    """
    # Convert string responses to boolean for easier logic handling
    # YAML passes "Oui"/"Non" but we need True/False for Python logic
    # None values (from skipped questions) are treated as False
    personal_ec_bool = personal_ec is not None and str(personal_ec).lower() == "oui"
    personal_other_ls_bool = (
        personal_other_ls is not None and str(personal_other_ls).lower() == "oui"
    )

    # --- V0-V4: Individual cancer indicators ---
    # V0: Sex indicator (1 for male, 0 for female)
    V0 = 1 if str(sex).lower()[0] in ["m", "h"] else 0
    # V1: Exactly 1 CRC
    V1 = int(personal_crc_count == 1)
    # V2: 2 or more CRCs
    V2 = int(personal_crc_count >= 2)
    # V3: Endometrial cancer
    V3 = int(personal_ec_bool)
    # V4: Other Lynch syndrome cancer
    V4 = int(personal_other_ls_bool)

    # --- V5: CRC family history score ---
    # Weighted score: FDR=1 (or 2 if >=2), SDR=0.5 (or 1 if >=2)
    A = int(fdr_crc_count == 1)
    B = int(fdr_crc_count >= 2)
    C = int(sdr_crc_count == 1)
    D = int(sdr_crc_count >= 2)
    V5 = 1 * A + 2 * B + 0.5 * C + 1 * D

    # --- V6: EC family history score ---
    A = int(fdr_ec_count == 1)
    B = int(fdr_ec_count >= 2)
    C = int(sdr_ec_count == 1)
    D = int(sdr_ec_count >= 2)
    V6 = 1 * A + 2 * B + 0.5 * C + 1 * D

    # --- V7: Other LS cancer family history score ---
    E = int(fdr_other_ls_count >= 1)
    F = int(sdr_other_ls_count >= 1)
    V7 = 1 * E + 0.5 * F

    # --- V8: Sum of (age_at_CRC_diagnosis - 45) ---
    # Only include ages for actual cases, default to 45 (neutral) if None or no case
    # This creates a penalty for younger age at diagnosis
    c1 = (
        age_crc_proband
        if personal_crc_count > 0 and age_crc_proband is not None
        else 45
    )
    c2 = age_crc_fdr if fdr_crc_count > 0 and age_crc_fdr is not None else 45
    c3 = age_crc_sdr if sdr_crc_count > 0 and age_crc_sdr is not None else 45
    V8 = (c1 - 45) + (c2 - 45) + (c3 - 45)

    # --- V9: Sum of (age_at_EC_diagnosis - 45) ---
    # Same logic as V8 but for endometrial cancer
    e1 = age_ec_proband if personal_ec_bool and age_ec_proband is not None else 45
    e2 = age_ec_fdr if fdr_ec_count > 0 and age_ec_fdr is not None else 45
    e3 = age_ec_sdr if sdr_ec_count > 0 and age_ec_sdr is not None else 45
    V9 = (e1 - 45) + (e2 - 45) + (e3 - 45)

    # --- V10: Current age ---
    V10 = current_age

    # --- Linear predictors for each gene ---
    # These coefficients are from the published PREMM5 model
    lp_MLH1 = (
        -5.325
        + 0.904 * V0
        + 2.586 * V1
        + 3.183 * V2
        + 1.621 * V3
        + 1.276 * V4
        + 1.560 * V5
        + 0.804 * V6
        + 0.397 * V7
        - 0.0557 * V8
        + 0.0115 * V9
        - 0.0476 * V10
    )

    lp_MSH2 = (
        -4.427
        + 0.937 * V0
        + 1.799 * V1
        + 2.593 * V2
        + 1.924 * V3
        + 1.585 * V4
        + 1.337 * V5
        + 0.670 * V6
        + 0.607 * V7
        - 0.0441 * V8
        + 0.0002 * V9
        - 0.0482 * V10
    )

    lp_MSH6 = (
        -4.675
        + 0.816 * V0
        + 1.265 * V1
        - 53.205 * V2
        + 1.759 * V3
        + 0.538 * V4
        + 0.545 * V5
        + 0.923 * V6
        + 0.313 * V7
        - 0.0095 * V8
        + 0.0344 * V9
        - 0.0363 * V10
    )

    lp_PMS2 = (
        -4.913
        + 0.294 * V0
        + 0.989 * V1
        - 0.354 * V2
        + 0.739 * V3
        + 0.395 * V4
        - 0.002 * V5
        - 0.426 * V6
        - 0.105 * V7
        - 0.0086 * V8
        + 0.0008 * V9
        - 0.0074 * V10
    )

    # --- Softmax transformation to get probabilities ---
    # Convert linear predictors to probabilities using multinomial logit
    e = [math.exp(lp) for lp in [lp_MLH1, lp_MSH2, lp_MSH6, lp_PMS2]]
    denom = 1 + sum(e)
    probs = [exp_val / denom for exp_val in e]

    # --- Return as dictionary ---
    # Dictionary format aligns with Python conventions
    # Keys match the expected output format
    return {
        "p_MLH1": probs[0],
        "p_MSH2_EPCAM": probs[1],
        "p_MSH6": probs[2],
        "p_PMS2": probs[3],
        "p_any": sum(probs),
        "p_none": 1 - sum(probs),
    }


def scoring(
    sex: str,
    current_age: int,
    personal_crc_count: int,
    age_crc_proband: Optional[int] = None,
    personal_ec: Optional[str] = None,
    age_ec_proband: Optional[int] = None,
    personal_other_ls: Optional[str] = None,
    fdr_crc_count: int = 0,
    age_crc_fdr: Optional[int] = None,
    fdr_ec_count: int = 0,
    age_ec_fdr: Optional[int] = None,
    fdr_other_ls_count: int = 0,
    sdr_crc_count: int = 0,
    age_crc_sdr: Optional[int] = None,
    sdr_ec_count: int = 0,
    age_ec_sdr: Optional[int] = None,
    sdr_other_ls_count: int = 0,
) -> Tuple[str, List[List[str]], Dict[str, bool]]:
    """Main entry point for PrevMed scoring.

    This function is called by PrevMed via execute_scoring_python.
    Parameter names must match the 'variable' fields in premm5.yaml.
    All optional parameters use default None for conditional questions to handle cases
    where they are not shown based on YAML conditions.

    Parameters
    ----------
    sex : str
        Patient sex
    current_age : int
        Current age
    personal_crc_count : int
        Number of patient's CRCs
    age_crc_proband : Optional[int], default=None
        Age at CRC diagnosis for patient
    personal_ec : Optional[str], default=None
        "Oui"/"Non" for endometrial cancer
    age_ec_proband : Optional[int], default=None
        Age at EC diagnosis for patient
    personal_other_ls : Optional[str], default=None
        "Oui"/"Non" for other LS cancer
    fdr_crc_count : int, default=0
        First degree relative CRC count
    age_crc_fdr : Optional[int], default=None
        Age at CRC diagnosis for FDR
    fdr_ec_count : int, default=0
        First degree relative EC count
    age_ec_fdr : Optional[int], default=None
        Age at EC diagnosis for FDR
    fdr_other_ls_count : int, default=0
        First degree relative other LS cancer count
    sdr_crc_count : int, default=0
        Second degree relative CRC count
    age_crc_sdr : Optional[int], default=None
        Age at CRC diagnosis for SDR
    sdr_ec_count : int, default=0
        Second degree relative EC count
    age_ec_sdr : Optional[int], default=None
        Age at EC diagnosis for SDR
    sdr_other_ls_count : int, default=0
        Second degree relative other LS cancer count

    Returns
    -------
    Tuple[str, List[List[str]], Dict[str, bool]]
        A tuple containing:
        - markdown_str: Markdown-formatted results table
        - table_data: List of lists with headers and data rows
        - pdf_options: Dict controlling PDF generation (include_md_in_pdf, include_data_in_pdf)
    """
    # Delegate to the main computation function
    # This wrapper ensures compatibility with PrevMed's calling convention
    results = compute_premm5_from_data(
        sex=sex,
        personal_crc_count=personal_crc_count,
        personal_ec=personal_ec,
        personal_other_ls=personal_other_ls,
        current_age=current_age,
        fdr_crc_count=fdr_crc_count,
        sdr_crc_count=sdr_crc_count,
        fdr_ec_count=fdr_ec_count,
        sdr_ec_count=sdr_ec_count,
        fdr_other_ls_count=fdr_other_ls_count,
        sdr_other_ls_count=sdr_other_ls_count,
        age_crc_proband=age_crc_proband,
        age_crc_fdr=age_crc_fdr,
        age_crc_sdr=age_crc_sdr,
        age_ec_proband=age_ec_proband,
        age_ec_fdr=age_ec_fdr,
        age_ec_sdr=age_ec_sdr,
    )

    # Format results as markdown table
    markdown = "## Résultats du scoring\n\n"
    markdown += "| Gène/Catégorie | Probabilité |\n"
    markdown += "|---------------|-------------|\n"
    markdown += f"| MLH1 | {results['p_MLH1'] * 100:05.2f}% |\n"
    markdown += f"| MSH2/EPCAM | {results['p_MSH2_EPCAM'] * 100:05.2f}% |\n"
    markdown += f"| MSH6 | {results['p_MSH6'] * 100:05.2f}% |\n"
    markdown += f"| PMS2 | {results['p_PMS2'] * 100:05.2f}% |\n"
    markdown += f"| **Total (any)** | **{results['p_any'] * 100:05.2f}%** |\n"
    markdown += f"| None | {results['p_none'] * 100:05.2f}% |\n"

    # Return tuple with 3 elements: markdown string, table data, and PDF options
    # Table data is a list where first element is headers, rest are data rows
    # This allows for flexible n-column tables instead of just 2-column key-value pairs
    table_data = [
        ["Gène/Catégorie", "Probabilité"],  # Headers
        ["MLH1", f"{results['p_MLH1'] * 100:05.2f}%"],
        ["MSH2/EPCAM", f"{results['p_MSH2_EPCAM'] * 100:05.2f}%"],
        ["MSH6", f"{results['p_MSH6'] * 100:05.2f}%"],
        ["PMS2", f"{results['p_PMS2'] * 100:05.2f}%"],
        ["Total (any)", f"{results['p_any'] * 100:05.2f}%"],
        ["None", f"{results['p_none'] * 100:05.2f}%"],
    ]

    # PDF generation options control what gets included in the PDF report
    # include_md_in_pdf: Whether to include the markdown-formatted results
    # include_data_in_pdf: Whether to include the structured data table
    pdf_options = {"include_md_in_pdf": True, "include_data_in_pdf": True}

    return (markdown, table_data, pdf_options)
