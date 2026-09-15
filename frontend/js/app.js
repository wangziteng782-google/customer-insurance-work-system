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
let allUsers = [];
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

async function loadTasks() {
  const resp = await authFetch('/api/chat/tasks?limit=1000');
  if (!resp.ok) throw new Error('加载任务失败');
  const raw = await resp.json();
  allTasks = await Promise.all(raw.map(async t => {
    const comments = RETURNED_STATUSES.includes(t.status) ? await loadComments(t.task_id) : [];
    const messages = await loadMessages(t.task_id);
    const images = countImagesFromMessages(messages);
    return normalizeTask(t, comments, images, messages);
  }));
}

async function loadUsers() {
  try {
    const resp = await authFetch('/api/users');
    if (!resp.ok) return;
    const users = await resp.json();
    allUsers = users.filter(u => u.role === 1).map(u => u.display_name);
  } catch {}
}

async function loadComments(taskId) {
  try {
    const resp = await authFetch(`/api/chat/tasks/${taskId}/comments`);
    if (!resp.ok) return [];
    return await resp.json();
  } catch { return []; }
}

async function loadMessages(taskId) {
  try {
    const resp = await authFetch(`/api/chat/messages?task_id=${taskId}`);
    if (!resp.ok) return [];
    return await resp.json();
  } catch { return []; }
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

function renderSidebar() {
  const companies = {};
  allTasks.forEach(t => {
    const name = t._insuranceCompany || '未知';
    if (!companies[name]) companies[name] = { count: 0, users: new Set() };
    companies[name].count++;
    if (t.user) companies[name].users.add(t.user);
  });

  // 更新保险公司数量
  const countEl = document.getElementById('companyCount');
  if (countEl) countEl.textContent = Object.keys(companies).length + ' 家';

  const wrap = document.querySelector('.company-list');
  if (!wrap) return;

  let html = '';
  // "全部" 按钮
  const totalCount = allTasks.length;
  const totalUsers = [...new Set(allTasks.map(t => t.user).filter(Boolean))];
  html += `<button class="company${currentCompany === '全部' ? ' active' : ''}" data-company="全部" onclick="selectCompany('全部',this)">
    <div class="company-left"><span class="company-name">全部</span><span class="company-meta">${totalCount} 条 · ${totalUsers.join('、')}</span></div>
    <span class="badge">${totalCount}</span>
  </button>`;

  // 各保险公司按钮
  Object.entries(companies).forEach(([name, info]) => {
    html += `<button class="company${currentCompany === name ? ' active' : ''}" data-company="${name}" onclick="selectCompany('${name}',this)">
      <div class="company-left"><span class="company-name">${name}</span><span class="company-meta">${info.count} 条 · ${[...info.users].join('、')}</span></div>
      <span class="badge">${info.count}</span>
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
    const uClass = t.user === '小步' ? 'u-xb' : t.user === '小陈' ? 'u-xc' : 'u-other';
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
      <div class="msg-block">
        ${(() => {
          const msgs = (t.messages || []).slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          if (!msgs.length) return '<div class="msg-line"><span class="dot"></span><span class="t"></span><span class="c">共 0 条消息</span></div>';
          return msgs.map(m => {
            const time = m.created_at ? String(m.created_at).replace('T', ' ').slice(0, 19) : '';
            return `<div class="msg-line"><span class="dot"></span><span class="t">${time}</span><span class="c">${m.content || '(无内容)'}</span></div>`;
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

function selectCompany(name, el) {
  currentCompany = name;
  selected = [];
  document.querySelectorAll(".company").forEach(x => x.classList.remove("active"));
  el.classList.add("active");
  render();
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

async function openModal(i) {
  const task = renderedTasks[i];
  if (!task) return;
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

function closeModal() { document.getElementById("modalMask").classList.remove("show"); }

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
  document.getElementById("ocrImgCount").textContent = imgUrls.length + " 张";
  document.getElementById("ocrThumbList").innerHTML = imgUrls.length ? imgUrls.map((url, k) => {
    return `<div class="ocr-thumb${k === 0 ? " active" : ""}" id="ocrThumb-${k}" onclick="ocrSelect(${k});openImgViewer('${url}','图片 ${k+1}')" title="点击查看大图">
      <img src="${url}" alt="图片 ${k+1}" onerror="this.style.display='none'">
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

function closeOcrModal() { document.getElementById("ocrMask").classList.remove("show"); }

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
  const total = t ? t.images || 0 : 0;
  const btn = document.getElementById("ocrActionBtn");
  btn.disabled = true;
  btn.textContent = "识别中...";
  document.getElementById("ocrResultArea").innerHTML = `
    <div class="ocr-loading"><span class="spinner"></span>正在识别 ${total} 张身份证，请稍候...</div>`;
  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = "重新识别";
    btn.onclick = ocrStart;
    document.getElementById("ocrVerifyBtn").style.display = "inline-flex";
    ocrFillResult();
    toast("OCR 识别完成");
  }, 900);
}

const ocrFakeData = [
  { name: "张伟", id: "440301198907123456" },
  { name: "李娜", id: "440302199203254521" },
  { name: "王强", id: "440303198511087633" },
  { name: "刘敏", id: "440304199410192248" }
];

function ocrFillResult() {
  const t = renderedTasks[ocrTaskIdx];
  const total = t ? t.images || 0 : 0;
  const lines = Array.from({ length: total }, (_, k) => {
    const r = ocrFakeData[k % 4];
    return r.name + " " + r.id;
  });
  document.getElementById("ocrResultArea").innerHTML = `
    <textarea class="cr-edit ocr-summary" id="ocrSummary" placeholder="识别结果为空，可手动输入或粘贴">${lines.join("\n")}</textarea>`;
  document.getElementById("ocrVerifyTip").style.display = "none";
}

function ocrVerify() {
  const ta = document.getElementById("ocrSummary");
  const text = ta ? ta.value : "";
  const tip = document.getElementById("ocrVerifyTip");
  tip.style.display = "block";
  const lines = text.split("\n").map(l => l.trim()).filter(l => l);
  if (!lines.length) {
    tip.innerHTML = `<div class="cr-verify fail">识别结果为空</div>`;
    toast("校验失败：识别结果为空");
    return;
  }
  const bad = lines.filter(l => !/^\S+\s+\d{17}[\dXx]$/.test(l));
  if (bad.length) {
    tip.innerHTML = `<div class="cr-verify fail">${bad.length} 条记录格式不正确</div>`;
    toast("校验失败：存在格式不正确的记录");
  } else {
    tip.innerHTML = `<div class="cr-verify">共 ${lines.length} 条记录，校验通过</div>`;
    toast("身份证校验通过");
  }
}

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
    await loadUsers();
    await loadTasks();
    render();
  } catch (e) {
    toast("加载失败：" + e.message);
  }
}

init();