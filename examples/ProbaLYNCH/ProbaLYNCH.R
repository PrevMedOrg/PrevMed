# ProbaLYNCH Scoring Function for PrevMed
#
# IMPORTANT: This R script has a Python equivalent (ProbaLYNCH.py) that must be kept
# in sync. Any modification to this file MUST be accompanied by the corresponding
# modification to ProbaLYNCH.py to ensure both implementations produce identical results.
#
# This script implements the ProbaLYNCH (Prediction Model for MLH1, MSH2, MSH6, PMS2)
# risk assessment for Lynch syndrome mutations.
# 
# Expected to be called by PrevMed via rpy2.
# The main entry point is the 'scoring' function which is called with named arguments
# matching the variables defined in ProbaLYNCH.yaml.
#
# Design decisions:
# - NULL values are handled for conditional parameters (questions only shown when conditions are met)
# - Returns a named list (not data.frame) for easier conversion by rpy2 to Python dict

compute_probalynch_from_data <- function(
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
  # These coefficients are from the published ProbaLYNCH model
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
# Parameter names must match the 'variable' fields in ProbaLYNCH.yaml.
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
  # Check if any cancer is reported at all (personal or family)
  personal_ec_bool <- !is.null(personal_ec) && (tolower(as.character(personal_ec)) == "oui")
  personal_other_ls_bool <- !is.null(personal_other_ls) && (tolower(as.character(personal_other_ls)) == "oui")
  no_cancer <- (personal_crc_count == 0 &&
                !personal_ec_bool &&
                !personal_other_ls_bool &&
                fdr_crc_count == 0 && sdr_crc_count == 0 &&
                fdr_ec_count == 0 && sdr_ec_count == 0 &&
                fdr_other_ls_count == 0 && sdr_other_ls_count == 0)
  if (no_cancer) {
    markdown <- "# ProbaLYNCH ne peut évaluer votre probabilité qu'en cas de cancer dans la famille"
    table_data <- list(c("", ""))
    pdf_options <- list(include_md_in_pdf = TRUE, include_data_in_pdf = FALSE)
    return(list(markdown, table_data, pdf_options))
  }

  # Delegate to the main computation function
  # This wrapper ensures compatibility with PrevMed's calling convention
  results <- compute_probalynch_from_data(
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
  
  # Format results
  p_any_pct <- results$p_any * 100
  total_formatted <- paste0(gsub("\\.", ",", sprintf("%.1f", p_any_pct)), "%")
  markdown <- paste0(
    "# Estimation de votre probabilité d'être une personne porteuse ",
    "de la fragilité génétique du syndrome de Lynch : ", total_formatted
  )

  # Common preamble text shared across probability-based cases
  preamble <- paste0(
    "En préambule, il est utile de savoir que chaque personne possède plusieurs ",
    "fragilités dans son patrimoine génétique ([comprendre la génétique](https://preventionfamiliale.fr/files/Comprendre-la-Genetique.pdf)). Si votre ",
    "démarche vous amène à apprendre que vous êtes, depuis toujours, une personne ",
    "porteuse d'une fragilité du syndrome de Lynch, vous êtes « en avance » sur ",
    "l'immense majorité des personnes, qui ignorent tout de leurs risques génétiques. ",
    "Vous allez bénéficier d'une prévention personnalisée. Grâce à vous, plusieurs ",
    "personnes de votre famille, également porteuses du risque génétique, vont ",
    "pouvoir être protégées."
  )

  # Common lifestyle optimization paragraph (shared across all probability tiers)
  lifestyle <- paste0(
    "## Optimisez votre mode de vie",
    "\n\nCertains facteurs d'environnement contribuant au cancer colorectal sont ",
    "modifiables par une adaptation du mode de vie : ",
    "[alimentation trop riche](https://preventionfamiliale.fr/files/Prevention-nutritionnelle.pdf) ",
    "en viande rouge (plus de 500 g par semaine) et charcuterie (plus de 150 g par ",
    "semaine), pauvre en fruits et légumes (moins de 5 par jour), alcool (plus de ",
    "10 verres par semaine), surpoids, tabac et ",
    "[manque d'activité physique](https://preventionfamiliale.fr/files/Eval-Activite-Physique.pdf) ",
    "(moins de 2 heures et demi d'équivalent marche rapide par semaine). ",
    "L'adaptation de l'environnement modifiable permettrait d'éviter jusqu'à la ",
    "moitié des cancers colorectaux non-génétiques. Elle est particulièrement ",
    "recommandée quand il existe un cas de cancer colorectal dans sa famille."
  )

  # Common colonoscopy prevention header (shared across all probability tiers)
  colonoscopy_header <- paste0(
    "## Si, finalement, le syndrome de Lynch est exclu, la recommandation ",
    "de coloscopie de prévention familiale à vie à partir de 45 ans est formelle ",
    "pour les apparentés très proches des personnes qui ont été atteintes de cancer ",
    "colorectal"
  )

  colonoscopy_intro <- paste0(
    "La plupart des hypothèses de syndrome de Lynch, après exploration, seront ",
    "exclues (9 fois sur 10 quand la probabilité est estimée à 10 %). Il n'en reste ",
    "pas moins qu'il existe un risque familial accru de cancer colorectal pour les ",
    "apparentés les plus proches d'une personne atteinte, tout au long de leur ",
    "vie : les enfants à partir de 45 ans, les frères et sœurs et les parents."
  )

  # Special case: person aged 50-75 with no personal CRC and no FDR CRC
  if (current_age >= 50 && current_age <= 75 && personal_crc_count == 0 && fdr_crc_count == 0) {
    markdown <- paste0(markdown,
      "\n\n## Vous avez entre 50 et 75 ans, sans personne apparentée proche atteinte de ",
      "cancer colo-rectal et l'hypothèse du syndrome de Lynch est exclue\n\n",
      "Si vous ne faites pas déjà partie des 30% de personnes qui participent au ",
      "dépistage en population générale du cancer colorectal, où le risque de ce cancer ",
      "est d'environ 4% au cours de la vie, vous pouvez retirer le kit de dépistage ",
      "auprès de votre médecin, de votre pharmacien ou directement auprès de ",
      "l'assurance-maladie. Ce dépistage est à renouveler tous les deux ans, pour ",
      "obtenir une bonne efficacité. Le taux de participation actuel en France est ",
      "d'environ 30 %, alors qu'il est de 40 à 74% en Europe (par ordre croissant : ",
      "Espagne, Allemagne, Italie, Grande-Bretagne, Pays-Bas, Scandinavie avec la ",
      "palme pour la Finlande). Monter le taux à 65% permettrait d'éviter au total ",
      "5.700 cancers colorectaux par an (12% des cancers colorectaux). En parallèle, ",
      "l'adaptation de l'environnement modifiable permettrait d'éviter jusqu'à la ",
      "moitié des cancers colorectaux non-génétiques.",
      "\n\n", colonoscopy_header,
      "\n\n", colonoscopy_intro,
      " Si vous êtes une personne très proche d'une personne atteinte de cancer ",
      "colorectal, votre risque du même cancer est quasi-complètement écarté par la ",
      "coloscopie de prévention familiale, qui permet de retirer les « polypes ",
      "adénomateux », avant que ceux-ci n'évoluent vers un cancer colorectal en une ",
      "dizaine d'années (« adénocarcinome » en langage médical). Typiquement, ces ",
      "coloscopies sont à renouveler au minimum tous les cinq ans à partir de 45 ans, ",
      "sans limite d'âge. L'application de cette simple coloscopie de prévention ",
      "familiale permettrait d'éviter 7.000 cancers colorectaux par an !",
      "\n\n", lifestyle)

  } else if (p_any_pct >= 10) {
    # Case: probability >= 10% - recommend oncogenetics consultation
    markdown <- paste0(markdown,
      "\n\n# Recommandation, à titre indicatif, de consultation d'oncogénétique, à discuter avec votre médecin généraliste et vos autres médecins",
      "\n\n", preamble,
      "\n\n### Probabilité d'au moins 10 %",
      "\n\nPour commencer, vérifiez que chacune des personnes apparentées atteintes de cancer ",
      "descendent potentiellement d'un même grand-parent (qui aurait transmis la ",
      "fragilité à sa descendance). Si ce n'est pas le cas (par exemple : cancer ",
      "colorectal chez le père et cancer de l'utérus chez la grand-mère maternelle), ",
      "refaites le questionnaire pour chaque hypothèse de grand-parent transmetteur ",
      "(en omettant les cas de cancer non-apparentés à ce grand-parent) et ne retenez ",
      "que l'hypothèse avec la probabilité la plus élevée ([illustration](https://preventionfamiliale.fr/files/Illustration-1.pdf)). Avec les moyens actuels limités, peu ",
      "consultations « d'oncogénétique » (génétique du cancer) peuvent donner des ",
      "rendez-vous pour faire le point quand la probabilité est d'au moins 10 %.",
      "\n\nLes rendez-vous sont donnés sans urgence, souvent avec un long délai ",
      "d'attente : en cas de symptômes [suspects](https://syndrome-de-lynch.fr/2026/01/20/connaitre-les-symptomes-dalerte-par-organe/), c'est votre médecin généraliste qui ",
      "est à consulter sans tarder !",
      "\n\nPour éviter une consultation d'oncogénétique inutile, tentez de récupérer ",
      "les résultats d'une éventuelle analyse spécifique de tumeurs suspectes survenues ",
      "chez vous ou chez vos proches (dans le « compte rendu anatomo-pathologique » ",
      "qui a fait le diagnostic de cancer (« adénocarcinome » en langage médical), ",
      "chercher les mots-clés « immunohistochimie MLH1, MSH2, MSH6, PMS2 » et/ou ",
      "« analyse des marqueurs microsatellites », recommandée systématiquement pour tous les nouveaux ",
      "cancers colorectaux depuis 2021. Une analyse normale d'une tumeur permet ",
      "d'écarter le diagnostic de syndrome de Lynch pour cette tumeur, qui doit donc ",
      "être retirée dans le questionnaire, qui est alors à refaire pour ré-évaluer ",
      "votre probabilité d'être une personne porteuse du syndrome de Lynch. Si cette ",
      "analyse reste à faire, c'est possible jusqu'à au moins 10 ans sur le ",
      "prélèvement de diagnostic conservé au laboratoire d'anatomie-pathologique, sur ",
      "prescription du médecin de la personne qui a été atteinte de cette tumeur. Si ",
      "votre probabilité reste d'au moins 10 %, ou si vous n'avez pu obtenir aucune ",
      "information complémentaire, la consultation d'oncogénétique reste indiquée.",
      "\n\nPour faciliter l'obtention d'un rendez-vous à la consultation ",
      "d'oncogénétique de votre choix ([liste des consultations d'oncogénétique](https://www.cancer.fr/professionnels-de-sante/l-organisation-de-l-offre-de-soins/organisation-des-soins-pour-les-predispositions-genetiques/le-dispositif-national-d-oncogenetique)), sauvegardez votre document de ",
      "recommandation (pdf, attention, rien n'est stocké sur ce site : refaites votre ",
      "questionnaire au besoin) et joignez-le au [document que vous obtiendrez en ",
      "cliquant ici](https://preventionfamiliale.fr/files/Tableau-Preconsultation-Oncogenetique.pdf), soigneusement rempli pour décrire vos antécédents et adressez ",
      "l'ensemble par courrier avec une lettre de votre médecin traitant.",
      "\n\n", colonoscopy_header,
      "\n\n", colonoscopy_intro,
      "\n\nSi vous êtes une personne très proche d'une personne atteinte de cancer ",
      "colorectal, votre risque de ce cancer ne peut être quasi-complètement écarté ",
      "que par la coloscopie de prévention familiale à partir de 45 ans, qui permet ",
      "de retirer les « polypes adénomateux » de votre colon, avant que ceux-ci ",
      "n'évoluent vers un « adénocarcinome » (cancer colorectal en langage médical), ",
      "en une dizaine d'années. Typiquement, ces coloscopies sont à renouveler au ",
      "minimum tous les cinq ans à partir de 45 ans, sans limite d'âge. L'application ",
      "de cette simple coloscopie de prévention familiale, insuffisamment suivie, ",
      "permettrait d'éviter 7.000 cancers colorectaux par an.",
      "\n\n## Le syndrome de Lynch étant exclu, en l'absence d'apparenté très proche ",
      "atteint de cancer colorectal, pour les personnes entre 50 et 75 ans",
      "\n\nUn risque de cancer colorectal persistant, un peu supérieur à 4% au cours ",
      "de la vie, particulièrement dans cette tranche d'âge, la participation au ",
      "dépistage organisé du cancer colorectal par l'Assurance Maladie est spécialement ",
      "indiquée pour réduire son risque ([dépistage cancer](https://www.depistagecanceraura.fr)).",
      "\n\n", lifestyle)

  } else if (p_any_pct >= 2.5) {
    # Case: probability between 2.5% and 10% - recommend discussion with GP
    markdown <- paste0(markdown,
      "\n\n# Recommandation, à titre indicatif, de discussion avec votre médecin généraliste et vos autres médecins",
      "\n\n", preamble,
      "\n\n### Probabilité entre 2,5 % et 10 %",
      "\n\nPour commencer, vérifiez que chacune des personnes apparentées atteintes de cancer ",
      "descendent potentiellement d'un même grand-parent (qui aurait transmis la ",
      "fragilité à sa descendance). Si ce n'est pas le cas (par exemple : cancer ",
      "colorectal chez le père et cancer de l'utérus chez la grand-mère maternelle), ",
      "refaites le questionnaire pour chaque hypothèse de grand-parent transmetteur ",
      "(en omettant les cas de cancer non-apparentés à ce grand-parent) et ne retenez ",
      "que l'hypothèse avec la probabilité la plus élevée ([illustration](https://preventionfamiliale.fr/files/Illustration-2.pdf)). Avec les moyens actuels limités, peu ",
      "de consultations « d'oncogénétique » (génétique du cancer) peuvent donner des ",
      "rendez-vous pour faire le point quand la probabilité est inférieure à 10 %.",
      "\n\nPour éviter une demande de consultation d'oncogénétique inutile, tentez de ",
      "récupérer les résultats d'une éventuelle analyse spécifique de tumeurs ",
      "suspectes survenues chez vous ou chez vos proches (dans le « compte ",
      "rendu anatomo-pathologique » qui a fait le diagnostic de cancer ",
      "(« adénocarcinome » en langage médical), chercher les mots-clés ",
      "« immunohistochimie MLH1, MSH2, MSH6, PMS2 » et/ou « analyse des marqueurs ",
      "microsatellites », recommandée systématiquement pour tous les nouveaux cancers colorectaux ",
      "depuis 2021. Une analyse normale d'une tumeur permet d'écarter le diagnostic ",
      "de syndrome de Lynch pour cette tumeur, qui doit donc être retirée dans le ",
      "questionnaire, qui est alors à refaire pour ré-évaluer votre probabilité ",
      "d'être une personne porteuse du syndrome de Lynch. Si cette analyse reste à ",
      "faire, c'est possible jusqu'à au moins 10 ans sur le prélèvement de diagnostic ",
      "conservé au laboratoire d'anatomie-pathologique, sur prescription du médecin ",
      "de la personne qui a été atteinte de cette tumeur.",
      "\n\nSi votre probabilité reste ",
      "d'au moins 2,5 %, ou si vous n'avez pu obtenir aucune information ",
      "complémentaire, votre médecin peut tenter de vous obtenir un rendez-vous. Ces ",
      "rendez-vous sont donnés sans urgence, souvent avec un long délai d'attente : ",
      "en cas de symptômes [suspects](https://syndrome-de-lynch.fr/2026/01/20/connaitre-les-symptomes-dalerte-par-organe/), c'est votre médecin généraliste qui est à ",
      "consulter sans tarder !",
      "\n\nPour faciliter l'obtention d'un rendez-vous à la consultation ",
      "d'oncogénétique de votre choix ([liste des consultations d'oncogénétique](https://www.cancer.fr/professionnels-de-sante/l-organisation-de-l-offre-de-soins/organisation-des-soins-pour-les-predispositions-genetiques/le-dispositif-national-d-oncogenetique)), sauvegardez votre document de ",
      "recommandation (pdf, attention, rien n'est stocké sur ce site : refaites votre ",
      "questionnaire au besoin) et joignez-le au [document que vous obtiendrez en ",
      "cliquant ici](https://preventionfamiliale.fr/files/Tableau-Preconsultation-Oncogenetique.pdf), soigneusement rempli pour décrire vos antécédents et adressez ",
      "l'ensemble par courrier avec une lettre de votre médecin.",
      "\n\n", colonoscopy_header,
      "\n\n", colonoscopy_intro,
      " Si vous êtes une personne très proche d'une personne atteinte de cancer ",
      "colorectal, votre risque du même cancer est quasi-complètement écarté par la ",
      "coloscopie de prévention familiale, qui permet de retirer les « polypes ",
      "adénomateux », avant que ceux-ci n'évoluent vers un cancer colorectal en une ",
      "dizaine d'années (« adénocarcinome » en langage médical). Typiquement, ces ",
      "coloscopies sont à renouveler au minimum tous les cinq ans à partir de 45 ans, ",
      "sans limite d'âge. L'application de cette simple coloscopie de prévention ",
      "familiale permettrait d'éviter 7.000 cancers colorectaux par an !",
      "\n\n## Le syndrome de Lynch étant exclu, en l'absence d'apparenté très proche ",
      "atteint de cancer colorectal, pour les personnes entre 50 et 75 ans",
      "\n\nUn risque de cancer colorectal persistant, un peu supérieur à 4% au cours ",
      "de la vie, particulièrement dans cette tranche d'âge, la participation au ",
      "dépistage organisé du cancer colorectal par l'Assurance Maladie est spécialement ",
      "indiquée pour réduire son risque ([dépistage cancer](https://www.depistagecanceraura.fr)).",
      "\n\n", lifestyle)

  } else {
    # Case: probability < 2.5% - Lynch syndrome unlikely
    markdown <- paste0(markdown,
      "\n\n# Recommandation, à titre indicatif, de discussion avec votre médecin généraliste et vos autres médecins",
      "\n\n", preamble,
      "\n\nLe syndrome de Lynch est peu probable d'après les seuls antécédents de ",
      "cancer dans la famille, mais il peut être évoqué à l'analyse ",
      "« anatomo-pathologique » d'un cancer destinée à le dépister, analyse ",
      "recommandée à titre systématique depuis 2021 pour le cancer colorectal et ",
      "pour le cancer du corps de l'utérus (endomètre), d'autant que cette analyse ",
      "peut orienter le choix du traitement du cancer (« immunothérapie »).",
      "\n\n", colonoscopy_header,
      "\n\n", colonoscopy_intro,
      " Si vous êtes une personne très proche d'une personne atteinte de cancer ",
      "colorectal, votre risque du même cancer est quasi-complètement écarté par la ",
      "coloscopie de prévention familiale, qui permet de retirer les « polypes ",
      "adénomateux », avant que ceux-ci n'évoluent vers un cancer colorectal en une ",
      "dizaine d'années (« adénocarcinome » en langage médical). Typiquement, ces ",
      "coloscopies sont à renouveler au minimum tous les cinq ans à partir de 45 ans, ",
      "sans limite d'âge. L'application de cette simple coloscopie de prévention ",
      "familiale permettrait d'éviter 7.000 cancers colorectaux par an !",
      "\n\n## Le syndrome de Lynch étant exclu, en l'absence d'apparenté très proche ",
      "atteint de cancer colorectal, pour les personnes entre 50 et 75 ans",
      "\n\nUn risque de cancer colorectal persistant, un peu supérieur à 4% au cours ",
      "de la vie, particulièrement dans cette tranche d'âge, la participation au ",
      "dépistage organisé du cancer colorectal par l'Assurance Maladie est spécialement ",
      "indiquée pour réduire son risque ([dépistage cancer](https://www.depistagecanceraura.fr)).",
      "\n\n", lifestyle)
  }

  # Wrap in justified text div (matching header style from CSS)
  markdown <- paste0("<div class=\"force_justify_text\">\n\n", markdown, "\n\n</div>")

  # Return list with 3 elements: markdown string, table data, and PDF options
  # Table data is a list where first element is headers, rest are data rows
  # This allows for flexible n-column tables instead of just 2-column key-value pairs
  table_data <- list(
    c("Gène/Catégorie", "Probabilité"),  # Headers
    c("MLH1", sprintf("%05.2f%%", results$p_MLH1 * 100)),
    c("MSH2/EPCAM", sprintf("%05.2f%%", results$p_MSH2_EPCAM * 100)),
    c("MSH6", sprintf("%05.2f%%", results$p_MSH6 * 100)),
    c("PMS2", sprintf("%05.2f%%", results$p_PMS2 * 100)),
    c("Total (any)", paste0(gsub("\\.", ",", sprintf("%.1f", results$p_any * 100)), "%")),
    c("None", sprintf("%05.2f%%", results$p_none * 100))
  )
  
  # PDF generation options control what gets included in the PDF report
  # include_md_in_pdf: Whether to include the markdown-formatted results
  # include_data_in_pdf: Whether to include the structured data table
  # Only the markdown string (with Total probability) is shown in PDF, not the detailed table
  pdf_options <- list(
    include_md_in_pdf = TRUE,
    include_data_in_pdf = FALSE
  )
  
  list(
    markdown,
    table_data,
    pdf_options
  )
}
