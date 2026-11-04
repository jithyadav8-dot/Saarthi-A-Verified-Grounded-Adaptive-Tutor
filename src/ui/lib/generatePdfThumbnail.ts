/** Render only PDFs, locally, without evaluating embedded PDF JavaScript. */
export async function generatePdfThumbnail(file: File): Promise<string | undefined> {
  if (!/\.pdf$/i.test(file.name)) return undefined;
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
  const task = pdfjs.getDocument({ data: await file.arrayBuffer() });
  try {
    const document = await task.promise;
    const page = await document.getPage(1);
    const viewport = page.getViewport({ scale: 0.4 });
    const canvas = window.document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const context = canvas.getContext("2d");
    if (!context) return undefined;
    await page.render({ canvas, canvasContext: context, viewport }).promise;
    return canvas.toDataURL("image/png");
  } catch {
    return undefined;
  } finally {
    await task.destroy();
  }
}
