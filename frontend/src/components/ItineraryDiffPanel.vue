<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { ItineraryDiffActionInput, ItineraryDiffResponse } from "../api";

type DiffStatusFilter = "all" | "pending" | "applied" | "rolled_back" | "ignored" | "read";

type ActionEventPayload = ItineraryDiffActionInput & {
  item_key?: string;
  field?: string;
  before?: unknown;
  after?: unknown;
  current?: Record<string, unknown>;
  source?: Record<string, unknown>;
};

type TimelineRow = {
  diffKey: string;
  diffType: "added" | "removed" | "modified";
  itemKey: string;
  dayIndex: number;
  sortOrder: number;
  nodeLabel: string;
  title: string;
  field?: string;
  before?: unknown;
  after?: unknown;
  current?: Record<string, unknown>;
  source?: Record<string, unknown>;
  hiddenByDefault?: boolean;
};

type DraftItemLite = {
  dayIndex: number;
  sortOrder: number;
  poi: {
    name?: string | null;
  };
};

const props = defineProps<{
  open: boolean;
  loading: boolean;
  error: string;
  diff: ItineraryDiffResponse | null;
  activeDay: number;
  queuedCount: number;
  submitPending: boolean;
  submitError: string;
  submitWarnings: string[];
  items: DraftItemLite[];
}>();

const emit = defineEmits<{
  (e: "jump-to-key", itemKey: string): void;
  (e: "stage-action", payload: ActionEventPayload): void;
  (e: "submit-actions"): void;
}>();

const META_FIELD_LABELS: Record<string, string> = {
  title: "行程标题",
  destination: "目的地",
  days: "行程天数",
  status: "行程状态",
  visibility: "可见范围",
  cover_image_url: "封面图片",
  start_date: "开始日期"
};

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_progress: "进行中",
  published: "已发布"
};

const VISIBILITY_LABELS: Record<string, string> = {
  private: "仅自己可见",
  followers: "关注者可见",
  public: "公开可见"
};

const ITEM_FIELD_LABELS: Record<string, string> = {
  day_index: "天数",
  sort_order: "站点顺序",
  poi_id: "POI ID",
  poi_name: "POI 名称",
  poi_type: "POI 类型",
  longitude: "经度",
  latitude: "纬度",
  address: "地址",
  opening_hours: "营业时间",
  ticket_price: "门票",
  start_time: "开始时间",
  duration_minutes: "停留时长",
  cost: "预算",
  tips: "备注"
};

const statusFilter = ref<DiffStatusFilter>("all");
const expandedDays = ref<Set<number>>(new Set());
const showReferenceTimeFields = ref(false);
const localActionStatuses = ref<Record<string, string>>({});

watch(
  () => props.diff?.source_snapshot_id,
  () => {
    localActionStatuses.value = {};
    expandedDays.value = new Set([props.activeDay || 1]);
    statusFilter.value = "all";
  }
);

watch(
  () => props.activeDay,
  (value) => {
    if (!value) return;
    expandedDays.value.add(value);
  }
);

function parseItemKey(key: string): { dayIndex: number; sortOrder: number } {
  const match = key.match(/^d(\d+)-s(\d+)$/);
  if (!match) {
    return { dayIndex: 999, sortOrder: 999 };
  }
  return { dayIndex: Number(match[1]), sortOrder: Number(match[2]) };
}

function formatMetaFieldLabel(field: string): string {
  return META_FIELD_LABELS[field] ?? `其他信息（${field}）`;
}

function isBlank(value: unknown): boolean {
  return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
}

function formatMetaValue(field: string, value: unknown): string {
  if (isBlank(value)) {
    return "未设置";
  }
  if (field === "status" && typeof value === "string") {
    return STATUS_LABELS[value] ?? value;
  }
  if (field === "visibility" && typeof value === "string") {
    return VISIBILITY_LABELS[value] ?? value;
  }
  if (field === "cover_image_url") {
    return "已设置封面链接";
  }
  if (field === "days" && typeof value === "number") {
    return `${value} 天`;
  }
  return String(value);
}

function formatItemFieldLabel(field: string): string {
  return ITEM_FIELD_LABELS[field] ?? `其他信息（${field}）`;
}

