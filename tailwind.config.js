/** @type {import('tailwindcss').Config} */
const colors = require('tailwindcss/colors')
module.exports = {
  content: ["./templates/**/*.{html,js}"],
  theme: {
    extend: {},
    colors: {
      "catalina-blue": {
        300: "#e6ebf1",
        500: "#9bb0c6",
        400: "#6a88a9",
        600: "#1f4d7e",
        700: "#063970",
        800: "#052e5a",
        900: "#042243",
      },
      gray: colors.gray,
      white: colors.white,
      zinc: colors.zinc,
      green: colors.green,
      slate: colors.slate,
      zinc: colors.zinc,
      stone: colors.stone,
      blue: colors.blue,
      sky: colors.sky,
      red: colors.red
    },
  },
  plugins: [],
  variants: {
    extend: {
      textColor: ["active"],
    },
  },
};
