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
  8: "已作废", 9: "待递交", 10: "进行中(修改)"
};

const STATUS_CSS = {
  0: "tag-muted", 1: "tag-processing", 2: "tag-error", 3: "tag-done",
  4: "tag-teal", 5: "tag-orange", 6: "tag-purple", 7: "tag-rejected",
  8: "tag-muted", 9: "tag-indigo", 10: "tag-mod"
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
let tagFilterIds = []; // 标签筛选选中的标签 id（多选 OR）
let renderedTasks = [];

// SVG icons
const ICONS = {
  img: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.83z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
};

// ── API 对接 ──

async function loadCompanies() {
  try {
    const resp = await authFetch('/api/chat/companies');
    if (!resp.ok) return;
    allCompanies = await resp.json();
  } catch {}
}

async function loadTasks(company, search) {
  let url = '/api/chat/tasks?limit=1000';
  if (search) url += '&search=' + encodeURIComponent(search);
  const resp = await authFetch(url);
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
  await Promise.all([loadCompanies(), loadTagBindings()]);
}

// 当前用户全部任务标签绑定：taskId -> [{tt_id, tag_id, name, color}]
let tagBindings = new Map();

async function loadTagBindings() {
  try {
    const r = await authFetch('/api/tags/bindings');
    if (!r.ok) throw new Error();
    const list = await r.json();
    tagBindings = new Map();
    list.forEach(b => {
      if (!tagBindings.has(b.task_id)) tagBindings.set(b.task_id, []);
      tagBindings.get(b.task_id).push(b);
    });
  } catch { tagBindings = new Map(); }
}

async function loadUsers() {
  try {
    const resp = await authFetch('/api/users');
    if (!resp.ok) return;
    const users = await resp.json();
    // 客服人员筛选：客服(1) + 客服主管(11) 都是提单人，只显示名称不显示角色
    allUsers = users.filter(u => u.role === 1 || u.role === 11).map(u => u.display_name);
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

// 时间戳格式化：2026-09-18T09:01:44 → 2026-09-18 09:01:44
const fmtTs = v => String(v || "").replace('T', ' ').slice(0, 19);

// 附件文件名（后端上传时按原文件名命名并做了 URL 转义，这里解回来）
function decodeName(raw) {
  try {
    return decodeURIComponent(raw || "");
  } catch {
    return raw || "";   // 含非法转义（如名字里带 %）时原样返回，不抛异常
  }
}

// API 字段 → 模板字段映射
function normalizeTask(t, comments, images, messages) {
  const isReturned = RETURNED_STATUSES.includes(t.status);
  const rejectReason = isReturned && comments.length ? comments[comments.length - 1].content : "";
  // 最新一条消息的发送时间（列表按 updated_at 升序排，通常与该时间一致）
  const lastMsgAt = (messages || []).reduce(
    (m, x) => (x.created_at && String(x.created_at) > m ? String(x.created_at) : m),
    ""
  );
  return {
    id: t.task_id,
    _insuranceCompany: t.insurance_company || "未知",
    company: t.customer_company || t.insurance_company || "未知",
    user: t.creator || "未知",
    time: fmtTs(t.created_at),          // head-row2 展示：任务创建时间
    lastMsgAt: fmtTs(lastMsgAt),        // 最新消息时间（= 通常意义上的"更新时间"）
    updated_at: t.updated_at || t.created_at || "",
    type: TYPE_LABELS[t.business_type] || "",  // desktop 已不再选择类型，新任务为空
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
/** 未读判据：本地没记录过"已读"，或这条在你上次查看之后又被更新过 */
function isUnreadOf(id, updatedAt) {
  if (!id || !updatedAt) return false;
  const seen = localStorage.getItem('seen_' + id);
  return !seen || updatedAt > seen;
}

function isUnread(task) {
  return isUnreadOf(task.id, task.lastMsgAt);
}

function markSeen(task) {
  if (task.lastMsgAt) localStorage.setItem('seen_' + task.id, task.lastMsgAt);
}

async function refreshTasks() {
  const btn = document.querySelector('.refresh-tasks-btn');
  if (btn) btn.classList.add('busy'); // 点击后图标持续旋转，直到刷新完成
  try {
    await loadTasks();
    render();
    toast('已刷新');
  } catch (e) {
    toast('刷新失败');
  } finally {
    if (btn) btn.classList.remove('busy');
  }
}

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
  renderSidebar();
}

function companyHasUnread(company) {
  // 优先用 /api/chat/companies 的 task_times：侧栏 15s 轻量轮询这个接口时红点也能刷新
  const c = allCompanies.find(x => x.name === company);
  if (c && Array.isArray(c.task_times)) {
    return c.task_times.some(x => isUnreadOf(x.id, fmtTs(x.last_msg_at)));
  }
  // 兼容没有 task_times 的接口：退回已加载的全量任务数据
  return allAllTasks.some(t => (t._insuranceCompany || t.insurance_company) === company && isUnread(t));
}

// ── 置顶保险公司（localStorage 保存顺序，数组下标即显示位置）──
const PINNED_KEY = 'pinned_companies';

function getPinned() {
  try {
    return JSON.parse(localStorage.getItem(PINNED_KEY) || '[]');
  } catch {
    return [];
  }
}

function togglePin(name) {
  const pinned = getPinned();
  const i = pinned.indexOf(name);
  if (i >= 0) pinned.splice(i, 1); // 已置顶 → 取消
  else pinned.push(name);          // 未置顶 → 追加到置顶区末尾
  localStorage.setItem(PINNED_KEY, JSON.stringify(pinned));
  renderSidebar();
}

function renderSidebar() {
  const countEl = document.getElementById('companyCount');
  if (countEl) countEl.textContent = allCompanies.length + ' 家';

  const wrap = document.querySelector('.company-list');
  if (!wrap) return;

  let html = '';
  const totalCount = allCompanies.reduce((s, c) => s + c.count, 0);
  html += `<button class="company${currentCompany === '全部' ? ' active' : ''}" data-company="全部" onclick="selectCompany('全部',this)">
    <div class="company-left"><span class="company-name">全部</span></div>
    <span class="badge">${totalCount}</span>
  </button>`;

  // 置顶的排前面（按置顶先后），其余保持原顺序
  const pinned = getPinned();
  const ordered = [
    ...pinned.map(n => allCompanies.find(c => c.name === n)).filter(Boolean),
    ...allCompanies.filter(c => !pinned.includes(c.name)),
  ];

  ordered.forEach(c => {
    const dot = companyHasUnread(c.name) ? '<i class="new-flag"></i>' : '';
    const on = pinned.includes(c.name);
    html += `<button class="company${currentCompany === c.name ? ' active' : ''}" data-company="${c.name}" onclick="selectCompany('${c.name}',this)">
      <div class="company-left"><span class="company-name">${c.name}</span></div>
      <span class="pin-btn${on ? ' on' : ''}" title="${on ? '取消置顶' : '置顶该保险公司'}" onclick="event.stopPropagation();togglePin('${c.name}')">${on ? '已置顶' : '置顶'}</span>
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

  // 标签筛选面板（个人标签，多选 OR：任务带任一选中标签即显示）
  document.getElementById("tagSelectPanel").innerHTML = myTags.length
    ? `<div class="tag-filter-chips">` + myTags.map(tag => {
        const on = tagFilterIds.includes(tag.id);
        // 选中=实色深底白字；未选=白底+实色描边+彩字（与选择标签弹窗一致）
        return `<span class="pick-tag" style="background:${on ? tag.color : '#fff'};color:${on ? '#fff' : tag.color};border:1.5px solid ${tag.color}" onclick="toggleTagFilter(${tag.id})">${esc(tag.name)}</span>`;
      }).join("") + `<span class="pick-tag tag-clear" onclick="resetTagFilter()">清空</span></div>`
    : `<div class="tag-filter-empty">还没有标签，先在左下角「个人标签管理」创建</div>`;
  const tagTrigger = document.getElementById("tagSelectLabel");
  document.getElementById("tagSelect").classList.toggle("has-sel", tagFilterIds.length > 0);
  const firstName = tagFilterIds.length ? ((myTags.find(t => t.id === tagFilterIds[0]) || {}).name || "") : "";
  if (tagFilterIds.length === 0) tagTrigger.textContent = "全部";
  else if (tagFilterIds.length === 1) tagTrigger.textContent = firstName;
  else tagTrigger.innerHTML = `<span>${esc(firstName)}等</span><span class="count">${tagFilterIds.length}</span>`;

  // 筛选任务
  const statusChecks = Array.from(document.querySelectorAll("#statusFilter input:checked")).map(c => parseInt(c.value));
  const typeVal = (document.getElementById("typeFilter") || {}).value || "";
  const kw = ((document.getElementById("keywordInput") || {}).value || "").trim().toLowerCase();
  const baseTasks = selected.length ? d.tasks.filter(t => selected.includes(t.user)) : d.tasks;
  let tasks = statusChecks.length ? baseTasks.filter(t => statusChecks.includes(t.status)) : baseTasks;
  // 做单类型精确匹配：无类型的新任务只在「全部」里出现
  if (typeVal) tasks = tasks.filter(t => t.type === typeVal);
  // 标签筛选：任务带任一选中标签即显示（OR）。
  // ponytail: 用内存里的 tagBindings 过滤，任务超 limit=1000 会漏——与现有全部筛选同天花板
  if (tagFilterIds.length)
    tasks = tasks.filter(t => tagFilterIds.some(id => (tagBindings.get(t.id) || []).some(b => b.tag_id === id)));
  if (kw) tasks = tasks.filter(t => `${t.company} ${t.user} ${t.id}`.toLowerCase().includes(kw));
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
    // 卡片左上角红点：判据与侧栏保险公司红点完全一致（见 isUnread / markTaskSeen），
    // 区别只在位置和样式，用来指向"这张单有新的提单消息"
    const unreadDot = isUnread(t)
      ? '<i class="unread-dot card" title="有新的提单消息"></i>'
      : "";
    // 个人标签片（底部）：实色深底白字，点击打开选择弹窗，悬浮右上角 × 直接移除
    const tagChips = (tagBindings.get(t.id) || []).map(b =>
      `<span class="card-tag" style="background:${b.color};color:#fff" onclick="openTagPicker(event, ${i})">${esc(b.name)}<i class="tag-x" title="移除标签" onclick="removeTaskTag(event, ${i}, ${b.tag_id})">×</i></span>`
    ).join('');
    return `
    <div class="task-item">
      ${unreadDot}
      <div class="task-head">
        <div class="task-head-left">
          <div class="head-info">
            <div class="head-row1">
              <span class="name">${t.company || t.user}</span>
              ${t.type ? `<span class="type-tag ${t.type === '批改' ? 'type-end' : 'type-new'}">${t.type}</span>` : ""}
            </div>
            <div class="head-row2" title="创建：${t.time}${t.lastMsgAt ? `｜最新消息：${t.lastMsgAt}` : ""}">
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
      <details class="msg-fold" ${(t.status === 1 || t.status === 10) ? "open" : ""}>
      <summary></summary>
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
            const isNew = seen && fmtTs(m.created_at) > seen;
            const newDot = isNew ? '<span class="unread-dot msg"></span>' : '';
            return `<div class="msg-line"><span class="dot"></span><span class="t">${time}</span><span class="c">${c}</span>${newDot}</div>`;
          }).join('');
        })()}
      </div>
      </details>
      ${isReturned && t.rejectReason ? `<div class="reject-box"><div class="rb-head"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>退回原因</div><div class="rb-body">${t.rejectReason}</div></div>` : ''}
      <div class="task-foot">
        <div class="foot-left">
          <button type="button" class="stat-chip" title="点击查看图片并做 OCR 识别" onclick="runCardOCR(${i})">${ICONS.img}<span><b>${t.images}</b> 张图片</span></button>
          <button type="button" class="stat-chip" title="点击查看附件详情" onclick="openModal(${i})">${ICONS.file}<span><b>${t.docCount}</b> 个附件</span></button>
          <span class="stat-chip">${ICONS.search}<span><b>${t.msgCount}</b> 条消息</span></span>
          ${tagChips}
          <button type="button" class="stat-chip tag-add" title="添加标签" onclick="openTagPicker(event, ${i})">${ICONS.tag}<span>＋ 标签</span></button>
        </div>
      </div>
    </div>`;
  }).join("");

  wrap.innerHTML = `<div class="card-list">${items}</div>`;
}

// ── 事件处理 ──

async function selectCompany(name, el) {
  currentCompany = name;
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

// 点击空白处关闭已打开的下拉（客服人员/标签共用；点在面板内部不关）
document.addEventListener("click", e => {
  document.querySelectorAll(".multi-select.on").forEach(el => {
    if (!el.contains(e.target)) el.classList.remove("on");
  });
});

// 消息区复制到 Excel：浏览器默认同时放 text/plain（带 \n）和 text/html（裸 \n 会被
// 折叠成空格）进剪贴板，Excel 优先读 HTML 就全挤成一行。这里拦截消息区的复制，
// HTML 改用 <table> 每行一个 <tr>，Excel 逐行成行；纯数字长编号（身份证等）加
// mso 文本格式标记防止丢精度（复用 Excel 预览复制的 isExcelIdLike / fpEsc）。
document.addEventListener("copy", e => {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.rangeCount) return;
  const node = sel.anchorNode;
  const el = node && (node.nodeType === 3 ? node.parentElement : node);
  if (!el || !el.closest(".msg-block")) return;
  const text = sel.toString();
  const lines = text.split("\n");
  const html = "<table>" + lines.map(line =>
    "<tr><td" + (isExcelIdLike(line.trim()) ? " style=\"mso-number-format:'\\@'\"" : "")
    + ">" + fpEsc(line) + "</td></tr>"
  ).join("") + "</table>";
  e.clipboardData.setData("text/plain", text);
  e.clipboardData.setData("text/html", html);
  e.preventDefault();
});

function toggleUser(user) {
  if (selected.includes(user)) selected = selected.filter(x => x !== user);
  else selected.push(user);
  selected.sort();
  render();
}

async function toggleTagPanel() {
  const el = document.getElementById("tagSelect");
  const opening = !el.classList.contains("on");
  el.classList.toggle("on");
  // 打开时拿最新标签（可能刚在个人标签管理里建过/删过），顺带清掉已删除标签的残留选中
  if (opening) {
    await loadMyTags();
    const ids = new Set(myTags.map(t => t.id));
    tagFilterIds = tagFilterIds.filter(id => ids.has(id));
    render();
  }
}

function toggleTagFilter(id) {
  tagFilterIds = tagFilterIds.includes(id) ? tagFilterIds.filter(x => x !== id) : [...tagFilterIds, id];
  render();
}

function resetTagFilter() {
  tagFilterIds = [];
  render();
}

// 关键词查询（查询按钮 / 输入框回车）
function doQuery() {
  const keyword = document.getElementById('keywordInput').value.trim();
  loadTasks(currentCompany, keyword).then(render).catch(() => toast('查询失败'));
}

// 状态「全部」：清空所有状态勾选（按钮高亮由 CSS 判断，无需 JS 维护）
function resetStatusFilter() {
  document.querySelectorAll("#statusFilter input").forEach(c => c.checked = false);
  render();
}

function resetFilter() {
  selected = [];
  document.querySelectorAll(".filter-input").forEach(i => i.value = "");
  document.querySelectorAll(".filter-select").forEach(s => s.selectedIndex = 0);
  document.querySelectorAll("#statusFilter input").forEach(c => c.checked = false);
  loadTasks(currentCompany).then(render).catch(() => toast('重置失败'));
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
let modalFiles = [];   // 当前详情弹窗里的文档附件（点击时按序号取）

// ── 附件在线预览（Word / Excel 就地渲染，PDF 内嵌浏览器阅读器）──
// 库文件放在 js/vendor/，第一次点预览才按需加载，首屏不变慢。
// 七牛已开跨域（Access-Control-Allow-Origin: *），所以前端能直接 fetch 到文件内容。
const PREVIEWABLE_TYPES = { pdf: 1, word: 1, excel: 1 };
const PREVIEW_MAX_MB = 20;      // 超过只给下载，避免卡住浏览器
const SHEET_MAX_ROWS = 500;     // Excel 只渲染前 N 行

/** 点击附件：能预览的就地预览，其余照旧新窗口打开 */
function openFileAt(idx) {
  const f = modalFiles[idx];
  if (!f) return;
  if (PREVIEWABLE_TYPES[f.type]) openFilePreview(f);
  else window.open(f.url, "_blank");
}

/** 动态注入脚本（同一个库只加载一次） */
function loadScriptOnce(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error("库加载失败：" + src));
    document.head.appendChild(s);
  });
}

/** 按文件类型确保依赖库就绪（docx-preview 依赖先加载好的 JSZip） */
async function ensurePreviewLibs(type) {
  if (type === "excel") {
    if (!window.XLSX) await loadScriptOnce("js/vendor/xlsx.full.min.js");
    if (!window.XLSX) throw new Error("Excel 解析库未就绪");
    return;
  }
  if (!window.JSZip) await loadScriptOnce("js/vendor/jszip.min.js");
  if (!window.docx) await loadScriptOnce("js/vendor/docx-preview.min.js");
  if (!window.docx) throw new Error("Word 渲染库未就绪");
}

/** 打开预览层 */
function openFilePreview(f) {
  document.getElementById("filePreviewName").textContent = f.name;
  const dl = document.getElementById("filePreviewDl");
  dl.href = f.url;
  dl.setAttribute("download", f.name);
  const body = document.getElementById("filePreviewBody");
  body.innerHTML = '<div class="fp-tip">正在加载预览…</div>';
  document.getElementById("filePreviewMask").classList.add("show");

  if (f.type === "pdf") {
    // 用 iframe 内嵌：走浏览器自带 PDF 阅读器，也不会被"PDF 一律下载"的设置拦下
    body.textContent = "";
    const frame = document.createElement("iframe");
    frame.className = "fp-frame";
    frame.src = f.url;
    body.appendChild(frame);
    return;
  }

  renderOfficePreview(f, body).catch(err => {
    console.warn("预览失败:", err);
    body.textContent = "";
    const tip = document.createElement("div");
    tip.className = "fp-tip err";
    tip.textContent = "预览失败：" + (err && err.message ? err.message : err) + "，可点右上角「下载原件」查看";
    body.appendChild(tip);
  });
}

/** Word / Excel：取回字节后就地渲染 */
async function renderOfficePreview(f, body) {
  await ensurePreviewLibs(f.type);
  const resp = await fetch(f.url);
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  const buf = await resp.arrayBuffer();
  const sizeMb = buf.byteLength / 1048576;
  if (sizeMb > PREVIEW_MAX_MB) {
    throw new Error("文件较大（" + sizeMb.toFixed(1) + "MB）");
  }
  body.textContent = "";

  if (f.type === "word") {
    // docx-preview 把 docx 渲染成 DOM（保留表格 / 图片 / 基本版式）
    await window.docx.renderAsync(buf, body, null, {
      className: "fp-docx",
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: true,
    });
    return;
  }

  const wb = window.XLSX.read(buf, { type: "array" });
  // 隐藏的工作表 Excel 里本来就不显示，预览也跟着不列（工作簿里有 Sheet1 之外的辅助表时会清爽很多）
  const sheetMeta = (wb.Workbook && wb.Workbook.Sheets) || [];
  const names = (wb.SheetNames || []).filter((n, i) => !(sheetMeta[i] && sheetMeta[i].Hidden));
  if (!names.length) throw new Error("文件里没有可显示的工作表");

  const tabs = document.createElement("div");
  tabs.className = "fp-tabs";
  const pane = document.createElement("div");
  pane.className = "fp-sheet";
  // 每个 sheet 一份视图状态（筛选/排序/选择），切标签回来不丢
  const views = new Map();
  const show = name => showSheet(wb.Sheets[name], pane, views, name);
  names.forEach((name, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "fp-tab" + (i === 0 ? " on" : "");
    b.textContent = name;
    b.onclick = () => {
      tabs.querySelectorAll(".fp-tab").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      show(name);
    };
    tabs.appendChild(b);
  });
  body.appendChild(tabs);
  body.appendChild(pane);
  show(names[0]);
}

/**
 * 判断是不是"编号型"的数字：复制到 Excel 时要按文本处理
 *
 * ① 纯数字且 ≥15 位：超出 Excel 的 15 位有效数字，粘贴过去会丢精度（311021110320213000 → 3.11021E+17）
 * ② 以 0 开头：粘贴后前导 0 会被吃掉（001234 → 123）
 * 其它数字照常按数字粘贴（金额、数量等还能直接求和）
 */
function isExcelIdLike(text) {
  return /^\d{15,}$/.test(text) || /^0\d+$/.test(text);
}

// ── Excel 预览：表格视图（行号 / 整行整列选择 / 排序 / 筛选 / 复制所选）──
const FP_FILTER_MAX_VALUES = 500;   // 单列可选值上限，超了用搜索

function cellText(v) {
  return v == null ? "" : String(v);
}

/** 看起来是数字（用于排序：避免 10 排在 9 前面） */
function isNumericLike(t) {
  return /^-?\d+(\.\d+)?$/.test(t);
}

/** 单元格比较：数字按数值，其余按中文排序；空值排最前 */
function compareCells(a, b) {
  if (a === b) return 0;
  if (!a) return -1;
  if (!b) return 1;
  if (isNumericLike(a) && isNumericLike(b)) return Number(a) - Number(b);
  return a.localeCompare(b, "zh");
}

function fpEsc(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** 首次打开某 sheet 时解析数据成视图状态（之后复用，切标签回来筛选/排序还在） */
function getSheetView(views, name, sheet) {
  if (views && name && views.has(name)) return views.get(name);
  const all = window.XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false, defval: "" });
  const header = (all[0] || []).map(cellText);
  const body = all.slice(1, SHEET_MAX_ROWS + 1).map(r => (r || []).map(cellText));
  const colCount = Math.max(header.length, ...body.map(r => r.length), 0);
  while (header.length < colCount) header.push("");
  body.forEach(r => { while (r.length < colCount) r.push(""); });
  const st = {
    header, body, colCount,
    totalRows: all.length - 1,
    truncated: all.length - 1 > body.length,
    filters: {},     // 列号 → Set(保留显示的值)
    sort: null,      // { col, dir: 1 | -1 }
    sel: null,       // { type: 'row' | 'col', from, to }
    anchor: null,    // Shift 连选的锚点
    forceCopy: false,
  };
  if (views && name) views.set(name, st);
  return st;
}

/** 当前筛选 + 排序后的数据行下标（相对 body） */
function visibleRows(st) {
  let idx = st.body.map((_, i) => i);
  const cols = Object.keys(st.filters);
  if (cols.length) {
    idx = idx.filter(i => cols.every(c => st.filters[c].has(st.body[i][c] || "")));
  }
  if (st.sort) {
    const { col, dir } = st.sort;
    idx = idx.slice().sort((i, j) => compareCells(st.body[i][col], st.body[j][col]) * dir);
  }
  return idx;
}

/** 某列的取值 → 出现次数 */
function columnValueMap(st, c) {
  const m = new Map();
  for (const r of st.body) {
    const v = r[c] || "";
    m.set(v, (m.get(v) || 0) + 1);
  }
  return m;
}

/** 一个工作表 → 可交互表格（数据全用 textContent 赋值，不拼 innerHTML） */
function showSheet(sheet, pane, views, name) {
  pane.textContent = "";
  if (!sheet) return;
  const st = getSheetView(views, name, sheet);
  if (!st.colCount && !st.body.length) {
    const tip = document.createElement("div");
    tip.className = "fp-tip";
    tip.textContent = "（空工作表）";
    pane.appendChild(tip);
    return;
  }
  const wrap = document.createElement("div");
  wrap.className = "fp-sheet-wrap";
  const bar = document.createElement("div");
  bar.className = "fp-sheet-bar";
  const scroll = document.createElement("div");
  scroll.className = "fp-sheet-scroll";
  wrap.appendChild(bar);
  wrap.appendChild(scroll);
  pane.appendChild(wrap);

  st.wrap = wrap;
  st.bar = bar;
  st.scroll = scroll;
  closeFilterPanel(st);                       // 换 sheet 时旧面板失效
  scroll.addEventListener("click", e => onSheetClick(st, e));
  scroll.addEventListener("scroll", () => closeFilterPanel(st));

  paintSheet(st);
  currentSheetState = st;
}

/** 重绘表格与状态行（筛选 / 排序 / 选择变化时调用） */
function paintSheet(st) {
  const vis = visibleRows(st);
  st.visible = vis;

  // ── 状态行 ──
  st.bar.textContent = "";
  const info = document.createElement("span");
  info.className = "fp-sel";
  let selText = "未选择";
  if (st.sel) {
    const n = st.sel.to - st.sel.from + 1;
    selText = st.sel.type === "row" ? "已选 " + n + " 行" : "已选 " + n + " 列";
  }
  info.textContent = selText + " · 显示 " + vis.length + " / " + st.body.length + " 行";
  st.bar.appendChild(info);

  if (st.truncated) {
    const tip = document.createElement("span");
    tip.textContent = "（原表共 " + st.totalRows + " 行，仅载入前 " + st.body.length + " 行）";
    st.bar.appendChild(tip);
  }
  const hint = document.createElement("span");
  hint.textContent = "支持 Ctrl+C 复制所选";
  st.bar.appendChild(hint);

  const sp = document.createElement("span");
  sp.className = "sp";
  st.bar.appendChild(sp);

  const mkBtn = (label, fn) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "fp-mini";
    b.textContent = label;
    b.onclick = fn;
    return b;
  };
  st.bar.appendChild(mkBtn("复制所选", () => copySelection(st)));
  if (Object.keys(st.filters).length || st.sort) {
    st.bar.appendChild(mkBtn("清除筛选/排序", () => {
      st.filters = {};
      st.sort = null;
      paintSheet(st);
      closeFilterPanel(st);
    }));
  }

  // ── 表头 ──
  const table = document.createElement("table");
  table.className = "fp-table";
  const thead = document.createElement("thead");
  const htr = document.createElement("tr");
  const corner = document.createElement("th");
  corner.className = "fp-corner";
  corner.title = "全选（复制整张表）";
  htr.appendChild(corner);
  for (let c = 0; c < st.colCount; c++) {
    const th = document.createElement("th");
    th.className = "fp-colhead";
    th.dataset.c = c;
    if (st.sel && st.sel.type === "col" && c >= st.sel.from && c <= st.sel.to) th.classList.add("on");
    const nm = document.createElement("span");
    nm.className = "fp-colname";
    nm.textContent = st.header[c] || "第" + (c + 1) + "列";
    th.appendChild(nm);
    if (st.sort && st.sort.col === c) {
      const mark = document.createElement("span");
      mark.className = "fp-sort-mark";
      mark.textContent = st.sort.dir === 1 ? " ▲" : " ▼";
      th.appendChild(mark);
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "fp-fbtn" + (st.filters[c] ? " on" : "");
    btn.title = "筛选 / 排序";
    btn.textContent = "▾";
    th.appendChild(btn);
    htr.appendChild(th);
  }
  thead.appendChild(htr);
  table.appendChild(thead);

  // ── 表体 ──
  const tbody = document.createElement("tbody");
  vis.forEach((ri, vi) => {
    const tr = document.createElement("tr");
    if (st.sel && st.sel.type === "row" && vi >= st.sel.from && vi <= st.sel.to) {
      tr.className = "row-sel";
    }
    const no = document.createElement("td");
    no.className = "fp-rowno";
    no.dataset.r = vi;
    no.textContent = String(ri + 1);
    tr.appendChild(no);
    for (let c = 0; c < st.colCount; c++) {
      const td = document.createElement("td");
      const text = st.body[ri][c] || "";
      td.textContent = text;
      // 编号型数字带上 Excel 的"文本格式"标记：复制出去的 HTML 会被 Excel 读取，
      // 这样粘贴过去仍是原文（18 位不丢精度、前导 0 不丢）
      if (isExcelIdLike(text)) {
        td.setAttribute("style", "mso-number-format:'\\@'");
      }
      if (st.sel && st.sel.type === "col" && c >= st.sel.from && c <= st.sel.to) {
        td.classList.add("col-sel");
      }
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  st.scroll.textContent = "";
  st.scroll.appendChild(table);
}

/** 表格内的点击分派：列头=选整列、行号=选整行、▾=筛选面板 */
function onSheetClick(st, e) {
  const btn = e.target.closest && e.target.closest(".fp-fbtn");
  if (btn) {
    const c = Number(btn.closest("th").dataset.c);
    if (st.openFilterCol === c) closeFilterPanel(st);
    else openFilterPanel(st, c);
    return;
  }
  const th = e.target.closest && e.target.closest("th.fp-colhead");
  if (th) {
    selectColumn(st, Number(th.dataset.c), e.shiftKey);
    return;
  }
  if (e.target.closest && e.target.closest("th.fp-corner")) {
    st.anchor = { type: "row", from: 0 };
    st.sel = { type: "row", from: 0, to: Math.max(0, (st.visible || []).length - 1) };
    paintSheet(st);
    return;
  }
  const rowNo = e.target.closest && e.target.closest("td.fp-rowno");
  if (rowNo) selectRow(st, Number(rowNo.dataset.r), e.shiftKey);
}

function selectRow(st, vi, extend) {
  if (!extend || !st.anchor || st.anchor.type !== "row") st.anchor = { type: "row", from: vi };
  const a = st.anchor.from;
  st.sel = { type: "row", from: Math.min(a, vi), to: Math.max(a, vi) };
  paintSheet(st);
}

function selectColumn(st, c, extend) {
  if (!extend || !st.anchor || st.anchor.type !== "col") st.anchor = { type: "col", from: c };
  const a = st.anchor.from;
  st.sel = { type: "col", from: Math.min(a, c), to: Math.max(a, c) };
  paintSheet(st);
}

// ── 筛选 / 排序面板 ──

function closeFilterPanel(st) {
  if (st.openFilterPanel) {
    st.openFilterPanel.remove();
    st.openFilterPanel = null;
  }
  st.openFilterCol = null;
}

function openFilterPanel(st, c) {
  closeFilterPanel(st);
  const th = st.scroll.querySelector('th.fp-colhead[data-c="' + c + '"]');
  if (!th) return;
  st.openFilterCol = c;

  const panel = document.createElement("div");
  panel.className = "fp-filter";

  const search = document.createElement("input");
  search.type = "text";
  search.placeholder = "搜索值…";
  panel.appendChild(search);

  const links = document.createElement("div");
  links.className = "fp-filter-links";
  const allBtn = document.createElement("a");
  allBtn.textContent = "全选";
  const noneBtn = document.createElement("a");
  noneBtn.textContent = "清空";
  links.appendChild(allBtn);
  links.appendChild(noneBtn);
  panel.appendChild(links);

  const list = document.createElement("div");
  list.className = "fp-filter-list";
  panel.appendChild(list);

  const sortRow = document.createElement("div");
  sortRow.className = "fp-filter-sort";
  const mkMini = (label, fn) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "fp-mini";
    b.textContent = label;
    b.onclick = fn;
    return b;
  };
  sortRow.appendChild(mkMini("升序", () => { st.sort = { col: c, dir: 1 }; paintSheet(st); }));
  sortRow.appendChild(mkMini("降序", () => { st.sort = { col: c, dir: -1 }; paintSheet(st); }));
  sortRow.appendChild(mkMini("取消排序", () => { st.sort = null; paintSheet(st); }));
  panel.appendChild(sortRow);

  const values = columnValueMap(st, c);
  const entries = [...values.entries()].sort((a, b) => compareCells(a[0], b[0]));
  const boxes = () => Array.from(list.querySelectorAll("input[type=checkbox]"));

  const applyChecked = () => {
    const picked = new Set(boxes().filter(x => x.checked).map(x => x.value));
    if (picked.size >= values.size) delete st.filters[c];   // 全选 = 该列不筛选
    else st.filters[c] = picked;
    paintSheet(st);
  };
  allBtn.onclick = () => { boxes().forEach(x => { x.checked = true; }); applyChecked(); };
  noneBtn.onclick = () => { boxes().forEach(x => { x.checked = false; }); applyChecked(); };

  const renderList = () => {
    const kw = search.value.trim().toLowerCase();
    const keep = st.filters[c];
    list.textContent = "";
    const shown = entries.filter(([v]) => !kw || String(v).toLowerCase().includes(kw));
    if (entries.length > FP_FILTER_MAX_VALUES) {
      const t = document.createElement("div");
      t.className = "fp-none";
      t.textContent = "该列取值较多，请用上面搜索";
      list.appendChild(t);
    }
    shown.slice(0, FP_FILTER_MAX_VALUES).forEach(([v, n]) => {
      const label = document.createElement("label");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.value = v;
      box.checked = keep ? keep.has(v) : true;
      box.onchange = applyChecked;
      const span = document.createElement("span");
      span.textContent = v || "（空白）";
      const cnt = document.createElement("em");
      cnt.textContent = String(n);
      label.appendChild(box);
      label.appendChild(span);
      label.appendChild(cnt);
      list.appendChild(label);
    });
    if (!shown.length) {
      const t = document.createElement("div");
      t.className = "fp-none";
      t.textContent = "没有匹配的值";
      list.appendChild(t);
    }
  };
  renderList();
  search.oninput = renderList;

  // 面板挂在 wrap 上（不放在 th 里）—— 这样重绘表格不会把它弄没
  st.wrap.style.position = "relative";
  st.wrap.appendChild(panel);
  const wr = st.wrap.getBoundingClientRect();
  const tr = th.getBoundingClientRect();
  let left = tr.left - wr.left;
  if (left + 244 > st.wrap.clientWidth) left = Math.max(0, st.wrap.clientWidth - 244);
  panel.style.left = left + "px";
  panel.style.top = (tr.bottom - wr.top) + "px";
  st.openFilterPanel = panel;
  search.focus();
}

// ── 复制所选（整行 / 整列）──

function buildCopyRows(st) {
  if (!st.sel) return null;
  const vis = st.visible || visibleRows(st);
  const out = [];
  const allCols = [];
  for (let c = 0; c < st.colCount; c++) allCols.push(c);
  if (st.sel.type === "col") {
    const cols = allCols.filter(c => c >= st.sel.from && c <= st.sel.to);
    out.push(cols.map(c => st.header[c] || ""));          // 选整列时连表头一起（与 Excel 一致）
    vis.forEach(i => out.push(cols.map(c => st.body[i][c] || "")));
  } else {
    vis.forEach((i, vi) => {
      if (vi < st.sel.from || vi > st.sel.to) return;
      out.push(allCols.map(c => st.body[i][c] || ""));
    });
  }
  return out;
}

function copySelection(st) {
  const rows = buildCopyRows(st);
  if (!rows || !rows.length) {
    toast("先点左侧行号或表头，选中整行 / 整列");
    return;
  }
  st.forceCopy = true;
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (e) {
    ok = false;
  }
  st.forceCopy = false;
  if (!ok) toast("复制失败，请按 Ctrl + C");
}

let currentSheetState = null;

document.addEventListener("copy", e => {
  const st = currentSheetState;
  if (!st || !st.sel || !st.scroll || !document.body.contains(st.scroll)) return;
  if (!st.forceCopy) {
    const sel = window.getSelection();
    // 用户自己在拖选文字 → 交给浏览器默认行为（含之前修好的长数字文本格式）
    if (sel && !sel.isCollapsed && String(sel).trim()) return;
  }
  const rows = buildCopyRows(st);
  if (!rows) return;
  e.preventDefault();
  const text = rows.map(r => r.map(t => t.replace(/[\t\r\n]/g, " ")).join("\t")).join("\n");
  const html = "<table>" + rows.map(r => "<tr>" + r.map(t => {
    const style = isExcelIdLike(t) ? " style=\"mso-number-format:'\\@'\"" : "";
    return "<td" + style + ">" + fpEsc(t) + "</td>";
  }).join("") + "</tr>").join("") + "</table>";
  e.clipboardData.setData("text/plain", text);
  e.clipboardData.setData("text/html", html);
  toast("已复制 " + rows.length + " 行 × " + (rows[0] ? rows[0].length : 0) + " 列");
});

document.addEventListener("click", e => {
  const st = currentSheetState;
  if (!st || !st.openFilterPanel) return;
  if (st.openFilterPanel.contains(e.target)) return;
  if (e.target.closest && e.target.closest(".fp-fbtn")) return;
  closeFilterPanel(st);
});

function closeFilePreview() {
  const mask = document.getElementById("filePreviewMask");
  if (!mask) return;
  mask.classList.remove("show");
  // 清空内容：iframe 里的 PDF 会继续占用内存，关掉就释放
  document.getElementById("filePreviewBody").textContent = "";
  currentSheetState = null;
}

/** 点遮罩空白处关闭（点面板内部不关） */
function onFilePreviewMaskClick(e) {
  if (e.target && e.target.id === "filePreviewMask") closeFilePreview();
}

document.addEventListener("keydown", e => {
  if (e.key !== "Escape") return;
  // 先关「筛选/排序」面板，再关整个预览层
  if (currentSheetState && currentSheetState.openFilterPanel) {
    closeFilterPanel(currentSheetState);
    return;
  }
  if (document.getElementById("filePreviewMask").classList.contains("show")) {
    closeFilePreview();
  }
});

async function openModal(i) {
  const task = renderedTasks[i];
  if (!task) return;
  currentModalTask = task;
  document.getElementById("modalSub").textContent =
    (task.company || task.user) + (task.type ? " · " + task.type : "");
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
        // 上传时间 = 所属消息的发送时间，与卡片消息列表同款格式
        files.push({ name: decodeName(url.split('/').pop()), type: type, url: url,
          time: m.created_at ? String(m.created_at).replace('T', ' ').slice(0, 19) : '' });
      });
    });
    // 提单详情只展示文档附件，不展示图片
    const docFiles = files.filter(f => f.type !== "image");
    document.getElementById("fileCount").textContent = docFiles.length + " 个";
    const typeLabel = { pdf: "PDF", excel: "XLS", word: "DOC", image: "IMG" };
    if (docFiles.length) {
      // 点击时按序号取（不把文件名/URL 拼进 onclick 属性，避免引号把属性截断）
      modalFiles = docFiles;
      fileList.innerHTML = docFiles.map((f, idx) => `
        <div class="file-item" onclick="openFileAt(${idx})">
          <div class="file-icon t-${f.type}">${typeLabel[f.type] || "FILE"}</div>
          <div class="file-info">
            <div class="file-name">${f.name}</div>
            <div class="file-meta">${f.time}</div>
          </div>
          <span class="file-dl">${PREVIEWABLE_TYPES[f.type] ? "预览" : "下载"}</span>
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

// ── OCR 弹窗 ──

let ocrTaskIdx = -1;
let ocrTaskId = "";
let ocrImages = [];          // 当前任务的身份证图片 [{url, created_at}]
let ocrSelected = new Set(); // 已勾选的图片下标
let ocrFiles = {};           // 预取的图片二进制 File（下标 → File），用于拖拽出真实文件

// OCR 识别结果按任务持久化：关闭弹窗、刷新页面都保留，只有「重新识别」才覆盖
const OCR_CACHE_KEY = "ocr_text_cache";

// 识别结果的读写（含"结果第几行 ↔ 第几张图"的映射）都在 js/ocr-preview.js，那边是唯一数据源；
// 这里只留薄封装给原有调用点
function ocrGetCached(taskId) {
  return ocrvCacheText(taskId);
}

// 识别进度标记：值 = 识别完成时任务内最新图片的 created_at。
// 缩略图红点 = 未识别（created_at > done），与消息红点(seen_)是两个维度
const OCR_DONE_KEY = "ocr_done_";

function ocrIsPending(item) {
  const done = localStorage.getItem(OCR_DONE_KEY + ocrTaskId);
  return !done || item.created_at > done;
}

// 把识别结果写入文本框（用 .value 赋值，避免内容含特殊字符破坏 HTML）
function ocrSetResultText(text) {
  document.getElementById("ocrResultArea").innerHTML =
    `<textarea class="cr-edit ocr-summary" id="ocrSummary" placeholder="识别结果为空，可手动输入或粘贴" oninput="ocrSaveText()"></textarea>`;
  document.getElementById("ocrSummary").value = text || "";
}

// 手动编辑后同步到缓存；文本真被改了才丢弃"行 ↔ 图"映射（见 js/ocr-preview.js）
function ocrSaveText() {
  if (!ocrTaskId) return;
  const ta = document.getElementById("ocrSummary");
  if (!ta) return;
  ocrvCacheSaveEdited(ocrTaskId, ta.value);
}

function runCardOCR(i) {
  const t = renderedTasks[i];
  if (!t) return;
  ocrTaskIdx = i;
  ocrTaskId = t.id;
  document.getElementById("ocrSub").textContent = (t.company || t.user) + " · " + (t.type || "新投");
  const imgWithTime = [];
  (t.messages || []).forEach(m => {
    (m.file_paths || []).forEach(url => {
      if (IMAGE_EXTS.includes('.' + url.split('.').pop().toLowerCase())) {
        imgWithTime.push({ url, created_at: m.created_at });
      }
    });
  });
  ocrImages = imgWithTime;
  // 标题"新图片" = 有未识别的图片，与缩略图红点同口径
  const newImgMarker = ocrImages.some(ocrIsPending) ? "新" : "";
  document.getElementById("ocrImgCount").textContent = ocrImages.length + " 张" + (newImgMarker ? " · " + newImgMarker + "图片" : "");
  ocrSelected = new Set();
  renderOcrThumbs();
  ocrFiles = {}; // 清掉上一个任务的预取结果；勾选后才按需预取（见 ocrPrefetchSelected）
  document.getElementById("ocrVerifyTip").style.display = "none";
  // 该任务之前识别过 → 回显上次结果；只有点「重新识别」才会覆盖
  const cached = ocrGetCached(t.id);
  if (cached) {
    ocrSetResultText(cached);
    document.getElementById("ocrVerifyBtn").style.display = "inline-flex";
    document.getElementById("ocrCopyBtn").style.display = "inline-flex";
  } else {
    document.getElementById("ocrResultArea").innerHTML = `
    <div class="ocr-loading">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32" style="color:var(--gray-300)"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 8h3M7 12h5M7 16h4M15 8v8M18 8v8"/></svg>
      点击下方「身份证识别」录入信息，或「图片识别」原样输出文字
    </div>`;
    document.getElementById("ocrVerifyBtn").style.display = "none";
    document.getElementById("ocrCopyBtn").style.display = "none";
  }
  document.getElementById("ocrActionBtn").onclick = ocrStart;
  document.getElementById("ocrMask").classList.add("show");
}

function closeOcrModal() {
  ocrSaveText(); // 关闭前保存手动编辑的内容
  window._verifyResults = null;
  if (ocrTaskIdx >= 0 && renderedTasks[ocrTaskIdx]) markSeen(renderedTasks[ocrTaskIdx]);
  document.getElementById("ocrMask").classList.remove("show");
}

let viewerRot = 0, viewerScale = 1;

function viewerApply() {
  document.getElementById("imgViewerSrc").style.transform =
    `rotate(${viewerRot}deg) scale(${viewerScale})`;
  // 旋转 90/270 时宽高预算要对调（否则图会被裁掉、看着像"旋转没反应"），交给 ocr-preview.js
  if (typeof ocrvOnViewerTransform === "function") ocrvOnViewerTransform();
}

function openImgViewer(src, tag) {
  viewerRot = 0;
  viewerScale = 1;
  const img = document.getElementById("imgViewerSrc");
  // 展示用 1600 版本（原图 11MB 要等 4.5s）；下载链接仍指向原图
  img.src = qiniuImg(src, VIEW_WIDTH);
  viewerApply();
  document.getElementById("imgViewerTag").textContent = tag || "";
  // 设置下载链接（原图）
  const dl = document.getElementById("imgViewerDl");
  dl.href = src;
  dl.download = (tag || "image") + ".jpg";
  document.getElementById("imgViewer").classList.add("show");
}
function viewerRotate() {
  viewerRot += 90;
  viewerApply();
}

// 滚轮缩放：以图片中心缩放（复用现有 .2s 过渡），1~8 倍，打开时复位
document.getElementById("imgViewer").addEventListener("wheel", e => {
  e.preventDefault();
  viewerScale = Math.min(8, Math.max(1, viewerScale * (e.deltaY < 0 ? 1.2 : 1 / 1.2)));
  viewerApply();
});
function closeImgViewer() {
  document.getElementById("imgViewer").classList.remove("show");
  // 对照模式（js/ocr-preview.js）要顺手解绑键盘、复位样式；那个文件没加载时函数不存在，所以判一下
  if (typeof ocrvOnViewerClosed === "function") ocrvOnViewerClosed();
}

// ── 缩略图：勾选 / 全选 / 拖拽 / 批量下载 ──

/**
 * 七牛图片处理 URL：把原图换成长边受限的版本（原图只留给下载和拖拽）
 * auto-orient 必须带 —— 七牛处理完会丢掉 EXIF 方向，不先转正，竖拍照片在缩略图里是躺着的
 * ponytail: 每张图首次请求要走 fop 生成（实测约 1.4s），之后 CDN 缓存命中；
 *           量大了再到七牛控制台把这些尺寸存成命名样式，URL 更短
 */
const qiniuImg = (url, width) => `${url}?imageMogr2/auto-orient/thumbnail/${width}x>`;
const THUMB_WIDTH = 400; // 缩略图宽度
const VIEW_WIDTH = 1600; // 双击看大图的宽度

function renderOcrThumbs() {
  const list = document.getElementById("ocrThumbList");
  if (!list) return;
  if (!ocrImages.length) {
    list.innerHTML = '<div style="color:#999;padding:20px;">该任务暂无图片</div>';
    updateOcrSelBar();
    return;
  }
  list.innerHTML = ocrImages.map((item, k) => {
    const isNew = ocrIsPending(item);
    const imgNew = isNew ? '<span class="unread-dot ocr"></span>' : '';
    const sel = ocrSelected.has(k) ? " sel" : "";
    return `<div class="ocr-thumb${sel}" id="ocrThumb-${k}" draggable="true"
        ondragstart="ocrDragStart(event, ${k})"
        onclick="ocrToggleSelect(${k})"
        ondblclick="openOcrViewer(${k})"
        title="单击勾选 · 双击看大图并对照识别结果 · 可直接拖拽">
      <span class="ocr-check">✓</span>
      ${imgNew}<img src="${qiniuImg(item.url, THUMB_WIDTH)}" loading="lazy" decoding="async" alt="图片 ${k+1}" draggable="false" onerror="this.style.display='none'">
      <div class="ocr-thumb-label">图片 ${k+1}</div>
    </div>`;
  }).join("");
  updateOcrSelBar();
}

// 后台预取图片二进制：拖拽时能交出真实 File（拖到文件夹会直接落文件，且支持多张）
// 只取「已勾选」的那几张 —— 打开弹窗就把所有原图整份下下来会把带宽占满，
// 结果缩略图反而更慢（这是之前"图片加载特别慢"的主因）
const ocrPrefetching = new Set();
async function ocrPrefetchSelected() {
  for (const k of [...ocrSelected]) {
    const item = ocrImages[k];
    if (!item || ocrFiles[k] || ocrPrefetching.has(k)) continue;
    ocrPrefetching.add(k);
    try {
      const resp = await fetch(item.url); // 原图：拖出去的就是原件
      if (!resp.ok) continue;
      const blob = await resp.blob();
      ocrFiles[k] = new File([blob], `图片${k + 1}.jpg`, {
        type: blob.type || "image/jpeg",
      });
    } catch {
      /* 跨域或网络失败：拖拽时退回 DownloadURL 方式 */
    } finally {
      ocrPrefetching.delete(k);
    }
  }
}

// 同步「全选」与「下载所选(N)」的状态
function updateOcrSelBar() {
  const all = document.getElementById("ocrSelectAll");
  if (all) {
    all.checked = ocrImages.length > 0 && ocrSelected.size === ocrImages.length;
    all.parentElement.style.display = ocrImages.length ? "inline-flex" : "none";
  }
  const n = ocrSelected.size;
  const btn = document.getElementById("ocrDownloadBtn");
  if (btn) btn.disabled = n === 0;
  const cnt = document.getElementById("ocrDownloadCount");
  if (cnt) cnt.textContent = n ? `(${n})` : "";
}

function ocrToggleSelect(k) {
  if (ocrSelected.has(k)) ocrSelected.delete(k);
  else ocrSelected.add(k);
  // 只切样式，不重建 DOM —— 重建会让所有 <img> 重新发起请求、并闪一下
  document.getElementById(`ocrThumb-${k}`)?.classList.toggle("sel", ocrSelected.has(k));
  updateOcrSelBar();
  ocrPrefetchSelected();
}

function ocrToggleAll(el) {
  ocrSelected = el.checked ? new Set(ocrImages.map((_, k) => k)) : new Set();
  ocrImages.forEach((_, k) => {
    document.getElementById(`ocrThumb-${k}`)?.classList.toggle("sel", ocrSelected.has(k));
  });
  updateOcrSelBar();
  ocrPrefetchSelected();
}

// 拖拽缩略图到桌面 / 文件夹 / 微信等
// 优先交出真实 File 对象（最可靠，且勾选后可一次拖多张）；二进制未预取到则退回 DownloadURL
function ocrDragStart(e, k) {
  const dt = e.dataTransfer;
  dt.effectAllowed = "copy";
  // 有勾选时拖的是「所选」，否则只拖当前这张
  const list = ocrSelected.size ? [...ocrSelected].sort((a, b) => a - b) : [k];
  const targets = list.includes(k) ? list : [k];
  const files = targets.map(i => ocrFiles[i]).filter(Boolean);
  if (files.length) {
    files.forEach(f => dt.items.add(f));
    return; // 不要同时写 text/uri-list，否则接收方会当成网址去"下载"
  }
  const item = ocrImages[k];
  if (item) {
    dt.setData("DownloadURL", `image/jpeg:图片${k + 1}.jpg:${item.url}`);
  }
}

// 下载所选图片（逐张下载，间隔 400ms 避免浏览器拦截多文件）
async function ocrDownloadSelected() {
  const idx = [...ocrSelected].sort((a, b) => a - b);
  if (!idx.length) return;
  toast(`开始下载 ${idx.length} 张图片`);
  for (let i = 0; i < idx.length; i++) {
    await ocrDownloadOne(ocrImages[idx[i]].url, `图片${idx[i] + 1}.jpg`);
    if (i < idx.length - 1) await new Promise(r => setTimeout(r, 400));
  }
}

async function ocrDownloadOne(url, name) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(resp.status);
    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  } catch {
    // 跨域拿不到文件内容时兜底：新窗口打开，可右键另存为
    window.open(url, "_blank");
  }
}

