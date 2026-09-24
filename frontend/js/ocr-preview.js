/**
 * OCR 图片对照预览（内勤页）
 * =====================================================================
 * 做单员核对时用：双击 OCR 弹窗里的缩略图 → 左边看整张图，右边看这张图识别出来的
 * 内容；可以一张一张翻，翻到哪张，右边就高亮那一行（点右边的行也能反过来跳图）。
 *
 * 为什么单独一个文件：app.js 已经很长了，而这里真正需要讲清楚的是
 * 「结果第几行 ↔ 第几张图」这个对应关系，放在一起更好维护。
 *
 * 依赖 app.js 的全局（同页面普通 <script>，共享全局作用域）：
 *   ocrTaskId / ocrImages / OCR_CACHE_KEY
 *   qiniuImg / THUMB_WIDTH / openImgViewer / esc
 * 约束：
 *   1) 必须加载在 app.js **之后**（要读它的顶层 let/const，加载早了会取不到）
 *   2) 不能重复声明上面任何名字：顶层 let/const/function 重名会让整个脚本报错
 *   3) 本文件不在顶层碰 DOM，只在函数里碰 —— 方便单独跑单元测试
 */

// ───────────────────────── 结果缓存：文本 + 行↔图 映射 ─────────────────────────
/**
 * 一条缓存记录统一读成：
 *   text   文本框里的原始文本
 *   order  第 i 行对应第几张图（1 基，与「图片 N」一致）；null = 对应关系不可信
 *   manual 是否被手动编辑过（编辑后行与图不再一一对应，只能按行号兜底）
 *
 * storage 里的形态有三种，都要认：
 *   "张三 4101..."                      老版本：纯字符串
 *   { text, order: [1,2,3] }            识别写入：映射可靠
 *   { text, manual: true }              手动编辑过：映射已丢
 */
function ocrvCacheEntry(taskId) {
  if (!taskId) return { text: "", order: null, manual: false, legacy: false };
  let raw;
  try {
    raw = JSON.parse(localStorage.getItem(OCR_CACHE_KEY) || "{}")[taskId];
  } catch (e) {
    raw = undefined;
  }
  if (raw === undefined || raw === null) {
    return { text: "", order: null, manual: false, legacy: false };
  }
  if (typeof raw === "string") {
    // 老版本：按「第 i 行 = 第 i 张图」折算；行数对不上时由界面提示（见 ocrvMapLines）
    return { text: raw, order: null, manual: false, legacy: true };
  }
  return {
    text: String(raw.text || ""),
    order: Array.isArray(raw.order) ? raw.order.map(Number) : null,
    manual: !!raw.manual,
    legacy: false,
  };
}

/** 老调用点要的只是文本 */
function ocrvCacheText(taskId) {
  return ocrvCacheEntry(taskId).text;
}

function ocrvCacheRawAll() {
  try {
    return JSON.parse(localStorage.getItem(OCR_CACHE_KEY) || "{}");
  } catch (e) {
    return {};
  }
}

/** order 传 null 表示"这次的结果与图片无法对应"，界面会降级成按行号 */
function ocrvCacheWrite(taskId, text, order, manual) {
  if (!taskId) return;
  const all = ocrvCacheRawAll();
  all[taskId] = order ? { text, order } : { text, manual: !!manual };
  localStorage.setItem(OCR_CACHE_KEY, JSON.stringify(all));
}

/** 文本框手动改动 → 同步缓存；文本没变（例如只是关闭弹窗顺手保存）就保留映射 */
function ocrvCacheSaveEdited(taskId, text) {
  if (!taskId) return;
  const cur = ocrvCacheEntry(taskId);
  if (cur.text === text) return;
  ocrvCacheWrite(taskId, text, null, true);
}

// ───────────────────────── 文本 ↔ 行 ↔ 图片（纯函数，好测） ─────────────────────────

/** 文本 → 非空行数组（空行只是分隔，不占"图片槽位"） */
function ocrvLines(text) {
  return String(text == null ? "" : text)
    .split("\n")
    .map(l => l.trim())
    .filter(Boolean);
}

/**
 * 结果行 → [{ no, text, failed, extra }]
 *   no     这张结果对应的图片序号（1 基）。order 缺失时退化成"第 i 行 = 第 i 张图"
 *   failed 「（图片 N 识别失败）」这类占位行
 *   extra  no 超出图片总数的多余行（人工加的），不参与高亮
 */
