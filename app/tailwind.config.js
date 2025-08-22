/** tailwind.config.js */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./apps/**/templates/**/*.html",
        "./static/js/**/*.js",
        // add any other paths with Tailwind classes
    ],
    theme: {
        extend: {},
    },
    plugins: [
        require("daisyui")
    ],
    daisyui: {
        themes: ["light", "dark"], // adjust as you like
    },
}