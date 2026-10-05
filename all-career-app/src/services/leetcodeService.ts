import { LeetCodeProblem, LeetCodeStatsData } from '../types/leetcode';

export class LeetCodeService {
  private problems: LeetCodeProblem[] = [];
  private totalOfficialProblems = 4073;

  async loadProblems(): Promise<{ problems: LeetCodeProblem[]; stats: LeetCodeStatsData }> {
    if (this.problems.length > 0) {
      return { problems: this.problems, stats: this.computeStats() };
    }

    try {
      const res = await fetch('/ultimate_leetcode_master.json');
      if (res.ok) {
        const data = await res.json();
        this.problems = data.problems || [];
      }
    } catch (e) {
      console.warn('Could not load local ultimate master:', e);
    }

    return {
      problems: this.problems,
      stats: this.computeStats()
    };
  }

  computeStats(): LeetCodeStatsData {
    let easy = 0, med = 0, hard = 0;
    const allCompanies = new Set<string>();

    for (const p of this.problems) {
      const d = (p.difficulty || '').toLowerCase();
      if (d === 'easy') easy++;
      else if (d === 'hard') hard++;
      else med++;

      for (const c of p.companies || []) {
        allCompanies.add(c);
      }
    }

    return {
      totalOfficialCount: this.totalOfficialProblems, // Official platform count
      totalCompanyTaggedCount: this.problems.length,   // 3,474 tagged
      totalUniqueCompanies: allCompanies.size || 1418,
      easyCount: easy,
      mediumCount: med,
      hardCount: hard
    };
  }

  filterProblems(
    searchTerm: string,
    selectedCompany: string,
    selectedDifficulty: string,
    selectedTopic: string
  ): LeetCodeProblem[] {
    const term = searchTerm.toLowerCase().trim();
    const comp = selectedCompany.toLowerCase().trim();
    const diff = selectedDifficulty.toLowerCase().trim();
    const topic = selectedTopic.toLowerCase().trim();

    return this.problems.filter(p => {
      if (term) {
        const matchTitle = p.title.toLowerCase().includes(term);
        const matchId = String(p.id) === term;
        if (!matchTitle && !matchId) return false;
      }
      if (comp && comp !== 'all') {
        const hasComp = p.companies?.some(c => c.toLowerCase() === comp);
        if (!hasComp) return false;
      }
      if (diff && diff !== 'all') {
        if (p.difficulty.toLowerCase() !== diff) return false;
      }
      if (topic && topic !== 'all') {
        const hasTopic = p.topic_tags?.some(t => t.toLowerCase() === topic);
        if (!hasTopic) return false;
      }
      return true;
    });
  }
}

export const leetcodeService = new LeetCodeService();
