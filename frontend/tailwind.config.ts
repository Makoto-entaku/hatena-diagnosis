import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // はてな展のキーカラー(紺)
        navy: {
          DEFAULT: '#1f2c5b',
          deep:    '#142046',
          light:   '#3a4a85',
        },
        cream: '#f8f4e8',
      },
      fontFamily: {
        // Mac の日本語フォントを優先(印刷時 sheet.py と揃える)。
        sans: [
          '"Hiragino Sans"',
          '"Hiragino Kaku Gothic ProN"',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
export default config;