function formatItemValue(field: string, value: unknown): string {
  if (isBlank(value)) {
    return "未设置";
  }
  if (field === "duration_minutes") {
    const num = Number(value);
    return Number.isFinite(num) ? `${num} 分钟` : String(value);
  }
  if (field === "cost" || field === "ticket_price") {
    const num = Number(value);
    return Number.isFinite(num) ? `¥${num}` : String(value);
  }
  if (field === "day_index" || field === "sort_order") {
    const num = Number(value);
    return Number.isFinite(num) ? String(Math.floor(num)) : String(value);
  }
  if (field === "start_time") {
    const text = String(value);
    return text.length >= 5 ? text.slice(0, 5) : text;
  }
  return String(value);
}

function itemLabel(dayIndex: number, sortOrder: number, poiName: string | null | undefined): string {
  const safeName = poiName && poiName.trim() ? poiName : "未命名节点";
  return `Day ${dayIndex} · ${safeName}（第${sortOrder}站）`;
}

const metadataRows = computed(() => {
  if (!props.diff) {
    return [] as Array<{
      diffKey: string;
      field: string;
      label: string;
      before: unknown;
      after: unknown;
    }>;
  }
  return props.diff.metadata_diffs.map((entry) => ({
    diffKey: `meta:${entry.field}`,
    field: entry.field,
    label: formatMetaFieldLabel(entry.field),
    before: entry.before,
    after: entry.after
  }));
});

const itemNameByKey = computed(() => {
  const map = new Map<string, string>();
  for (const item of props.items || []) {
    const key = `d${item.dayIndex}-s${item.sortOrder}`;
    const name = String(item.poi?.name || "").trim();
    if (name) {
      map.set(key, name);
    }
  }
  return map;
});

const timelineRows = computed<TimelineRow[]>(() => {
  if (!props.diff) return [];
  const rows: TimelineRow[] = [];

  for (const item of props.diff.added_items) {
    const parsed = parseItemKey(item.key);
    rows.push({
      diffKey: `added:${item.key}`,
      diffType: "added",
      itemKey: item.key,
      dayIndex: parsed.dayIndex,
      sortOrder: parsed.sortOrder,
      nodeLabel: itemLabel(parsed.dayIndex, parsed.sortOrder, String(item.current.poi_name || itemNameByKey.value.get(item.key) || "")),
      title: "新增节点",
      current: item.current
    });
  }

  for (const item of props.diff.removed_items) {
    const parsed = parseItemKey(item.key);
    rows.push({
      diffKey: `removed:${item.key}`,
      diffType: "removed",
      itemKey: item.key,
      dayIndex: parsed.dayIndex,
      sortOrder: parsed.sortOrder,
      nodeLabel: itemLabel(parsed.dayIndex, parsed.sortOrder, String(item.source.poi_name || itemNameByKey.value.get(item.key) || "")),
      title: "删除节点",
      source: item.source
    });
  }

  for (const item of props.diff.modified_items) {
    const parsed = parseItemKey(item.key);
    const poiField = item.fields.find((field) => field.field === "poi_name");
    const poiName = String(poiField?.after ?? poiField?.before ?? itemNameByKey.value.get(item.key) ?? "");
    for (const field of item.fields) {
      rows.push({
        diffKey: `modified:${item.key}:${field.field}`,
        diffType: "modified",
        itemKey: item.key,
        dayIndex: parsed.dayIndex,
        sortOrder: parsed.sortOrder,
        nodeLabel: itemLabel(parsed.dayIndex, parsed.sortOrder, poiName),
        title: `修改字段：${formatItemFieldLabel(field.field)}`,
        field: field.field,
        before: field.before,
        after: field.after,
        hiddenByDefault: field.field === "start_time"
      });
    }
  }

  return rows.sort((a, b) => a.dayIndex - b.dayIndex || a.sortOrder - b.sortOrder || a.diffKey.localeCompare(b.diffKey));
});

const timelineRowsByDay = computed(() => {
  const map = new Map<number, TimelineRow[]>();
  for (const row of timelineRows.value) {
    if (!map.has(row.dayIndex)) map.set(row.dayIndex, []);
    map.get(row.dayIndex)!.push(row);
  }
  return Array.from(map.entries())
    .map(([dayIndex, rows]) => ({ dayIndex, rows }))
    .sort((a, b) => a.dayIndex - b.dayIndex);
});

