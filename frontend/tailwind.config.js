/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        espresso: { 950: '#2B1B16', 900: '#3A2520', 800: '#4A3028', 700: '#63463B', 600: '#80665A' },
        sand: { 300: '#CBB9AC', 200: '#E9DED6', 100: '#F5EFEA', 50: '#FAF8F6' },
        clay: '#B08968',
        gold: '#B89B72',
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(43,27,22,.04), 0 8px 30px -12px rgba(43,27,22,.14)',
        lift: '0 2px 4px rgba(43,27,22,.05), 0 20px 50px -18px rgba(43,27,22,.28)',
      },
      borderRadius: { '2xl': '1.25rem', '3xl': '1.75rem' },
    },
  },
  plugins: [],
}
