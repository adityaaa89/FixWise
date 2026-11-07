/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#171821',
          darkSurface: '#21222D',
          darkBorder: '#2E303D',
          darkMuted: '#8E92A4',
          lime: '#C8F135',
          limeHover: '#B5DE27',
          limeSoft: '#F2FCC9',
          canvas: '#F5F6F8',
          card: '#FFFFFF',
          border: '#E8EAED',
          text: '#111827',
          muted: '#6B7280',
        },
        repair: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        replace: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
        },
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
};