const criticalRows = computed(() => {
  const out: Array<{ key: string; text: string }> = [];
  for (const row of timelineRows.value) {
    if (row.diffType === "removed") {
      out.push({ key: row.diffKey, text: `${row.nodeLabel}：删除节点` });
      continue;
    }
    if (row.diffType !== "modified") continue;

    if (row.field === "duration_minutes") {
      if (isBlank(row.before) || isBlank(row.after)) {
        out.push({ key: row.diffKey, text: `${row.nodeLabel}：停留时长从“未设置”变更` });
        continue;
      }
      const before = Number(row.before);
      const after = Number(row.after);
      if (!Number.isFinite(before) || !Number.isFinite(after)) continue;
      const denom = Math.abs(before) < 1e-6 ? 1 : Math.abs(before);
      const ratio = Math.abs(after - before) / denom;
      if (ratio > 0.3) {
        out.push({ key: row.diffKey, text: `${row.nodeLabel}：停留时长变化超过 30%` });
      }
    }

    if (row.field === "cost") {
      if (isBlank(row.before) || isBlank(row.after)) continue;
      const before = Number(row.before);
      const after = Number(row.after);
      if (!Number.isFinite(before) || !Number.isFinite(after)) continue;
      const denom = Math.abs(before) < 1e-6 ? 1 : Math.abs(before);
      const ratio = Math.abs(after - before) / denom;
      if (ratio > 0.3) {
        out.push({ key: row.diffKey, text: `${row.nodeLabel}：预算变化超过 30%` });
      }
    }
  }

  for (const row of metadataRows.value) {
    if (["status", "visibility", "days"].includes(row.field)) {
      out.push({
        key: row.diffKey,
        text: `${row.label}：${formatMetaValue(row.field, row.before)} → ${formatMetaValue(row.field, row.after)}`
      });
    }
  }
  return out.slice(0, 5);
});

function statusFor(diffKey: string): string {
  return localActionStatuses.value[diffKey] || props.diff?.action_statuses?.[diffKey] || "pending";
}

function statusLabel(value: string): string {
  if (value === "applied") return "已处理";
  if (value === "rolled_back") return "已回滚";
  if (value === "ignored") return "已忽略";
  if (value === "read") return "已读";
  return "未处理";
}

function statusClass(value: string): string {
  if (value === "applied") return "state-applied";
  if (value === "rolled_back") return "state-rollback";
  if (value === "ignored") return "state-ignored";
  if (value === "read") return "state-read";
  return "state-pending";
}

function passesFilter(diffKey: string): boolean {
  if (statusFilter.value === "all") return true;
  return statusFor(diffKey) === statusFilter.value;
}

function toggleDay(dayIndex: number) {
  if (expandedDays.value.has(dayIndex)) {
    expandedDays.value.delete(dayIndex);
    return;
  }
  expandedDays.value.add(dayIndex);
}

function stageAction(payload: ActionEventPayload) {
  localActionStatuses.value[payload.diff_key] = payload.action;
  emit("stage-action", payload);
}

function handleIgnore(payload: Omit<ActionEventPayload, "action" | "reason">) {
  const reason = window.prompt("请输入忽略原因（必填）", "");
  if (!reason || !reason.trim()) return;
  stageAction({
    ...payload,
    action: "ignored",
    reason: reason.trim()
  });
}
</script>

