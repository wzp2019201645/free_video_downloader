/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1677FF',
          hover: '#0958D9',
          light: '#E6F4FF',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          muted: '#F5F5F5',
        },
      },
      boxShadow: {
        card: '0 2px 8px rgba(0, 0, 0, 0.08)',
        input: '0 2px 12px rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        card: '12px',
      },
    },
  },
  plugins: [],
}
