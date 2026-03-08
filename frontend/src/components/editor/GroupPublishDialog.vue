<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Block, BlockType } from "../../types/block";
import { BLOCK_TYPE_CONFIGS } from "../../types/block";

const props = defineProps<{
  open: boolean;
  selectedBlocks: Block[];
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "publish", data: {
    title: string;
    description: string | null;
    styleTags: string[];
    blockType: string;
    isGroup: boolean;
    contentSnapshot: Record<string, unknown> | null;
    childrenSnapshot: Record<string, unknown>[] | null;
    regionName: string | null;
  }): void;
}>();

const title = ref("");
const description = ref("");
const tagInput = ref("");
const styleTags = ref<string[]>([]);
const regionName = ref("");
const publishError = ref("");

const isGroup = computed(() => props.selectedBlocks.length > 1);

const primaryType = computed(() => {
  if (props.selectedBlocks.length === 0) return "scenic";
  if (isGroup.value) return "group";
  return props.selectedBlocks[0].blockType;
});

const primaryConfig = computed(() => {
  if (isGroup.value) {
    return { icon: "📦", label: "组合模板", color: "#7c5cff" };
  }
  return BLOCK_TYPE_CONFIGS[primaryType.value as BlockType] ?? BLOCK_TYPE_CONFIGS.scenic;
});

watch(() => props.open, (val) => {
  if (val && props.selectedBlocks.length > 0) {
    title.value = isGroup.value
      ? `${props.selectedBlocks[0].title} 等${props.selectedBlocks.length}项`
      : props.selectedBlocks[0].title;
    description.value = "";
    styleTags.value = [];
    tagInput.value = "";
    regionName.value = "";
    publishError.value = "";
  }
});

function addTag() {
  const tag = tagInput.value.trim();
  if (tag && !styleTags.value.includes(tag) && styleTags.value.length < 10) {
    styleTags.value.push(tag);
    tagInput.value = "";
  }
}

function removeTag(tag: string) {
  styleTags.value = styleTags.value.filter((t) => t !== tag);
}

function blockToSnapshot(block: Block): Record<string, unknown> {
  return {
    block_type: block.blockType,
    title: block.title,
    duration_minutes: block.durationMinutes,
    cost: block.cost,
    tips: block.tips,
    address: block.address,
    photos: block.photos,
    type_data: block.typeData,
    is_container: block.isContainer,
  };
}

function handlePublish() {
  if (!title.value.trim()) {
    publishError.value = "请输入模板名称";
    return;
  }
  if (props.selectedBlocks.length === 0) {
    publishError.value = "请选择至少一个块";
    return;
  }

  const data = {
    title: title.value.trim(),
    description: description.value.trim() || null,
    styleTags: styleTags.value,
    blockType: isGroup.value ? "group" : props.selectedBlocks[0].blockType,
    isGroup: isGroup.value,
    contentSnapshot: isGroup.value ? null : blockToSnapshot(props.selectedBlocks[0]),
    childrenSnapshot: isGroup.value ? props.selectedBlocks.map(blockToSnapshot) : null,
    regionName: regionName.value.trim() || null,
  };

  emit("publish", data);
}

function getBlockConfig(type: string) {
  return BLOCK_TYPE_CONFIGS[type as BlockType] ?? BLOCK_TYPE_CONFIGS.scenic;
}
</script>

