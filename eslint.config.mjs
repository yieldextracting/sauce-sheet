import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const SPORTSBOOK_LINK =
  "/(draftkings|fanduel|betmgm|caesars|espnbet|fanatics|bet365|pointsbet|betrivers|williamhill|pinnacle|bovada|mybookie)\\.(com|net|ag|eu)/i";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/lib/time.ts"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: "CallExpression[callee.property.name=/^toLocale(Date|Time)?String$/]",
          message: "Format dates only through src/lib/time.ts (US Eastern).",
        },
        {
          selector: "CallExpression[callee.property.name=/^get(Hours|Minutes|Date|Day|Month|FullYear)$/]",
          message: "Local-time getters use the machine's time zone. Use src/lib/time.ts.",
        },
        {
          selector: `Literal[value=${SPORTSBOOK_LINK}]`,
          message: "No links to sportsbooks (compliance).",
        },
      ],
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", ".venv/**", "data/**"]),
]);

export default eslintConfig;