function ocrStart() {
  if (!ocrImages.length) {
    toast("该任务暂无图片");
    return;
  }
  // 识别目标：勾选了就只识别勾选的；没勾选则识别带红点的（没有红点 = 全部）
  const targets = ocrComputeTargets();
  const btn = document.getElementById("ocrActionBtn");
  btn.disabled = true;
  btn.textContent = "识别中...";
  const ta = ocrShowRunning(`正在识别 ${targets.length} 张身份证，请稍候...`);
  authFetch('/api/ocr/recognize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_urls: targets.map(x => x.url) }),
  })
    .then(r => {
      if (!r.ok) return r.json().then(e => { throw new Error(e.detail || '识别失败'); });
      return r.json();
    })
    .then(data => {
      ocrResults = data.results || [];
      ocrErrors = data.errors || [];
      btn.disabled = false;
      btn.textContent = "身份证识别";
      btn.onclick = ocrStart;
      document.getElementById("ocrVerifyBtn").style.display = "inline-flex";
      document.getElementById("ocrCopyBtn").style.display = "inline-flex";
      // 记录识别进度：只推进到「本次已识别图片」的最新时间，且只增不减——
      // 勾选识别部分新图时，没识别的那几张红点保留；勾旧图重识别也不会把进度倒回去
      const oldDone = localStorage.getItem(OCR_DONE_KEY + ocrTaskId) || "";
      const maxAt = targets.reduce((m, x) => (x.at > m ? x.at : m), oldDone);
      localStorage.setItem(OCR_DONE_KEY + ocrTaskId, maxAt);
      renderOcrThumbs();
      ocrClearRunning(ta);
      ocrFillResult(targets);
      toast(`已识别 ${targets.length} 张，结果已追加到文本框`);
    })
    .catch(e => {
      btn.disabled = false;
      btn.textContent = "身份证识别";
      // 有文本框时撤掉进度条、保留内容和可编辑状态，错误只走 toast；没有文本框才显示错误占位
      ocrClearRunning(ta);
      if (!ta) {
        document.getElementById("ocrResultArea").innerHTML = `
          <div class="ocr-loading" style="color:#f5222d">识别失败：${e.message}</div>`;
      }
      toast("识别失败：" + e.message);
    });
}

