# PREMM5 Scoring Function for PrevMed
# 
# This script implements the PREMM5 (Prediction Model for MLH1, MSH2, MSH6, PMS2) 
# risk assessment for Lynch syndrome mutations.
# 
# Expected to be called by PrevMed via rpy2.
# The main entry point is the 'scoring' function which is called with named arguments
# matching the variables defined in premm5.yaml.
#
# Design decisions:
# - NULL values are handled for conditional parameters (questions only shown when conditions are met)
# - Returns a named list (not data.frame) for easier conversion by rpy2 to Python dict
# - Follows the PREMM5 model specification with linear predictors and softmax transformation

compute_premm5_from_data <- function(
  # 1) Individual patient data
  sex,                         # "M"/"F" or "Male"/"Female" or "Homme"/"Femme"
  personal_crc_count,          # Number of colorectal cancers (0, 1, >=2)
  personal_ec,                 # TRUE if endometrial cancer, FALSE otherwise
  personal_other_ls,           # TRUE if other Lynch syndrome cancer, FALSE otherwise
  current_age,                 # Current age (15-100)
  
  # 2) Family history
  fdr_crc_count,  sdr_crc_count,       # First/second degree relative CRC counts
  fdr_ec_count,   sdr_ec_count,        # First/second degree relative EC counts
  fdr_other_ls_count, sdr_other_ls_count,  # First/second degree other LS cancers
  
  # 3) Ages at diagnosis (NULL if no cancer in that category)
  age_crc_proband = NULL,
  age_crc_fdr     = NULL,
  age_crc_sdr     = NULL,
  age_ec_proband  = NULL,
  age_ec_fdr      = NULL,
  age_ec_sdr      = NULL
) {
  # Convert string responses to boolean for easier logic handling
  # YAML passes "Oui"/"Non" but we need TRUE/FALSE for R logic
  # NULL values (from skipped questions) are treated as FALSE
  personal_ec_bool <- !is.null(personal_ec) && (tolower(as.character(personal_ec)) == "oui")
  personal_other_ls_bool <- !is.null(personal_other_ls) && (tolower(as.character(personal_other_ls)) == "oui")
  
  # --- V0-V4: Individual cancer indicators ---
  # V0: Sex indicator (1 for male, 0 for female)
  V0  <- ifelse(tolower(substr(sex, 1, 1)) %in% c("m", "h"), 1, 0)
  # V1: Exactly 1 CRC
  V1  <- as.integer(personal_crc_count == 1)
  # V2: 2 or more CRCs
  V2  <- as.integer(personal_crc_count >= 2)
  # V3: Endometrial cancer
  V3  <- as.integer(personal_ec_bool)
  # V4: Other Lynch syndrome cancer
  V4  <- as.integer(personal_other_ls_bool)
  
  # --- V5: CRC family history score ---
  # Weighted score: FDR=1 (or 2 if >=2), SDR=0.5 (or 1 if >=2)
  A <- as.integer(fdr_crc_count == 1)
  B <- as.integer(fdr_crc_count >= 2)
  C <- as.integer(sdr_crc_count == 1)
  D <- as.integer(sdr_crc_count >= 2)
  V5 <- 1*A + 2*B + 0.5*C + 1*D
  
  # --- V6: EC family history score ---
  A <- as.integer(fdr_ec_count == 1)
  B <- as.integer(fdr_ec_count >= 2)
  C <- as.integer(sdr_ec_count == 1)
  D <- as.integer(sdr_ec_count >= 2)
  V6 <- 1*A + 2*B + 0.5*C + 1*D
  
  # --- V7: Other LS cancer family history score ---
  E <- as.integer(fdr_other_ls_count >= 1)
  F <- as.integer(sdr_other_ls_count >= 1)
  V7 <- 1*E + 0.5*F
  
  # --- V8: Sum of (age_at_CRC_diagnosis - 45) ---
  # Only include ages for actual cases, default to 45 (neutral) if NULL or no case
  # This creates a penalty for younger age at diagnosis
  c1 <- if (personal_crc_count > 0 && !is.null(age_crc_proband)) age_crc_proband else 45
  c2 <- if (fdr_crc_count > 0 && !is.null(age_crc_fdr)) age_crc_fdr else 45
  c3 <- if (sdr_crc_count > 0 && !is.null(age_crc_sdr)) age_crc_sdr else 45
  V8 <- (c1 - 45) + (c2 - 45) + (c3 - 45)
  
  # --- V9: Sum of (age_at_EC_diagnosis - 45) ---
  # Same logic as V8 but for endometrial cancer
  e1 <- if (personal_ec_bool && !is.null(age_ec_proband)) age_ec_proband else 45
  e2 <- if (fdr_ec_count > 0 && !is.null(age_ec_fdr)) age_ec_fdr else 45
  e3 <- if (sdr_ec_count > 0 && !is.null(age_ec_sdr)) age_ec_sdr else 45
  V9 <- (e1 - 45) + (e2 - 45) + (e3 - 45)
  
  # --- V10: Current age ---
  V10 <- current_age
  
  # --- Linear predictors for each gene ---
  # These coefficients are from the published PREMM5 model
  lp_MLH1 <- -5.325 + 0.904*V0 + 2.586*V1 + 3.183*V2 + 1.621*V3 +
    1.276*V4 + 1.560*V5 + 0.804*V6 + 0.397*V7 -
    0.0557*V8 + 0.0115*V9 - 0.0476*V10
  
  lp_MSH2  <- -4.427 + 0.937*V0 + 1.799*V1 + 2.593*V2 + 1.924*V3 +
    1.585*V4 + 1.337*V5 + 0.670*V6 + 0.607*V7 -
    0.0441*V8 + 0.0002*V9 - 0.0482*V10
  
  lp_MSH6  <- -4.675 + 0.816*V0 + 1.265*V1 - 53.205*V2 + 1.759*V3 +
    0.538*V4 + 0.545*V5 + 0.923*V6 + 0.313*V7 -
    0.0095*V8 + 0.0344*V9 - 0.0363*V10
  
  lp_PMS2  <- -4.913 + 0.294*V0 + 0.989*V1 - 0.354*V2 + 0.739*V3 +
    0.395*V4 - 0.002*V5 - 0.426*V6 - 0.105*V7 -
    0.0086*V8 + 0.0008*V9 - 0.0074*V10
  
  # --- Softmax transformation to get probabilities ---
  # Convert linear predictors to probabilities using multinomial logit
  e      <- exp(c(lp_MLH1, lp_MSH2, lp_MSH6, lp_PMS2))
  denom  <- 1 + sum(e)
  probs  <- e / denom
  
  # --- Return as named list ---
  # Named list format is preferred over data.frame for rpy2 conversion
  # Python code expects these exact key names
  list(
    p_MLH1        = probs[1],
    p_MSH2_EPCAM  = probs[2],
    p_MSH6        = probs[3],
    p_PMS2        = probs[4],
    p_any         = sum(probs),
    p_none        = 1 - sum(probs)
  )
}


