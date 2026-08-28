export type CountGroup = { label: string; count: number };

export type ResponseSignal = {
  population: string;
  median_difference_percentage_points: number;
  p_value: number;
  adjusted_p_value: number;
  fdr_significant: boolean;
};

export type OverviewData = {
  counts: { projects: number; subjects: number; samples: number; cell_measurements: number };
  sample_types: CountGroup[];
  conditions: CountGroup[];
  projects: CountGroup[];
  response_signal: ResponseSignal | null;
  baseline_response_signal: ResponseSignal | null;
};

export type FrequencyRow = {
  sample: string;
  total_count: number;
  population: string;
  count: number;
  percentage: number;
};

export type FrequencyResponse = { total: number; rows: FrequencyRow[] };

export type ResponseValue = {
  subject_key: number;
  project: string;
  subject: string;
  response: "yes" | "no";
  population: string;
  mean_percentage: number;
};

export type StatisticalResult = {
  population: string;
  responders_n: number;
  nonresponders_n: number;
  responder_median_percentage: number;
  nonresponder_median_percentage: number;
  median_difference_percentage_points: number;
  mann_whitney_u: number;
  p_value: number;
  rank_biserial_effect_size: number;
  adjusted_p_value: number;
  nominally_significant_at_0_05: boolean;
  fdr_significant_at_0_05: boolean;
};

export type ResponseAnalysisData = {
  subject_count: number;
  values: ResponseValue[];
  statistics: StatisticalResult[];
  baseline_values: ResponseValue[];
  baseline_statistics: StatisticalResult[];
};

export type BaselineSummary = {
  baseline_sample_count: number;
  baseline_subject_count: number;
  samples_by_project: Record<string, number>;
  subjects_by_response: Record<string, number>;
  subjects_by_sex: Record<string, number>;
  average_b_cells_melanoma_male_responders_time_0: number;
};

export type Page = "overview" | "frequencies" | "response" | "baseline";
