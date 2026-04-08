// @ts-check
// NativeWind v4 runs this config in Node context — must use require, not import.
const { brand } = require("shared/colors");

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}", "../shared/**/*.{ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: brand.primary.hex,
        background: brand.background.hex,
        foreground: brand.foreground.hex,
        surface: brand.surface.hex,
        muted: brand.muted.hex,
        success: brand.success.hex,
        danger: brand.danger.hex,
        warning: brand.warning.hex,
      },
    },
  },
};
