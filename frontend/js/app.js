// ── 带认证的请求封装 ──
function authFetch(url, opts={}) {
  const h = { ...(opts.headers||{}) };
  const t = localStorage.getItem('token');
  if (t) h.Authorization = 'Bearer ' + t;
  return fetch(url, { ...opts, headers: h }).then(r => {
    if (r.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('currentUser');
      location.href = 'login.html';
    }
    return r;
  });
}

// ── 状态映射 ──
const STATUS_TO_INT = {
  pending: 0, in_progress: 1, returned_confirm: 2, done: 3,
  submitted: 4, payment_pending: 5, qrcode: 6, returned_supply: 7,
  void: 8, pending_submit: 9
};

const STATUS_LABELS = {
  0: "待处理", 1: "进行中", 2: "打回·待确认", 3: "已做单",
  4: "已递交", 5: "对公认款中", 6: "二维码", 7: "打回·待补充",
  8: "已作废", 9: "待递交"
};

const STATUS_CSS = {
  0: "tag-muted", 1: "tag-processing", 2: "tag-error", 3: "tag-done",
  4: "tag-teal", 5: "tag-orange", 6: "tag-purple", 7: "tag-rejected",
  8: "tag-muted", 9: "tag-indigo"
};

const TYPE_LABELS = { 1: "新投", 2: "批改" };
const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'];
const RETURNED_STATUSES = [2, 7];

// ── 数据 ──
let allTasks = [];
let allAllTasks = [];
let allUsers = [];
let allCompanies = [];
let currentCompany = "全部";
let selected = [];
let renderedTasks = [];

// SVG icons
const ICONS = {
  img: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
};

// ── API 对接 ──

async function loadCompanies() {
  try {
    const resp = await authFetch('/api/chat/companies');
    if (!resp.ok) return;
    allCompanies = await resp.json();
  } catch {}
}

async function loadTasks(company) {
  const resp = await authFetch('/api/chat/tasks?limit=1000');
  if (!resp.ok) throw new Error('加载任务失败');
  const raw = await resp.json();
  const normalized = await Promise.all(raw.map(async t => {
    const messages = t.messages || [];
    const comments = t.comments || [];
    const images = countImagesFromMessages(messages);
    return normalizeTask(t, comments, images, messages);
  }));
  allAllTasks = normalized;
  allTasks = (company && company !== '全部')
    ? normalized.filter(t => t._insuranceCompany === company)
    : normalized;
  await loadCompanies();
}

async function loadUsers() {
  try {
    const resp = await authFetch('/api/users');
    if (!resp.ok) return;
    const users = await resp.json();
    allUsers = users.filter(u => u.role === 1).map(u => u.display_name);
  } catch {}
}

function countImagesFromMessages(messages) {
  let count = 0;
  messages.forEach(m => {
    (m.file_paths || []).forEach(url => {
      const ext = '.' + url.split('.').pop().toLowerCase();
      if (IMAGE_EXTS.includes(ext)) count++;
    });
  });
  return count;
}

// API 字段 → 模板字段映射
function normalizeTask(t, comments, images, messages) {
  const isReturned = RETURNED_STATUSES.includes(t.status);
  const rejectReason = isReturned && comments.length ? comments[comments.length - 1].content : "";
  return {
    id: t.task_id,
    _insuranceCompany: t.insurance_company || "未知",
    company: t.customer_company || t.insurance_company || "未知",
    user: t.creator || "未知",
    time: t.created_at ? String(t.created_at).replace('T', ' ').slice(0, 19) : "",
    updated_at: t.updated_at || t.created_at || "",
    type: TYPE_LABELS[t.business_type] || "新投",
    status: t.status,
    rejectReason: rejectReason,
    images: images,
    docCount: countDocsFromMessages(messages),
    msgCount: t.msg_count || 0,
    messages: messages || []
  };
}

function countDocsFromMessages(messages) {
  let count = 0;
  messages.forEach(m => {
    (m.file_paths || []).forEach(url => {
      const ext = '.' + url.split('.').pop().toLowerCase();
      if (!IMAGE_EXTS.includes(ext)) count++;
    });
  });
  return count;
}

