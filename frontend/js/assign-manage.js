/**
 * 人员筛选管理（内勤负责关系弹窗，仅 can_manage_dropdowns=1）
 * =====================================================================
 * 配置「某内勤负责对接某保司下的哪些客服」。配置生效后（app.js 的 myScopeRows /
 * taskInScope，见 render 过滤链）：该内勤登录 index 只能看到自己负责的任务。
 *
 * 为什么单独一个文件：app.js 已经太长，而这里是一段自成一体的弹窗 CRUD，
 * 和 ocr-preview.js 一样拆出去，只在 openAssignManage 一个入口进出。
 *
 * 依赖 app.js 的全局（同页面普通 <script>，共享全局作用域）：
 *   allUserRows / allAssignments        数据（app.js 的 loadUsers / loadAssignments 拉）
 *   loadUsers / loadAssignments         拉数据
 *   authFetch / esc / toast             工具
 *   userDropdown                        头像下拉（打开弹窗前收起它）
 * 约束（同 ocr-preview.js）：
 *   1) 必须加载在 app.js **之后**
 *   2) 不能和 app.js 顶层声明重名（assignCsSelected / assignCompanies / assignActiveOp /
 *      operatorUsers / csUserRows / loadAssignCompanies / openAssignManage / closeAssignManage /
 *      fillAssignForm / resetAssignForm / toggleAssignCsPanel / toggleAssignCs /
 *      onAssignAllChange / renderAssignCsPanel / saveAssignGroup / editAssignGroup /
 *      delAssignGroup / renderAssignList / pickAssignOperator 都是本文件的）
 *   3) 不在顶层碰 DOM，只在函数里碰
 */

let assignCsSelected = [];   // 表单选中的客服 id
let assignCompanies = [];    // 保司选项（dropdown_options 的 insurance_company）
let assignActiveOp = null;   // 列表左栏选中的内勤 id（保存/删除后不清空，免得跳回第一个）

const operatorUsers = () => allUserRows.filter(u => u.role === 2 || u.role === 22);
const csUserRows = () => allUserRows.filter(u => u.role === 1 || u.role === 11);

async function loadAssignCompanies() {
  try {
    const r = await authFetch('/api/dropdowns/insurance_company');
    if (!r.ok) throw new Error();
    assignCompanies = await r.json();
  } catch { assignCompanies = []; }
}

async function openAssignManage() {
  userDropdown.classList.remove('show');
  document.getElementById('assignManageMask').style.display = 'flex';
  await Promise.all([loadUsers(), loadAssignments(), loadAssignCompanies()]);
  fillAssignForm();
  renderAssignList();
}

function closeAssignManage() {
  document.getElementById('assignManageMask').style.display = 'none';
}

// 表单：编辑时预填该组（editOpId/editCompany），不传 = 清空新增
function fillAssignForm(editOpId, editCompany) {
  document.getElementById('assignOperator').innerHTML =
    '<option value="">选择内勤</option>' + operatorUsers().map(u =>
      `<option value="${u.id}" ${u.id === editOpId ? 'selected' : ''}>${esc(u.display_name)}</option>`).join('');
  document.getElementById('assignCompany').innerHTML =
    '<option value="">选择保司</option>' + assignCompanies.map(c =>
      `<option value="${esc(c.value)}" ${c.value === editCompany ? 'selected' : ''}>${esc(c.value)}</option>`).join('');
  if (editOpId && editCompany) {
    const rows = allAssignments.filter(a => a.operator_id === editOpId && a.insurance_company === editCompany);
    const isAll = rows.length === 1 && rows[0].user_id === null;
    document.getElementById('assignAll').checked = isAll;
    assignCsSelected = isAll ? [] : rows.map(r => r.user_id).filter(id => id !== null);
  } else {
    document.getElementById('assignAll').checked = false;
    assignCsSelected = [];
  }
  renderAssignCsPanel();
}

function resetAssignForm() {
  fillAssignForm();
}

function toggleAssignCsPanel() {
  document.getElementById('assignCsSelect').classList.toggle('on');
}

function toggleAssignCs(id) {
  if (assignCsSelected.includes(id)) assignCsSelected = assignCsSelected.filter(x => x !== id);
  else assignCsSelected.push(id);
  renderAssignCsPanel();
}

function onAssignAllChange() {
  renderAssignCsPanel();
}

function renderAssignCsPanel() {
  const all = document.getElementById('assignAll').checked;
  document.getElementById('assignCsPanel').innerHTML = csUserRows().map(u => `
    <label class="multi-option">
      <input type="checkbox" ${assignCsSelected.includes(u.id) ? 'checked' : ''} ${all ? 'disabled' : ''} onchange="toggleAssignCs(${u.id})">
      <span class="chk"></span>${esc(u.display_name)}
    </label>`).join('');
  document.getElementById('assignCsLabel').textContent = all ? '全部客服'
    : (assignCsSelected.length ? `${assignCsSelected.length} 位客服` : '选择客服');
}

