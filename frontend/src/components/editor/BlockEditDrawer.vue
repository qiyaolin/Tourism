<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Block, BlockType } from "../../types/block";
import { BLOCK_TYPE_CONFIGS } from "../../types/block";

const props = defineProps<{
  block: Block | null;
  open: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "save", data: Record<string, unknown>): void;
}>();

// Local form state
const title = ref("");
const blockType = ref<BlockType>("scenic");
const durationMinutes = ref<string>("");
const cost = ref<string>("");
const tips = ref("");
const address = ref("");
const isContainer = ref(false);

// Type-specific fields
const typeFields = ref<Record<string, string>>({});

const config = computed(() => BLOCK_TYPE_CONFIGS[blockType.value]);
const allTypes = computed(() => Object.values(BLOCK_TYPE_CONFIGS));

watch(
  () => props.block,
  (block) => {
    if (!block) return;
    title.value = block.title;
    blockType.value = block.blockType;
    durationMinutes.value = block.durationMinutes != null ? String(block.durationMinutes) : "";
    cost.value = block.cost != null ? String(block.cost) : "";
    tips.value = block.tips || "";
    address.value = block.address || "";
    isContainer.value = block.isContainer;

    // Populate type-specific fields
    const td = block.typeData || {};
    typeFields.value = {};
    for (const key of config.value.fields) {
      const val = td[key];
      typeFields.value[key] = val != null ? String(val) : "";
    }
  },
  { immediate: true }
);

// Reset type fields when block type changes
watch(blockType, (newType) => {
  const newConfig = BLOCK_TYPE_CONFIGS[newType];
  const oldFields = { ...typeFields.value };
  typeFields.value = {};
  for (const key of newConfig.fields) {
    typeFields.value[key] = oldFields[key] || "";
  }
});

function getFieldLabel(key: string): string {
  const labels: Record<string, string> = {
    // Scenic
    opening_hours: "营业时间",
    ticket_price: "门票价格",
    highlights: "亮点",
    photo_spots: "拍照点",
    // Dining
    per_capita: "人均消费",
    cuisine_type: "菜系",
    recommended_dishes: "推荐菜品",
    reservation_info: "预约信息",
    // Lodging
    room_type: "房型",
    price_per_night: "每晚价格",
    check_in_time: "入住时间",
    check_out_time: "退房时间",
    // Transit
    from_title: "出发地",
    to_title: "目的地",
    method: "方式",
    line_info: "线路信息",
    distance_km: "距离(km)",
    // Note
    content_markdown: "内容",
    // Shopping
    shop_name: "店铺名",
    products: "推荐商品",
    business_hours: "营业时间",
    // Activity
    event_name: "活动名称",
    time_slot: "时间段",
    booking_method: "预约方式",
  };
  return labels[key] || key;
}

function handleSave() {
  const typeData: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(typeFields.value)) {
    if (val.trim()) typeData[key] = val.trim();
  }

  emit("save", {
    title: title.value,
    blockType: blockType.value,
    durationMinutes: durationMinutes.value ? Number(durationMinutes.value) : null,
    cost: cost.value ? Number(cost.value) : null,
    tips: tips.value || null,
    address: address.value || null,
    isContainer: isContainer.value,
    typeData: Object.keys(typeData).length > 0 ? typeData : null,
  });
}
</script>