function getCompanyGroups() {
  const groups = {};
  allTasks.forEach(t => {
    // 从 allTasks 中推断保险公司（用任务原始字段）
    const company = t._insuranceCompany || '未知';
    if (!groups[company]) groups[company] = { users: new Set(), tasks: [] };
    groups[company].tasks.push(t);
    if (t.user) groups[company].users.add(t.user);
  });
  Object.values(groups).forEach(g => g.users = [...g.users]);
  return groups;
}

// ── 侧栏渲染 ──

// ── 未读标记（localStorage + updated_at）──
function isUnread(task) {
  if (!task.updated_at) return false;
  const seen = localStorage.getItem('seen_' + task.id);
  return !seen || task.updated_at > seen;
}

function markSeen(task) {
  if (task.updated_at) localStorage.setItem('seen_' + task.id, task.updated_at);
}

// ── 安全渲染：render() 会重建整块列表 DOM，如果用户正在选中文字（准备复制），
//    重建会把选区清掉导致复制失败，因此这种情况下推迟渲染 ──
let renderPending = false;

function canSafelyRender() {
  const sel = window.getSelection && window.getSelection();
  return !(sel && String(sel).length > 0);
}

function safeRender() {
  if (canSafelyRender()) {
    renderPending = false;
    render();
  } else {
    renderPending = true;
  }
}

// 选区取消后补一次渲染（例如用户复制完点开空白处）
document.addEventListener('mouseup', () => {
  if (!renderPending) return;
  setTimeout(() => {
    if (canSafelyRender()) {
      renderPending = false;
      render();
    }
  }, 0);
});

function markTaskSeen(i) {
  const t = renderedTasks[i];
  if (!t) return;
  // 用户正在选中/复制文字时直接返回，避免重建 DOM 把选区清掉
  const sel = window.getSelection && window.getSelection();
  if (sel && String(sel).length > 0) return;
  // 本就没有未读内容：无需重渲染，保持 DOM 与选中状态不动
  if (!isUnread(t)) return;
  markSeen(t);
  render();
}

function companyHasUnread(company) {
  return allAllTasks.some(t => (t._insuranceCompany || t.insurance_company) === company && isUnread(t));
}

function hasNewImages(task) {
  return isUnread(task) && (task.messages || []).some(m => (m.file_paths || []).length > 0);
}

function renderSidebar() {
  const countEl = document.getElementById('companyCount');
  if (countEl) countEl.textContent = allCompanies.length + ' 家';

  const wrap = document.querySelector('.company-list');
  if (!wrap) return;

  let html = '';
  const totalCount = allCompanies.reduce((s, c) => s + c.count, 0);
  const totalUsers = [...new Set(allCompanies.flatMap(c => c.users || []))];
  html += `<button class="company${currentCompany === '全部' ? ' active' : ''}" data-company="全部" onclick="selectCompany('全部',this)">
    <div class="company-left"><span class="company-name">全部</span><span class="company-meta">${totalCount} 条 · ${totalUsers.join('、')}</span></div>
    <span class="badge">${totalCount}</span>
  </button>`;

  allCompanies.forEach(c => {
    const dot = companyHasUnread(c.name) ? '<i style="width:7px;height:7px;border-radius:50%;background:#f5222d;display:inline-block;margin-left:4px;vertical-align:middle;"></i>' : '';
    html += `<button class="company${currentCompany === c.name ? ' active' : ''}" data-company="${c.name}" onclick="selectCompany('${c.name}',this)">
      <div class="company-left"><span class="company-name">${c.name}</span><span class="company-meta">${c.count} 条 · ${(c.users || []).join('、')}</span></div>
      <span class="badge">${c.count}</span>${dot}
    </button>`;
  });

  wrap.innerHTML = html;
}

// ── 渲染 ──