function ocrvMapLines(text, order, imageCount) {
  return ocrvLines(text).map((line, i) => {
    const no = order && order[i] ? Number(order[i]) : i + 1;
    return {
      no,
      text: line,
      failed: /^（图片\s*\d+\s*识别失败）$/.test(line),
      extra: !!imageCount && no > imageCount,
    };
  });
}

/**
 * 识别完成 → 生成文本框内容并落缓存（含映射）。app.js 的 ocrFillResult 调这里。
 * 追加模式（只勾选了几张识别）时，新行的图片序号是 targets 里的 no，
 * 不是"接着上次的行号" —— 这正是以前靠行号推断会错位的地方。
 */
function ocrvResultBuild(taskId, targets, results, append) {
  const prev = append ? ocrvCacheEntry(taskId) : { text: "", order: null };
  const prevLines = append ? ocrvLines(prev.text) : [];

  const rows = [];
  (results || []).forEach((r, i) => {
    const no = targets && targets[i] ? targets[i].no : i + 1;
    const line = !r
      ? `（图片 ${no} 识别失败）`
      : (r.name ? `${r.name} ${r.id_number}` : r.id_number);
    if (line && String(line).trim()) rows.push({ line: String(line).trim(), no });
  });

  const text = prevLines.concat(rows.map(x => x.line)).join("\n");
  // 映射怎么算：
  //   没有旧文本（首次识别，或首次只勾了几张）→ 本次结果就是全部，按 targets 的 no 记
  //   有旧文本且旧映射能对上 → 接上去
  //   有旧文本但映射对不上（被手动改过/老数据）→ 宁可不记，也别记错的
  const order = !prevLines.length
    ? rows.map(x => x.no)
    : (prev.order && prev.order.length === prevLines.length
        ? prev.order.concat(rows.map(x => x.no))
        : null);

  ocrvCacheWrite(taskId, text, order);
  return text;
}

// ───────────────────────── 预览层 ─────────────────────────

let ocrvIndex = 0;
let ocrvOpen = false;

/** 入口：双击 OCR 弹窗缩略图 */
function openOcrViewer(index) {
  const images = ocrImages || [];
  if (!images.length) return;
  ocrvOpen = true;
  const box = document.getElementById("imgViewer");
  box.classList.add("iv-ocr");
  // 只有一张图时不显示左右切换：显示成灰的反而让人以为按钮坏了
  box.classList.toggle("iv-multi", images.length > 1);
  document.addEventListener("keydown", ocrvOnKey);
  window.addEventListener("resize", ocrvScrollActiveIntoView);
  // 上一张 / 下一张：HTML 里只给了 id，点击事件得在这里绑（只绑一次也行，重复赋同一个引用没副作用）
  const prevBtn = document.getElementById("ivPrev");
  const nextBtn = document.getElementById("ivNext");
  if (prevBtn) {
    prevBtn.onclick = () => ocrViewerStep(-1);
    prevBtn.disabled = false;
  }
  if (nextBtn) {
    nextBtn.onclick = () => ocrViewerStep(1);
    nextBtn.disabled = false;
  }
  // 滚轮缩放是绑在整个预览层上的（app.js 的 viewerScale）：不拦一下，
  // 在右栏或缩略图条上滚滚轮会变成缩放图片（还 preventDefault 掉，列表反而滚不动）
  for (const id of ["ivSideBody", "ivThumbs"]) {
    const el = document.getElementById(id);
    if (el) el.onwheel = e => e.stopPropagation();
  }
  ocrvBuildThumbs();
  ocrvShow(Math.max(0, Math.min(images.length - 1, Number(index) || 0)));
}

/** app.js 的 closeImgViewer 收尾时调用（解绑键盘、复位对照态） */
function ocrvOnViewerClosed() {
  if (!ocrvOpen) return;
  ocrvOpen = false;
  document.removeEventListener("keydown", ocrvOnKey);
  window.removeEventListener("resize", ocrvScrollActiveIntoView);
  document.getElementById("imgViewer").classList.remove("iv-ocr");
}

/**
 * app.js 的 viewerApply（旋转 / 缩放）会回调这里。
 * 竖着看（旋转 90 / 270）时给图片换个 class，宽高预算由 CSS 对调 ——
 * 否则横图转竖后仍按"宽度 ≤ 舞台宽"限制，会被裁掉，看着就像"旋转没反应"。
 * viewerRot 是 app.js 的顶层变量，同一页面的普通脚本可以直接读。
 */
