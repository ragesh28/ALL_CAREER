const codingLanguages = [
  ['cpp', 'C++'], ['java', 'Java'], ['python3', 'Python3'], ['python', 'Python'],
  ['javascript', 'JavaScript'], ['typescript', 'TypeScript'], ['csharp', 'C#'],
  ['c', 'C'], ['golang', 'Go'], ['kotlin', 'Kotlin'], ['swift', 'Swift'],
  ['rust', 'Rust'], ['ruby', 'Ruby'], ['php', 'PHP'], ['dart', 'Dart'],
  ['scala', 'Scala'], ['elixir', 'Elixir'], ['erlang', 'Erlang'], ['racket', 'Racket'],
] as const;

const sqlLanguages = [
  ['mysql', 'MySQL'], ['mssql', 'MS SQL Server'], ['postgresql', 'PostgreSQL'], ['oraclesql', 'Oracle'],
] as const;

export const practiceLanguageGroups = [
  { label: 'Programming', options: codingLanguages },
  { label: 'Shell', options: [['bash', 'Bash']] as const },
  { label: 'Databases and data frames', options: [...sqlLanguages, ['pythondata', 'Pandas'] as const] },
];

const optionAliases = new Map<string, string>(
  practiceLanguageGroups.flatMap(group => [...group.options].flatMap(([value, label]) =>
    [[value, value], [label.toLowerCase(), value]] as [string, string][]
  )),
);
optionAliases.set('shell', 'bash');

// The current catalog has no editor-language metadata. These IDs cover
// JavaScript exercises whose catalog rows lack a JavaScript topic tag.
const javascriptProblems = new Set([
  2618, 2619, 2620, 2621, 2622, 2623, 2625, 2626, 2627, 2629, 2630, 2631, 2634, 2635, 2636, 2637,
  2648, 2665, 2666, 2667, 2675, 2694, 2700, 2703, 2704, 2705, 2715, 2721, 2722, 2723, 2724,
  2725, 2726, 2727, 2758, 2774, 2794, 2803,
]);

const concurrencyLanguages = new Set(['cpp', 'java', 'python3', 'python', 'csharp', 'c', 'golang']);
const generalLanguages = new Set<string>(codingLanguages.map(([value]) => value));
const databaseLanguages = new Set<string>(sqlLanguages.map(([value]) => value));

interface LanguageProblem {
  id: number;
  topics?: string[];
  languages?: unknown;
  codeSnippets?: unknown;
}

export function matchesPracticeLanguage(problem: LanguageProblem, language: string): boolean {
  if (language === 'all') return true;

  const metadata = [problem.languages, problem.codeSnippets]
    .flatMap(value => Array.isArray(value) ? value : []);
  const supported = new Set(metadata.map((entry: unknown) => {
    const snippet = typeof entry === 'object' && entry !== null ? entry as Record<string, unknown> : null;
    const value = typeof entry === 'string' ? entry : snippet?.langSlug ?? snippet?.lang;
    return typeof value === 'string' ? optionAliases.get(value.trim().toLowerCase()) : undefined;
  }).filter(Boolean));
  if (supported.size) return supported.has(language);

  const topics = problem.topics?.map(topic => topic.toLowerCase()) ?? [];
  if (topics.includes('shell') || topics.includes('bash')) return language === 'bash';
  if (topics.includes('pandas') || (problem.id >= 2877 && problem.id <= 2891)) return language === 'pythondata';
  if (topics.includes('database') || topics.includes('sql')) return databaseLanguages.has(language) || language === 'pythondata';
  if (topics.includes('javascript') || javascriptProblems.has(problem.id)) return language === 'javascript' || language === 'typescript';
  if (topics.includes('concurrency')) return concurrencyLanguages.has(language);
  return generalLanguages.has(language);
}