function render() {
  // 动态生成侧栏保险公司列表
  renderSidebar();

  let d;
  if (currentCompany === "全部") {
    d = { tasks: allTasks };
  } else {
    d = { tasks: allTasks.filter(t => t._insuranceCompany === currentCompany) };
  }

  document.getElementById("companyTitle").textContent = currentCompany;
  document.getElementById("companyTitle2").textContent = currentCompany;
  document.getElementById("userTotal").textContent = allUsers.length + " 个用户";
  document.getElementById("recordTotal").textContent = d.tasks.length + " 条记录";

  // 人员多选面板
  const panel = document.getElementById("userSelectPanel");
  panel.innerHTML = allUsers.map(u => `
    <label class="multi-option">
      <input type="checkbox" ${selected.includes(u) ? "checked" : ""} onchange="toggleUser('${u}')">
      <span class="chk"></span>${u}
    </label>
  `).join("");

  const trigger = document.getElementById("userSelectLabel");
  if (selected.length === 0) trigger.textContent = "全部";
  else if (selected.length === 1) trigger.textContent = selected[0];
  else trigger.innerHTML = `<span>${selected[0]}等</span><span class="count">${selected.length}</span>`;

  // 筛选任务
  const statusChecks = Array.from(document.querySelectorAll("#statusFilter input:checked")).map(c => parseInt(c.value));
  const typeVal = (document.getElementById("typeFilter") || {}).value || "";
  const baseTasks = selected.length ? d.tasks.filter(t => selected.includes(t.user)) : d.tasks;
  let tasks = statusChecks.length ? baseTasks.filter(t => statusChecks.includes(t.status)) : baseTasks;
  if (typeVal) tasks = tasks.filter(t => (t.type || "新投") === typeVal);
  document.getElementById("listCount").textContent = tasks.length;

  const wrap = document.getElementById("taskTableWrap");
  if (!tasks.length) {
    wrap.innerHTML = `<div class="empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6v6H9z"/></svg>
      <div class="empty-text">暂无匹配的提单消息</div>
    </div>`;
    return;
  }

  renderedTasks = tasks;
  const items = tasks.map((t, i) => {
    const stCls = STATUS_CSS[t.status] || "tag-processing";
    const stLabel = STATUS_LABELS[t.status] || "未知";
    const isReturned = RETURNED_STATUSES.includes(t.status);
    return `
    <div class="task-item">
      <div class="task-head">
        <div class="task-head-left">
          <div class="head-info">
            <div class="head-row1">
              <span class="name">${t.company || t.user}</span>
              <span class="type-tag ${t.type === '批改' ? 'type-end' : 'type-new'}">${t.type || '新投'}</span>
            </div>
            <div class="head-row2">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <span class="creator">${t.user}</span>
              <span class="dot-sep">·</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              ${t.time}
            </div>
          </div>
        </div>
        <div class="head-right">
          <span class="tag ${stCls}" onclick="toggleStatusPop(event, ${i})">${stLabel}</span>
          <button class="detail-btn" onclick="runCardOCR(${i})">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 8h3M7 12h5M7 16h4M15 8v8M18 8v8"/></svg>
            OCR 识别
          </button>
          <button class="detail-btn" onclick="openModal(${i})">查看详情 →</button>
        </div>
      </div>
      <div class="msg-block" onclick="markTaskSeen(${i})">
        ${(() => {
          const msgs = (t.messages || []).slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          if (!msgs.length) return '<div class="msg-line"><span class="dot"></span><span class="t"></span><span class="c">共 0 条消息</span></div>';
          const seen = localStorage.getItem('seen_' + t.id);
          return msgs.map(m => {
            const time = m.created_at ? String(m.created_at).replace('T', ' ').slice(0, 19) : '';
            const imgs = (m.file_paths || []).filter(u => IMAGE_EXTS.includes('.' + u.split('.').pop().toLowerCase()));
            const docs = (m.file_paths || []).filter(u => !IMAGE_EXTS.includes('.' + u.split('.').pop().toLowerCase()));
            let c = m.content || '';
            if (!c) {
              const parts = [];
              if (imgs.length) parts.push(`上传了 ${imgs.length} 张图片`);
              if (docs.length) parts.push(`上传了 ${docs.length} 个附件`);
              c = parts.join('，');
            }
            if (!c) return '';
            const isNew = seen && m.created_at > seen;
            const newDot = isNew ? '<span class="unread-dot msg"></span>' : '';
            return `<div class="msg-line"><span class="dot"></span><span class="t">${time}</span><span class="c">${c}</span>${newDot}</div>`;
          }).join('');
        })()}
      </div>
      ${isReturned && t.rejectReason ? `<div class="reject-box"><div class="rb-head"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>退回原因</div><div class="rb-body">${t.rejectReason}</div></div>` : ''}
      <div class="task-foot">
        <div class="foot-left">
          <span class="stat-chip">${ICONS.img}<span><b>${t.images}</b> 张图片</span></span>
          <span class="stat-chip">${ICONS.file}<span><b>${t.docCount}</b> 个附件</span></span>
          <span class="stat-chip">${ICONS.search}<span><b>${t.msgCount}</b> 条消息</span></span>
        </div>
      </div>
    </div>`;
  }).join("");

  wrap.innerHTML = `<div class="card-list">${items}</div>`;
}