<template>
  <transition name="modal">
    <div v-if="open" class="group-publish-overlay">
      <div class="group-publish-backdrop" @click="emit('close')" />
      <div class="group-publish-dialog">
        <div class="dialog-header">
          <span class="dialog-icon">{{ primaryConfig.icon }}</span>
          <h3 class="dialog-title">发布{{ isGroup ? '组合' : '' }}模板到社区</h3>
          <button class="dialog-close" @click="emit('close')">✕</button>
        </div>

        <div class="dialog-body">
          <!-- Preview of selected blocks -->
          <div class="selected-preview">
            <div class="selected-label">已选择 {{ selectedBlocks.length }} 个块</div>
            <div class="selected-list">
              <div
                v-for="block in selectedBlocks"
                :key="block.id"
                class="selected-chip"
                :style="{ '--sc-color': getBlockConfig(block.blockType).color }"
              >
                <span>{{ getBlockConfig(block.blockType).icon }}</span>
                <span>{{ block.title }}</span>
              </div>
            </div>
          </div>

          <!-- Form -->
          <div class="field-group">
            <label class="field-label">模板名称 *</label>
            <input v-model="title" class="field-input" placeholder="如：故宫三小时精华路线" />
          </div>

          <div class="field-group">
            <label class="field-label">描述</label>
            <textarea v-model="description" class="field-textarea" rows="3" placeholder="简要描述这个模板的特色..." />
          </div>

          <div class="field-group">
            <label class="field-label">标签</label>
            <div class="tag-input-row">
              <input
                v-model="tagInput"
                class="field-input tag-input"
                placeholder="输入标签后按回车"
                @keydown.enter.prevent="addTag"
              />
              <button class="tag-add-btn" @click="addTag">+</button>
            </div>
            <div v-if="styleTags.length" class="tag-list">
              <span v-for="tag in styleTags" :key="tag" class="tag-item">
                {{ tag }}
                <button class="tag-remove" @click="removeTag(tag)">✕</button>
              </span>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">地区</label>
            <input v-model="regionName" class="field-input" placeholder="如：北京·东城" />
          </div>

          <div v-if="publishError" class="publish-error">{{ publishError }}</div>
        </div>

        <div class="dialog-footer">
          <button class="btn-cancel" @click="emit('close')">取消</button>
          <button class="btn-publish" :style="{ background: primaryConfig.color }" @click="handlePublish">
            🚀 发布到社区
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.group-publish-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.group-publish-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(4px);
}
.group-publish-dialog {
  position: relative;
  width: 480px;
  max-width: 90vw;
  max-height: 85vh;
  background: var(--surface-2, #1e1e2e);
  border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 22px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.dialog-icon { font-size: 22px; }
.dialog-title {
  flex: 1;
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary, #e8e8e8);
}
.dialog-close {
  background: none;
  border: none;
  color: var(--text-secondary, #a0a0a0);
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}
.dialog-close:hover { background: rgba(255,255,255,0.08); }

.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selected-preview {
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.06);
}
.selected-label {
  font-size: 12px;
  color: var(--text-secondary, #a0a0a0);
  margin-bottom: 8px;
}
.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.selected-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
  border-left: 3px solid var(--sc-color);
  font-size: 13px;
  color: var(--text-primary, #e8e8e8);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.field-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary, #a0a0a0);
}
.field-input, .field-textarea {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 14px;
  color: var(--text-primary, #e8e8e8);
}
.field-input:focus, .field-textarea:focus {
  outline: none;
  border-color: rgba(255,255,255,0.2);
}
.field-textarea {
  resize: vertical;
  font-family: inherit;
}

.tag-input-row {
  display: flex;
  gap: 6px;
}
.tag-input { flex: 1; }
.tag-add-btn {
  padding: 0 14px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-primary, #e8e8e8);
  font-size: 16px;
  cursor: pointer;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.tag-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(124,92,255,0.12);
  border-radius: 6px;
  font-size: 12px;
  color: var(--accent, #7c5cff);
}
.tag-remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 10px;
  padding: 0 2px;
  opacity: 0.7;
}
.tag-remove:hover { opacity: 1; }

.publish-error {
  font-size: 13px;
  color: #e06b6b;
  padding: 6px 10px;
  background: rgba(224,107,107,0.1);
  border-radius: 6px;
}

.dialog-footer {
  display: flex;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.btn-cancel, .btn-publish {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-cancel {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: var(--text-secondary, #a0a0a0);
}
.btn-publish {
  border: none;
  color: #fff;
}
.btn-publish:hover, .btn-cancel:hover { opacity: 0.85; }

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