/**
 * 识别中：锁定文本框 + 在结果区顶部插一条紧凑进度条；
 * 还没有文本框（首次识别）就把占位提示整块换成大加载条。
 * 返回值是当前的 textarea（可能为 null），结束时要交给 ocrClearRunning 收拾。
 */
function ocrShowRunning(message) {
  const ta = document.getElementById("ocrSummary");
  if (ta) {
    ta.readOnly = true;
    document.getElementById("ocrResultArea").insertAdjacentHTML("afterbegin",
      `<div class="ocr-loading ocr-running" id="ocrRunning"><span class="spinner"></span>${message}</div>`);
  } else {
    document.getElementById("ocrResultArea").innerHTML = `
      <div class="ocr-loading"><span class="spinner"></span>${message}</div>`;
  }
  return ta;
}

/** 识别结束（成功、失败都要调）：撤掉进度条、放开文本框 */
function ocrClearRunning(ta) {
  document.getElementById("ocrRunning")?.remove();
  if (ta) ta.readOnly = false;
}

/**
 * 识别目标。
 *   onlySelected = true → 只认勾选的图片（「图片识别」用；没勾选就返回空，由调用方拦下）
 *   其它（身份证识别）   → 勾选 → 只识别勾选的；没勾选 → 识别带红点（未识别）的；都没有 → 全部
 */