// ── 事件处理 ──

async function selectCompany(name, el) {
  currentCompany = name;
  selected = [];
  document.querySelectorAll(".company").forEach(x => x.classList.remove("active"));
  el.classList.add("active");
  try {
    await loadTasks(name);
    render();
  } catch (e) {
    toast("加载失败：" + e.message);
  }
}

function toggleMultiPanel() {
  document.getElementById("userSelect").classList.toggle("on");
}

function toggleUser(user) {
  if (selected.includes(user)) selected = selected.filter(x => x !== user);
  else selected.push(user);
  selected.sort();
  render();
}

function resetFilter() {
  selected = [];
  document.querySelectorAll(".filter-input").forEach(i => i.value = "");
  document.querySelectorAll(".filter-select").forEach(s => s.selectedIndex = 0);
  document.querySelectorAll("#statusFilter input").forEach(c => c.checked = false);
  render();
  toast("已重置筛选条件");
}

async function refreshData() {
  const btn = document.getElementById("refreshBtn");
  btn.classList.remove("spinning");
  void btn.offsetWidth;
  btn.classList.add("spinning");
  try {
    await loadTasks();
    render();
    toast("数据已刷新");
  } catch (e) {
    toast("刷新失败");
  }
}

document.addEventListener("click", function (e) {
  const sel = document.getElementById("userSelect");
  if (sel && !sel.contains(e.target)) sel.classList.remove("on");
});

// ── 详情弹窗 ──

let currentModalTask = null;

async function openModal(i) {
  const task = renderedTasks[i];
  if (!task) return;
  currentModalTask = task;
  document.getElementById("modalSub").textContent = (task.company || task.user) + " · " + (task.type || "新投");
  const fileList = document.getElementById("fileList");
  fileList.innerHTML = `<div style="text-align:center;padding:24px;color:var(--gray-400);font-size:var(--fs-sm)">加载中...</div>`;
  document.getElementById("modalMask").classList.add("show");

  try {
    const resp = await authFetch(`/api/chat/messages?task_id=${task.id}`);
    const messages = resp.ok ? await resp.json() : [];
    const files = [];
    messages.forEach(m => {
      (m.file_paths || []).forEach(url => {
        const ext = '.' + url.split('.').pop().toLowerCase();
        const isImg = IMAGE_EXTS.includes(ext);
        let type = "file";
        if (isImg) type = "image";
        else if (ext === '.pdf') type = "pdf";
        else if (ext === '.doc' || ext === '.docx') type = "word";
        else if (ext === '.xls' || ext === '.xlsx') type = "excel";
        files.push({ name: url.split('/').pop(), type: type, size: "", url: url });
      });
    });
    // 提单详情只展示文档附件，不展示图片
    const docFiles = files.filter(f => f.type !== "image");
    document.getElementById("fileCount").textContent = docFiles.length + " 个";
    const typeLabel = { pdf: "PDF", excel: "XLS", word: "DOC", image: "IMG" };
    if (docFiles.length) {
      fileList.innerHTML = docFiles.map(f => `
        <div class="file-item" onclick="window.open('${f.url}', '_blank')">
          <div class="file-icon t-${f.type}">${typeLabel[f.type] || "FILE"}</div>
          <div class="file-info">
            <div class="file-name">${f.name}</div>
            <div class="file-meta">${f.size}</div>
          </div>
          <span class="file-dl">下载</span>
        </div>
      `).join("");
    } else {
      fileList.innerHTML = `<div style="text-align:center;padding:24px;color:var(--gray-400);font-size:var(--fs-sm)">暂无附件</div>`;
    }
  } catch (e) {
    fileList.innerHTML = `<div style="text-align:center;padding:24px;color:#ff4d4f;font-size:var(--fs-sm)">加载失败</div>`;
  }
}

