type ExportPosterItem = {
  day_index: number;
  sort_order: number;
  start_time: string | null;
  duration_minutes: number | null;
  cost: number | null;
  tips: string | null;
  poi: {
    name: string;
    type: string;
    address: string | null;
    opening_hours: string | null;
    ticket_price: number | null;
  };
};

type ExportItineraryData = {
  title: string;
  destination: string;
  days: number;
  author_nickname: string;
  share_url: string;
  items: ExportPosterItem[];
};

type ExportOptions = {
  data: ExportItineraryData;
  fileBaseName: string;
};

const POSTER_WIDTH = 1180;
const POSTER_PADDING = 44;
const POSTER_SCALE = 2;
const A4_RATIO = 297 / 210;
const MAX_CANVAS_DIMENSION = 32000;

function sanitizeFileName(input: string): string {
  return input.replace(/[\\/:*?"<>|]/g, "-").trim() || "itinerary-export";
}

function formatMoney(value: number | null): string {
  if (value == null) {
    return "未提供";
  }
  return `¥${value}`;
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  const paragraphs = text.split(/\r?\n/);
  for (const para of paragraphs) {
    const normalized = para.trim();
    if (!normalized) {
      lines.push("");
      continue;
    }
    let current = "";
    for (const char of normalized) {
      const candidate = `${current}${char}`;
      if (ctx.measureText(candidate).width <= maxWidth) {
        current = candidate;
      } else {
        if (current) lines.push(current);
        current = char;
      }
    }
    if (current) {
      lines.push(current);
    }
  }
  return lines;
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function measureItemHeight(ctx: CanvasRenderingContext2D, item: ExportPosterItem, contentWidth: number): number {
  let height = 20;

  ctx.font = '700 30px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  const nameLines = wrapText(ctx, `${item.sort_order}. ${item.poi.name}`, contentWidth);
  height += nameLines.length * 40;

  height += 30; // type
  height += 28; // start time
  height += 32; // cost

  ctx.font = '500 18px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  const addressLines = wrapText(ctx, `地址：${item.poi.address || "未提供"}`, contentWidth);
  height += addressLines.length * 26;

  const openingLines = wrapText(ctx, `营业时间：${item.poi.opening_hours || "未提供"}`, contentWidth);
  height += openingLines.length * 26;

  if (item.tips) {
    height += 8;
    const tipLines = wrapText(ctx, `建议：${item.tips}`, contentWidth);
    height += tipLines.length * 26;
  }

  return height + 20;
}

function buildPosterCanvas(data: ExportItineraryData): HTMLCanvasElement {
  const grouped = new Map<number, ExportPosterItem[]>();
  for (const item of data.items) {
    if (!grouped.has(item.day_index)) {
      grouped.set(item.day_index, []);
    }
    grouped.get(item.day_index)?.push(item);
  }
  const sortedDays = [...grouped.keys()].sort((a, b) => a - b);
  for (const day of sortedDays) {
    grouped.get(day)?.sort((a, b) => a.sort_order - b.sort_order);
  }

  // Pass 1: Measure height precisely
  const measureCanvas = document.createElement("canvas");
  measureCanvas.width = 1;
  measureCanvas.height = 1;
  const mCtx = measureCanvas.getContext("2d");
  if (!mCtx) {
    throw new Error("导出失败：无法创建画布上下文(预检)");
  }

  let measureY = POSTER_PADDING;
  mCtx.font = '600 18px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  measureY += 36;

  mCtx.font = '700 52px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  const titleLines = wrapText(mCtx, data.title, POSTER_WIDTH - POSTER_PADDING * 2);
  measureY += titleLines.length * 62;
  measureY += 40;

  mCtx.font = '500 18px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  const shareLines = wrapText(mCtx, `公开链接：${data.share_url}`, POSTER_WIDTH - POSTER_PADDING * 2);
  measureY += shareLines.length * 30;
  measureY += 20;
  measureY += 32;

  for (const day of sortedDays) {
    measureY += 52;
    const dayItems = grouped.get(day) || [];
    for (const item of dayItems) {
      const cardInnerWidth = POSTER_WIDTH - POSTER_PADDING * 2 - 40;
      const itemHeight = measureItemHeight(mCtx, item, cardInnerWidth);
      measureY += itemHeight + 16;
    }
    measureY += 18;
  }
  measureY += 18;
  measureY += 40;

  const finalHeight = measureY + POSTER_PADDING;

  // Protect max dimensions
  let scale = POSTER_SCALE;
  if (finalHeight * scale > MAX_CANVAS_DIMENSION) {
    scale = Math.floor(MAX_CANVAS_DIMENSION / finalHeight * 10) / 10;
    if (scale < 1) scale = 1;
  }

  const canvas = document.createElement("canvas");
  canvas.width = POSTER_WIDTH * scale;
  canvas.height = finalHeight * scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("导出失败：无法创建最终画布");
  }

  ctx.scale(scale, scale);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, POSTER_WIDTH, finalHeight);
  ctx.fillStyle = "#1b2a30";
  ctx.textBaseline = "top";

  // Pass 2: render layout
  let y = POSTER_PADDING;
  ctx.font = '600 18px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  ctx.fillStyle = "#4d5f66";
  ctx.fillText("Project Atlas 行程海报", POSTER_PADDING, y);
  y += 36;

  ctx.font = '700 52px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  ctx.fillStyle = "#17242a";
  for (const line of titleLines) {
    if (line) ctx.fillText(line, POSTER_PADDING, y);
    y += 62;
  }

  ctx.font = '500 24px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  ctx.fillStyle = "#30424a";
  ctx.fillText(`${data.destination} · ${data.days} 天 · 作者 ${data.author_nickname}`, POSTER_PADDING, y);
  y += 40;

  ctx.font = '500 18px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  ctx.fillStyle = "#516169";
  for (const line of shareLines) {
    if (line) ctx.fillText(line, POSTER_PADDING, y);
    y += 30;
  }
  y += 20;

  ctx.strokeStyle = "#d9d2c5";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(POSTER_PADDING, y);
  ctx.lineTo(POSTER_WIDTH - POSTER_PADDING, y);
  ctx.stroke();
  y += 32;

  for (const day of sortedDays) {
    ctx.font = '700 36px "Noto Sans SC", "Microsoft YaHei", sans-serif';
    ctx.fillStyle = "#173238";
    ctx.fillText(`Day ${day}`, POSTER_PADDING, y);
    y += 52;

    const dayItems = grouped.get(day) || [];
    for (const item of dayItems) {
      const cardX = POSTER_PADDING;
      const cardY = y;
      const cardWidth = POSTER_WIDTH - POSTER_PADDING * 2;
      const cardInnerWidth = cardWidth - 40;
      const cardInnerX = cardX + 20;
      const itemHeight = measureItemHeight(ctx, item, cardInnerWidth);

      ctx.fillStyle = "#fffaf1";
      drawRoundedRect(ctx, cardX, cardY, cardWidth, itemHeight, 20);
      ctx.fill();
      ctx.strokeStyle = "#e2d9ca";
      ctx.lineWidth = 2;
      ctx.stroke();

      let lineY = cardY + 20;
      ctx.font = '700 30px "Noto Sans SC", "Microsoft YaHei", sans-serif';
      ctx.fillStyle = "#17242a";
      const nameLines = wrapText(ctx, `${item.sort_order}. ${item.poi.name}`, cardInnerWidth);
      for (const line of nameLines) {
        if (line) ctx.fillText(line, cardInnerX, lineY);
        lineY += 40;
      }

      ctx.font = '500 20px "Noto Sans SC", "Microsoft YaHei", sans-serif';
      ctx.fillStyle = "#516169";
      ctx.fillText(item.poi.type || "未分类", cardInnerX, lineY);
      lineY += 30;

      ctx.font = '500 18px "Noto Sans SC", "Microsoft YaHei", sans-serif';
      ctx.fillStyle = "#2f3f46";
      ctx.fillText(
        `开始时间：${item.start_time || "未提供"}    停留时长：${item.duration_minutes == null ? "未提供" : `${item.duration_minutes} 分钟`}`,
        cardInnerX,
        lineY
      );
      lineY += 28;
      ctx.fillText(
        `预算花费：${formatMoney(item.cost)}    参考票价：${formatMoney(item.poi.ticket_price)}`,
        cardInnerX,
        lineY
      );
      lineY += 32;

      const addressLines = wrapText(ctx, `地址：${item.poi.address || "未提供"}`, cardInnerWidth);
      for (const line of addressLines) {
        if (line) ctx.fillText(line, cardInnerX, lineY);
        lineY += 26;
      }

      const openingLines = wrapText(ctx, `营业时间：${item.poi.opening_hours || "未提供"}`, cardInnerWidth);
      for (const line of openingLines) {
        if (line) ctx.fillText(line, cardInnerX, lineY);
        lineY += 26;
      }

      if (item.tips) {
        lineY += 8;
        ctx.fillStyle = "#22574d";
        const tipLines = wrapText(ctx, `建议：${item.tips}`, cardInnerWidth);
        for (const line of tipLines) {
          if (line) ctx.fillText(line, cardInnerX, lineY);
          lineY += 26;
        }
      }

      y += itemHeight + 16;
    }
    y += 18;
  }

  ctx.strokeStyle = "#d9d2c5";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(POSTER_PADDING, y);
  ctx.lineTo(POSTER_WIDTH - POSTER_PADDING, y);
  ctx.stroke();
  y += 18;

  ctx.font = '500 16px "Noto Sans SC", "Microsoft YaHei", sans-serif';
  ctx.fillStyle = "#5e6b71";
  ctx.fillText(
    `生成时间：${new Date().toLocaleString("zh-CN", { hour12: false })}`,
    POSTER_PADDING,
    y
  );

  return canvas;
}

function sliceCanvasByPage(source: HTMLCanvasElement): string[] {
  const pagePixelHeight = Math.floor(source.width * A4_RATIO);
  const pages: string[] = [];
  let offsetY = 0;
  while (offsetY < source.height) {
    const sliceHeight = Math.min(pagePixelHeight, source.height - offsetY);
    const pageCanvas = document.createElement("canvas");
    pageCanvas.width = source.width;
    pageCanvas.height = sliceHeight;
    const ctx = pageCanvas.getContext("2d");
    if (!ctx) {
      throw new Error("导出失败：无法创建分页画布");
    }
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
    ctx.drawImage(source, 0, offsetY, source.width, sliceHeight, 0, 0, pageCanvas.width, sliceHeight);
    pages.push(pageCanvas.toDataURL("image/png"));
    offsetY += sliceHeight;
  }
  return pages;
}

function openPrintWindow(printWindow: Window, pages: string[], fileBaseName: string): void {
  const safeTitle = sanitizeFileName(fileBaseName);
  const pageHtml = pages
    .map(
      (pageData, index) => `
      <section class="sheet">
        <img src="${pageData}" alt="page-${index + 1}" />
        <p class="page-no">${index + 1}/${pages.length}</p>
      </section>
    `
    )
    .join("");
  printWindow.document.open();
  printWindow.document.write(`
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="UTF-8" />
        <title>${safeTitle}</title>
        <style>
          body { margin: 0; background: #f2f2f2; font-family: "Noto Sans SC", sans-serif; }
          .sheet { width: 210mm; min-height: 297mm; margin: 0 auto 8mm; background: #fff; position: relative; }
          .sheet img { width: 100%; display: block; }
          .page-no { position: absolute; right: 8mm; bottom: 6mm; margin: 0; font-size: 10px; color: #4d4d4d; }
          @media print {
            body { background: #fff; }
            .sheet { margin: 0; page-break-after: always; }
            .sheet:last-child { page-break-after: auto; }
          }
        </style>
      </head>
      <body>
        ${pageHtml}
        <script>
          window.onload = () => {
            window.print();
          };
        </script>
      </body>
    </html>
  `);
  printWindow.document.close();
}


export async function exportItineraryPosterPng(options: ExportOptions): Promise<void> {
  await document.fonts.ready;
  const canvas = buildPosterCanvas(options.data);
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("长图生成失败，可能是行程过长超出了浏览器限制"));
        return;
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.download = `${sanitizeFileName(options.fileBaseName)}.png`;
      link.href = url;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      resolve();
    }, "image/png");
  });
}

export async function exportItineraryPdf(options: ExportOptions): Promise<void> {
  // Synchronously open a blank window immediately upon click to bypass popup blockers
  const printWindow = window.open("", "_blank", "noopener,noreferrer");
  if (!printWindow) {
    throw new Error("导出失败：浏览器阻止了打印窗口，请允许弹窗后重试");
  }

  // Show a loading text in the new window while we render
  printWindow.document.write("正在生成 PDF，请稍候...");

  try {
    await document.fonts.ready;
    const canvas = buildPosterCanvas(options.data);
    const pages = sliceCanvasByPage(canvas);
    openPrintWindow(printWindow, pages, `${sanitizeFileName(options.fileBaseName)}.pdf`);
  } catch (error) {
    printWindow.close();
    throw error;
  }
}