function ocrComputeTargets(onlySelected) {
  const selIdx = [...ocrSelected].sort((a, b) => a - b);
  if (onlySelected) {
    return selIdx.map(i => ({ url: ocrImages[i].url, no: i + 1, at: ocrImages[i].created_at }));
  }
  const pendingIdx = ocrImages.map((_, i) => i).filter(i => ocrIsPending(ocrImages[i]));
  const idxs = selIdx.length
    ? selIdx
    : (pendingIdx.length ? pendingIdx : ocrImages.map((_, i) => i));
  return idxs.map(i => ({ url: ocrImages[i].url, no: i + 1, at: ocrImages[i].created_at }));
}

/** 「图片识别」：只识别勾选的图片，原文按原样追加到文本框（不做身份证字段提取） */
async function ocrStartRaw() {
  if (!ocrImages.length) {
    toast("该任务暂无图片");
    return;
  }
  // 必须显式勾选才识别：没勾选就一个请求都不发（既不误识别别的图，也不白占推理）
  if (!ocrSelected.size) {
    toast("请先勾选要识别的图片（单击缩略图勾选）");
    return;
  }
  const targets = ocrComputeTargets(true);
  const btn = document.getElementById("ocrRawBtn");
  btn.disabled = true;
  btn.textContent = "识别中...";
  const ta = ocrShowRunning(`正在识别 ${targets.length} 张图片，请稍候...`);
  try {
    const resp = await authFetch('/api/ocr/recognize_raw', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_urls: targets.map(x => x.url) }),
    });
    if (!resp.ok) {
      const e = await resp.json().catch(() => ({}));
      throw new Error(e.detail || '识别失败');
    }
    const data = await resp.json();
    const results = data.results || [];
    // 原文按识别顺序拼接，中间只留一个换行：不加"===== 图片 N ====="这类前后缀，
    // 否则就跟图上的格式对不上了一行一行的原样了
    const parts = targets.map((t, i) => {
      const r = results[i];
      return r && r.text ? r.text : `图片 ${t.no} 识别失败`;
    });
    ocrAppendResult(parts.join("\n"));
    ocrClearRunning(ta);
    toast("图片识别完成，已追加到文本框");
  } catch (e) {
    ocrClearRunning(ta);
    toast("图片识别失败：" + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "图片识别";
  }
}

