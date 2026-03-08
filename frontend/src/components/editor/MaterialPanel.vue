<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { TemplateApiResponse } from "../../api";
import { fetchTemplates } from "../../api";
import type { BlockType } from "../../types/block";
import { BLOCK_TYPE_CONFIGS } from "../../types/block";

defineProps<{
  token: string;
}>();

const emit = defineEmits<{
  (e: "drag-start", template: TemplateApiResponse): void;
  (e: "select-template", template: TemplateApiResponse): void;
}>();

const activeTab = ref<"elements" | "combinations" | "favorites">("elements");
const searchQuery = ref("");
const filterType = ref<BlockType | "">("");
const sortBy = ref("hot");
const templates = ref<TemplateApiResponse[]>([]);
const loading = ref(false);
const total = ref(0);

const allTypes = computed(() => Object.values(BLOCK_TYPE_CONFIGS));

async function loadTemplates() {
  loading.value = true;
  try {
    const params: Record<string, string | number> = {
      sort_by: sortBy.value,
      offset: 0,
      limit: 50,
    };
    if (filterType.value) params.block_type = filterType.value;
    if (searchQuery.value.trim()) params.search = searchQuery.value.trim();
    if (activeTab.value === "combinations") params.block_type = "group";

    const result = await fetchTemplates(params);
    templates.value = result.items;
    total.value = result.total;
  } catch (e) {
    console.error("Failed to fetch templates:", e);
  } finally {
    loading.value = false;
  }
}

watch([activeTab, filterType, sortBy], () => loadTemplates(), { immediate: true });

function onSearch() {
  loadTemplates();
}

function handleDragStart(event: DragEvent, template: TemplateApiResponse) {
  if (!event.dataTransfer) return;
  event.dataTransfer.setData("application/json", JSON.stringify(template));
  event.dataTransfer.effectAllowed = "copy";
  emit("drag-start", template);
}

function getTypeConfig(type: string) {
  return BLOCK_TYPE_CONFIGS[type as BlockType] ?? BLOCK_TYPE_CONFIGS.scenic;
}

function formatRating(rating: number | null): string {
  return rating != null ? rating.toFixed(1) : "-";
}
</script>

<template>
  <div class="material-panel">
    <!-- Tabs -->
    <div class="panel-tabs">
      <button
        v-for="tab in [
          { key: 'elements', label: '🧩 元素' },
          { key: 'combinations', label: '📦 组合' },
          { key: 'favorites', label: '⭐ 收藏' },
        ]"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key as typeof activeTab"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Search -->
    <div class="panel-search">
      <input
        v-model="searchQuery"
        class="search-input"
        placeholder="搜索景点/模板..."
        @keyup.enter="onSearch"
      />
    </div>

    <!-- Type filters -->
    <div v-if="activeTab === 'elements'" class="type-filters">
      <button
        class="filter-pill"
        :class="{ active: filterType === '' }"
        @click="filterType = ''"
      >
        全部
      </button>
      <button
        v-for="t in allTypes"
        :key="t.type"
        class="filter-pill"
        :class="{ active: filterType === t.type }"
        :style="{ '--pill-color': t.color }"
        @click="filterType = filterType === t.type ? '' : t.type"
      >
        {{ t.icon }} {{ t.label }}
      </button>
    </div>

    <!-- Sort -->
    <div v-if="activeTab !== 'favorites'" class="sort-bar">
      <select v-model="sortBy" class="sort-select">
        <option value="hot">🔥 热门</option>
        <option value="newest">🕐 最新</option>
        <option value="rating">⭐ 评分</option>
      </select>
      <span class="result-count">{{ total }} 个结果</span>
    </div>

    <!-- Template list -->
    <div class="template-list">
      <div v-if="loading" class="loading-indicator">加载中...</div>
      <div v-else-if="templates.length === 0" class="empty-state">
        暂无模板
      </div>
      <div
        v-for="t in templates"
        :key="t.id"
        class="template-card"
        :style="{ '--tc-color': getTypeConfig(t.block_type).color }"
        draggable="true"
        @dragstart="handleDragStart($event, t)"
        @click="emit('select-template', t)"
      >
        <div class="template-card__left-bar" />
        <div class="template-card__body">
          <div class="template-card__header">
            <span class="template-card__icon">{{ getTypeConfig(t.block_type).icon }}</span>
            <span class="template-card__title">{{ t.title }}</span>
          </div>
          <div class="template-card__meta">
            <span v-if="t.author_nickname" class="template-card__author">{{ t.author_nickname }}</span>
            <span class="template-card__stat">⭐ {{ formatRating(t.rating_avg) }}</span>
            <span class="template-card__stat">🔄 {{ t.fork_count }}</span>
          </div>
          <div v-if="t.style_tags?.length" class="template-card__tags">
            <span v-for="tag in t.style_tags.slice(0, 3)" :key="tag" class="tag-chip">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.material-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-1, #181825);
  border-right: 1px solid rgba(255,255,255,0.06);
  overflow: hidden;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.tab-btn {
  flex: 1;
  padding: 10px 6px;
  background: none;
  border: none;
  color: var(--text-secondary, #a0a0a0);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  border-bottom: 2px solid transparent;
}
.tab-btn.active {
  color: var(--text-primary, #e8e8e8);
  border-bottom-color: var(--accent, #7c5cff);
}
.tab-btn:hover:not(.active) {
  background: rgba(255,255,255,0.04);
}

.panel-search {
  padding: 10px;
}
.search-input {
  width: 100%;
  padding: 8px 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-primary, #e8e8e8);
  font-size: 13px;
  box-sizing: border-box;
}
.search-input:focus {
  outline: none;
  border-color: rgba(255,255,255,0.2);
}

.type-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 0 10px 8px;
}
.filter-pill {
  padding: 4px 8px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  color: var(--text-secondary, #a0a0a0);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-pill.active {
  border-color: var(--pill-color, var(--accent));
  color: var(--pill-color, var(--accent));
  background: color-mix(in srgb, var(--pill-color, var(--accent)) 12%, transparent);
}

.sort-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px 8px;
}
.sort-select {
  padding: 4px 8px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: var(--text-primary, #e8e8e8);
  font-size: 12px;
}
.result-count {
  font-size: 11px;
  color: var(--text-secondary, #a0a0a0);
}

.template-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.loading-indicator,
.empty-state {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary, #a0a0a0);
  font-size: 13px;
}

.template-card {
  display: flex;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255,255,255,0.03);
  cursor: grab;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.template-card:hover {
  border-color: rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.05);
}
.template-card:active {
  cursor: grabbing;
}

.template-card__left-bar {
  width: 3px;
  background: var(--tc-color);
}

.template-card__body {
  flex: 1;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.template-card__header {
  display: flex;
  align-items: center;
  gap: 5px;
}

.template-card__icon {
  font-size: 14px;
}

.template-card__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #e8e8e8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-card__meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary, #a0a0a0);
}

.template-card__tags {
  display: flex;
  gap: 4px;
}
.tag-chip {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 6px;
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary, #a0a0a0);
}
</style>
