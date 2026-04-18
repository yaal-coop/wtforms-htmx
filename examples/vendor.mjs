// Copy the front-end dependencies of the examples from node_modules to
// examples/static/vendor/. Runs as the npm postinstall script.
import { cpSync, mkdirSync } from "node:fs"
import { dirname } from "node:path"

const FILES = {
  "htmx2/htmx.min.js": "htmx2/dist/htmx.min.js",
  "htmx2/head-support.js": "htmx-ext-head-support/head-support.js",
  "htmx4/htmx.min.js": "htmx4/dist/htmx.min.js",
  "htmx4/hx-head.js": "htmx4/dist/ext/hx-head.js",
  "Sortable.min.js": "sortablejs/Sortable.min.js",
  "pico.min.css": "@anyblades/blades/css/pico.min.css",
}

for (const [dest, src] of Object.entries(FILES)) {
  const target = `examples/static/vendor/${dest}`
  mkdirSync(dirname(target), { recursive: true })
  cpSync(`node_modules/${src}`, target)
}