/**
 * 把新文本接着写到文本框末尾（不覆盖已有内容）。
 * 两种识别结果因此可以并存；正文变了之后"行 ↔ 图片"的对应关系不再成立，所以清空映射。
 */
function ocrAppendResult(addText) {
  const add = String(addText || "").trim();
  if (!add) return;
  const ta = document.getElementById("ocrSummary");
  const merged = [ta ? ta.value.trim() : ocrGetCached(ocrTaskId).trim(), add]
    .filter(Boolean)
    .join("\n");
  if (ta) {
    ta.value = merged; // 原地追加：重建 textarea 会丢滚动位置和输入状态
  } else {
    ocrSetResultText(merged);
  }
  ocrvCacheWrite(ocrTaskId, merged, null);
  // 有内容了就把「校验 / 复制结果」露出来
  document.getElementById("ocrVerifyBtn").style.display = "inline-flex";
  document.getElementById("ocrCopyBtn").style.display = "inline-flex";
}

let ocrResults = [];
let ocrErrors = [];

function ocrFillResult(targets) {
  // 一律"接着已有内容往下写"，不覆盖已有结果；
  // 文本与"第几行对应第几张图"的映射都由 ocr-preview.js 的 ocrvResultBuild 一并维护
  const text = ocrvResultBuild(ocrTaskId, targets, ocrResults, true);
  ocrSetResultText(text);
  document.getElementById("ocrVerifyTip").style.display = "none";
}