function ocrvOnViewerTransform() {
  const img = document.getElementById("imgViewerSrc");
  if (!img) return;
  const deg = ((Number(viewerRot) % 360) + 360) % 360;
  img.classList.toggle("iv-rot-side", deg % 180 !== 0);
}

/** 显示第 i 张：左图 + 右栏高亮对应行 */
function ocrvShow(i) {
  const images = ocrImages || [];
  if (!images[i]) return;
  ocrvIndex = i;
  // 复用 app.js 的查看器：它负责设图源（1600 宽）、下载链接、复位旋转缩放、显示图层
  openImgViewer(images[i].url, `图片 ${i + 1} / ${images.length}`);
  const prev = document.getElementById("ivPrev");
  const next = document.getElementById("ivNext");
  if (prev) prev.disabled = i === 0;
  if (next) next.disabled = i === images.length - 1;
  ocrvMarkThumb(i);
  ocrvRenderSide(i);
}

function ocrViewerStep(delta) {
  const images = ocrImages || [];
  const next = ocrvIndex + delta;
  if (next < 0 || next >= images.length) return;
  ocrvShow(next);
}

/** 点右边的行 → 跳到对应的图片 */
function ocrvGotoLine(no) {
  const images = ocrImages || [];
  if (no >= 1 && no <= images.length) ocrvShow(no - 1);
}

function ocrViewerGoto(index) {
  ocrvShow(Number(index) || 0);
}

function ocrvOnKey(e) {
  if (!ocrvOpen) return;
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    ocrViewerStep(-1);
  } else if (e.key === "ArrowRight") {
    e.preventDefault();
    ocrViewerStep(1);
  } else if (e.key === "Escape") {
    e.preventDefault();
    closeImgViewer(); // 它内部会回调 ocrvOnViewerClosed 收尾
  }
}

/** 底部缩略图条：只在打开时建一次，切换只改高亮样式（避免 <img> 反复重新请求） */
function ocrvBuildThumbs() {
  const box = document.getElementById("ivThumbs");
  if (!box) return;
  const images = ocrImages || [];
  box.innerHTML = images
    .map((it, k) => `<button type="button" class="iv-thumb" data-k="${k}" title="图片 ${k + 1}">
        <img src="${qiniuImg(it.url, THUMB_WIDTH)}" loading="lazy" decoding="async" alt="图片 ${k + 1}">
      </button>`)
    .join("");
  box.style.display = images.length > 1 ? "flex" : "none";
  box.onclick = e => {
    const btn = e.target.closest(".iv-thumb");
    if (btn) ocrViewerGoto(btn.dataset.k);
  };
}

function ocrvMarkThumb(i) {
  document.querySelectorAll("#ivThumbs .iv-thumb").forEach(el => {
    el.classList.toggle("on", Number(el.dataset.k) === i);
  });
}

/** 右栏：结果逐行 + 当前行高亮 */
function ocrvRenderSide(i) {
  const body = document.getElementById("ivSideBody");
  if (!body) return;

  const images = ocrImages || [];
  const entry = ocrvCacheEntry(ocrTaskId);
  const lines = ocrvMapLines(entry.text, entry.order, images.length);

  if (!lines.length) {
    body.innerHTML = `<div class="iv-empty">该任务还没有识别结果<br>
      <span>关闭本窗口后点「身份证识别」或「图片识别」</span></div>`;
    return;
  }

  const curNo = i + 1;
  const hasCur = lines.some(l => l.no === curNo);
  const head = hasCur
    ? ""
    : `<div class="iv-line on placeholder"><span class="iv-no">图${curNo}</span>
         <span class="iv-text">（本张暂无识别结果）</span></div>`;

  body.innerHTML = head + lines
    .map(l => {
      const cls = ["iv-line"];
      if (l.no === curNo) cls.push("on");
      if (l.failed) cls.push("fail");
      if (l.extra) cls.push("extra");
      return `<div class="${cls.join(" ")}" onclick="ocrvGotoLine(${l.no})">
          <span class="iv-no">${l.extra ? "—" : "图" + l.no}</span>
          <span class="iv-text">${esc(l.text)}</span>
        </div>`;
    })
    .join("");

  ocrvScrollActiveIntoView();
}

function ocrvScrollActiveIntoView() {
  const el = document.querySelector("#ivSideBody .iv-line.on");
  // block:"nearest" —— 只滚右栏，不去动 OCR 弹窗自己的滚动位置
  if (el) el.scrollIntoView({ block: "nearest" });
}
