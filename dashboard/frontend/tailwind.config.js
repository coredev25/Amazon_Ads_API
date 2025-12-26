/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class', // Enable dark mode via class strategy
  theme: {
    extend: {
      colors: {
        // Amazon-inspired color palette
        amazon: {
          orange: '#FF9900',
          'orange-dark': '#E68A00',
          blue: '#146EB4',
          'blue-dark': '#0F5B8A',
          navy: '#232F3E',
          'navy-light': '#37475A',
        },
        // Dashboard accent colors
        accent: {
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          info: '#3B82F6',
        },
        // Light mode surfaces
        surface: {
          light: '#FFFFFF',
          'light-elevated': '#F9FAFB',
          'light-border': '#E5E7EB',
          'light-muted': '#9CA3AF',
        },
      },
      fontFamily: {
        sans: ['Instrument Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};

