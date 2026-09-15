/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Manrope", "Segoe UI", "sans-serif"],
        mono: ["DM Mono", "Cascadia Code", "monospace"],
      },
      colors: {
        meridian: {
          ink: "#d8e7f1",
          muted: "#7890a5",
          cyan: "#62e7df",
          violet: "#9182ff",
          amber: "#f5c674",
          red: "#ff7e85",
        },
      },
      boxShadow: {
        aura: "0 0 28px rgba(98, 231, 223, .13)",
        panel: "0 20px 60px rgba(0, 0, 0, .12)",
      },
    },
  },
  plugins: [],
};
