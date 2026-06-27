// Suggested questions for the chat, tailored to the investor's tech-savviness and
// rotated on each mount (page refresh or investor switch) so the set feels fresh.

const POOL: Record<'simple' | 'advanced', string[]> = {
  simple: [
    'How is my portfolio doing?',
    'What do I own and what is it worth?',
    'What fees and capital calls are coming up?',
    'What does MOIC mean for my portfolio?',
    'Have I received any money back yet?',
    'Which sectors am I most invested in?',
    'Explain my account statement in plain terms.',
    'Do I owe anything right now?',
  ],
  advanced: [
    'Give me portfolio MOIC, DPI and RVPI.',
    'Break down my Forgecraft position across rounds.',
    'What are my upcoming and overdue management fees?',
    'Show realised distributions net of carry.',
    'Where do I have fee discounts vs the deal standard?',
    'How has my biggest holding been marked over time?',
    'What is my exposure and concentration by sector?',
    'Summarise my account statement and net cashflow.',
  ],
}

export function pickSuggestions(tech: string | null, count = 4): string[] {
  const pool = tech === 'High' ? POOL.advanced : POOL.simple
  const start = Math.floor(Math.random() * pool.length)
  const out: string[] = []
  for (let i = 0; i < count && i < pool.length; i++) {
    out.push(pool[(start + i) % pool.length])
  }
  return out
}

// Contextual follow-up questions, picked from the topic of the assistant's last
// answer so the next step is always one click away.
const FOLLOW_UPS: { test: RegExp, options: string[] }[] = [
  {
    test: /\bfee|carry|discount|structuring|admin\b/i,
    options: [
      'What capital calls and fees are coming up?',
      'How do my fees compare to the deal standard?',
      'Show my account statement.',
    ],
  },
  {
    test: /\bdistribution|exit|secondary|received|proceeds\b/i,
    options: [
      'What is my current blended MOIC?',
      'Summarise my account statement.',
      'What are my upcoming obligations?',
    ],
  },
  {
    test: /\bcapital call|obligation|overdue|upcoming|due\b/i,
    options: [
      'What have I received from exits so far?',
      'How is my portfolio doing overall?',
      'Show my account statement.',
    ],
  },
  {
    test: /\bvaluation|marked|markup|down round|share price\b/i,
    options: [
      'How does that affect my MOIC?',
      'What fees do I pay on it?',
      'How is my portfolio doing overall?',
    ],
  },
  {
    test: /\bmoic|portfolio|value|holding|own|sector\b/i,
    options: [
      'What fees and capital calls are coming up?',
      'What have I received from exits so far?',
      'Which sectors am I most invested in?',
    ],
  },
  {
    test: /\bstatement|cashflow|contribution|committed|contributed\b/i,
    options: [
      'What is my blended MOIC?',
      'What are my upcoming obligations?',
      'What have I received so far?',
    ],
  },
]

const GENERIC_FOLLOW_UPS = [
  'How is my portfolio doing?',
  'What are my upcoming fees and capital calls?',
  'What have I received from exits so far?',
]

export function followUps(lastAnswer: string, count = 3): string[] {
  for (const { test, options } of FOLLOW_UPS) {
    if (test.test(lastAnswer)) {
      return options.slice(0, count)
    }
  }
  return GENERIC_FOLLOW_UPS.slice(0, count)
}
