# Replication Package: GitHub Actions Workflows Compliance & LLM-Assisted Auditing

**Paper:** "How Compliant Are GitHub Actions Workflows? A Checklist-Based Study with LLM-Assisted Auditing"  
**Conference:** Accepted for publication at The 30th International Conference on Evaluation and Assessment in Software Engineering (EASE 2026)


## Overview

This replication package provides the tools, data, and results for studying checklist-based compliance of GitHub Actions workflows in open-source projects with Large Language Models (LLMs)-assited auditing. The package includes:

- A comprehensive compliance checklist with 30 questions covering security, maintainability, and best practices
- Scripts for automated compliance checking using multiple LLM models
- Analysis tools for aggregating and comparing results across different models
- Evaluation results from multiple LLM models on a dataset of GitHub Actions workflow files

## Repository Structure

```
EASE_Compliance_Replication_Package/
├── Data/
│   ├── compliance_questions.json    # Compliance checklist (30 questions)
│   └── java_yml_files.zip           # Dataset of GitHub Actions workflow files
├── Scripts/
│   ├── LLM_Compliance_Check.py      # Main script for LLM-based compliance checking
│   ├── Compliance_Analysis.py       # Analysis and aggregation of compliance results
│   └── Compliance_Aggregation.py    # Statistical analysis and inter-rater agreement
└── Results/
    ├── Compliance_Checklist_and_Results.xlsx
    ├── java_llama3.1-8b_yml_analysis_results.csv
    ├── java_gemma3-12b_yml_analysis_results.csv
    ├── java_mistral-7b_yml_analysis_results.csv
    ├── java_phi4-14b_yml_analysis_results.csv
    ├── java_gpt-5_yml_analysis_results_section6.csv
    └── combined_results.csv
```

## Requirements

### Python Dependencies

The scripts require Python 3.x with the following packages:

- `pandas` - Data manipulation and analysis
- `numpy` - Numerical computations
- `scipy` - Statistical functions
- `statsmodels` - Statistical modeling (for Fleiss' Kappa, McNemar tests)
- `pyyaml` - YAML file parsing
- `ollama` - For local LLM models (llama3.1:8b, gemma3:12b, mistral:7b, phi4:14b)
- `openai` - For OpenAI API access (GPT-5)

### LLM Access

The scripts support two types of LLM access:

1. **Local Models (via Ollama)**: For models like `llama3.1:8b`, `gemma3:12b`, `mistral:7b`, and `phi4:14b`
   - Requires [Ollama](https://ollama.ai/) to be installed and running locally
   - Models must be pulled using: `ollama pull <model_name>`

2. **OpenAI API**: For GPT-5 model
   - Requires an OpenAI API key
   - Update `OPENAI_API_KEY` in `LLM_Compliance_Check.py` with your API key

## Installation

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install pandas numpy scipy statsmodels pyyaml ollama openai
   ```

3. (Optional) For local LLM models, install and configure Ollama:
   ```bash
   # Install Ollama (see https://ollama.ai/)
   ollama pull llama3.1:8b
   ollama pull gemma3:12b
   ollama pull mistral:7b
   ollama pull phi4:14b
   ```

4. For OpenAI models, set your API key in `Scripts/LLM_Compliance_Check.py`

## Usage

### 1. Running Compliance Checks

The main script `LLM_Compliance_Check.py` performs compliance checking on GitHub Actions workflow files:

```bash
cd Scripts
python LLM_Compliance_Check.py
```

**Configuration:**
- Input: `Data/java_yml_files.zip` (contains workflow YAML files)
- Output: `Results/java_gha_compliance_llm_check_results.json`
- Models: Configured in the script (default: llama3.1:8b, gemma3:12b, mistral:7b, gpt-5)
- Sample size: 95 files per model (randomly selected)

The script processes each workflow file through the specified LLM models, asking them to evaluate compliance against the 30-question checklist.

### 2. Analyzing Results

#### Compliance Analysis (`Compliance_Analysis.py`)

Aggregates results from multiple models and performs agreement analysis:

```bash
cd Scripts
python Compliance_Analysis.py
```

**Outputs:**
- `models_in_agreement_and_disagreement_v6.csv` - Per-file agreement statistics
- `full_agreement.csv` - Cases where all models agree
- `partial_agreement_any.csv` - Cases with partial agreement
- `partial_agreement_min3.csv` - Cases with at least 3 models agreeing
- `exactly_2_agree_any_label.csv` - Cases with exactly 2 models agreeing
- `stats_agree_3_4_and_only2.csv` - Overall agreement statistics
- `model_agreement_scores_normalized.csv` - Normalized per-model performance scores
- `audit_triage_gpt5_on_2agree.csv` - GPT-5 validation for 2-agreement cases

#### Statistical Aggregation (`Compliance_Aggregation.py`)

Performs statistical analysis including inter-rater agreement:

```bash
cd Scripts
python Compliance_Aggregation.py
```

**Outputs:**
- Model performance metrics (agreement rates)
- Pairwise agreement between models
- McNemar tests for model comparison
- Fleiss' Kappa for inter-rater agreement

## Data Description

### Compliance Checklist (`Data/compliance_questions.json`)

The compliance checklist contains 30 criteria organized into four main sections:

- **Workflow** (3 criteria: W1-W3): Error/failure handling, environment configuration, and security best practices
- **Jobs** (11 criteria: J1-J11): Clarity, error handling, environment, modularity, performance optimization, and security
- **Steps** (15 criteria: S1-S15): Modularity, input validation, error/failure handling, maintainability, and security
- **Permissions** (1 criterion: P1): Secure secret management

Within each section, criteria are further organized by themes such as Clarity, Modularity, Security, Performance, Error/Failure Handling, Input Validation, Maintainability, and Environment.

Each question expects one of three responses:
- `YES` - Compliance requirement met
- `NO: <reason>` - Non-compliance with explanation
- `NOT APPLICABLE` - Question does not apply to the workflow

### Workflow Dataset (`Data/java_yml_files.zip`)

Contains GitHub Actions workflow files (`.yml`) collected from Java repositories. The dataset includes:
- Various workflow types (CI, CD, security scanning, etc.)
- Different complexity levels
- Real-world examples from open-source projects

### Results

The `Results/` directory contains:

- **Individual model results**: CSV files with compliance evaluations from each LLM model
- **Aggregated results**: Combined analysis across all models
- **Statistical outputs**: Agreement metrics, model comparisons, and performance scores


## Citation

If you use this replication package in your research, please cite:

```bibtex
@inproceedings{abrokwah2026compliant,
  title={How Compliant Are GitHub Actions Workflows? A Checklist-Based Study with LLM-Assisted Auditing},
  author={Edward Abrokwah and Taher A. Ghaleb},
  booktitle={Proceedings of the 30th International Conference on Evaluation and Assessment in Software Engineering (EASE 2026)},
  year={2026}
}
```

## License

This replication package is provided for research purposes. Please refer to the paper for detailed methodology and findings.

## Contact

For questions or issues regarding this replication package, please refer to the paper submission or contact the authors through the conference submission system.

## Notes

- The scripts are configured to process a subset of 95 files per model for efficiency
- Results may vary slightly due to randomness in file selection and LLM non-determinism
- Some models (GPT-5) are used for validation on specific cases (2-agreement scenarios)
- The compliance checklist is designed to be comprehensive but may not cover all edge cases