<template>
  <section v-if="open" class="panel-card diff-panel">
    <div class="diff-panel-head">
      <h3>修改对比</h3>
      <div class="diff-panel-actions">
        <span class="subtle">待提交动作：{{ queuedCount }}</span>
        <button class="btn primary" :disabled="submitPending || queuedCount === 0" @click="emit('submit-actions')">
          {{ submitPending ? "提交中..." : "提交动作" }}
        </button>
      </div>
    </div>

    <p class="subtle">阅读顺序：关键摘要 → 时间轴变更（按 Day）→ 行程元信息</p>

    <p v-if="diff?.stale_warning" class="error">当前差异基于旧快照，源行程已有更新。你仍可提交动作，但建议先刷新对比。</p>
    <p v-for="warning in submitWarnings" :key="warning" class="error">{{ warning }}</p>
    <p v-if="submitError" class="error">{{ submitError }}</p>

    <p v-if="loading" class="subtle">正在加载差异数据...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else-if="diff">
      <div class="diff-summary">
        <span class="diff-badge added">新增 {{ diff.summary.added }}</span>
        <span class="diff-badge removed">删除 {{ diff.summary.removed }}</span>
        <span class="diff-badge modified">修改 {{ diff.summary.modified }}</span>
      </div>

      <div class="diff-section">
        <h4>关键变更（最多 5 条）</h4>
        <p v-if="criticalRows.length === 0" class="subtle">当前无关键变更。</p>
        <ul v-else class="diff-critical-list">
          <li v-for="row in criticalRows" :key="row.key">{{ row.text }}</li>
        </ul>
      </div>

      <div class="diff-section">
        <div class="diff-filter-row">
          <h4>时间轴变更</h4>
          <select v-model="statusFilter" class="input diff-filter">
            <option value="all">全部状态</option>
            <option value="pending">未处理</option>
            <option value="applied">已处理</option>
            <option value="rolled_back">已回滚</option>
            <option value="ignored">已忽略</option>
            <option value="read">已读</option>
          </select>
        </div>

        <article v-for="group in timelineRowsByDay" :key="`day-${group.dayIndex}`" class="diff-day-group">
          <button class="btn ghost diff-day-toggle" @click="toggleDay(group.dayIndex)">
            Day {{ group.dayIndex }}（{{ group.rows.length }} 条）{{ expandedDays.has(group.dayIndex) ? "收起" : "展开" }}
          </button>

          <div v-if="expandedDays.has(group.dayIndex)" class="diff-day-list">
            <article
              v-for="row in group.rows"
              :key="row.diffKey"
              v-show="passesFilter(row.diffKey) && (!row.hiddenByDefault || showReferenceTimeFields)"
              class="diff-line"
              :class="row.diffType"
            >
              <p class="diff-field"><strong>{{ row.nodeLabel }}</strong></p>
              <p class="diff-change">
                {{ row.title }}
                <template v-if="row.field">：{{ formatItemValue(row.field, row.before) }} → {{ formatItemValue(row.field, row.after) }}</template>
              </p>
              <p class="diff-state">
                <span class="diff-state-tag" :class="statusClass(statusFor(row.diffKey))">{{ statusLabel(statusFor(row.diffKey)) }}</span>
              </p>
              <div class="diff-row-actions">
                <button class="btn ghost" @click="emit('jump-to-key', row.itemKey)">定位</button>
                <button
                  class="btn"
                  @click="stageAction({ diff_key: row.diffKey, diff_type: row.diffType, action: 'applied', item_key: row.itemKey, field: row.field, before: row.before, after: row.after, current: row.current, source: row.source })"
                >
                  应用
                </button>
                <button
                  class="btn"
                  @click="stageAction({ diff_key: row.diffKey, diff_type: row.diffType, action: 'rolled_back', item_key: row.itemKey, field: row.field, before: row.before, after: row.after, current: row.current, source: row.source })"
                >
                  回滚
                </button>
                <button
                  class="btn"
                  @click="handleIgnore({ diff_key: row.diffKey, diff_type: row.diffType, item_key: row.itemKey, field: row.field, before: row.before, after: row.after, current: row.current, source: row.source })"
                >
                  忽略
                </button>
              </div>
            </article>
          </div>
        </article>

        <button class="btn ghost" @click="showReferenceTimeFields = !showReferenceTimeFields">
          {{ showReferenceTimeFields ? "隐藏参考变更（开始时间）" : "展开参考变更（开始时间）" }}
        </button>
      </div>

      <div class="diff-section">
        <h4>行程元信息</h4>
        <article v-for="row in metadataRows" :key="row.diffKey" v-show="passesFilter(row.diffKey)" class="diff-line modified">
          <p class="diff-field">{{ row.label }}</p>
          <p class="diff-change">
            <span class="diff-before">{{ formatMetaValue(row.field, row.before) }}</span>
            <span class="diff-arrow">→</span>
            <span class="diff-after">{{ formatMetaValue(row.field, row.after) }}</span>
          </p>
          <p class="diff-state">
            <span class="diff-state-tag" :class="statusClass(statusFor(row.diffKey))">{{ statusLabel(statusFor(row.diffKey)) }}</span>
          </p>
          <div class="diff-row-actions">
            <button class="btn" @click="stageAction({ diff_key: row.diffKey, diff_type: 'metadata', action: 'applied', field: row.field, before: row.before, after: row.after })">应用</button>
            <button class="btn" @click="stageAction({ diff_key: row.diffKey, diff_type: 'metadata', action: 'rolled_back', field: row.field, before: row.before, after: row.after })">回滚</button>
            <button class="btn" @click="handleIgnore({ diff_key: row.diffKey, diff_type: 'metadata', field: row.field, before: row.before, after: row.after })">忽略</button>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
