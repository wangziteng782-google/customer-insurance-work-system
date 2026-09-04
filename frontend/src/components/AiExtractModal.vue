<script setup lang="ts">
import { ref, computed } from 'vue';
import { aiExtract, type ChatTask } from '../api';

const props = defineProps<{
  task: ChatTask;
}>();

const emit = defineEmits<{
  close: [];
  submitted: [];
}>();

type TemplateType = 'new' | 'endorsement';

const loading = ref(false);
const extracting = ref(false);

// 根据任务类型自动推断模板（1=新投, 2=批改, 默认新投）
const templateType = computed<TemplateType>(() => props.task.business_type === 2 ? 'endorsement' : 'new');
const typeLabel = computed(() => props.task.business_type === 2 ? '批改' : '新投');

// 表单数据
const form = ref({
  company_name: '',
  source: '',
  job_type: '',
  plan: '',
  is_renewal: '',
  specified_effective: false,
  discovery_date: '',
  insurance_type: '',
  annual_salary: '',
  remarks: '',
  qualification: '',
});

// 新投字段配置
const newPolicyFields = [
  { key: 'company_name', label: '公司名称', type: 'text', required: true },
  { key: 'source', label: '来源', type: 'text' },
  { key: 'job_type', label: '工种', type: 'text' },
  { key: 'plan', label: '方案', type: 'text' },
  { key: 'is_renewal', label: '续保/新投', type: 'select', options: ['新投', '续保'] },
  { key: 'specified_effective', label: '是否指定生效', type: 'checkbox' },
  { key: 'discovery_date', label: '发现日期', type: 'date' },
  { key: 'insurance_type', label: '险种', type: 'text' },
  { key: 'annual_salary', label: '年薪', type: 'number' },
  { key: 'remarks', label: '备注', type: 'textarea' },
  { key: 'qualification', label: '资质', type: 'text' },
];

// 批改字段配置
const endorsementFields = [
  { key: 'company_name', label: '公司名称', type: 'text', required: true },
  { key: 'job_type', label: '工种', type: 'text' },
  { key: 'specified_effective', label: '是否指定生效', type: 'checkbox' },
  { key: 'insurance_type', label: '险种', type: 'text' },
  { key: 'annual_salary', label: '年薪', type: 'number' },
  { key: 'remarks', label: '备注', type: 'textarea' },
];

// 当前显示的字段
const currentFields = computed(() => {
  return templateType.value === 'new' ? newPolicyFields : endorsementFields;
});

// AI提取
async function handleExtract() {
  extracting.value = true;
  try {
    const result = await aiExtract(props.task.task_id);
    // 填充表单
    for (const key of Object.keys(form.value)) {
      if (result[key] !== undefined && result[key] !== null) {
        form.value[key as keyof typeof form.value] = result[key];
      }
    }
  } catch (e) {
    console.error('AI提取失败:', e);
    alert('AI提取失败，请稍后重试');
  } finally {
    extracting.value = false;
  }
}

// 提交（先仅提示，后续接接口）
function handleSubmit() {
  if (!form.value.company_name.trim()) {
    alert('请填写公司名称');
    return;
  }
  console.log('提交数据:', { type: templateType.value, ...form.value });
  alert('提交成功（功能开发中）');
  emit('submitted');
  emit('close');
}

// 关闭
function handleClose() {
  emit('close');
}
</script>

