/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'level-blue': '#2563eb',
        'level-green': '#059669',
        'level-amber': '#d97706',
        'level-red': '#dc2626',
      }
    },
  },
  plugins: [],
}