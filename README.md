# Teiko Immune Response Explorer

This project loads immune cell count data into SQLite, runs the requested analyses, and presents the results in an interactive React and FastAPI dashboard.

## Dashboard

[Open the live dashboard](https://teiko-immune-response-explorer.vercel.app/)

## Running the project

The project is designed to run in GitHub Codespaces with Python 3.12, Node.js, npm, and Make.

```bash
make setup
make pipeline
make dashboard
```

Open `http://localhost:8000` after the server starts. To run the automated checks:

```bash
make test
```

`make pipeline` recreates `cell-count.db` from `cell-count.csv` and writes all generated tables, summaries, and plots to `outputs/`.

## What the pipeline does

1. Validates the source CSV and loads all projects, subjects, samples, and cell counts into SQLite.
2. Calculates the count and relative frequency of all five cell populations in every sample.
3. Compares melanoma patients receiving miraclib using PBMC samples, grouped by treatment response.
4. Produces the requested baseline cohort counts and B-cell calculation.

The main outputs are:

- `sample_frequencies.csv`: the Part 2 summary table
- `statistical_results.csv` and `response_boxplots.png`: the Part 3 comparison
- `baseline_samples.csv` and the baseline summary files: the Part 4 results
- `baseline_predictive_statistics.csv`: a separate day 0 sensitivity analysis

## Database design

The source CSV repeats subject information across samples and stores the five cell populations as separate columns. The database normalizes it into five related tables:

```text
projects 1 ─── many subjects 1 ─── many samples
                                      │
                                      many
                                      │
                               cell_counts many ─── 1 cell_populations
```

`projects` and `subjects` hold trial and patient information. `samples` holds specimen type and treatment timepoint. `cell_populations` stores the population names, and `cell_counts` stores one measurement for each sample and population.

This avoids repeating subject metadata and allows additional cell populations without changing the measurement table. Foreign keys and validation constraints protect data integrity, while indexes support the response and baseline filters. The same structure can support hundreds of projects and millions of measurements; for a much larger deployment, it could be moved to PostgreSQL or a columnar analytics store without changing the analytical model.

The `sample_population_frequencies` database view provides one shared definition for the Part 2 table:

```text
percentage = population count / total sample count × 100
```

## Statistical analysis

The response analysis includes melanoma subjects receiving miraclib with PBMC samples and a recorded yes or no response. Because each subject appears at days 0, 7, and 14, the primary analysis uses each subject's mean frequency rather than treating repeated samples as independent patients.

For each population, a two-sided Mann–Whitney U test compares responders and nonresponders. The output also reports rank-biserial effect size and Benjamini–Hochberg adjusted p values across the five tests.

CD4 T cells have the smallest raw p value across all timepoints (`p = 0.012`), but the adjusted p value is `0.062`. No population meets the corrected 0.05 threshold. The day 0 analysis also finds no significant population differences, so the data does not establish a baseline predictive biomarker.

## Baseline results

The baseline subset contains melanoma PBMC samples at day 0 from subjects receiving miraclib.

| Measure | Result |
| --- | ---: |
| Total samples | 656 |
| Project `prj1` | 384 |
| Project `prj3` | 272 |
| Responders | 331 |
| Nonresponders | 325 |
| Male subjects | 344 |
| Female subjects | 312 |

Across melanoma male responders at day 0, including all sample and treatment types, the average B-cell count is **10,206.15**.

## Project structure

```text
backend/          SQLite loading, analysis functions, and FastAPI routes
frontend/src/     React and TypeScript dashboard
outputs/          Generated analysis tables and plots
tests/            Data, statistics, API, and full-pipeline checks
load_data.py      Required root-level database loader
run_pipeline.py   Runs Parts 2 through 4
Makefile          Setup, pipeline, dashboard, and test commands
```

The analysis code is independent of the web interface. FastAPI exposes the results as JSON and serves the compiled React application, so the production dashboard runs as a single service.