function ocrCopyResults() {
  const ta = document.getElementById("ocrSummary");
  if (!ta) return;
  const text = ta.value.split('\n').map(l => l.trim()).filter(Boolean).map(line => {
    const m = line.match(/^(.+?)\s+(\d{17}[\dXx])$/);
    return m ? m[1] + '\t' + m[2] : line;
  }).join('\n');
  if (!text) { toast('识别结果为空'); return; }
  copyText(text, '已复制到剪贴板');
}

/**
 * 复制纯文本到剪贴板。
 *
 * 这里**不能**用 navigator.clipboard：内勤页走的是 http://192.168.1.9:8001（非安全上下文），
 * 浏览器只在 HTTPS 或 localhost 下才提供它 → 在这个页面里它是 undefined，
 * 调用会同步抛 TypeError（连 .catch 都进不去），表现出来就是"点了按钮毫无反应、也没有提示"。
 * document.execCommand("copy") 只要求"用户手势"，http 下照常可用 —— 本文件里表格复制一直用的就是它。
 *
 * 注意：临时文本框不能 display:none（那样选不中就复制不到），放到视口外即可。
 */
function copyText(text, okMsg) {
  const tmp = document.createElement("textarea");
  tmp.value = text;
  tmp.setAttribute("readonly", "");
  tmp.style.position = "fixed";
  tmp.style.top = "-1000px";
  tmp.style.left = "-1000px";
  document.body.appendChild(tmp);
  tmp.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (e) {
    ok = false;
  }
  document.body.removeChild(tmp);
  toast(ok ? (okMsg || "已复制") : "复制失败，请手动选中后按 Ctrl + C");
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

function esc(s) { return s ? String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') : '-'; }

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

// ── 下拉选项管理入口（仅 can_manage_dropdowns=1 可见）──

const DROPDOWN_CATEGORY = 'insurance_company';
const DROPDOWN_CATEGORY_LABEL = '保险公司';

/**
 * 是否显示"下拉选项管理"入口
 * 权限以服务端为准：localStorage 里那份是「登录那一刻」的快照，
 * 权限刚开通、或换了账号时会过期，所以进页面时用 /api/users 里自己那条刷新一次；
 * 请求失败（后端没更新/断网）就沿用本地快照，不影响使用
 */
async function syncDropdownEntry() {
  const btn = document.getElementById('dropdownManageBtn');
  if (!btn) return;
  const me = JSON.parse(localStorage.getItem('currentUser') || '{}');
  let allowed = !!me.can_manage_dropdowns;
  try {
    const r = await authFetch('/api/users');
    if (r.ok) {
      const mine = (await r.json()).find(x => x.id === me.id);
      if (mine) allowed = !!mine.can_manage_dropdowns;
    }
  } catch (e) { /* 后端不可用：沿用本地快照 */ }
  btn.style.display = allowed ? 'block' : 'none';
}

syncDropdownEntry();

// ── 下拉选项管理 ──

function openDropdownManage() {
  userDropdown.classList.remove('show');
  document.getElementById('dropdownManageSub').textContent = DROPDOWN_CATEGORY_LABEL;
  document.getElementById('dropdownManageMask').style.display = 'flex';
  document.getElementById('dropdownNewValue').value = '';
  loadDropdownList();
}

function closeDropdownManage() {
  document.getElementById('dropdownManageMask').style.display = 'none';
}

function dropdownRow(o) {
  return `<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid var(--line);border-radius:var(--r-sm);background:#fff">
      <span style="flex:1;min-width:0;font-size:var(--fs-sm);color:var(--gray-800);word-break:break-all">${esc(o.value)}</span>
      <button class="btn" style="height:26px;padding:0 10px;font-size:var(--fs-xs)" onclick="doDeleteDropdown(${o.id})">删除</button>
    </div>`;
}

// ── 个人标签 ──

async function loadMyTags() {
  try {
    const r = await authFetch('/api/tags');
    if (!r.ok) throw new Error('加载标签失败');
    myTags = await r.json();
  } catch { myTags = []; }
}

async function createMyTag(name, color) {
  const r = await authFetch('/api/tags', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `name=${encodeURIComponent(name)}&color=${encodeURIComponent(color || '#1677ff')}`
  });
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || '创建失败'); }
  await loadMyTags();
}

