/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: '#0b2447',
          dark: '#081a2e',
          blue: '#19376d',
          accent: '#0284c7',
          muted: '#64748b',
          surface: '#f8fafc',
          border: '#e2e8f0',
        },
        thermal: {
          light: '#ffedd5',
          DEFAULT: '#ea580c',
          glow: '#fb923c',
          dark: '#9a3412',
        },
        risk: {
          light: '#fee2e2',
          DEFAULT: '#dc2626',
          dark: '#991b1b',
        },
        facility: {
          light: '#dbeafe',
          DEFAULT: '#2563eb',
          dark: '#1e40af',
        },
        invest: {
          light: '#dcfce7',
          DEFAULT: '#16a34a',
          dark: '#15803d',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 10px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02)',
        elevated: '0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)',
        hotspot: '0 0 15px rgba(234, 88, 12, 0.6), 0 0 30px rgba(239, 68, 68, 0.4)',
      },
      keyframes: {
        'pulse-slow': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.6', transform: 'scale(1.15)' },
        },
        'radar-ping': {
          '0%': { transform: 'scale(0.8)', opacity: '0.9' },
          '100%': { transform: 'scale(2.2)', opacity: '0' },
        }
      },
      animation: {
        'pulse-slow': 'pulse-slow 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'radar-ping': 'radar-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
      }
    },
  },
  plugins: [],
}