async function saveAssignGroup() {
  const operatorId = parseInt(document.getElementById('assignOperator').value);
  const company = document.getElementById('assignCompany').value;
  if (!operatorId) { toast('请选择内勤'); return; }
  if (!company) { toast('请选择保司'); return; }
  const all = document.getElementById('assignAll').checked;
  if (!all && !assignCsSelected.length) { toast('请选择客服，或勾选「全部」'); return; }
  const r = await authFetch('/api/assignments', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId, insurance_company: company, user_ids: all ? null : assignCsSelected }),
  });
  if (!r.ok) { const e = await r.json().catch(() => ({})); toast(e.detail || '保存失败'); return; }
  toast('已保存');
  await loadAssignments();
  assignActiveOp = operatorId;  // 保存后左栏停在这个内勤身上，方便接着配他的其他保司
  renderAssignList();
  resetAssignForm();
}

function editAssignGroup(opId, co) {
  fillAssignForm(opId, co);
}

async function delAssignGroup(opId, co) {
  if (!confirm(`删除「${co}」的这组负责关系？`)) return;
  const r = await authFetch(`/api/assignments/${opId}?insurance_company=${encodeURIComponent(co)}`, { method: 'DELETE' });
  if (!r.ok) { const e = await r.json().catch(() => ({})); toast(e.detail || '删除失败'); return; }
  toast('已删除');
  await loadAssignments();
  assignActiveOp = opId;  // 删完仍停在这人身上；他若已被删空，renderAssignList 会落回第一个人
  renderAssignList();
}

// 左栏点人：换一个人看他的绑定关系
function pickAssignOperator(opId) {
  if (assignActiveOp === opId) return;
  assignActiveOp = opId;
  renderAssignList();
}

/**
 * 列表：左栏内勤、右栏这个内勤负责的保司与客服。
 *
 * 原来是把所有内勤的组一次性铺开，人一多就得整屏滚着找；改成"点谁看谁"。
 * 选中的人存在 assignActiveOp 里 —— 保存/删除后重渲染不会跳回第一个，
 * 因为这两个动作之后紧接着要做的事，基本都是在同一个人身上继续配。
 * 右栏的数据全部来自 allAssignments（同一个接口），点人只是换渲染范围，不额外请求。
 */
function renderAssignList() {
  const box = document.getElementById('assignManageList');
  if (!allAssignments.length) {
    box.innerHTML = '<div class="assign-empty">还没有配置负责关系<br><b>用上方表单添加</b></div>';
    return;
  }
  // 按内勤分组（保持接口返回的顺序，不重排）
  const byOp = new Map();
  allAssignments.forEach(a => {
    if (!byOp.has(a.operator_id)) byOp.set(a.operator_id, { name: a.operator_name, rows: [] });
    byOp.get(a.operator_id).rows.push(a);
  });
  // 选中的人可能已经不存在了（配置被删空）→ 落回第一个人，避免右栏空着
  if (!byOp.has(assignActiveOp)) assignActiveOp = [...byOp.keys()][0];

  const people = [...byOp.entries()].map(([opId, g]) => {
    const companyCount = new Set(g.rows.map(r => r.insurance_company)).size;
    const name = g.name || ('内勤 #' + opId);
    return `<button class="ap-item${opId === assignActiveOp ? ' on' : ''}" onclick="pickAssignOperator(${opId})">
        <span class="ap-avatar">${esc(name.charAt(0))}</span>
        <span class="ap-name">${esc(name)}</span>
        <span class="ap-count">${companyCount}</span>
      </button>`;
  }).join('');

  const active = byOp.get(assignActiveOp);
  const byCo = new Map();
  active.rows.forEach(r => {
    if (!byCo.has(r.insurance_company)) byCo.set(r.insurance_company, []);
    byCo.get(r.insurance_company).push(r);
  });
  const coRows = [...byCo.entries()].map(([co, rows]) => {
    const isAll = rows.length === 1 && rows[0].user_id === null;
    const names = isAll ? '全部客服' : rows.map(r => r.user_name).filter(Boolean).map(esc).join('、');
    // 保司名走 data-co 取值（esc 不转义单引号，拼进 onclick 会断）
    return `<div class="assign-row">
        <span class="assign-co">${esc(co)}</span>
        <span class="assign-cs">${names}</span>
        <span class="assign-ops">
          <button class="btn af-btn" data-co="${esc(co)}" onclick="editAssignGroup(${assignActiveOp}, this.dataset.co)">编辑</button>
          <button class="btn af-btn af-del" data-co="${esc(co)}" onclick="delAssignGroup(${assignActiveOp}, this.dataset.co)">删除</button>
        </span>
      </div>`;
  }).join('');

  box.innerHTML = `<div class="assign-people">
      <div class="assign-people-head">内勤<span class="ag-count">${byOp.size} 人</span></div>
      ${people}
    </div>
    <div class="assign-detail">
      <div class="assign-detail-head">${esc(active.name || ('内勤 #' + assignActiveOp))}<span class="ag-count">${byCo.size} 个保司</span></div>
      ${coRows}
    </div>`;
}
