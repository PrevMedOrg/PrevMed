# PrevMed (Prévention Médicale)

**Plateforme minimaliste permettant à des personnes non techniques de produire des questionnaires cliniques ne stockant aucune information personnelle.**

> 📖 **English version available:** See [README_english.md](https://github.com/PrevMedOrg/PrevMed/blob/main/README_english.md) for the English documentation.

## Table des matières

- [Objectif Principal](#objectif-principal)
- [Description Technique](#description-technique)
- [Installation](#installation)
  - [Prérequis](#prérequis)
  - [Installation des dépendances](#installation-des-dépendances)
  - [Déploiement avec Docker](#déploiement-avec-docker)
- [Utilisation](#utilisation)
  - [Lancement basique](#lancement-basique)
  - [Exemple avec PREMM5](#exemple-avec-premm5)
  - [Options de ligne de commande](#options-de-ligne-de-commande)
- [Analytics (Optionnel)](#analytics-optionnel)
  - [Configuration](#configuration)
- [Configuration du questionnaire (YAML)](#configuration-du-questionnaire-yaml)
  - [Types de widgets disponibles](#types-de-widgets-disponibles)
  - [Logique conditionnelle](#logique-conditionnelle)
- [Scripts de scoring](#scripts-de-scoring)
  - [Script R](#script-r)
  - [Script Python](#script-python)
- [Génération de rapports PDF](#génération-de-rapports-pdf)
  - [Gestion des fichiers temporaires](#gestion-des-fichiers-temporaires)
- [Stockage des données structurées (si activé)](#stockage-des-données-structurées-si-activé)
  - [Fichiers JSON compressés (si `--save-user-data` activé)](#fichiers-json-compressés-si---save-user-data-activé)
  - [Logs CSV (si `--save-user-data` activé)](#logs-csv-si---save-user-data-activé)
- [Structure du projet](#structure-du-projet)
- [Logs](#logs)
- [Exemple PREMM5](#exemple-premm5)
- [Développement](#développement)
  - [Conventions de code](#conventions-de-code)
  - [Contributions](#contributions)
- [Licence](#licence)
- [Références](#références)

## Objectif Principal

PrevMed est conçu pour **simplifier le workflow clinique** en permettant aux professionnels de santé de créer facilement des questionnaires d'aide à la décision clinique avec des compétences courantes en programmation : un script en langage [R](https://en.wikipedia.org/wiki/R_%28programming_language%29) (ou [Python](https://en.wikipedia.org/wiki/Python_(programming_language))) et un fichier `.yaml`.

**Fonctionnement :**
1. Le patient remplit le questionnaire sur l'interface web
2. Un PDF avec les réponses et résultats est généré instantanément
3. Le patient vient en consultation avec ce PDF
4. **Aucune donnée personnelle n'est stockée** sur le serveur

Ce système fait **gagner du temps à tout le monde** : le patient prépare ses réponses en amont, et le clinicien dispose immédiatement d'informations structurées et de scores calculés automatiquement.

## Description Technique

PrevMed permet de créer des questionnaires cliniques interactifs à partir de fichiers de configuration YAML. Le système génère automatiquement une interface web avec Gradio, gère la logique conditionnelle des questions, exécute des scripts de scoring (R ou Python), et produit des rapports PDF.

**Caractéristiques principales :**

- ✨ Configuration déclarative via YAML
- 🔀 Questions conditionnelles (affichage dynamique basé sur les réponses précédentes)
- 📊 Support de scripts de scoring en R (via rpy2) ou Python
- 🖥️ Interface web intuitive avec Gradio
- 📄 Génération automatique de rapports PDF
- 📝 Logging détaillé avec loguru
- 🎯 Type hints et documentation NumPy style

## Installation

### Prérequis

- Python, arbitrairement fixé à 3.13.5 pour sa vitesse sans être aussi récent que 3.14.
- R et rpy2 si vous utilisez des scripts de scoring en R. Sur ubuntu il suffit de `sudo apt install r-base`.
- Sur ubuntu 22.04, vous pouvez avoir besoin de `sudo apt-get install libtirpc-dev` ([source](https://github.com/rpy2/rpy2/issues/1106#issuecomment-2118710471))

### Installation des dépendances

Après avoir téléchargé le repo, commencez par créer un venv:

```bash
uv venv
source .venv/bin/activate
```

```bash
uv pip install .
```

**Note :** Sur certains systèmes, vous devrez peut-être installer R séparément avant d'installer rpy2.

### Déploiement avec Docker

PrevMed peut être déployé avec Docker pour une installation simplifiée et isolée :

```bash
# Cloner le repository
git clone https://github.com/PrevMedOrg/PrevMed
cd PrevMed

# Accéder au répertoire docker
cd docker

# Modifier docker-compose.yml pour spécifier les arguments souhaités dans la section 'command'
# Par exemple: --survey-yaml, --scoring-script, --save-user-data, etc.

# Lancer le conteneur en arrière-plan
sudo docker compose up --build -d
```

**Gestion des volumes :**
- Les dossiers `logs/` et `survey_data/` sont **montés comme volumes** pour persister les données entre redémarrages
- Le dossier `temp_pdfs/` n'est **pas monté** pour garantir qu'il reste non-persistant et respecte la vie privée

Cette configuration permet de bénéficier de l'isolation Docker tout en conservant les logs et données importantes, sans compromettre la nature temporaire des PDFs.

## Utilisation

### Lancement basique

```bash
prevmed --survey-yaml <chemin_yaml> --scoring-script <chemin_script>
```

### Exemple avec PREMM5

Le projet inclut un exemple complet du questionnaire PREMM5 (évaluation du risque de syndrome de Lynch) :

```bash
prevmed --survey-yaml examples/PREMM5/premm5.yaml --scoring-script examples/PREMM5/premm5.R
```

Ceci lancera une interface Gradio accessible via votre navigateur web.

### Options de ligne de commande

PrevMed supporte plusieurs options pour personnaliser le comportement de l'application :

#### Sauvegarde des données utilisateur

Par défaut, **aucune donnée utilisateur n'est sauvegardée**. Les rapports PDF générés sont créés comme **fichiers temporaires** uniquement pour le téléchargement par le patient, sans logging des réponses ou des résultats.

Pour **sauvegarder les données utilisateur de manière permanente** (dans le répertoire `survey_data/`), utilisez l'option `--save-user-data` :

```bash
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --save-user-data
```

**Avec `--save-user-data` activé, les données suivantes sont sauvegardées :**
- Fichiers JSON compressés (`.json.gz`) contenant toutes les réponses et résultats
- Logs CSV centralisés pour analyse rapide
- Rapports PDF stockés de manière permanente

**Sans cette option (comportement par défaut) :**
- Seuls des PDFs temporaires sont créés pour le téléchargement
- Aucune donnée n'est loggée dans les fichiers CSV
- Aucun fichier JSON n'est sauvegardé
- Respect maximal de la vie privée des patients

#### Autres options utiles

```bash
# Ouvrir automatiquement le navigateur au démarrage
prevmed --survey-yaml <yaml> --scoring-script <script> --open-browser

# Utiliser un port personnalisé (par défaut: 7860)
prevmed --survey-yaml <yaml> --scoring-script <script> --port 8080

# Activer le logging de niveau debug dans la console
prevmed --survey-yaml <yaml> --scoring-script <script> --debug

# Spécifier l'URL réelle où le questionnaire est hébergé (apparaîtra dans les PDFs)
prevmed --survey-yaml <yaml> --scoring-script <script> --actual-url "https://survey.hopital.fr/premm5"
```

#### Arguments supplémentaires pour demo.launch()

PrevMed permet de passer **n'importe quel argument supporté par Gradio** directement à `demo.launch()`. Tous les arguments non reconnus par PrevMed sont automatiquement transmis à Gradio.

**Formats supportés :**

```bash
# Arguments avec valeur (chaîne, int, float)
prevmed --survey-yaml <yaml> --scoring-script <script> --gradio-option value

# Drapeaux booléens (True)
prevmed --survey-yaml <yaml> --scoring-script <script> --enable-feature

# Drapeaux booléens (False)
prevmed --survey-yaml <yaml> --scoring-script <script> --no-disable-feature
```

**Exemples pratiques :**

```bash
# Désactiver la fermeture automatique du serveur après inactivité
prevmed --survey-yaml <yaml> --scoring-script <script> --prevent-thread-lock

# Activer le mode favicon personnalisé
prevmed --survey-yaml <yaml> --scoring-script <script> --favicon-path /path/to/favicon.ico

# Combiner plusieurs arguments
prevmed --survey-yaml <yaml> --scoring-script <script> \
    --max-file-size 10000000 \
    --allowed-paths /data /images \
    --no-show-error
```

**Note :** Consultez la [documentation Gradio Blocks](https://www.gradio.app/docs/gradio/blocks) pour la liste complète des arguments supportés par `demo.launch()`.

#### Options de performance

PrevMed inclut des options pour optimiser les performances sous charge importante :

```bash
# Augmenter le nombre maximum de threads (par défaut: 40)
prevmed --survey-yaml <yaml> --scoring-script <script> --max-threads 100

# Désactiver la file d'attente des requêtes (activée par défaut)
prevmed --survey-yaml <yaml> --scoring-script <script> --no-queue
```

**Note :** La file d'attente (`queue`) est **activée par défaut** car elle améliore les performances sous charge. Pour plus d'informations sur l'optimisation des performances de Gradio, consultez le guide officiel : [Setting Up a Demo for Maximum Performance](https://www.gradio.app/guides/setting-up-a-demo-for-maximum-performance).

## Analytics (Optionnel)

PrevMed supporte l'intégration de [Umami](https://umami.is/), une solution d'analytics respectueuse de la vie privée, self-hostable, open-source, respectant le RGPD et avec une option gratuite.

### Configuration

Pour activer l'analytics, utilisez les arguments de ligne de commande `--umami-website-id` et optionnellement `--umami-url` :

```bash
# Option 1: Utiliser le service cloud gratuit Umami (cloud.umami.is)
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-website-id "votre-website-id"

# Option 2: Utiliser votre propre instance Umami auto-hébergée
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-url "https://votre-instance.example.com" \
              --umami-website-id "votre-website-id"
```

**Exemple complet :**

```bash
# Avec cloud.umami.is (gratuit)
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-website-id "70991a3f-4cc9-49ae-a848-867bc75a1fd1"

# Avec instance auto-hébergée
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-url "https://analytics.monhopital.fr" \
              --umami-website-id "70991a3f-4cc9-49ae-a848-867bc75a1fd1"
```

**Note :** Si aucun argument analytics n'est fourni, l'application fonctionne sans analytics.

## Configuration du questionnaire (YAML)

Les questionnaires sont définis dans des fichiers YAML avec la structure suivante :

```yaml
survey_name: Nom du questionnaire

# Uniquement pour être mentionnée dans les logs etc:
survey_version: 1.0.0
PrevMed_version: 1.0.0

# Optionnel: texte d'en-tête affiché en haut du questionnaire (format Markdown)
header: |
  ## À propos de ce questionnaire

  Description du questionnaire...

questions:
  - variable: nom_variable
    order: 1
    widget: Radio|Number|Checkbox|Textbox
    widget_args:
      # Arguments spécifiques au widget
      choices: ["Option1", "Option2"]  # Pour Radio
      precision: 0  # Pour Number
      step: 1  # Pour Slider
      label: "Texte du widget"          # Optionnel: par défaut utilise question
    question: "Texte de la question"
    skip_if: "(nom_variable == 2) and (nom_variable > autre_variable)"  # Si l'expression vaut True alors la question n'est pas posée (l'expression doit être en Python et a accès aux variables du reste du script.)
```


### Types de widgets disponibles

Par principe, PrevMed devrait marcher avec n'importe quel widget Gradio. La liste des widgets Gradio est disponible [ici](https://www.gradio.app/docs/gradio). Les widgets suivants sont les plus utilisés:

- **Radio** : Boutons radio pour choix unique
  - `choices` : Liste des options (requis)
- **Number** : Champ numérique avec contrôles
- **Checkbox** : Case à cocher booléenne
- **Textbox** : Champ texte libre

### Logique conditionnelle

PrevMed supporte deux types de logique conditionnelle :

#### 1. Affichage conditionnel des questions (`skip_if`)

Les questions peuvent être affichées ou masquées dynamiquement via le champ `skip_if`. Les conditions sont des expressions Python évaluées avec les valeurs des variables précédentes :

```yaml
- variable: age_diagnostic
  skip_if: "not (diagnostic_positif == True)"
  # Cette question ne s'affiche que si diagnostic_positif n'est pas True

- variable: age_crc_proband
  skip_if: "personal_crc_count == 0"
  # Cette question est ignorée si le patient n'a aucun cancer colorectal
```

**Points importants :**
- L'expression retourne `True` → la question est **ignorée**
- L'expression retourne `False` → la question est **affichée**
- Les expressions peuvent utiliser toutes les variables des questions précédentes
- Les opérateurs Python standards sont supportés (`==`, `!=`, `>`, `<`, `and`, `or`, `not`, etc.)

#### 2. Validation des réponses (`valid_if`)

Les réponses peuvent être validées avant de passer à la question suivante via le champ `valid_if`. Si la validation échoue, un message d'erreur est affiché et l'utilisateur doit corriger sa réponse :

```yaml
- variable: current_age
  widget: Number
  question: "Âge actuel du patient (en années)"
  valid_if: "current_age >= 15 and current_age <= 120"
  invalid_message: "L'âge doit être compris entre 15 et 120 ans."

- variable: personal_crc_count
  widget: Number
  question: "Combien de cancers colorectaux ?"
  valid_if: "personal_crc_count >= 0"
  invalid_message: "Le nombre de cancers ne peut pas être négatif."
```

**Points importants :**
- L'expression retourne `True` → la réponse est **valide**, on peut continuer
- L'expression retourne `False` → la réponse est **invalide**, un avertissement est affiché
- Le champ `invalid_message` (optionnel) permet de personnaliser le message d'erreur
- Si `invalid_message` n'est pas fourni, un message par défaut est utilisé
- La validation s'exécute avant de passer à la question suivante

## Scripts de scoring

### Script R

Le script R doit définir une fonction `scoring()` qui prend les variables du questionnaire comme arguments nommés et retourne une liste avec **3 éléments** :

1. Une chaîne de caractères contenant du **markdown** à afficher au patient
2. Une liste de listes représentant une **table** (première liste = headers, suivantes = lignes de données)
3. Une liste nommée avec les **options PDF** (`include_md_in_pdf` et `include_data_in_pdf`)

```r
scoring <- function(variable1, variable2 = NULL, ...) {
  # Logique de calcul
  score_total <- 0.40
  
  # Générer le texte markdown à afficher
  markdown_result <- sprintf("## Résultats\n\nVotre score total est: %.1f%%", score_total * 100)
  
  # Créer la table de données (format: liste de listes)
  # Première liste = headers, suivantes = lignes de données
  table_data <- list(
    c("Catégorie", "Probabilité"),  # Headers
    c("Catégorie 1", sprintf("%.2f%%", 0.15 * 100)),
    c("Catégorie 2", sprintf("%.2f%%", 0.25 * 100)),
    c("Total", sprintf("%.2f%%", 0.40 * 100))
  )
  
  # Options de génération PDF
  pdf_options <- list(
    include_md_in_pdf = TRUE,    # Inclure le markdown dans le PDF
    include_data_in_pdf = TRUE   # Inclure la table de données dans le PDF
  )
  
  # Retourner une liste avec 3 éléments
  list(
    markdown_result,  # Élément 1: texte markdown
    table_data,       # Élément 2: table de données
    pdf_options       # Élément 3: options PDF
  )
}
```

**Points importants :**
- Les paramètres conditionnels doivent avoir `= NULL` comme valeur par défaut
- Retourner une **liste avec 3 éléments** : markdown, table_data, pdf_options
- Le **premier élément** est une chaîne markdown affichée au patient
- Le **deuxième élément** est une liste de listes où la première liste contient les headers et les suivantes les lignes de données
- Le **troisième élément** contrôle ce qui est inclus dans le PDF (markdown et/ou table)
- Les noms de paramètres doivent correspondre aux noms de variables du YAML

### Script Python

Le script Python doit définir une fonction `scoring()` qui retourne un **tuple avec 3 éléments** :

1. Une chaîne contenant du **markdown** à afficher au patient
2. Une liste de listes représentant une **table** (première liste = headers, suivantes = lignes de données)
3. Un dictionnaire avec les **options PDF** (`include_md_in_pdf` et `include_data_in_pdf`)

```python
def scoring(variable1: str, variable2: int = None, **kwargs) -> tuple[str, list[list[str]], dict[str, bool]]:
    """Calcul du score."""
    # Logique de calcul
    score_total = 0.40
    
    # Générer le texte markdown à afficher
    markdown_result = f"## Résultats\n\nVotre score total est: {score_total * 100:.1f}%"
    
    # Créer la table de données (format: liste de listes)
    # Première liste = headers, suivantes = lignes de données
    table_data = [
        ["Catégorie", "Probabilité"],  # Headers
        ["Catégorie 1", f"{0.15 * 100:.2f}%"],
        ["Catégorie 2", f"{0.25 * 100:.2f}%"],
        ["Total", f"{0.40 * 100:.2f}%"]
    ]
    
    # Options de génération PDF
    pdf_options = {
        "include_md_in_pdf": True,    # Inclure le markdown dans le PDF
        "include_data_in_pdf": True   # Inclure la table de données dans le PDF
    }
    
    # Retourner un tuple avec 3 éléments
    return (markdown_result, table_data, pdf_options)
```

**Points importants :**
- Retourner un **tuple avec 3 éléments** : markdown, table_data, pdf_options
- Le **premier élément** est une chaîne markdown affichée au patient
- Le **deuxième élément** est une liste de listes où la première liste contient les headers et les suivantes les lignes de données
- Le **troisième élément** contrôle ce qui est inclus dans le PDF (markdown et/ou table)
- Les valeurs de la table peuvent être de n'importe quel type (elles seront converties en chaînes automatiquement)
- Les noms de paramètres doivent correspondre aux noms de variables du YAML

## Génération de rapports PDF

Les rapports PDF sont générés automatiquement à la fin du questionnaire et incluent :

- Nom et version du questionnaire
- Code de référence unique (format XXX-YYY, facile à mémoriser)
- Horodatage de génération
- Résultats du scoring (texte formaté + tableau structuré)
- Toutes les réponses aux questions

### Gestion des fichiers temporaires

**Stockage des PDFs :**
- **Par défaut** : fichiers temporaires stockés dans `temp_pdfs/` uniquement pour téléchargement (non sauvegardés de manière permanente)
- **Avec `--save-user-data`** : sauvegarde permanente dans `survey_data/` en plus du PDF temporaire

**Nettoyage automatique :**

Pour éviter l'accumulation de fichiers temporaires, PrevMed implémente un système de nettoyage automatique multi-niveaux :

- **Au démarrage de l'application** : le répertoire `temp_pdfs/` est intégralement supprimé s'il existe
- **Avant chaque génération de PDF** : tous les fichiers du répertoire `temp_pdfs/` **plus anciens qu'1 heure** sont automatiquement supprimés
- **À l'arrêt de l'application** : le répertoire `temp_pdfs/` est intégralement supprimé
- Ce nettoyage multi-niveaux garantit qu'aucun fichier temporaire ne reste indéfiniment sur le serveur
- Le répertoire `temp_pdfs/` est créé automatiquement au premier besoin
- Même sous charge élevée, le système maintient un répertoire propre et performant

**Exemple de cycle de vie d'un PDF temporaire :**

1. Patient complète le questionnaire à 14h00
2. PDF généré dans `temp_pdfs/survey_ABC-XYZ_1729500000.pdf`
3. Patient télécharge le PDF immédiatement
4. À 15h30, un autre patient génère son PDF
5. Le système nettoie automatiquement tous les PDFs créés avant 14h30 (plus d'1h)
6. Le PDF de 14h00 est supprimé automatiquement, libérant l'espace disque

Cette approche assure **zéro maintenance manuelle** tout en respectant la vie privée des patients.

## Stockage des données structurées (si activé)

Lorsque l'option `--save-user-data` est activée, PrevMed sauvegarde toutes les données sous deux formats complémentaires :

### Fichiers JSON compressés (si `--save-user-data` activé)

Avec `--save-user-data`, chaque soumission est sauvegardée en JSON compressé (`.json.gz`) dans `survey_data/` avec :
- Nom du questionnaire et versions
- Réponses complètes
- Résultats de scoring
- Code de référence unique
- Timestamp Unix
- Hashes de client (pour détection de doublons anonyme)

**Format du nom de fichier :** `{timestamp}_{reference_code}.json.gz`

**Exemple :** `1729500000_A2B-3C4.json.gz`

### Logs CSV (si `--save-user-data` activé)

Avec `--save-user-data`, un **fichier CSV centralisé** enregistre toutes les soumissions pour analyse rapide :

**Emplacement :** `survey_data/csv/{PrevMed_version}/{survey_name}_{survey_version}/survey_submissions.csv`

**Exemple :** `survey_data/csv/0.8.0/PREMM5_2.0/survey_submissions.csv`

#### Caractéristiques du système CSV

**Structure des colonnes :**
- Colonnes fixes : `reference_code`, `row_number`, `timestamp_unix`, `datetime`
- Colonnes de scoring : une par résultat (ex: `p_MLH1`, `p_MSH2`, formatées en pourcentages)
- Colonnes de hashes : `answers_hash` + hashes individuels par attribut client (ex: `user_agent_hash`, `ip_address_hash`)

**Gestion de la concurrence :**
- Utilise `filelock` pour garantir l'atomicité des écritures
- Supporte l'accès concurrent depuis plusieurs processus/serveurs
- Timeout de 10 secondes sur le verrou

**Rotation automatique :**
- Le CSV est automatiquement archivé après 1000 lignes
- Fichier archivé : `survey_submissions_{timestamp}.csv` (sauvegarde permanente)
- Nouveau CSV créé automatiquement pour continuer l'enregistrement
- **Objectif :** maintenir des performances élevées même avec accès concurrent intensif

**Gestion des erreurs :**
- En cas de timeout du verrou (charge très élevée), les données sont sauvegardées dans un fichier de secours
- Format : `survey_submissions_fallback_{timestamp}_{random}.csv`
- **Garantie :** aucune perte de données même sous charge extrême

**Détection de doublons :**
- `answers_hash` : hash court (12 caractères) des réponses uniquement
- Hashes individuels de client : chaque attribut (user-agent, IP, etc.) haché séparément avec le code de référence comme sel
- Permet l'analyse de doublons tout en préservant la vie privée

**Exemple de contenu CSV :**

```csv
reference_code,row_number,timestamp_unix,datetime,p_MLH1,p_MSH2,p_MSH6,p_PMS2,p_total,answers_hash,user_agent_hash,ip_address_hash,session_hash_hash
A2B-3C4,1,1729500000,2024-10-21 14:20:00,15.23,25.47,8.92,10.38,60.00,a1b2c3d4e5f6,x9y8z7w6v5u4,q1w2e3r4t5y6,m1n2b3v4c5x6
D5E-6F7,2,1729500120,2024-10-21 14:22:00,2.15,3.28,1.45,1.12,8.00,f6e5d4c3b2a1,u4v5w6z7y8x9,y6t5r4e3w2q1,x6c5v4b3n2m1
```

**Avantages de cette architecture :**
- **Performance** : rotation limite la taille des fichiers pour maintenir vitesse d'accès
- **Fiabilité** : système de fallback garantit zéro perte de données
- **Traçabilité** : archivage automatique avec timestamps
- **Analyse** : format CSV facilite l'analyse statistique rapide
- **Scalabilité** : gestion de concurrence permet déploiement multi-processus/multi-serveurs
- **Vie privée** : hashes salés permettent détection de doublons sans stocker données personnelles brutes

## Structure du projet

```
PrevMed/
├── src/
│   ├── __init__.py          # Setup du logging
│   ├── __main__.py          # Point d'entrée CLI
│   └── utils/
│       ├── gui.py           # Interface Gradio
│       ├── css.py           # Le CSS utilisé dans Gradio
│       ├── js.py            # Le js utilisé dans Gradio
│       ├── io.py            # Chargement YAML et scripts
│       ├── logic.py         # Logique conditionnelle
│       ├── pdf.py           # Génération PDF
│       ├── scoring.py       # Exécution scripts R/Python
│       └── settings.py      # Stocke des variables disponibles dans tout le script
├── examples/
│   └── PREMM5/
│       ├── premm5.yaml      # Configuration PREMM5
│       └── premm5.R         # Script de scoring PREMM5
├── logs/                    # Logs rotatifs (créé automatiquement)
├── survey_pdfs/             # Rapports PDF (créé automatiquement)
├── requirements.txt
└── setup.py
```

## Logs

Les logs sont automatiquement sauvegardés dans `./logs/` avec rotation journalière et rétention de 365 jours. Le format inclut :

- Horodatage avec millisecondes
- Niveau de log
- Fichier, fonction et ligne
- Message

## Exemple PREMM5

Le questionnaire PREMM5 évalue le risque de mutations dans les gènes MLH1, MSH2, MSH6 et PMS2 (syndrome de Lynch) basé sur :

- L'histoire personnelle de cancers (colorectal, endomètre, autres)
- Les âges au diagnostic
- L'histoire familiale (apparentés du 1er et 2ème degré)

Le scoring utilise un modèle de régression logistique multinomiale avec transformation softmax pour calculer les probabilités de mutation pour chaque gène.

## Développement

### Conventions de code

- Type hints et docstrings NumPy style partout
- Commentaires explicites pour les décisions de design
- Utilisation de `loguru` pour le logging
- Code simple et robuste privilégié
- Utilisation de [Ruff](https://astral.sh/ruff) comme linter pour assurer la qualité du code

### Contributions

Ce projet a été développé avec l'assistance de [aider.chat](https://github.com/Aider-AI/aider/).

**Nous accueillons volontiers :**
- 🐛 Les signalements de bugs via les [Issues](https://github.com/PrevMedOrg/PrevMed/issues)
- ✨ Les demandes de fonctionnalités
- 🔧 Les Pull Requests pour améliorer le projet

N'hésitez pas à contribuer !

## Licence

Actuellement sous licence GPL-v3. Cependant, nous sommes flexibles et ouverts à des arrangements de licence alternatifs - n'hésitez pas à nous contacter si vous avez besoin d'une licence différente pour votre cas d'usage.

## Références

Pour PREMM5 :
- Kastrinos F, et al. "Development and Validation of the PREMM5 Model for Comprehensive Risk Assessment of Lynch Syndrome." J Clin Oncol. 2017.
