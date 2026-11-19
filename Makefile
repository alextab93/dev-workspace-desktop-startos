ARCHES := x86 arm
include node_modules/@start9labs/start-sdk/s9pk.mk

.PHONY: check-assets

ingredients: check-assets

check-assets:
	@node -e 'const fs = require("node:fs"); const invalid = fs.readdirSync("assets", {recursive: true}).filter(name => name.split("/").includes("__pycache__") || /\.py[co]$$/.test(name)); if (invalid.length) { console.error("Remove generated Python cache files from assets before packaging:\n" + invalid.join("\n")); process.exit(1); }'