<template>
  <transition name="drawer">
    <div v-if="open" class="block-edit-drawer">
      <div class="drawer__overlay" @click="emit('close')" />
      <div class="drawer__panel">
        <div class="drawer__header">
          <span class="drawer__icon">{{ config.icon }}</span>
          <h3 class="drawer__title">{{ block ? '编辑块' : '新建块' }}</h3>
          <button class="drawer__close" @click="emit('close')">✕</button>
        </div>

        <div class="drawer__body">
          <!-- Block Type Selector -->
          <div class="field-group">
            <label class="field-label">类型</label>
            <div class="type-selector">
              <button
                v-for="t in allTypes"
                :key="t.type"
                class="type-btn"
                :class="{ active: blockType === t.type }"
                :style="{ '--btn-color': t.color }"
                @click="blockType = t.type"
              >
                <span>{{ t.icon }}</span>
                <span>{{ t.label }}</span>
              </button>
            </div>
          </div>

          <!-- Common fields -->
          <div class="field-group">
            <label class="field-label">名称</label>
            <input v-model="title" class="field-input" placeholder="输入名称" />
          </div>

          <div class="field-row">
            <div class="field-group flex-1">
              <label class="field-label">时长 (分钟)</label>
              <input v-model="durationMinutes" class="field-input" type="number" placeholder="60" />
            </div>
            <div class="field-group flex-1">
              <label class="field-label">费用 (¥)</label>
              <input v-model="cost" class="field-input" type="number" placeholder="0" />
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">地址</label>
            <input v-model="address" class="field-input" placeholder="地址" />
          </div>

          <div class="field-group">
            <label class="field-label">备注</label>
            <textarea v-model="tips" class="field-textarea" rows="2" placeholder="小贴士..." />
          </div>

          <div class="field-group">
            <label class="field-check">
              <input v-model="isContainer" type="checkbox" />
              <span>作为容器（可包含子块）</span>
            </label>
          </div>

          <!-- Type-specific fields -->
          <div v-if="config.fields.length" class="type-fields">
            <div class="type-fields__header">
              <span class="type-fields__icon" :style="{ color: config.color }">{{ config.icon }}</span>
              <span>{{ config.label }}专属字段</span>
            </div>
            <div v-for="fieldKey in config.fields" :key="fieldKey" class="field-group">
              <label class="field-label">{{ getFieldLabel(fieldKey) }}</label>
              <input
                v-if="fieldKey !== 'content_markdown'"
                v-model="typeFields[fieldKey]"
                class="field-input"
                :placeholder="getFieldLabel(fieldKey)"
              />
              <textarea
                v-else
                v-model="typeFields[fieldKey]"
                class="field-textarea"
                rows="4"
                placeholder="Markdown 内容..."
              />
            </div>
          </div>
        </div>

        <div class="drawer__footer">
          <button class="btn-cancel" @click="emit('close')">取消</button>
          <button class="btn-save" :style="{ background: config.color }" @click="handleSave">保存</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.block-edit-drawer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.4);
  backdrop-filter: blur(2px);
}

.drawer__panel {
  position: relative;
  width: 400px;
  max-width: 90vw;
  height: 100%;
  background: var(--surface-2, #1e1e2e);
  box-shadow: -4px 0 24px rgba(0,0,0,0.3);
  display: flex;
  flex-direction: column;
  z-index: 1;
}

.drawer__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.drawer__icon {
  font-size: 20px;
}

.drawer__title {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary, #e8e8e8);
}

.drawer__close {
  background: none;
  border: none;
  color: var(--text-secondary, #a0a0a0);
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}
.drawer__close:hover {
  background: rgba(255,255,255,0.08);
}

.drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.type-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.type-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
  color: var(--text-secondary, #a0a0a0);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.type-btn.active {
  border-color: var(--btn-color);
  background: color-mix(in srgb, var(--btn-color) 15%, transparent);
  color: var(--btn-color);
}
.type-btn:hover:not(.active) {
  background: rgba(255,255,255,0.08);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 12px;
  color: var(--text-secondary, #a0a0a0);
  font-weight: 500;
}

.field-input,
.field-textarea {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--text-primary, #e8e8e8);
  transition: border-color 0.15s;
}
.field-input:focus,
.field-textarea:focus {
  outline: none;
  border-color: rgba(255,255,255,0.25);
}

.field-textarea {
  resize: vertical;
  font-family: inherit;
}

.field-row {
  display: flex;
  gap: 12px;
}

.flex-1 {
  flex: 1;
}

.field-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary, #a0a0a0);
  cursor: pointer;
}

.type-fields {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.type-fields__header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #e8e8e8);
}

.drawer__footer {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid rgba(255,255,255,0.08);
}

.btn-cancel,
.btn-save {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-cancel {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: var(--text-secondary, #a0a0a0);
}
.btn-save {
  border: none;
  color: #fff;
}
.btn-save:hover,
.btn-cancel:hover {
  opacity: 0.85;
}

/* Drawer transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: all 0.3s ease;
}
.drawer-enter-active .drawer__panel,
.drawer-leave-active .drawer__panel {
  transition: transform 0.3s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .drawer__panel {
  transform: translateX(100%);
}
.drawer-leave-to .drawer__panel {
  transform: translateX(100%);
}
</style>