function closeModal() {
  currentModalTask = null;
  document.getElementById("modalMask").classList.remove("show");
}

// ── 状态修改弹窗 ──

let statusTargetIdx = -1;

function toggleStatusPop(e, i) {
  e.stopPropagation();
  statusTargetIdx = i;
  const t = renderedTasks[i];
  if (!t) return;
  document.getElementById("statusSub").textContent = (t.company || t.user);
  // 预选当前状态（int 值）
  document.querySelectorAll('#statusGrid input[name="st"]').forEach(r => {
    r.checked = (parseInt(r.value) === t.status);
  });
  // 回显驳回原因
  document.getElementById("rejectInput").value = t.rejectReason || "";
  const showReject = RETURNED_STATUSES.includes(t.status);
  document.getElementById("rejectWrap").style.display = showReject ? 'block' : 'none';
  document.getElementById("statusMask").classList.add("show");
}

function closeStatusModal() { document.getElementById("statusMask").classList.remove("show"); }

// 选中退回时显示原因输入框
document.addEventListener("change", function (e) {
  if (e.target.name === "st") {
    document.getElementById("rejectWrap").style.display = RETURNED_STATUSES.includes(parseInt(e.target.value)) ? 'block' : 'none';
  }
});

async function confirmStatus() {
  if (statusTargetIdx < 0) return;
  const t = renderedTasks[statusTargetIdx];
  if (!t) return;
  const sel = document.querySelector('input[name="st"]:checked');
  if (!sel) { toast("请选择状态"); return; }
  const val = parseInt(sel.value);
  const RETURNED = RETURNED_STATUSES;
  if (RETURNED.includes(val)) {
    const reason = document.getElementById("rejectInput").value.trim();
    if (!reason) { toast("请输入退回原因"); return; }
  }
  try {
    const reason = document.getElementById("rejectInput").value.trim() || null;
    const resp = await authFetch(`/api/chat/tasks/${t.id}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: val, reject_reason: reason })
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      toast(err.detail || "修改失败");
      return;
    }
    closeStatusModal();
    await loadTasks();
    render();
    toast("状态已更新为：" + (STATUS_LABELS[val] || val));
  } catch (e) {
    toast("网络错误，修改失败");
  }
}

// ── OCR 弹窗（UI 占位） ──

let ocrTaskIdx = -1;

function runCardOCR(i) {
  const t = renderedTasks[i];
  if (!t) return;
  ocrTaskIdx = i;
  // 收集任务中的所有图片 URL
  const imgUrls = (t.messages || []).flatMap(m => m.file_paths || [])
    .filter(url => IMAGE_EXTS.includes('.' + url.split('.').pop().toLowerCase()));
  document.getElementById("ocrSub").textContent = (t.company || t.user) + " · " + (t.type || "新投");
  const newImgMarker = hasNewImages(t) ? "新" : "";
  document.getElementById("ocrImgCount").textContent = imgUrls.length + " 张" + (newImgMarker ? " · " + newImgMarker + "图片" : "");
  const seen = localStorage.getItem('seen_' + t.id);
  const imgWithTime = [];
  (t.messages || []).forEach(m => {
    (m.file_paths || []).forEach(url => {
      if (IMAGE_EXTS.includes('.' + url.split('.').pop().toLowerCase())) {
        imgWithTime.push({ url, created_at: m.created_at });
      }
    });
  });
  document.getElementById("ocrThumbList").innerHTML = imgWithTime.length ? imgWithTime.map((item, k) => {
    const isNew = !seen || item.created_at > seen;
    const imgNew = isNew ? '<span class="unread-dot ocr"></span>' : '';
    return `<div class="ocr-thumb${k === 0 ? " active" : ""}" id="ocrThumb-${k}" onclick="ocrSelect(${k});openImgViewer('${item.url}','图片 ${k+1}')" title="点击查看大图">
      ${imgNew}<img src="${item.url}" alt="图片 ${k+1}" onerror="this.style.display='none'">
      <div class="ocr-thumb-label">图片 ${k+1}</div>
    </div>`;
  }).join("") : '<div style="color:#999;padding:20px;">该任务暂无图片</div>';
  document.getElementById("ocrResultArea").innerHTML = `
    <div class="ocr-loading">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32" style="color:var(--gray-300)"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 8h3M7 12h5M7 16h4M15 8v8M18 8v8"/></svg>
      点击下方"开始识别"按钮进行 OCR 识别
    </div>`;
  document.getElementById("ocrVerifyTip").style.display = "none";
  document.getElementById("ocrVerifyBtn").style.display = "none";
  document.getElementById("ocrActionBtn").textContent = "开始识别";
  document.getElementById("ocrActionBtn").onclick = ocrStart;
  document.getElementById("ocrMask").classList.add("show");
}

function closeOcrModal() {
  if (ocrTaskIdx >= 0 && renderedTasks[ocrTaskIdx]) markSeen(renderedTasks[ocrTaskIdx]);
  document.getElementById("ocrMask").classList.remove("show");
}

let viewerRot = 0;
function openImgViewer(src, tag) {
  viewerRot = 0;
  const img = document.getElementById("imgViewerSrc");
  img.src = src;
  img.style.transform = "rotate(0deg)";
  document.getElementById("imgViewerTag").textContent = tag || "";
  // 设置下载链接
  const dl = document.getElementById("imgViewerDl");
  dl.href = src;
  dl.download = (tag || "image") + ".jpg";
  document.getElementById("imgViewer").classList.add("show");
}
function viewerRotate() {
  viewerRot += 90;
  document.getElementById("imgViewerSrc").style.transform = `rotate(${viewerRot}deg)`;
}
function closeImgViewer() { document.getElementById("imgViewer").classList.remove("show"); }

function ocrSelect(k) {
  document.querySelectorAll(".ocr-thumb").forEach((el, idx) => el.classList.toggle("active", idx === k));
}

function ocrStart() {
  const t = renderedTasks[ocrTaskIdx];
  if (!t) return;
  const imgUrls = (t.messages || []).flatMap(m => m.file_paths || [])
    .filter(url => IMAGE_EXTS.includes('.' + url.split('.').pop().toLowerCase()));
  if (!imgUrls.length) {
    toast("该任务暂无图片");
    return;
  }
  const btn = document.getElementById("ocrActionBtn");
  btn.disabled = true;
  btn.textContent = "识别中...";
  document.getElementById("ocrResultArea").innerHTML = `
    <div class="ocr-loading"><span class="spinner"></span>正在识别 ${imgUrls.length} 张身份证，请稍候...</div>`;
  authFetch('/api/ocr/recognize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_urls: imgUrls }),
  })
    .then(r => {
      if (!r.ok) return r.json().then(e => { throw new Error(e.detail || '识别失败'); });
      return r.json();
    })
    .then(data => {
      ocrResults = data.results || [];
      ocrErrors = data.errors || [];
      btn.disabled = false;
      btn.textContent = "重新识别";
      btn.onclick = ocrStart;
      document.getElementById("ocrVerifyBtn").style.display = "inline-flex";
      document.getElementById("ocrCopyBtn").style.display = "inline-flex";
      ocrFillResult();
      toast("OCR 识别完成");
    })
    .catch(e => {
      btn.disabled = false;
      btn.textContent = "开始识别";
      document.getElementById("ocrResultArea").innerHTML = `
        <div class="ocr-loading" style="color:#f5222d">识别失败：${e.message}</div>`;
      toast("识别失败：" + e.message);
    });
}

let ocrResults = [];
let ocrErrors = [];

function ocrFillResult() {
  const lines = ocrResults.map((r, i) => {
    if (!r) return `（第 ${i + 1} 张识别失败）`;
    return (r.name || "未知") + " " + r.id_number;
  });
  document.getElementById("ocrResultArea").innerHTML = `
    <textarea class="cr-edit ocr-summary" id="ocrSummary" placeholder="识别结果为空，可手动输入或粘贴">${lines.join("\n")}</textarea>`;
  document.getElementById("ocrVerifyTip").style.display = "none";
}

function ocrCopyResults() {
  // 优先复制校验结果表格（Tab 分隔多列）
  if (window._verifyResults && window._verifyResults.length) {
    const lines = ['姓名\t身份证号\t状态\t出生日期\t年龄\t性别'];
    window._verifyResults.forEach(r => {
      lines.push([
        r.name || '',
        r.id_card || '',
        r.is_valid ? '通过' : '失败',
        r.birth_date || '',
        r.age != null ? r.age + '岁' : '',
        r.gender || '',
      ].join('\t'));
    });
    navigator.clipboard.writeText(lines.join('\n')).then(() => toast('校验结果已复制')).catch(() => toast('复制失败'));
    return;
  }
  // 否则复制识别结果（姓名\t身份证号）
  const ta = document.getElementById("ocrSummary");
  if (!ta) return;
  const text = ta.value.split('\n').map(l => l.trim()).filter(Boolean).map(line => {
    const m = line.match(/^(.+?)\s+(\d{17}[\dXx])$/);
    return m ? m[1] + '\t' + m[2] : line;
  }).join('\n');
  navigator.clipboard.writeText(text).then(() => toast('已复制到剪贴板')).catch(() => toast('复制失败'));
}

function ocrVerify() {
  const tip = document.getElementById("ocrVerifyTip");
  tip.style.display = "block";
  const ta = document.getElementById("ocrSummary");
  if (!ta) { tip.innerHTML = '<div class="cr-verify fail">请先进行 OCR 识别</div>'; return; }
  const lines = ta.value.split('\n').map(l => l.trim()).filter(Boolean);
  if (!lines.length) { tip.innerHTML = '<div class="cr-verify fail">识别结果为空</div>'; return; }
  tip.innerHTML = '<div class="ocr-loading"><span class="spinner"></span>正在校验...</div>';
  const reqs = lines.map(line => {
    const parts = line.split(/\s+/);
    const id_number = parts.find(p => /\d{17}[\dXx]/.test(p)) || '';
    const name = id_number ? line.replace(id_number, '').trim() : '';
    return authFetch('/api/ocr/verify', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, id_number }),
    }).then(r => r.ok ? r.json() : { errors: ['请求失败'], is_valid: false });
  });
  Promise.all(reqs).then(results => {
    const pass = results.filter(r => r.is_valid).length;
    const fail = results.length - pass;
    tip.innerHTML = verifyTable(results) +
      '<div class="verify-summary">校验完成：<span class="vs-ok">' + pass + ' 通过</span>，<span class="vs-fail">' + fail + ' 失败</span></div>';
    toast('校验完成：' + pass + ' 通过，' + fail + ' 失败');
    window._verifyResults = results;
    document.getElementById("ocrCopyBtn").style.display = "inline-flex";
  }).catch(e => { tip.innerHTML = '<div class="cr-verify fail">校验失败：' + e.message + '</div>'; });
}

function verifyTable(results) {
  let h = '<table class="verify-table"><thead><tr>' +
    '<th>#</th><th>姓名</th><th>证件号</th><th>类型</th><th>地区</th>' +
    '<th>出生日期</th><th>性别</th><th>年龄</th><th>状态</th><th>提示</th>' +
    '</tr></thead><tbody>';
  results.forEach((r, i) => {
    const st = r.is_valid ? '<span class="v-pass">✓ 通过</span>' : '<span class="v-fail">✗ 失败</span>';
    let note = '-';
    if (!r.is_valid && r.correct_check_code) {
      note = '校验码应为 <strong>' + r.correct_check_code + '</strong>';
      if (r.errors && r.errors.length) note += '<br>' + r.errors.map(e => esc(e)).join('<br>');
    } else if (r.errors && r.errors.length) {
      note = r.errors.map(e => esc(e)).join('<br>');
    } else if (r.warnings && r.warnings.length) {
      note = '<span class="v-warn">' + r.warnings.map(w => esc(w)).join('；') + '</span>';
    }
    h += '<tr><td>' + (i + 1) + '</td>' +
      '<td>' + esc(r.name) + '</td>' +
      '<td>' + esc(r.id_card) + '</td>' +
      '<td>' + esc(r.id_type) + '</td>' +
      '<td>' + esc(r.area) + '</td>' +
      '<td>' + esc(r.birth_date) + '</td>' +
      '<td>' + esc(r.gender) + '</td>' +
      '<td>' + (r.age != null ? r.age + '岁' : '-') + '</td>' +
      '<td>' + st + '</td>' +
      '<td>' + note + '</td></tr>';
  });
  return h + '</tbody></table>';
}

function esc(s) { return s ? String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : '-'; }

// ── Toast ──

let toastTimer;
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
}

// ── 用户下拉菜单 ──

const userMenu = document.getElementById('userMenu');
const userDropdown = document.getElementById('userDropdown');

if (userMenu) {
  userMenu.addEventListener('click', function(e) {
    e.stopPropagation();
    userDropdown.classList.toggle('show');
  });
  document.addEventListener('click', function() {
    userDropdown.classList.remove('show');
  });
}

// ── 修改密码 ──

function openPasswordModal() {
  userDropdown.classList.remove('show');
  const mask = document.getElementById('passwordMask');
  mask.style.display = 'flex';
  // 清空上次输入
  document.getElementById('oldPassword').value = '';
  document.getElementById('newPassword').value = '';
  document.getElementById('confirmPassword').value = '';
  document.getElementById('passwordError').textContent = '';
  document.getElementById('oldPassword').focus();
}

function closePasswordModal() {
  document.getElementById('passwordMask').style.display = 'none';
}

async function submitPassword() {
  const oldPwd = document.getElementById('oldPassword').value;
  const newPwd = document.getElementById('newPassword').value;
  const confirmPwd = document.getElementById('confirmPassword').value;
  const errEl = document.getElementById('passwordError');

  if (!oldPwd || !newPwd || !confirmPwd) {
    errEl.textContent = '请填写所有字段';
    return;
  }
  if (newPwd.length < 6) {
    errEl.textContent = '新密码至少6位';
    return;
  }
  if (newPwd !== confirmPwd) {
    errEl.textContent = '两次输入的新密码不一致';
    return;
  }

  errEl.textContent = '';
  const user = JSON.parse(localStorage.getItem('currentUser') || '{}');
  if (!user.id) {
    errEl.textContent = '用户信息缺失，请重新登录';
    return;
  }

  try {
    const resp = await authFetch(`/api/users/${user.id}/password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `old_password=${encodeURIComponent(oldPwd)}&new_password=${encodeURIComponent(newPwd)}`
    });
    if (!resp.ok) {
      const msg = await resp.text();
      errEl.textContent = msg || '修改失败';
      return;
    }
    toast('密码修改成功');
    closePasswordModal();
  } catch (e) {
    errEl.textContent = '网络错误，请稍后重试';
  }
}

// ── 初始化 ──

async function init() {
  try {
    await loadCompanies();
    await loadUsers();
    await loadTasks();
    render();
  } catch (e) {
    toast("加载失败：" + e.message);
  }
  // 自动刷新（15 秒）— 检测客服端新增的消息/图片
  // 用 safeRender：用户正在选中文字或输入时延迟重建 DOM，避免打断复制
  setInterval(async () => {
    try {
      await loadCompanies();
      await loadTasks();
      safeRender();
    } catch {}
  }, 15000);
}

init();