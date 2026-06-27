import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f4ff",
          500: "#3b82f6",
          600: "#2563eb",
          900: "#1e3a5f",
        },
      },
    },
  },
  plugins: [],
};
export default config;