async function deleteMyTag(id) {
  const r = await authFetch(`/api/tags/${id}`, { method: 'DELETE' });
  if (!r.ok) throw new Error('删除失败');
  await loadMyTags();
}

async function loadTaskTags(taskId) {
  try {
    const r = await authFetch(`/api/tags/tasks/${taskId}`);
    if (!r.ok) throw new Error('加载失败');
    return await r.json();
  } catch { return []; }
}

async function addTaskTag(taskId, tagId) {
  const r = await authFetch(`/api/tags/tasks/${taskId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `tag_id=${tagId}`
  });
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || '添加失败'); }
  return await r.json();
}

async function renameMyTag(id, name, color) {
  const body = `name=${encodeURIComponent(name)}` + (color ? `&color=${encodeURIComponent(color)}` : '');
  const r = await authFetch(`/api/tags/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body
  });
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || '修改失败'); }
  await loadMyTags();
}

async function deleteTaskTag(taskId, ttId) {
  const r = await authFetch(`/api/tags/tasks/${taskId}/${ttId}`, { method: 'DELETE' });
  if (!r.ok) throw new Error('删除失败');
}

let myTags = [];

// ── 个人标签管理弹窗 ──

const TAG_COLORS = ['#1677ff', '#52c41a', '#faad14', '#722ed1', '#fa541c', '#13c2c2'];
let tagColorPicked = TAG_COLORS[0];

function openTagManage() {
  document.getElementById('tagManageMask').style.display = 'flex';
  document.getElementById('tagNewName').value = '';
  tagColorPicked = TAG_COLORS[0];
  editingTagId = null;
  renderTagSwatches();
  loadTagManageList();
}

function closeTagManage() {
  document.getElementById('tagManageMask').style.display = 'none';
}

function pickTagColor(c) {
  tagColorPicked = c;
  renderTagSwatches();
}

function renderTagSwatches() {
  document.getElementById('tagColorSwatches').innerHTML = TAG_COLORS.map(c =>
    `<span class="tag-swatch${c === tagColorPicked ? ' on' : ''}" style="background:${c}" title="${c}" onclick="pickTagColor('${c}')"></span>`
  ).join('');
}

