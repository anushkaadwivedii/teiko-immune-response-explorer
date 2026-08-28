PRAGMA foreign_keys = ON;

CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY,
    project_code TEXT NOT NULL UNIQUE
);

CREATE TABLE subjects (
    subject_id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    subject_code TEXT NOT NULL,
    condition TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age BETWEEN 0 AND 130),
    sex TEXT NOT NULL CHECK (sex IN ('M', 'F')),
    treatment TEXT NOT NULL,
    response TEXT CHECK (response IN ('yes', 'no') OR response IS NULL),
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    UNIQUE (project_id, subject_code)
);

CREATE TABLE samples (
    sample_id INTEGER PRIMARY KEY,
    sample_code TEXT NOT NULL UNIQUE,
    subject_id INTEGER NOT NULL,
    sample_type TEXT NOT NULL,
    time_from_treatment_start INTEGER NOT NULL
        CHECK (time_from_treatment_start >= 0),
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

CREATE TABLE cell_populations (
    population_id INTEGER PRIMARY KEY,
    population_name TEXT NOT NULL UNIQUE
);

CREATE TABLE cell_counts (
    sample_id INTEGER NOT NULL,
    population_id INTEGER NOT NULL,
    cell_count INTEGER NOT NULL CHECK (cell_count >= 0),
    PRIMARY KEY (sample_id, population_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (population_id) REFERENCES cell_populations(population_id)
);

CREATE INDEX idx_subjects_analysis_filters
    ON subjects (condition, treatment, response);

CREATE INDEX idx_subjects_demographic_filters
    ON subjects (condition, sex, response);

CREATE INDEX idx_samples_subject_type_time
    ON samples (subject_id, sample_type, time_from_treatment_start);

CREATE INDEX idx_samples_type_time
    ON samples (sample_type, time_from_treatment_start);

CREATE INDEX idx_cell_counts_population
    ON cell_counts (population_id);

CREATE VIEW sample_totals AS
SELECT
    sample_id,
    SUM(cell_count) AS total_count
FROM cell_counts
GROUP BY sample_id;

CREATE VIEW sample_population_frequencies AS
SELECT
    s.sample_code AS sample,
    totals.total_count,
    p.population_name AS population,
    cc.cell_count AS count,
    100.0 * cc.cell_count / totals.total_count AS percentage
FROM cell_counts AS cc
JOIN samples AS s ON s.sample_id = cc.sample_id
JOIN cell_populations AS p ON p.population_id = cc.population_id
JOIN sample_totals AS totals ON totals.sample_id = cc.sample_id;
