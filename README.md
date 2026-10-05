 # ApoE Gene Expression Explorer

An interactive web application for exploring RNA-seq gene expression and differential expression data from a mouse study investigating how **Apoer2 (Lrp8) exon 19 splicing** interacts with **ApoE3 and ApoE4 genotypes** to influence hippocampal gene expression.

The application combines a **Flask backend**, **MariaDB relational database**, and interactive JavaScript frontend to provide searchable gene-level expression profiles, differential expression analysis, and interactive visualization.

## Project Overview

Apolipoprotein E (APOE) is one of the strongest genetic risk factors for Alzheimer's disease, with the APOE4 allele associated with increased disease risk. This project explores how Apoer2/Lrp8 exon 19 splicing may modify transcriptional responses in different ApoE genetic backgrounds.

The study uses a **2 × 2 experimental design**:

| Condition | ApoE genotype | Apoer2 exon 19  |
| --------- | ------------- | --------------- |
| `a3c`     | e3/e3 (ApoE3) | Present (+ex19) |
| `a3d`     | e3/e3 (ApoE3) | Deleted (Δex19) |
| `a4c`     | e4/e4 (ApoE4) | Present (+ex19) |
| `a4d`     | e4/e4 (ApoE4) | Deleted (Δex19) |

Each condition contains three biological samples.

## Features

### Gene Search

Search for genes using either gene symbols or Ensembl IDs and view:

* Mean expression counts for each experimental group
* Standard error of the mean (SEM)
* Individual sample-level counts
* Differential expression results across comparisons
* Gene annotations and identifiers
* Direct links to Ensembl

### Differential Expression Explorer

Explore differential expression results for individual pairwise comparisons.

Users can filter results by:

* False discovery rate (FDR)
* Absolute log₂ fold change
* Direction of expression change
* Number of genes displayed

Results include:

* Gene ID
* Gene name
* Gene type
* log₂ fold change
* logCPM
* F-statistic
* P-value
* FDR

### Differential Expression by Genotype / Exon Status

DE results can also be filtered according to the biological factors in the experimental design:

* ApoE3 vs. ApoE4
* Exon 19 present vs. deleted
* Upregulated vs. downregulated genes
* FDR threshold
* Minimum absolute log₂ fold change

### Interactive Volcano Plots

The application provides interactive volcano plots for individual differential expression comparisons.

Users can:

* Hover over genes to view statistics
* Zoom and pan across the plot
* Select individual genes
* Navigate directly to a gene's expression profile
* Export plots as PNG files

### Data Downloads

Filtered results can be downloaded as CSV files, including:

* Differential expression results for a comparison
* Expression counts for an individual gene
* Differential expression results for an individual gene
* Filtered DE results by genotype and exon status

## Technology Stack

### Backend

* **Python**
* **Flask**
* **MariaDB**
* SQL queries for data retrieval and filtering
* REST-style API endpoints

### Data Processing

* **R**
* **tidyverse**
* R Markdown

### Frontend

* HTML/CSS
* JavaScript
* **D3.js**
* **Chart.js**
* jQuery

### Database

The application uses a relational database containing five primary tables:

```text
genes
  │
  ├── expression_counts ── samples
  │
  └── differential_expression ── comparisons
```

The data-processing workflow prepares the source data for loading into MariaDB while performing validation checks on gene IDs, sample IDs, and comparison groups.

## Data Processing Workflow

The `Data Manuipulation.Rmd` notebook transforms the original expression and differential expression files into normalized tables for database ingestion.

### Input

```text
counts.csv
de_results.csv
```

### Generated tables

```text
genes.csv
samples.csv
comparisons.csv
expression_counts.csv
differential_expression.csv
```

The workflow also performs validation checks to identify orphaned gene IDs, sample IDs, or comparison groups before loading the data into the database.

Recommended database loading order:

```text
1. genes.csv
2. samples.csv
3. comparisons.csv
4. expression_counts.csv
5. differential_expression.csv
```

## Differential Expression Comparisons

The application supports the following biological comparisons:

| Comparison | Biological question                          |
| ---------- | -------------------------------------------- |
| `a3c_a3d`  | Effect of exon 19 deletion in ApoE3          |
| `a4c_a4d`  | Effect of exon 19 deletion in ApoE4          |
| `a3c_a4c`  | Effect of ApoE genotype with exon 19 present |
| `a3d_a4d`  | Effect of ApoE genotype with exon 19 deleted |

