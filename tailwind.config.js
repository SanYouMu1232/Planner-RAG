/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 深海军蓝顶栏
        navy: {
          DEFAULT: '#0f1d36',
          light: '#152544',
          dark: '#0a1528',
        },
        // 浅灰画布背景
        canvas: {
          DEFAULT: '#f2f4f7',
          alt: '#eef0f4',
        },
        // 主色调
        primary: {
          DEFAULT: '#1a5fdc',
          hover: '#1550c0',
          light: '#e8f0fe',
        },
        // 卡片与表面
        surface: {
          DEFAULT: '#ffffff',
          hover: '#f9fafb',
        },
        // 边框 (使用 edge 避免与 Tailwind border 核心插件冲突)
        edge: {
          DEFAULT: '#e5e7eb',
          light: '#f0f1f3',
          focus: '#1a5fdc',
        },
        // 文字
        foreground: {
          DEFAULT: '#1f2937',
          secondary: '#6b7280',
          muted: '#9ca3af',
        },
        // 状态色
        status: {
          active: '#16a34a',
          repealed: '#dc2626',
          draft: '#f59e0b',
        },
      },
      borderRadius: {
        card: '8px',
      },
      height: {
        control: '44px',
      },
      minHeight: {
        control: '44px',
      },
      fontSize: {
        'xs': ['12px', { lineHeight: '16px' }],
        'sm': ['14px', { lineHeight: '20px' }],
        'base': ['15px', { lineHeight: '24px' }],
        'lg': ['16px', { lineHeight: '24px' }],
        'xl': ['18px', { lineHeight: '28px' }],
        '2xl': ['20px', { lineHeight: '28px' }],
        '3xl': ['24px', { lineHeight: '32px' }],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'card-hover': '0 4px 12px 0 rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
        topbar: '0 1px 3px 0 rgba(0, 0, 0, 0.12)',
      },
    },
  },
  plugins: [],
}
