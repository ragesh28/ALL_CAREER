export interface LeetCodeProblem {
  id: number;
  title: string;
  slug?: string;
  url: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | string;
  paid_only?: boolean;
  total_acs?: number;
  total_submitted?: number;
  acceptance_rate?: number | string;
  total_companies_asking?: number;
  max_frequency_pct?: number;
  avg_frequency_pct?: number;
  interview_times_count?: number;
  global_frequency_score?: number;
  pattern?: string;
  revision_priority?: string;
  topic_tags?: string[];
  companies?: string[];
  company_details?: Record<string, {
    time_windows?: string[];
    frequencies?: Record<string, string | number>;
  }>;
}

export interface LeetCodeStatsData {
  totalOfficialCount: number;
  totalCompanyTaggedCount: number;
  totalUniqueCompanies: number;
  easyCount: number;
  mediumCount: number;
  hardCount: number;
}
