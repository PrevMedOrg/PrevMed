[![PyPI version](https://badge.fury.io/py/prevmed.svg)](https://badge.fury.io/py/prevmed) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

> 📖 **Version francaise disponible:** Voir [README.md](https://github.com/PrevMedOrg/PrevMed/blob/main/README.md).

# PrevMed (Preventive Medicine)

**Minimalist platform allowing non-technical people to create clinical questionnaires that store no personal information.**

## Table of Contents

- [Main Objective](#main-objective)
- [Technical Description](#technical-description)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Installing dependencies](#installing-dependencies)
  - [Docker Deployment](#docker-deployment)
- [Usage](#usage)
  - [Basic launch](#basic-launch)
  - [Example with ProbaLYNCH](#example-with-probalynch)
  - [Command line options](#command-line-options)
- [Analytics (Optional)](#analytics-optional)
  - [Configuration](#configuration)
- [Survey configuration (YAML)](#survey-configuration-yaml)
  - [Available widget types](#available-widget-types)
  - [Conditional logic](#conditional-logic)
- [Scoring scripts](#scoring-scripts)
  - [R Script](#r-script)
  - [Python Script](#python-script)
- [PDF Report Generation](#pdf-report-generation)
  - [Temporary file management](#temporary-file-management)
- [Structured Data Storage (if enabled)](#structured-data-storage-if-enabled)
  - [Compressed JSON files (if `--save-user-data` enabled)](#compressed-json-files-if---save-user-data-enabled)
  - [CSV logs (if `--save-user-data` enabled)](#csv-logs-if---save-user-data-enabled)
- [Project Structure](#project-structure)
- [Logs](#logs)
- [ProbaLYNCH Example](#probalynch-example)
- [Development](#development)
  - [Code conventions](#code-conventions)
  - [Contributions](#contributions)
- [License](#license)
- [References and Credits](#references-and-credits)

## Main Objective

PrevMed is designed to enable healthcare professionals with minimal IT skills to easily create clinical decision support questionnaires with a script ([R](https://en.wikipedia.org/wiki/R_%28programming_language%29) or [Python](https://en.wikipedia.org/wiki/Python_(programming_language))) and a `.yaml` file.

**How it works:**
1. The patient fills out the questionnaire on the web interface
2. A PDF with answers and results is generated instantly
3. The patient comes to consultation with this PDF
4. **No personal data is stored** on the server

This system **saves everyone time**: the patient prepares their answers in advance and the clinician immediately has structured information, or even automatically calculated scores, as in the ProbaLynch application, an example application of PrevMed.

## Technical Description

PrevMed allows creating interactive clinical questionnaires from YAML configuration files. The system automatically generates a web interface with Gradio, handles conditional question logic, executes scoring scripts (R or Python) and produces PDF reports.

**Main features:**

- ✨ Declarative configuration via YAML
- 🔀 Conditional questions (dynamic display based on previous answers)
- 📊 Support for scoring scripts in R (via rpy2) or Python
- 🖥️ Intuitive web interface with Gradio
- 📄 Automatic PDF report generation
- 📝 Detailed logging with loguru
- 🎯 Type hints and NumPy style documentation
- 🔒 System fonts only — no requests to Google Fonts or any external server (privacy-friendly)

## Installation

PrevMed can be installed in several ways depending on your needs:

### Method 1: Install from PyPI (Recommended for end users)

The simplest method for production use:

```bash
# Install PrevMed from PyPI
uv pip install PrevMed

# Or with traditional pip
pip install PrevMed
```

**Prerequisites:**
- Python 3.13.5 (or compatible version)
- R and rpy2 if you use R scoring scripts: `sudo apt install r-base`
- On Ubuntu 22.04, you might need: `sudo apt-get install libtirpc-dev` ([source](https://github.com/rpy2/rpy2/issues/1106#issuecomment-2118710471))

**Note:** You'll still need to clone the repository or download the examples separately to access sample YAML files and scoring scripts.

### Method 2: Install from source (Recommended for development)

For development or customization:

```bash
# Clone the repository
git clone https://github.com/PrevMedOrg/PrevMed
cd PrevMed

# Create and activate a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
uv pip install -e .
```

**Prerequisites:** Same as Method 1

### Method 3: Docker from PyPI (Production deployment)

For containerized production deployment without local source code:

```bash
# Clone the repository (only needed for docker-compose.yml and examples)
git clone https://github.com/PrevMedOrg/PrevMed
cd PrevMed

# Navigate to the docker directory
cd docker

# Modify docker-compose.yml to set INSTALL_MODE to "pypi"
# Change the line: INSTALL_MODE: local
# To: INSTALL_MODE: pypi

# Optionally modify the 'command' section to specify desired arguments
# For example: --survey-yaml, --scoring-script, --save-user-data, etc.

# Launch the container in detached mode (builds and installs from PyPI)
sudo docker compose up --build -d
```

**Note:** The examples directory will be mounted from your local clone. You can also provide your own YAML and scoring scripts by modifying the volume mounts in docker-compose.yml.

### Method 4: Docker from source (Development)

For containerized development with local source code:

```bash
# Clone the repository
git clone https://github.com/PrevMedOrg/PrevMed
cd PrevMed

# Navigate to the docker directory
cd docker

# Ensure INSTALL_MODE is set to "local" in docker-compose.yml (this is the default)

# Optionally modify the 'command' section to specify desired arguments
# For example: --survey-yaml, --scoring-script, --save-user-data, etc.

# Launch the container in detached mode (builds from local source)
sudo docker compose up --build -d
```

**Volume management:**
- The `logs/` and `survey_data/` folders are **mounted as volumes** to persist data between restarts
- PDFs are generated in-memory and served via `/dev/shm` (RAM tmpfs, no disk files) by default, ensuring maximum privacy

**Docker container security:**
- The container runs as the unprivileged `nobody` user (no root)
- The container filesystem is **read-only** (`read_only: true`), except for mounted volumes (`logs/` and `survey_data/`)
- These measures follow Docker security best practices and reduce the attack surface

This configuration allows you to benefit from Docker isolation while preserving important logs and data, without creating any temporary files on disk.

## Usage

### Basic launch

```bash
prevmed --survey-yaml <yaml_path> --scoring-script <script_path>
```

### Example with ProbaLYNCH

The project includes a complete example of the ProbaLYNCH questionnaire (see [References and Credits](#references-and-credits)) for Lynch syndrome risk assessment:

```bash
prevmed --survey-yaml examples/ProbaLYNCH/ProbaLYNCH.yaml --scoring-script examples/ProbaLYNCH/ProbaLYNCH.R
```

This will launch a Gradio interface accessible via your web browser.

### Command line options

PrevMed supports several options to customize application behavior:

#### User data saving

By default, **no user data is saved**. PDF reports are generated in-memory and briefly written to `/dev/shm` (RAM, chmod 600) only for patient download — **no files are ever written to disk**, no answers or results are logged.

To **save user data permanently** (in the `survey_data/` directory), use the `--save-user-data` option:

```bash
prevmed --survey-yaml examples/ProbaLYNCH/ProbaLYNCH.yaml \
              --scoring-script examples/ProbaLYNCH/ProbaLYNCH.R \
              --save-user-data
```

**With `--save-user-data` enabled, the following data is saved:**
- Compressed JSON files (`.json.gz`) containing all answers and results
- Centralized CSV logs for quick analysis
- PDF reports stored permanently in `survey_data/`

**Without this option (default behavior):**
- PDFs are generated in-memory and briefly written to `/dev/shm` (RAM, chmod 600) for download — **no files written to disk**
- No data is logged in CSV files
- No JSON files are saved
- Maximum respect for patient privacy - zero disk footprint

#### Other useful options

```bash
# Automatically open browser on startup
prevmed --survey-yaml <yaml> --scoring-script <script> --open-browser

# Use a custom port (default: 7860)
prevmed --survey-yaml <yaml> --scoring-script <script> --port 8080

# Enable debug level logging in console
prevmed --survey-yaml <yaml> --scoring-script <script> --debug

# Specify the actual URL where the questionnaire is hosted (will appear in PDFs)
prevmed --survey-yaml <yaml> --scoring-script <script> --actual-url "https://survey.hospital.com/probalynch"

# Display GDPR legal notices at the bottom of the page (collapsible <details> element)
# ⚠️  MANDATORY: the application refuses to start without this file.
# The file must contain at minimum: data controller identity, purposes,
# retention period, and data subject rights (GDPR art. 13/14).
prevmed --survey-yaml <yaml> --scoring-script <script> --terms-md legal_notices.md
```

#### Additional arguments for demo.launch()

PrevMed allows passing **any argument supported by Gradio** directly to `demo.launch()`. All arguments not recognized by PrevMed are automatically forwarded to Gradio.

**Supported formats:**

```bash
# Arguments with value (string, int, float)
prevmed --survey-yaml <yaml> --scoring-script <script> --gradio-option value

# Boolean flags (True)
prevmed --survey-yaml <yaml> --scoring-script <script> --enable-feature

# Boolean flags (False)
prevmed --survey-yaml <yaml> --scoring-script <script> --no-disable-feature
```

**Practical examples:**

```bash
# Disable automatic server shutdown after inactivity
prevmed --survey-yaml <yaml> --scoring-script <script> --prevent-thread-lock

# Enable custom favicon mode
prevmed --survey-yaml <yaml> --scoring-script <script> --favicon-path /path/to/favicon.ico

# Combine multiple arguments
prevmed --survey-yaml <yaml> --scoring-script <script> \
    --max-file-size 10000000 \
    --allowed-paths /data /images \
    --no-show-error
```

**Note:** See the [Gradio Blocks documentation](https://www.gradio.app/docs/gradio/blocks) for the complete list of arguments supported by `demo.launch()`.

#### Performance options

PrevMed includes options to optimize performance under heavy load:

```bash
# Increase maximum number of threads (default: 40)
prevmed --survey-yaml <yaml> --scoring-script <script> --max-threads 100

# Disable request queue (enabled by default)
prevmed --survey-yaml <yaml> --scoring-script <script> --no-queue
```

**Note:** The queue is **enabled by default** as it improves performance under load. For more information on optimizing Gradio performance, see the official guide: [Setting Up a Demo for Maximum Performance](https://www.gradio.app/guides/setting-up-a-demo-for-maximum-performance).

## Analytics (Optional)

PrevMed supports integration with [Umami](https://umami.is/), a privacy-friendly, self-hostable, open-source analytics solution that is GDPR compliant and has a free option.

**Privacy note:** Umami is configured by default to respect the Do Not Track (DNT) browser setting - users who have enabled DNT in their browser will not be tracked. This option can be modified with the `--umami-ignore-dnt` parameter if necessary.

### Configuration

To enable analytics, use the command line arguments `--umami-website-id` and optionally `--umami-url`:

```bash
# Option 1: Use the free Umami cloud service (cloud.umami.is)
prevmed --survey-yaml examples/ProbaLYNCH/ProbaLYNCH.yaml \
              --scoring-script examples/ProbaLYNCH/ProbaLYNCH.R \
              --umami-website-id "your-website-id"

# Option 2: Use your own self-hosted Umami instance
prevmed --survey-yaml examples/ProbaLYNCH/ProbaLYNCH.yaml \
              --scoring-script examples/ProbaLYNCH/ProbaLYNCH.R \
              --umami-url "https://your-instance.example.com" \
              --umami-website-id "your-website-id"
```

**Complete example:**

```bash
# With cloud.umami.is (free)
prevmed --survey-yaml examples/ProbaLYNCH/ProbaLYNCH.yaml \
              --scoring-script examples/ProbaLYNCH/ProbaLYNCH.R \
              --umami-website-id "70991a3f-4cc9-49ae-a848-867bc75a1fd1"

# With self-hosted instance
prevmed --survey-yaml examples/ProbaLYNCH/ProbaLYNCH.yaml \
              --scoring-script examples/ProbaLYNCH/ProbaLYNCH.R \
              --umami-url "https://analytics.myhospital.com" \
              --umami-website-id "70991a3f-4cc9-49ae-a848-867bc75a1fd1"

# To ignore Do Not Track browser preferences (not recommended)
prevmed --survey-yaml examples/ProbaLYNCH/ProbaLYNCH.yaml \
              --scoring-script examples/ProbaLYNCH/ProbaLYNCH.R \
              --umami-website-id "70991a3f-4cc9-49ae-a848-867bc75a1fd1" \
              --umami-ignore-dnt
```

**Available options:**
- `--umami-website-id`: Umami website ID (required to enable analytics)
- `--umami-url`: URL of the Umami instance (optional, defaults to cloud.umami.is)
- `--umami-ignore-dnt`: Ignore Do Not Track browser preferences (optional, **not recommended** for privacy reasons)

**Note:** If no analytics arguments are provided, the application runs without analytics.

## Survey configuration (YAML)

Surveys are defined in YAML files with the following structure:

```yaml
survey_name: Survey name

# Only used in the logs etc:
survey_version: 1.0.0
PrevMed_version: 1.0.0

# Optional: custom title displayed at the top left of the page
# If set, overrides survey_name as the title
# If starting with # or <: treating it as markdown (allowing HTML too)
# If not: treating it as markdown prepended by `# `
page_title: My survey

# Optional: display survey_name as a title at the top of the page (default: true)
# Ignored if page_title is set
show_survey_title: true

# Optional: display survey version on the web page and in the PDF (default: true)
show_survey_version: true

# Optional: display webapp version on the web page and in the PDF (default: true)
show_webapp_version: true

# Optional: extra pages served on their own routes.
# Each entry supports the same top-level keys as the main config (except
# "questions") plus a required "route" key.
# "body" and "header" values can be inline markdown OR a path to an
# existing .md file (absolute, or relative to this YAML file).
extra_pages:
  - route: home
    page_title: "Welcome"
    body: |
      Landing page description...

# Optional: body text displayed at the top of the survey (Markdown format, with HTML support)
# Can be inline markdown OR a path to an existing .md file (absolute, or relative to this YAML file).
body: |
  ## About this survey

  Survey description...

# File-path alternative:
# body: /app/examples/MyApp/body.md

# Optional: Markdown text displayed just before the questions (after the body and versions)
questions_header: |
  Please answer the following questions.

# Optional: summary text for the legal section (default: "LEGAL")
# Used as the <details><summary> label for legal notices (--terms-md)
legal_summary: "Legal notices & contact"

# Optional: extra Markdown content included in the generated PDF report
# Supports: headers (#, ##, ###), bold (**text**), italic (*text*), links [text](url)
pdf_extra_content: |
  ## Important Information

  This is **bold** and *italic* text.

  For more information, visit [our website](https://example.com).

questions:
  - variable: variable_name
    order: 1
    widget: Radio|Number|Checkbox|Textbox
    widget_args:
      # Widget-specific arguments
      choices: ["Option1", "Option2"]  # For Radio
      precision: 0  # For Number
      step: 1  # For Slider
      label: "Widget text"          # Optional: defaults to question
    question: "Question text"
    skip_if: "(variable_name == 2) and (variable_name > other_variable)"  # If the expression is True then the question is not asked (the expression must be in Python and has access to variables from the rest of the script.)
```


### Available widget types

In principle, PrevMed should work with any Gradio widget. The list of Gradio widgets is available [here](https://www.gradio.app/docs/gradio). The following widgets are most commonly used:

- **Radio**: Radio buttons for single choice
  - `choices`: List of options (required)
- **Number**: Numeric field with controls
- **Checkbox**: Boolean checkbox
- **Textbox**: Free text field

### Conditional logic

PrevMed supports two types of conditional logic:

#### 1. Conditional question display (`skip_if`)

Questions can be dynamically displayed or hidden via the `skip_if` field. Conditions are Python expressions evaluated with the values of previous variables:

```yaml
- variable: age_diagnosis
  skip_if: "not (positive_diagnosis == True)"
  # This question only displays if positive_diagnosis is not True

- variable: age_crc_proband
  skip_if: "personal_crc_count == 0"
  # This question is skipped if the patient has no colorectal cancer
```

**Important points:**
- Expression returns `True` → question is **skipped**
- Expression returns `False` → question is **displayed**
- Expressions can use all variables from previous questions
- Standard Python operators are supported (`==`, `!=`, `>`, `<`, `and`, `or`, `not`, etc.)

#### 2. Answer validation (`valid_if`)

Answers can be validated before moving to the next question via the `valid_if` field. If validation fails, an error message is displayed and the user must correct their answer:

```yaml
- variable: current_age
  widget: Number
  question: "Current age of patient (in years)"
  valid_if: "current_age >= 15 and current_age <= 120"
  invalid_message: "Age must be between 15 and 120 years."

- variable: personal_crc_count
  widget: Number
  question: "How many colorectal cancers?"
  valid_if: "personal_crc_count >= 0"
  invalid_message: "The number of cancers cannot be negative."
```

**Important points:**
- Expression returns `True` → answer is **valid**, can continue
- Expression returns `False` → answer is **invalid**, a warning is displayed
- The `invalid_message` field (optional) allows customizing the error message
- If `invalid_message` is not provided, a default message is used
- Validation runs before moving to the next question

## Scoring scripts

### R Script

The R script must define a `scoring()` function that takes survey variables as named arguments and returns a list with **3 elements**:

1. A character string containing **markdown** to display to the patient
2. A list of lists representing a **table** (first list = bodys, subsequent lists = data rows)
3. A named list with **PDF options** (`include_md_in_pdf` and `include_data_in_pdf`)

```r
scoring <- function(variable1, variable2 = NULL, ...) {
  # Calculation logic
  score_total <- 0.40
  
  # Generate markdown text to display to the patient on the web interface
  # This text is ALWAYS shown to the patient directly in their browser
  markdown_result <- sprintf("## Results\n\nYour total score is: %.1f%%", score_total * 100)
  
  # Create table data (format: list of lists)
  # First list = headers, subsequent lists = data rows
  table_data <- list(
    c("Category", "Probability"),  # Headers
    c("Category 1", sprintf("%.2f%%", 0.15 * 100)),
    c("Category 2", sprintf("%.2f%%", 0.25 * 100)),
    c("Total", sprintf("%.2f%%", 0.40 * 100))
  )
  
  # PDF generation options
  pdf_options <- list(
    include_md_in_pdf = TRUE,    # Also include the markdown in the PDF (it's always shown on the web interface)
    include_data_in_pdf = TRUE   # Include data table in PDF
  )
  
  # Return a list with 3 elements
  list(
    markdown_result,  # Element 1: markdown text
    table_data,       # Element 2: table data
    pdf_options       # Element 3: PDF options
  )
}
```

**Important points:**
- Conditional parameters must have `= NULL` as default value
- Return a **list with 3 elements**: markdown, table_data, pdf_options
- The **first element** is a markdown string that is **always displayed to the patient on the web interface**. The `include_md_in_pdf` option controls whether this same text is also included in the PDF report (supports full markdown formatting - see below)
- The **second element** is a list of lists where the first list contains headers and subsequent lists contain data rows
- The **third element** controls what is included in the PDF (markdown and/or table) - note that the markdown is always shown on the web page regardless of this setting
- Parameter names must match variable names from the YAML

### Python Script

The Python script must define a `scoring()` function that returns a **tuple with 3 elements**:

1. A string containing **markdown** to display to the patient
2. A list of lists representing a **table** (first list = headers, subsequent lists = data rows)
3. A dictionary with **PDF options** (`include_md_in_pdf` and `include_data_in_pdf`)

```python
def scoring(variable1: str, variable2: int = None, **kwargs) -> tuple[str, list[list[str]], dict[str, bool]]:
    """Score calculation."""
    # Calculation logic
    score_total = 0.40
    
    # Generate markdown text to display to the patient on the web interface
    # This text is ALWAYS shown to the patient directly in their browser
    markdown_result = f"## Results\n\nYour total score is: {score_total * 100:.1f}%"
    
    # Create table data (format: list of lists)
    # First list = headers, subsequent lists = data rows
    table_data = [
        ["Category", "Probability"],  # Headers
        ["Category 1", f"{0.15 * 100:.2f}%"],
        ["Category 2", f"{0.25 * 100:.2f}%"],
        ["Total", f"{0.40 * 100:.2f}%"]
    ]
    
    # PDF generation options
    pdf_options = {
        "include_md_in_pdf": True,    # Also include the markdown in the PDF (it's always shown on the web interface)
        "include_data_in_pdf": True   # Include data table in PDF
    }
    
    # Return a tuple with 3 elements
    return (markdown_result, table_data, pdf_options)
```

**Important points:**
- Return a **tuple with 3 elements**: markdown, table_data, pdf_options
- The **first element** is a markdown string that is **always displayed to the patient on the web interface**. The `include_md_in_pdf` option controls whether this same text is also included in the PDF report (supports full markdown formatting - see below)
- The **second element** is a list of lists where the first list contains headers and subsequent lists contain data rows
- The **third element** controls what is included in the PDF (markdown and/or table) - note that the markdown is always shown on the web page regardless of this setting
- Table values can be of any type (they will be converted to strings automatically)
- Parameter names must match variable names from the YAML

### Supported Markdown formatting

The markdown field returned by scoring scripts supports the following elements:

- **Headers**: `#`, `##`, `###`, etc. (arbitrary levels)
- **Bold**: `**text**`
- **Italic**: `*text*`
- **Links**: `[text](url)` (links with empty URLs are safely skipped)
- **Tables**: standard pipe format
- **HTML**: HTML tags are supported in Markdown fields (e.g., `<h1 style="text-align: center;">`, `<details>`, `<summary>`, etc.)

Example of a table in markdown:

```markdown
| Category | Value |
|----------|-------|
| A        | 10%   |
| B        | 20%   |
```

## PDF Report Generation

PDF reports are automatically generated at the end of the survey and include:

- Survey name and version
- Unique reference code (XXX-YYY format, easy to remember)
- Generation timestamp
- Scoring results (formatted text + structured table)
- All question answers

### In-memory PDF generation

**PDF storage approach:**
- **By default**: PDFs are generated in-memory and served via a short-lived temp file in `/dev/shm` (RAM-based tmpfs — **no disk writes**)
- **With `--save-user-data`**: PDFs are saved permanently in `survey_data/` alongside JSON data

**How in-memory generation works:**

When `--save-user-data` is not enabled (default behavior):

1. PDF is generated directly in memory using Python's BytesIO buffer
2. Bytes are written to a temporary file in `/dev/shm` (Linux RAM filesystem — never touches disk), with permissions `600` (owner-read only) to prevent other users from accessing it
3. Gradio's DownloadButton serves the file to the patient's browser (it requires a file path, not a BytesIO object)
4. The temp file is automatically deleted after a short delay once the download window has passed
5. **No files are ever written to disk** - maximum privacy protection

**Example workflow:**

1. Patient completes survey at 2:00 PM
2. PDF is generated in memory (BytesIO)
3. PDF is written to `/dev/shm` (RAM only, chmod 600) for Gradio to serve
4. Patient downloads the PDF
5. Temp file is deleted from RAM — **no trace remains on disk**

This approach ensures **zero disk footprint** and **maximum patient privacy**: data only ever lives in RAM.

## Structured Data Storage (if enabled)

When the `--save-user-data` option is enabled, PrevMed saves all data in two complementary formats:

### Compressed JSON files (if `--save-user-data` enabled)

With `--save-user-data`, each submission is saved as compressed JSON (`.json.gz`) in `survey_data/` with:
- Survey name and versions
- Complete answers
- Scoring results
- Unique reference code
- Unix timestamp
- Client hashes (for anonymous duplicate detection)

**File name format:** `{timestamp}_{reference_code}_{unique_id}.json.gz`

**Example:** `1729500000_A2B-3C4_a1b2c3d4.json.gz`

**Note:** The `{unique_id}` is a UUID fragment (first 8 characters) that guarantees absolute uniqueness even in case of timestamp collision.

### CSV logs (if `--save-user-data` enabled)

With `--save-user-data`, a **centralized CSV file** records all submissions for quick analysis:

**Location:** `survey_data/csv/{PrevMed_version}/{survey_name}_{survey_version}/survey_submissions.csv`

**Example:** `survey_data/csv/0.8.0/ProbaLYNCH_1.0.0/survey_submissions.csv`

#### CSV system characteristics

**Column structure:**
- Fixed columns: `reference_code`, `row_number`, `timestamp_unix`, `datetime`
- Scoring columns: one per result (e.g., `p_MLH1`, `p_MSH2`, formatted as percentages)
- Hash columns: `answers_hash` + individual hashes per client attribute (e.g., `user_agent_hash`, `ip_address_hash`)

**Concurrency management:**
- Uses `filelock` to guarantee write atomicity
- Supports concurrent access from multiple processes/servers
- 10-second timeout on lock

**Automatic rotation:**
- CSV is automatically archived after 1000 lines
- Archived file: `survey_submissions_{timestamp}.csv` (permanent backup)
- New CSV automatically created to continue recording
- **Goal:** maintain high performance even with intensive concurrent access

**Error handling:**
- In case of lock timeout (very high load), data is saved in a fallback file
- Format: `survey_submissions_fallback_{timestamp}_{uuid}.csv` (where `{uuid}` is an 8-character UUID fragment)
- **Guarantee:** no data loss even under extreme load

**Duplicate detection:**
- `answers_hash`: short hash (12 characters) of answers only
- Individual client hashes: each attribute (user-agent, IP, etc.) hashed separately with reference code as salt
- Allows duplicate analysis while preserving privacy

**Example CSV content:**

```csv
reference_code,row_number,timestamp_unix,datetime,p_MLH1,p_MSH2,p_MSH6,p_PMS2,p_total,answers_hash,user_agent_hash,ip_address_hash,session_hash_hash
A2B-3C4,1,1729500000,2024-10-21 14:20:00,15.23,25.47,8.92,10.38,60.00,a1b2c3d4e5f6,x9y8z7w6v5u4,q1w2e3r4t5y6,m1n2b3v4c5x6
D5E-6F7,2,1729500120,2024-10-21 14:22:00,2.15,3.28,1.45,1.12,8.00,f6e5d4c3b2a1,u4v5w6z7y8x9,y6t5r4e3w2q1,x6c5v4b3n2m1
```

**Advantages of this architecture:**
- **Performance**: rotation limits file size to maintain access speed
- **Reliability**: fallback system guarantees zero data loss
- **Traceability**: automatic archiving with timestamps
- **Analysis**: CSV format facilitates quick statistical analysis
- **Scalability**: concurrency management enables multi-process/multi-server deployment
- **Privacy**: salted hashes allow duplicate detection without storing raw personal data

## Project Structure

```
PrevMed/
├── src/
│   ├── __init__.py          # Logging setup
│   ├── __main__.py          # CLI entry point
│   └── utils/
│       ├── gui/             # Gradio interface (package)
│       │   ├── __init__.py  # Re-exports create_survey_interface
│       │   ├── extra_pages.py # Extra pages (extra_pages)
│       │   └── survey.py    # Survey (questions, scoring, PDF)
│       ├── css.py           # CSS used in Gradio
│       ├── js.py            # JS used in Gradio
│       ├── io.py            # YAML and script loading
│       ├── logic.py         # Conditional logic
│       ├── pdf.py           # PDF generation
│       ├── scoring.py       # R/Python script execution
│       └── settings.py      # Stores variables available throughout the script
├── examples/
│   └── ProbaLYNCH/
│       ├── ProbaLYNCH.yaml      # ProbaLYNCH configuration
│       └── ProbaLYNCH.R         # ProbaLYNCH scoring script
├── logs/                    # Rotating logs (created automatically)
├── survey_pdfs/             # PDF reports (created automatically)
├── requirements.txt
└── setup.py
```

## Logs

Logs are automatically saved in `./logs/` with daily rotation and 30-day retention. The format includes:

- Timestamp with milliseconds
- Log level
- File, function and line
- Message

By default, file logs are at **INFO** level. To enable **DEBUG** level (more verbose), set the `PREVMED_LOG_LEVEL` environment variable:

```bash
PREVMED_LOG_LEVEL=DEBUG prevmed --survey-yaml <yaml> --scoring-script <script>
```

## ProbaLYNCH Example

To illustrate how PrevMed works, we have implemented the ProbaLYNCH questionnaire ([preventionfamiliale.fr](https://preventionfamiliale.fr/)) (see [References and Credits](#references-and-credits)).

The ProbaLYNCH questionnaire assesses the risk of mutations in the MLH1, MSH2, MSH6 and PMS2 genes ([Lynch syndrome](https://syndrome-de-lynch.fr/)) based on:

- Personal cancer history (colorectal, uterine ("endometrial"), other)
- Ages at diagnosis
- Family history (close relatives)

The ProbaLYNCH model uses a multinomial logistic regression model with softmax transformation to calculate mutation probabilities for each gene from a predetermined list of genes. An R language adaptation was written in 2025 by Laury NICOLAS, MD from CHU de Pointe-à-Pitre, while he was a Junior Doctor in the GENOAP Department (Genetics-Oncogenetics-Adult-Prevention) at CHU de Clermont-Ferrand. This R script was subsequently optimized by Anna Serova-Erard, Genetic Counselor in Genetics and Predictive Medicine at GENOAP.

## Development

### Code conventions

- Type hints and NumPy style docstrings everywhere
- Explicit comments for design decisions
- Use of `loguru` for logging
- Simple and robust code preferred
- Use of [Ruff](https://astral.sh/ruff) as linter for code quality assurance

### Contributions

This project was developed with assistance from [aider.chat](https://github.com/Aider-AI/aider/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

**We happily accept:**
- 🐛 Bug reports via [Issues](https://github.com/PrevMedOrg/PrevMed/issues)
- ✨ Feature requests
- 🔧 Pull Requests to improve the project

Feel free to contribute!

## License

Currently licensed under [GNU Affero General Public License](https://en.wikipedia.org/wiki/GNU_Affero_General_Public_License). However, we are flexible and open to alternative licensing arrangements - please contact us if you need a different license for your use case.

## References and Credits

### Regarding the ProbaLYNCH example:

1. In order to allow anyone to assess their probability of carrying a genetic risk, the support association for genetic epidemiology ASAGE (French law 1901 n°RNA W751217490, J.O. of December 15, 2012) freely provides, at no cost and without storing any personal data, the *ProbaLYNCH* application (under the [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0)): the source code demonstrating the absence of data retention is [available online](https://github.com/PrevMedOrg) and runs on a French hosting provider. The initial application was coded in **R** programming language in 2025, while he was a Junior Doctor in the GENOAP Department (Genetics-Oncogenetics-Adult-Prevention) at CHU de Clermont-Ferrand, by Dr. Laury NICOLAS, currently University Clinical Fellow at Université des Antilles - Hospital Assistant at CHU de la Guadeloupe. The **R** script was optimized at GENOAP by Mrs. Anna SEROVA-ERARD, Genetic Counselor in Genetics and Predictive Medicine. The illustrations were created by Mrs. Anne SPECQ, Genetic Counselor in Genetics and Predictive Medicine, former intern at GENOAP. The ProbaLynch application was finalized by oliCorp on its PrevMed framework, itself a Free Open Source Software.
2. Kastrinos et al, J Clin Oncol 35, 2165-2172 (2017). DOI: 10.1200/JCO.2016.69.6120. "Development and Validation of the PREMM5 Model for Comprehensive Risk Assessment of Lynch Syndrome".
