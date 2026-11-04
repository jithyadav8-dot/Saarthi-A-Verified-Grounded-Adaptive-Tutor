import { copyFile } from "node:fs/promises";

// Keep the browser worker and PDF.js library on exactly the same installed version.
await copyFile(
  new URL("../node_modules/pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url),
  new URL("../public/pdf.worker.min.mjs", import.meta.url),
);