# Main entry point for PrevMed
#
# This function is called by PrevMed via rpy2.
# Parameter names must match the 'variable' fields in premm5.yaml.
# All parameters use default NULL for conditional questions to handle cases
# where they are not shown based on YAML conditions.
#
# Returns a list with 2 elements:
# 1. Character string with markdown-formatted results
# 2. Named list with data (for CSV/JSON storage)
scoring <- function(
  sex,
  current_age,
  personal_crc_count,
  age_crc_proband = NULL,
  personal_ec = NULL,
  age_ec_proband = NULL,
  personal_other_ls = NULL,
  fdr_crc_count,
  age_crc_fdr = NULL,
  fdr_ec_count,
  age_ec_fdr = NULL,
  fdr_other_ls_count,
  sdr_crc_count,
  age_crc_sdr = NULL,
  sdr_ec_count,
  age_ec_sdr = NULL,
  sdr_other_ls_count
) {
  # Delegate to the main computation function
  # This wrapper ensures compatibility with PrevMed's calling convention
  results <- compute_premm5_from_data(
    sex = sex,
    personal_crc_count = personal_crc_count,
    personal_ec = personal_ec,
    personal_other_ls = personal_other_ls,
    current_age = current_age,
    fdr_crc_count = fdr_crc_count,
    sdr_crc_count = sdr_crc_count,
    fdr_ec_count = fdr_ec_count,
    sdr_ec_count = sdr_ec_count,
    fdr_other_ls_count = fdr_other_ls_count,
    sdr_other_ls_count = sdr_other_ls_count,
    age_crc_proband = age_crc_proband,
    age_crc_fdr = age_crc_fdr,
    age_crc_sdr = age_crc_sdr,
    age_ec_proband = age_ec_proband,
    age_ec_fdr = age_ec_fdr,
    age_ec_sdr = age_ec_sdr
  )
  
  # Format results as markdown table
  markdown <- "## Résultats du scoring\n\n"
  markdown <- paste0(markdown, "| Gène/Catégorie | Probabilité |\n")
  markdown <- paste0(markdown, "|---------------|-------------|\n")
  markdown <- paste0(markdown, sprintf("| MLH1 | %05.2f%% |\n", results$p_MLH1 * 100))
  markdown <- paste0(markdown, sprintf("| MSH2/EPCAM | %05.2f%% |\n", results$p_MSH2_EPCAM * 100))
  markdown <- paste0(markdown, sprintf("| MSH6 | %05.2f%% |\n", results$p_MSH6 * 100))
  markdown <- paste0(markdown, sprintf("| PMS2 | %05.2f%% |\n", results$p_PMS2 * 100))
  markdown <- paste0(markdown, sprintf("| **Total (any)** | **%05.2f%%** |\n", results$p_any * 100))
  markdown <- paste0(markdown, sprintf("| None | %05.2f%% |\n", results$p_none * 100))
  
  # Return list with 3 elements: markdown string, table data, and PDF options
  # Table data is a list where first element is headers, rest are data rows
  # This allows for flexible n-column tables instead of just 2-column key-value pairs
  table_data <- list(
    c("Gène/Catégorie", "Probabilité"),  # Headers
    c("MLH1", sprintf("%05.2f%%", results$p_MLH1 * 100)),
    c("MSH2/EPCAM", sprintf("%05.2f%%", results$p_MSH2_EPCAM * 100)),
    c("MSH6", sprintf("%05.2f%%", results$p_MSH6 * 100)),
    c("PMS2", sprintf("%05.2f%%", results$p_PMS2 * 100)),
    c("Total (any)", sprintf("%05.2f%%", results$p_any * 100)),
    c("None", sprintf("%05.2f%%", results$p_none * 100))
  )
  
  # PDF generation options control what gets included in the PDF report
  # include_md_in_pdf: Whether to include the markdown-formatted results
  # include_data_in_pdf: Whether to include the structured data table
  pdf_options <- list(
    include_md_in_pdf = TRUE,
    include_data_in_pdf = TRUE
  )
  
  list(
    markdown,
    table_data,
    pdf_options
  )
}
