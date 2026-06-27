import type { Config } from 'tailwindcss'

// "equitie" theme — Bloomberg-dense, black background, blue accent (not orange).
export default <Partial<Config>>{
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        equitie: {
          blue: '#2f81f7',
          'blue-dark': '#1f6feb',
          'blue-deep': '#0d419d',
        },
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
}
