/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Pretendard',
          '-apple-system',
          '"SF Pro Display"',
          'system-ui',
          'sans-serif'
        ]
      },
      colors: {
        bg: {
          light: '#F9FAFB',
          dark: '#000000'
        },
        surface: {
          light: '#FFFFFF',
          dark: '#1C1C1E',
          'dark-elevated': '#2C2C2E'
        },
        text: {
          primary: {
            light: '#191F28',
            dark: '#FFFFFF'
          },
          secondary: {
            light: '#6B7684',
            dark: '#98989F'
          }
        },
        divider: {
          light: '#F2F4F6',
          dark: 'rgba(255,255,255,0.06)'
        },
        brand: {
          DEFAULT: '#3182F6',
          pressed: '#1B64DA',
          dark: '#4C9AFF'
        },
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#FF5847'
      },
      borderRadius: {
        card: '20px',
        button: '14px',
        input: '12px',
        badge: '8px'
      },
      boxShadow: {
        card: '0 1px 2px rgba(20,20,43,0.04), 0 12px 40px rgba(20,20,43,0.06)'
      },
      fontSize: {
        display: ['42px', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '700' }],
        title: ['24px', { lineHeight: '1.3', fontWeight: '700' }],
        body: ['17px', { lineHeight: '1.55', fontWeight: '400' }],
        caption: ['13px', { lineHeight: '1.4', fontWeight: '500' }]
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.2, 0.9, 0.2, 1.05)'
      }
    }
  },
  plugins: []
};
