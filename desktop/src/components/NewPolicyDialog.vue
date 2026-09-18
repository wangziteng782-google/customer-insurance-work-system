<template>
  <div class="modal-mask">
    <div class="dialog">
      <div class="dialog-head">
        <h2 class="dialog-title">新建保单收集</h2>
        <button class="close-btn" title="关闭" @click="$emit('close')">×</button>
      </div>

      <label class="field-label">保险公司 <span style="color: red">*</span></label>
      <div class="combo">
        <input
          ref="companyInput"
          v-model="company"
          type="text"
          placeholder="搜索或选择保险公司"
          @focus="companyOpen = true"
          @blur="companyOpen = false"
        />
        <div v-if="companyOpen && filteredCompanies.length" class="combo-list">
          <div
            v-for="c in filteredCompanies"
            :key="c"
            class="combo-item"
            :class="{ active: c === company }"
            @mousedown.prevent
            @click="selectCompany(c)"
          >
            {{ c }}
          </div>
        </div>
      </div>

      <label class="field-label">客户公司 <span style="color: red">*</span></label>
      <input v-model.trim="customerCompany" placeholder="输入客户公司名称" />

      <label class="field-label">保单类型 <span style="color: red">*</span></label>
      <div class="type-row">
        <label class="radio">
          <input v-model="policyType" type="radio" :value="1" />新投
        </label>
        <label class="radio">
          <input v-model="policyType" type="radio" :value="2" />批改
        </label>
      </div>

      <p class="error" :class="{ visible: !!error }">{{ error }}</p>

      <div class="btn-row">
        <button class="cancel-btn" @click="$emit('close')">取消</button>
        <button class="ok-btn" @click="onConfirm">确认开始</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { INSURANCE_COMPANIES } from "../constants";

const emit = defineEmits(["close", "confirm"]);

const company = ref("");
const customerCompany = ref("");
const policyType = ref(1);
const error = ref("");
const companyOpen = ref(false);
const companyInput = ref(null);

/** 过滤：包含匹配（对齐 PySide completer MatchContains），空输入显示全部 */
const filteredCompanies = computed(() => {
  const kw = company.value.trim();
  if (!kw) return INSURANCE_COMPANIES;
  return INSURANCE_COMPANIES.filter((c) => c.includes(kw));
});

function selectCompany(c) {
  company.value = c;
  companyOpen.value = false;
}

function onConfirm() {
  if (!company.value) {
    error.value = "请选择或输入保险公司";
    companyInput.value?.focus();
    return;
  }
  if (!customerCompany.value) {
    error.value = "请输入客户公司名称";
    return;
  }
  emit("confirm", {
    company: company.value,
    customerCompany: customerCompany.value,
    type: policyType.value,
  });
}

function onKeydown(e) {
  if (e.key === "Escape") emit("close");
}

onMounted(() => document.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
</script>

<style scoped>
.dialog {
  width: 380px;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
}
.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.dialog-title {
  font-size: 16px;
  color: var(--text-primary);
}
.close-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.close-btn:hover {
  background: #f0f0f0;
  color: var(--text-primary);
}
.field-label {
  display: block;
  font-size: 13px;
  color: #3a3a4a;
  margin-bottom: 6px;
}
/* 只作用于文本输入框，避免命中 radio 单选按钮 */
input:not([type="radio"]) {
  width: 100%;
  height: 36px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 0 10px;
  font-size: 13px;
  outline: none;
  margin-bottom: 12px;
}
input:not([type="radio"]):focus {
  border-color: var(--primary);
}

/* ── 自定义下拉 ── */
.combo {
  position: relative;
  margin-bottom: 12px;
}
.combo input {
  margin-bottom: 0;
}
.combo-list {
  position: absolute;
  top: 38px;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
}
.combo-item {
  padding: 7px 12px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
}
.combo-item:hover,
.combo-item.active {
  background: var(--primary-light);
  color: var(--primary);
}

.type-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 20px;
  margin-bottom: 12px;
}
.radio {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #3a3a4a;
  cursor: pointer;
  white-space: nowrap;
}
.radio input[type="radio"] {
  width: 14px;
  height: 14px;
  margin: 0;
  padding: 0;
  accent-color: var(--primary);
  cursor: pointer;
}
.error {
  min-height: 18px;
  font-size: 12px;
  color: #ff4d4f;
  margin-bottom: 4px;
  opacity: 0;
}
.error.visible {
  opacity: 1;
}
.btn-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.cancel-btn {
  width: 70px;
  height: 32px;
  background: #f5f5f5;
  color: var(--text-secondary);
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 13px;
}
.cancel-btn:hover {
  border-color: #b8bcc4;
}
.ok-btn {
  width: 90px;
  height: 32px;
  background: var(--primary);
  color: #fff;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}
.ok-btn:hover {
  background: var(--primary-hover);
}
</style>