These comparisons allow users to examine both the independent effects of ApoE genotype and exon 19 status as well as how the two factors interact.

## Application Architecture

```text
                    ┌─────────────────────┐
                    │     Web Browser     │
                    │  HTML / JavaScript  │
                    └──────────┬──────────┘
                               │
                               │ HTTP / JSON
                               ▼
                    ┌─────────────────────┐
                    │    Flask Backend    │
                    │    Python / API     │
                    └──────────┬──────────┘
                               │
                               │ SQL
                               ▼
                    ┌─────────────────────┐
                    │      MariaDB        │
                    │   Relational DB     │
                    └─────────────────────┘
                               ▲
                               │
                    ┌──────────┴──────────┐
                    │   R Data Pipeline   │
                    │      tidyverse      │
                    └─────────────────────┘
```

## Repository Structure

```text
ApoE-Gene-Expression-Explorer/
│
├── Team17_app.py
│   └── Flask application and API endpoints
│
├── Data Manuipulation.Rmd
│   └── Data transformation and validation workflow
│
├── templates/
│   └── index.html
│       └── Web application frontend
│
└── README.md
```

## Running the Application

### Requirements

Python 3.x and the following Python packages are required:

```bash
pip install flask mariadb
```

R is required for the data-processing workflow, with the `tidyverse` package:

```r
install.packages("tidyverse")
```

### Database Configuration

The Flask application requires access to a MariaDB database containing the project tables.

Database connection parameters are configured in `Team17_app.py`:

```python
DB_HOST = "..."
DB_USER = "..."
DB_PASSWORD = "..."
DB_NAME = "..."
DB_PORT = ...
```

**Do not commit database passwords or other credentials to GitHub.** For a production deployment, these values should be stored as environment variables or another secure configuration mechanism.

### Start the Flask Application

From the repository directory:

```bash
python Team17_app.py
```

The application will start using Flask's development server.

Once running, open the local address displayed in the terminal in a web browser.

## API Endpoints

The Flask backend exposes endpoints for retrieving and downloading data.

### Overview

```text
GET /api/stats/overview
```

Returns summary statistics including:

* Total genes
* Total samples
* Number of comparisons
* Number of significant DE results

### Gene Search

```text
GET /api/gene/search?q=<gene>
```

Searches for genes by gene symbol or Ensembl ID.

### Gene Details

```text
GET /api/gene/<gene_id>
```

Returns gene metadata, expression counts, group-level statistics, and differential expression results.

### Differential Expression

```text
GET /api/de/comparisons
GET /api/de/top
GET /api/de/by_group
```

These endpoints provide comparison-level and genotype/exon-level differential expression queries.

### Data Downloads

```text
GET /api/download/gene
GET /api/download/gene_de
GET /api/download/de
GET /api/download/de_by_group
```

These endpoints return filtered results as downloadable CSV files.

## Statistical Measures

The application reports several statistics from the differential expression analysis:

* **logFC** — log₂ fold change between the two conditions
* **logCPM** — log₂ counts per million, representing normalized expression abundance
* **F** — quasi-likelihood F-statistic
* **P-value** — nominal statistical significance
* **FDR** — multiple-testing-adjusted significance using the Benjamini–Hochberg procedure

An FDR threshold of **0.05** is used as the default significance cutoff in the application.

## Scientific Questions

The application was designed to facilitate exploration of questions such as:

1. Which genes differ between ApoE3 and ApoE4 backgrounds?
2. How does deletion of Apoer2 exon 19 affect gene expression?
3. Does the effect of exon 19 deletion differ between ApoE3 and ApoE4 backgrounds?
4. Which genes show the strongest differential expression in each comparison?
5. How does expression of a particular gene vary across the four experimental conditions?

## Project Context

This project was developed as part of **BF768 at Boston University during Spring 2026**.

The application was developed collaboratively by:

* Marilyn McCarthy
* Riya Desai
* Jiya Ashar
* Penelope Varela Dye

Faculty:

* Dr. Uwe Beffert
* Dr. Gary Benson

## Future Development

Potential future improvements include:

* Deploying the application to a publicly accessible server
* Moving database credentials to environment variables
* Adding automated database initialization
* Adding unit and integration tests for API endpoints
* Containerizing the application with Docker
* Adding additional transcriptomic visualizations
* Incorporating pathway and gene-set enrichment analysis
* Supporting additional RNA-seq datasets

## License

This repository was developed as an academic project. Please contact the repository authors regarding reuse or redistribution of the application and associated data.
