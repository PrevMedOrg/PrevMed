> **Note:** A French version of this document is also available: [README.md](https://github.com/PrevMedOrg/PrevMed/blob/main/README.md)

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
  - [Example with PREMM5](#example-with-premm5)
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
- [PREMM5 Example](#premm5-example)
- [Development](#development)
  - [Code conventions](#code-conventions)
  - [Contributions](#contributions)
- [License](#license)
- [References](#references)

## Main Objective

PrevMed is designed to **simplify the clinical workflow** by enabling healthcare professionals to easily create clinical decision support questionnaires with common programming skills: a script in [R](https://en.wikipedia.org/wiki/R_%28programming_language%29) (or [Python](https://en.wikipedia.org/wiki/Python_(programming_language))) and a `.yaml` file.

**How it works:**
1. The patient fills out the questionnaire on the web interface
2. A PDF with answers and results is generated instantly
3. The patient comes to consultation with this PDF
4. **No personal data is stored** on the server

This system **saves everyone time**: the patient prepares their answers in advance, and the clinician immediately has structured information and automatically calculated scores.

## Technical Description

PrevMed allows creating interactive clinical questionnaires from YAML configuration files. The system automatically generates a web interface with Gradio, handles conditional question logic, executes scoring scripts (R or Python), and produces PDF reports.

**Main features:**

- ✨ Declarative configuration via YAML
- 🔀 Conditional questions (dynamic display based on previous answers)
- 📊 Support for scoring scripts in R (via rpy2) or Python
- 🖥️ Intuitive web interface with Gradio
- 📄 Automatic PDF report generation
- 📝 Detailed logging with loguru
- 🎯 Type hints and NumPy style documentation

## Installation

### Prerequisites

- Python, arbitrarily set to 3.13.5 for its speed without being as recent as 3.14.
- R and rpy2 if you use R scoring scripts. On Ubuntu simply run `sudo apt install r-base`.
- On ubuntu 22.04, you might need `sudo apt-get install libtirpc-dev` ([source](https://github.com/rpy2/rpy2/issues/1106#issuecomment-2118710471))

### Installing dependencies

After downloading the repo, start by creating a venv:

```bash
uv venv
source .venv/bin/activate
```

```bash
uv pip install .
```

**Note:** On some systems, you may need to install R separately before installing rpy2.

### Docker Deployment

PrevMed can be deployed with Docker for simplified and isolated installation:

```bash
# Clone the repository
git clone https://github.com/PrevMedOrg/PrevMed
cd PrevMed

# Navigate to the docker directory
cd docker

# Modify docker-compose.yml to specify desired arguments in the 'command' section
# For example: --survey-yaml, --scoring-script, --save-user-data, etc.

# Launch the container in detached mode
sudo docker compose up --build -d
```

**Volume management:**
- The `logs/` and `survey_data/` folders are **mounted as volumes** to persist data between restarts
- The `temp_pdfs/` folder is **not mounted** to ensure it remains non-persistent and respects privacy

This configuration allows you to benefit from Docker isolation while preserving important logs and data, without compromising the temporary nature of PDFs.

## Usage

### Basic launch

```bash
prevmed --survey-yaml <yaml_path> --scoring-script <script_path>
```

### Example with PREMM5

The project includes a complete example of the PREMM5 questionnaire (Lynch syndrome risk assessment):

```bash
prevmed --survey-yaml examples/PREMM5/premm5.yaml --scoring-script examples/PREMM5/premm5.R
```

This will launch a Gradio interface accessible via your web browser.

### Command line options

PrevMed supports several options to customize application behavior:

#### User data saving

By default, **no user data is saved**. Generated PDF reports are created as **temporary files** only for patient download, without logging answers or results.

To **save user data permanently** (in the `survey_data/` directory), use the `--save-user-data` option:

```bash
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --save-user-data
```

**With `--save-user-data` enabled, the following data is saved:**
- Compressed JSON files (`.json.gz`) containing all answers and results
- Centralized CSV logs for quick analysis
- PDF reports stored permanently

**Without this option (default behavior):**
- Only temporary PDFs are created for download
- No data is logged in CSV files
- No JSON files are saved
- Maximum respect for patient privacy

#### Other useful options

```bash
# Automatically open browser on startup
prevmed --survey-yaml <yaml> --scoring-script <script> --open-browser

# Use a custom port (default: 7860)
prevmed --survey-yaml <yaml> --scoring-script <script> --port 8080

# Enable debug level logging in console
prevmed --survey-yaml <yaml> --scoring-script <script> --debug

# Specify the actual URL where the questionnaire is hosted (will appear in PDFs)
prevmed --survey-yaml <yaml> --scoring-script <script> --actual-url "https://survey.hospital.com/premm5"
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

### Configuration

To enable analytics, use the command line arguments `--umami-website-id` and optionally `--umami-url`:

```bash
# Option 1: Use the free Umami cloud service (cloud.umami.is)
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-website-id "your-website-id"

# Option 2: Use your own self-hosted Umami instance
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-url "https://your-instance.example.com" \
              --umami-website-id "your-website-id"
```

**Complete example:**

```bash
# With cloud.umami.is (free)
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-website-id "70991a3f-4cc9-49ae-a848-867bc75a1fd1"

# With self-hosted instance
prevmed --survey-yaml examples/PREMM5/premm5.yaml \
              --scoring-script examples/PREMM5/premm5.R \
              --umami-url "https://analytics.myhospital.com" \
              --umami-website-id "70991a3f-4cc9-49ae-a848-867bc75a1fd1"
```

**Note:** If no analytics arguments are provided, the application runs without analytics.

## Survey configuration (YAML)

Surveys are defined in YAML files with the following structure:

```yaml
survey_name: Survey name

# Only used in the logs etc:
survey_version: 1.0.0
PrevMed_version: 1.0.0

# Optional: header text displayed at the top of the survey (Markdown format)
header: |
  ## About this survey

  Survey description...

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
2. A list of lists representing a **table** (first list = headers, subsequent lists = data rows)
3. A named list with **PDF options** (`include_md_in_pdf` and `include_data_in_pdf`)

```r
scoring <- function(variable1, variable2 = NULL, ...) {
  # Calculation logic
  score_total <- 0.40
  
  # Generate markdown text to display
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
    include_md_in_pdf = TRUE,    # Include markdown in PDF
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
- The **first element** is a markdown string displayed to the patient
- The **second element** is a list of lists where the first list contains headers and subsequent lists contain data rows
- The **third element** controls what is included in the PDF (markdown and/or table)
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
    
    # Generate markdown text to display
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
        "include_md_in_pdf": True,    # Include markdown in PDF
        "include_data_in_pdf": True   # Include data table in PDF
    }
    
    # Return a tuple with 3 elements
    return (markdown_result, table_data, pdf_options)
```

**Important points:**
- Return a **tuple with 3 elements**: markdown, table_data, pdf_options
- The **first element** is a markdown string displayed to the patient
- The **second element** is a list of lists where the first list contains headers and subsequent lists contain data rows
- The **third element** controls what is included in the PDF (markdown and/or table)
- Table values can be of any type (they will be converted to strings automatically)
- Parameter names must match variable names from the YAML

## PDF Report Generation

PDF reports are automatically generated at the end of the survey and include:

- Survey name and version
- Unique reference code (XXX-YYY format, easy to remember)
- Generation timestamp
- Scoring results (formatted text + structured table)
- All question answers

### Temporary file management

**PDF storage:**
- **By default**: temporary files stored in `temp_pdfs/` only for download (not saved permanently)
- **With `--save-user-data`**: permanent save in `survey_data/` in addition to temporary PDF

**Automatic cleanup:**

To avoid accumulation of temporary files, PrevMed implements an automatic cleanup system:

- **On startup**: the entire `temp_pdfs/` directory is deleted if it exists, ensuring a clean start
- **During operation**: before each PDF generation, all files in the `temp_pdfs/` directory **older than 1 hour** are automatically deleted
- **On shutdown**: the entire `temp_pdfs/` directory is deleted when the application closes
- This multi-level cleanup ensures no temporary file remains indefinitely on the server
- The `temp_pdfs/` directory is created automatically when first needed
- Even under heavy load, the system maintains a clean and performant directory

**Example lifecycle of a temporary PDF:**

1. Patient completes survey at 2:00 PM
2. PDF generated in `temp_pdfs/survey_ABC-XYZ_1729500000.pdf`
3. Patient downloads PDF immediately
4. At 3:30 PM, another patient generates their PDF
5. The system automatically cleans all PDFs created before 2:30 PM (older than 1h)
6. The 2:00 PM PDF is automatically deleted, freeing disk space

This approach ensures **zero manual maintenance** while respecting patient privacy.

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

**File name format:** `{timestamp}_{reference_code}.json.gz`

**Example:** `1729500000_A2B-3C4.json.gz`

### CSV logs (if `--save-user-data` enabled)

With `--save-user-data`, a **centralized CSV file** records all submissions for quick analysis:

**Location:** `survey_data/csv/{PrevMed_version}/{survey_name}_{survey_version}/survey_submissions.csv`

**Example:** `survey_data/csv/0.8.0/PREMM5_2.0/survey_submissions.csv`

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
- Format: `survey_submissions_fallback_{timestamp}_{random}.csv`
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
│       ├── gui.py           # Gradio interface
│       ├── css.py           # CSS used in Gradio
│       ├── js.py            # JS used in Gradio
│       ├── io.py            # YAML and script loading
│       ├── logic.py         # Conditional logic
│       ├── pdf.py           # PDF generation
│       ├── scoring.py       # R/Python script execution
│       └── settings.py      # Stores variables available throughout the script
├── examples/
│   └── PREMM5/
│       ├── premm5.yaml      # PREMM5 configuration
│       └── premm5.R         # PREMM5 scoring script
├── logs/                    # Rotating logs (created automatically)
├── survey_pdfs/             # PDF reports (created automatically)
├── requirements.txt
└── setup.py
```

## Logs

Logs are automatically saved in `./logs/` with daily rotation and 365-day retention. The format includes:

- Timestamp with milliseconds
- Log level
- File, function and line
- Message

## PREMM5 Example

The PREMM5 questionnaire assesses the risk of mutations in the MLH1, MSH2, MSH6 and PMS2 genes (Lynch syndrome) based on:

- Personal cancer history (colorectal, endometrial, other)
- Ages at diagnosis
- Family history (1st and 2nd degree relatives)

The scoring uses a multinomial logistic regression model with softmax transformation to calculate mutation probabilities for each gene.

## Development

### Code conventions

- Type hints and NumPy style docstrings everywhere
- Explicit comments for design decisions
- Use of `loguru` for logging
- Simple and robust code preferred
- Use of [Ruff](https://astral.sh/ruff) as linter for code quality assurance

### Contributions

This project was developed with assistance from [aider.chat](https://github.com/Aider-AI/aider/).

**We happily accept:**
- 🐛 Bug reports via [Issues](https://github.com/PrevMedOrg/PrevMed/issues)
- ✨ Feature requests
- 🔧 Pull Requests to improve the project

Feel free to contribute!

## License

Currently licensed under GPL-v3. However, we are flexible and open to alternative licensing arrangements - please contact us if you need a different license for your use case.

## References

For PREMM5:
- Kastrinos F, et al. "Development and Validation of the PREMM5 Model for Comprehensive Risk Assessment of Lynch Syndrome." J Clin Oncol. 2017.