.diff-panel {
  --text-primary: #e8edf8;
  --text-secondary: #a7b3ca;
  --border-subtle: rgba(255, 255, 255, 0.14);
  --surface: #161b2c;
  --surface-soft: #1c2438;
  --primary: #4cc3ff;
  --success: #6ee7a8;
  --warning: #ffd27d;
  --danger: #ff9c9c;

  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--text-primary);
}

.panel-card {
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px;
}

.diff-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.diff-panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subtle {
  margin: 0;
  color: var(--text-secondary);
}

.error {
  margin: 0;
  color: var(--danger);
}

.input {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 7px 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary);
}

.btn {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
  cursor: pointer;
}

.btn.primary {
  background: #2f6df6;
  border-color: #2f6df6;
}

.btn.ghost {
  background: rgba(255, 255, 255, 0.04);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.diff-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.diff-badge {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
}

.diff-badge.added {
  background: rgba(77, 211, 142, 0.18);
  color: #8ef0bd;
}

.diff-badge.removed {
  background: rgba(255, 140, 140, 0.18);
  color: #ffc1c1;
}

.diff-badge.modified {
  background: rgba(255, 210, 125, 0.16);
  color: #ffe1a7;
}

.diff-section {
  border-top: 1px dashed var(--border-subtle);
  padding-top: 10px;
}

.diff-section h4 {
  margin: 0;
  font-size: 15px;
}

.diff-filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.diff-filter {
  max-width: 180px;
}

.diff-day-group {
  margin-top: 10px;
}

.diff-day-toggle {
  width: 100%;
  text-align: left;
}

.diff-day-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.diff-line {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 8px 10px;
  background: var(--surface-soft);
}

.diff-line.added {
  border-color: rgba(77, 211, 142, 0.45);
  background: rgba(77, 211, 142, 0.12);
}

.diff-line.removed {
  border-color: rgba(255, 140, 140, 0.42);
  background: rgba(255, 140, 140, 0.12);
}

.diff-line.modified {
  border-color: rgba(255, 210, 125, 0.45);
  background: rgba(255, 210, 125, 0.1);
}

.diff-field {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.diff-change {
  margin: 4px 0 0;
  word-break: break-word;
}

.diff-state {
  margin: 6px 0 0;
}

.diff-state-tag {
  display: inline-block;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  border: 1px solid var(--border-subtle);
  background: rgba(255, 255, 255, 0.05);
}

.diff-state-tag.state-pending {
  color: var(--text-secondary);
}

.diff-state-tag.state-applied {
  color: var(--success);
  border-color: rgba(110, 231, 168, 0.5);
  background: rgba(110, 231, 168, 0.14);
}

.diff-state-tag.state-rollback {
  color: var(--warning);
  border-color: rgba(255, 210, 125, 0.5);
  background: rgba(255, 210, 125, 0.14);
}

.diff-state-tag.state-ignored {
  color: var(--primary);
  border-color: rgba(76, 195, 255, 0.5);
  background: rgba(76, 195, 255, 0.14);
}

.diff-state-tag.state-read {
  color: var(--text-secondary);
}

.diff-row-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.diff-critical-list {
  margin: 10px 0 0;
  padding-left: 20px;
}

.diff-before {
  color: #ffb4b4;
}

.diff-after {
  color: #9af1c8;
}

.diff-arrow {
  margin: 0 6px;
  color: var(--text-secondary);
}
</style>