async function loadTagManageList() {
  const wrap = document.getElementById('tagManageList');
  wrap.innerHTML = '<div style="padding:12px;color:var(--gray-500);font-size:var(--fs-sm)">加载中…</div>';
  await loadMyTags();
  wrap.innerHTML = myTags.length
    ? myTags.map(tagManageRow).join('')
    : '<div style="padding:12px;color:var(--gray-500);font-size:var(--fs-sm)">还没有标签，先在上方创建</div>';
}

function tagManageRow(t) {
  if (t.id === editingTagId) {
    return `<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid var(--blue-300);border-radius:var(--r-sm);background:#f7faff;flex-wrap:wrap">
        <div id="tagEditSwatches" style="display:flex;gap:6px">${TAG_COLORS.map(c =>
          `<span class="tag-swatch${c === editColorPicked ? ' on' : ''}" style="background:${c}" onclick="pickEditColor('${c}')"></span>`
        ).join('')}</div>
        <input class="filter-input" id="tagEditName" value="${esc(t.name)}" onkeydown="if(event.key==='Enter')saveTagEdit(${t.id});if(event.key==='Escape')cancelTagEdit()" style="flex:1;margin:0;min-width:100px">
        <button class="btn primary" style="height:26px;padding:0 10px;font-size:var(--fs-xs)" onclick="saveTagEdit(${t.id})">保存</button>
        <button class="btn" style="height:26px;padding:0 10px;font-size:var(--fs-xs)" onclick="cancelTagEdit()">取消</button>
      </div>`;
  }
  return `<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid var(--line);border-radius:var(--r-sm);background:#fff">
      <span style="background:${t.color};color:#fff;font-size:var(--fs-sm);padding:3px 12px;border-radius:12px;flex:none;max-width:50%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-right:auto">${esc(t.name)}</span>
      <button class="btn" style="height:26px;padding:0 10px;font-size:var(--fs-xs)" onclick="doRenameTag(${t.id})">修改</button>
      <button class="btn" style="height:26px;padding:0 10px;font-size:var(--fs-xs)" onclick="doDeleteTag(${t.id})">删除</button>
    </div>`;
}

async function doAddTag() {
  const input = document.getElementById('tagNewName');
  const name = input.value.trim();
  if (!name) { toast('请输入标签名称'); input.focus(); return; }
  try {
    await createMyTag(name, tagColorPicked);
    input.value = '';
    loadTagManageList();
    toast('已创建：' + name);
  } catch (e) {
    toast(e.message);
  }
}

async function doDeleteTag(id) {
  if (!confirm('删除标签后，所有任务上的该标签也会被移除，确定？')) return;
  try {
    await deleteMyTag(id);
    // 绑定已被后端级联删除，刷新本地缓存让卡片同步消失
    await Promise.all([loadTagManageList(), loadTagBindings()]);
    render();
    toast('已删除');
  } catch (e) {
    toast(e.message);
  }
}

// 行内编辑标签：editingTagId 指向正在编辑的行，tagManageRow 据此渲染编辑态
let editingTagId = null;
let editColorPicked = '';

function doRenameTag(id) {
  const tag = myTags.find(x => x.id === id);
  if (!tag) return;
  editingTagId = id;
  editColorPicked = tag.color;
  loadTagManageList();
  setTimeout(() => { const inp = document.getElementById('tagEditName'); if (inp) { inp.focus(); inp.select(); } }, 0);
}

function pickEditColor(c) {
  editColorPicked = c;
  const wrap = document.getElementById('tagEditSwatches');
  if (wrap) wrap.innerHTML = TAG_COLORS.map(x =>
    `<span class="tag-swatch${x === editColorPicked ? ' on' : ''}" style="background:${x}" onclick="pickEditColor('${x}')"></span>`
  ).join('');
}

function cancelTagEdit() {
  editingTagId = null;
  loadTagManageList();
}

async function saveTagEdit(id) {
  const input = document.getElementById('tagEditName');
  const name = (input ? input.value : '').trim();
  const tag = myTags.find(x => x.id === id);
  if (!name) { toast('标签名不能为空'); return; }
  if (tag && name === tag.name && editColorPicked === tag.color) { cancelTagEdit(); return; }
  try {
    await renameMyTag(id, name, editColorPicked);
    editingTagId = null;
    // task_tags 只存引用，改完刷新绑定缓存让卡片同步生效
    await Promise.all([loadTagManageList(), loadTagBindings()]);
    render();
    toast('已保存');
  } catch (e) {
    toast(e.message);
  }
}

// ── 任务卡片标签选择弹窗 ──

let tagPickerIdx = -1;

async function openTagPicker(e, i) {
  if (e) e.stopPropagation();
  tagPickerIdx = i;
  const t = renderedTasks[i];
  if (!t) return;
  document.getElementById('tagPickerSub').textContent = (t.company || t.user);
  document.getElementById('tagPickerMask').style.display = 'flex';
  await loadMyTags(); // 拿最新标签（可能刚在管理弹窗里建了新的）
  renderTagPicker();
}

function closeTagPicker() {
  document.getElementById('tagPickerMask').style.display = 'none';
}

function renderTagPicker() {
  const t = renderedTasks[tagPickerIdx];
  if (!t) return;
  const wrap = document.getElementById('tagPickerList');
  const empty = document.getElementById('tagPickerEmpty');
  if (!myTags.length) {
    wrap.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  const applied = tagBindings.get(t.id) || [];
  wrap.innerHTML = myTags.map(tag => {
    const on = applied.some(b => b.tag_id === tag.id);
    // 选中=实色深底白字（与卡片标签一致）；未选=白底+实色描边+彩字，不用浅色蒙层
    return `<span class="pick-tag${on ? ' on' : ''}" style="background:${on ? tag.color : '#fff'};color:${on ? '#fff' : tag.color};border:1.5px solid ${tag.color}" onclick="toggleTaskTag(${tagPickerIdx}, ${tag.id})">${esc(tag.name)}</span>`;
  }).join('');
}

async function toggleTaskTag(i, tagId) {
  const t = renderedTasks[i];
  if (!t) return;
  const bindings = tagBindings.get(t.id) || [];
  const applied = bindings.find(b => b.tag_id === tagId);
  try {
    if (applied) {
      await deleteTaskTag(t.id, applied.tt_id);
      tagBindings.set(t.id, bindings.filter(b => b.tag_id !== tagId));
    } else {
      const nb = await addTaskTag(t.id, tagId);
      // 接口返回的关联 id 字段名是 id，统一成 tt_id 再入缓存（与服务端批量接口一致）
      tagBindings.set(t.id, [...bindings, { tt_id: nb.id, tag_id: nb.tag_id, name: nb.name, color: nb.color }]);
    }
    render();
    renderTagPicker();
  } catch (e) {
    toast(e.message);
  }
}

// 卡片标签片右上角 ×：直接移除该任务上的标签（不弹窗）
async function removeTaskTag(e, i, tagId) {
  e.stopPropagation();
  const t = renderedTasks[i];
  if (!t) return;
  const bindings = tagBindings.get(t.id) || [];
  const applied = bindings.find(b => b.tag_id === tagId);
  if (!applied) return;
  try {
    await deleteTaskTag(t.id, applied.tt_id);
    tagBindings.set(t.id, bindings.filter(b => b.tag_id !== tagId));
    render();
  } catch (err) {
    toast(err.message);
  }
}

async function loadDropdownList() {
  const wrap = document.getElementById('dropdownManageList');
  wrap.innerHTML = '<div style="padding:12px;color:var(--gray-500);font-size:var(--fs-sm)">加载中…</div>';
  try {
    const r = await authFetch(`/api/dropdowns/${DROPDOWN_CATEGORY}`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const list = await r.json();
    wrap.innerHTML = list.length
      ? list.map(dropdownRow).join('')
      : '<div style="padding:12px;color:var(--gray-500);font-size:var(--fs-sm)">还没有选项，先在上方添加</div>';
  } catch (e) {
    wrap.innerHTML = `<div style="padding:12px;color:#f5222d;font-size:var(--fs-sm)">加载失败：${esc(e.message)}</div>`;
  }
}

async function doAddDropdown() {
  const input = document.getElementById('dropdownNewValue');
  const value = input.value.trim();
  if (!value) {
    toast('请输入选项名称');
    input.focus();
    return;
  }
  try {
    const fd = new FormData();
    fd.append('value', value);
    const r = await authFetch(`/api/dropdowns/${DROPDOWN_CATEGORY}`, { method: 'POST', body: fd });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      toast(err.detail || '添加失败');
      return;
    }
    input.value = '';
    loadDropdownList();
    toast('已添加：' + value);
  } catch (e) {
    toast('网络错误，添加失败');
  }
}

async function doDeleteDropdown(id) {
  try {
    const r = await authFetch(`/api/dropdowns/${DROPDOWN_CATEGORY}/${id}`, { method: 'DELETE' });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      toast(err.detail || '删除失败');
      return;
    }
    loadDropdownList();
    toast('已删除');
  } catch (e) {
    toast('网络错误，删除失败');
  }
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
  // 自动刷新（15 秒）— 仅刷新侧栏保险公司列表，任务卡片需手动刷新
  setInterval(async () => {
    try {
      await loadCompanies();
      renderSidebar();
    } catch {}
  }, 15000);
}

init();