<template>
  <div class="modal-mask" @click.self="handleClose">
    <div class="modal-container">
      <!-- 头部 -->
      <div class="modal-header">
        <h3 class="modal-title">智能提取保单信息</h3>
        <button class="modal-close" @click="handleClose">✕</button>
      </div>

      <!-- 内容 -->
      <div class="modal-body">
        <!-- 保单类型（自动识别） -->
        <div class="form-row">
          <label class="form-label">保单类型</label>
          <span class="type-display" :class="{ edit: templateType === 'endorsement' }">{{ typeLabel }}</span>
        </div>

        <!-- 提取按钮 -->
        <div class="form-row extract-row">
          <button class="extract-btn" :disabled="extracting" @click="handleExtract">
            {{ extracting ? '提取中...' : 'AI自动提取' }}
          </button>
          <span class="extract-tip">点击从聊天消息中提取信息</span>
        </div>

        <!-- 动态表单 -->
        <div class="form-grid">
          <div v-for="field in currentFields" :key="field.key" class="form-row" :class="{ 'full-width': field.type === 'textarea' }">
            <label class="form-label">
              {{ field.label }}
              <span v-if="field.required" class="required">*</span>
            </label>

            <input
              v-if="field.type === 'text'"
              v-model="form[field.key as keyof typeof form]"
              type="text"
              class="form-input"
              :placeholder="'请输入' + field.label"
            />

            <input
              v-else-if="field.type === 'number'"
              v-model="form[field.key as keyof typeof form]"
              type="number"
              class="form-input"
              :placeholder="'请输入' + field.label"
            />

            <input
              v-else-if="field.type === 'date'"
              v-model="form[field.key as keyof typeof form]"
              type="date"
              class="form-input"
            />

            <select
              v-else-if="field.type === 'select'"
              v-model="form[field.key as keyof typeof form]"
              class="form-select"
            >
              <option value="">请选择</option>
              <option v-for="opt in (field as any).options" :key="opt" :value="opt">{{ opt }}</option>
            </select>

            <label v-else-if="field.type === 'checkbox'" class="form-checkbox">
              <input type="checkbox" v-model="form.specified_effective" />
              <span>是</span>
            </label>

            <textarea
              v-else-if="field.type === 'textarea'"
              v-model="form[field.key as keyof typeof form]"
              class="form-textarea"
              :placeholder="'请输入' + field.label"
              rows="3"
            />
          </div>
        </div>
      </div>

      <!-- 底部 -->
      <div class="modal-footer">
        <button class="footer-btn cancel" @click="handleClose">取消</button>
        <button class="footer-btn submit" @click="handleSubmit">提交</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-container {
  width: 560px;
  max-height: 80vh;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f2f5;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a202c;
  margin: 0;
}

.modal-close {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  font-size: 16px;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 4px;
}

.modal-close:hover {
  background: #f5f5f5;
  color: #3a3a4a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.form-row {
  margin-bottom: 14px;
}

.form-row.full-width {
  grid-column: 1 / -1;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 6px;
}

.required {
  color: #ff4d4f;
  margin-left: 2px;
}

.form-input,
.form-select {
  width: 100%;
  height: 34px;
  padding: 0 10px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  color: #3a3a4a;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus,
.form-select:focus {
  border-color: #1677ff;
}

.type-display {
  display: inline-block;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #1677ff;
  background: #e8f4ff;
  border-radius: 6px;
}
.type-display.edit {
  color: #fa8c16;
  background: #fff7e6;
}

.form-textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  color: #3a3a4a;
  outline: none;
  resize: vertical;
  font-family: inherit;
}

.form-textarea:focus {
  border-color: #1677ff;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #3a3a4a;
  cursor: pointer;
}

.form-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.extract-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.extract-btn {
  padding: 8px 16px;
  background: linear-gradient(135deg, #1677ff, #4096ff);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.extract-btn:hover:not(:disabled) {
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.3);
}

.extract-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.extract-tip {
  font-size: 12px;
  color: #9ca3af;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #f0f2f5;
  background: #fafbfc;
}

.footer-btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.footer-btn.cancel {
  background: #fff;
  color: #6b7280;
  border: 1px solid #d9d9d9;
}

.footer-btn.cancel:hover {
  border-color: #1677ff;
  color: #1677ff;
}

.footer-btn.submit {
  background: #1677ff;
  color: #fff;
}

.footer-btn.submit:hover {
  background: #4096ff;
}
</style>
