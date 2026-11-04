import type { Config } from 'tailwindcss';
const config: Config = { content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'], theme: { extend: { colors: { ink: '#0a101b', panel: '#111b2d', line: '#243249', mint: '#b9f66b', cyan: '#7de2d1' }, boxShadow: { glow: '0 0 0 1px rgba(185,246,107,.18), 0 18px 50px rgba(0,0,0,.24)' } } }, plugins: [] };
export default config;
