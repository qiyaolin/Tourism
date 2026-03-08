<script setup lang="ts">
import { computed, ref } from "vue";

import type { Block, BlockDependency, BlockEdgeType } from "../../types/block";
import { BLOCK_TYPE_CONFIGS, DEFAULT_LANES } from "../../types/block";
import BlockCard from "./BlockCard.vue";
import BlockContainer from "./BlockContainer.vue";

const props = defineProps<{
  blocks: Block[];
  dependencies: BlockDependency[];
  days: number;
  activeDay: number;
  activeBlockId: string;
  lanes?: Array<{ lane_key: string; label: string; block_count: number; done_count: number }>;
}>();

const emit = defineEmits<{
  (e: "update:activeDay", day: number): void;
  (e: "select-block", block: Block): void;
  (e: "edit-block", block: Block): void;
  (e: "delete-block", block: Block): void;
  (e: "ungroup-block", block: Block): void;
  (e: "drop", data: { template: unknown; dayIndex: number; sortOrder: number; laneKey?: string }): void;
  (e: "move-block-layout", payload: { blockId: string; dayIndex: number; laneKey: string }): void;
  (e: "create-dependency", payload: { fromBlockId: string; toBlockId: string; edgeType: BlockEdgeType }): void;
}>();

const dragOver = ref<{ day: number; lane: string } | null>(null);
const linkSourceId = ref<string>("");
const laneFilter = ref<string>("all");

const dayTabs = computed(() => Array.from({ length: props.days }, (_, i) => i + 1));

const lanes = computed(() => {
  const result = new Map<string, { key: string; label: string }>();
  for (const lane of DEFAULT_LANES) {
    result.set(String(lane.key), { key: String(lane.key), label: lane.label });
  }
  for (const lane of props.lanes || []) {
    result.set(lane.lane_key, { key: lane.lane_key, label: lane.label });
  }
  for (const block of props.blocks) {
    if (!result.has(block.laneKey)) result.set(block.laneKey, { key: block.laneKey, label: block.laneKey });
  }
  return Array.from(result.values());
});

const visibleLanes = computed(() =>
  laneFilter.value === "all" ? lanes.value : lanes.value.filter((lane) => lane.key === laneFilter.value)
);

const topBlocks = computed(() => props.blocks.filter((b) => !b.parentBlockId));

const blockNameMap = computed(() => {
  const map: Record<string, string> = {};
  for (const block of props.blocks) map[block.id] = block.title;
  return map;
});

const dependencyPreview = computed(() => props.dependencies.slice(0, 6));

function blocksForLane(day: number, laneKey: string): Block[] {
  return topBlocks.value
    .filter((b) => b.dayIndex === day && b.laneKey === laneKey)
    .sort((a, b) => {
      const aStart = a.startMinute ?? Number.MAX_SAFE_INTEGER;
      const bStart = b.startMinute ?? Number.MAX_SAFE_INTEGER;
      if (aStart !== bStart) return aStart - bStart;
      return a.sortOrder - b.sortOrder;
    });
}

function dayBlockCount(day: number): number {
  return topBlocks.value.filter((b) => b.dayIndex === day).length;
}

function dayTotalDuration(day: number): number {
  return topBlocks.value
    .filter((b) => b.dayIndex === day)
    .reduce((sum, b) => sum + (b.durationMinutes || 0), 0);
}

function formatDuration(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h${m > 0 ? m + "m" : ""}` : `${m}m`;
}

function formatMinute(minute: number | null): string {
  if (minute == null || !Number.isFinite(minute)) return "--:--";
  const normalized = Math.max(0, Math.min(24 * 60, Math.floor(minute)));
  const h = String(Math.floor(normalized / 60)).padStart(2, "0");
  const m = String(normalized % 60).padStart(2, "0");
  return `${h}:${m}`;
}

function statusLabel(status: Block["status"]): string {
  const map: Record<Block["status"], string> = {
    draft: "草稿",
    ready: "就绪",
    running: "进行中",
    done: "完成",
    blocked: "阻塞",
  };
  return map[status] || "草稿";
}

function getBlockConfig(type: string) {
  return BLOCK_TYPE_CONFIGS[type as keyof typeof BLOCK_TYPE_CONFIGS] ?? BLOCK_TYPE_CONFIGS.scenic;
}

function handleDragOver(event: DragEvent, day: number, laneKey: string) {
  event.preventDefault();
  dragOver.value = { day, lane: laneKey };
}

function handleDragLeave() {
  dragOver.value = null;
}

function handleDrop(event: DragEvent, day: number, laneKey: string) {
  event.preventDefault();
  dragOver.value = null;

  const movePayloadRaw = event.dataTransfer?.getData("application/x-atlas-block");
  if (movePayloadRaw) {
    try {
      const payload = JSON.parse(movePayloadRaw) as { blockId: string };
      if (payload.blockId) {
        emit("move-block-layout", { blockId: payload.blockId, dayIndex: day, laneKey });
        return;
      }
    } catch {
      // ignore malformed drag payload
    }
  }

  const templateRaw = event.dataTransfer?.getData("application/json");
  if (!templateRaw) return;
  try {
    const template = JSON.parse(templateRaw);
    const nextOrder = blocksForLane(day, laneKey).length + 1;
    emit("drop", { template, dayIndex: day, sortOrder: nextOrder, laneKey });
  } catch {
    // ignore malformed template payload
  }
}

function onNodeDragStart(event: DragEvent, block: Block) {
  event.dataTransfer?.setData("application/x-atlas-block", JSON.stringify({ blockId: block.id }));
  event.dataTransfer?.setData("text/plain", block.id);
}

function toggleDependencySource(block: Block) {
  if (linkSourceId.value === block.id) {
    linkSourceId.value = "";
    return;
  }
  if (!linkSourceId.value) {
    linkSourceId.value = block.id;
    return;
  }
  emit("create-dependency", { fromBlockId: linkSourceId.value, toBlockId: block.id, edgeType: "hard" });
  linkSourceId.value = "";
}
</script>

<template>
  <div class="timeline-track">
    <div class="timeline-track__toolbar">
      <div class="timeline-track__days">
        <button
          v-for="day in dayTabs"
          :key="day"
          class="day-tab"
          :class="{ active: activeDay === day }"
          @click="emit('update:activeDay', day)"
        >
          <span class="day-tab__label">Day {{ day }}</span>
          <span class="day-tab__meta">{{ dayBlockCount(day) }} 节点</span>
          <span v-if="dayTotalDuration(day)" class="day-tab__meta">{{ formatDuration(dayTotalDuration(day)) }}</span>
        </button>
      </div>
      <div class="timeline-track__filters">
        <label class="timeline-track__filter-label">泳道筛选</label>
        <select v-model="laneFilter" class="timeline-track__lane-select">
          <option value="all">全部泳道</option>
          <option v-for="lane in lanes" :key="lane.key" :value="lane.key">{{ lane.label }}</option>
        </select>
      </div>
    </div>

    <div class="timeline-track__dependency-strip">
      <span class="dependency-label">依赖关系 {{ dependencies.length }}</span>
      <span v-if="linkSourceId" class="dependency-hint">当前起点：{{ blockNameMap[linkSourceId] }}，再点一个节点建立依赖</span>
      <span v-for="edge in dependencyPreview" :key="edge.id" class="dependency-chip">
        {{ blockNameMap[edge.fromBlockId] || edge.fromBlockId }} → {{ blockNameMap[edge.toBlockId] || edge.toBlockId }}
      </span>
      <span v-if="dependencies.length > dependencyPreview.length" class="dependency-more">…</span>
    </div>

    <div class="timeline-track__canvas">
      <section
        v-for="lane in visibleLanes"
        :key="lane.key"
        class="lane-row"
        :class="{ dragover: dragOver && dragOver.day === activeDay && dragOver.lane === lane.key }"
        @dragover="handleDragOver($event, activeDay, lane.key)"
        @dragleave="handleDragLeave"
        @drop="handleDrop($event, activeDay, lane.key)"
      >
        <header class="lane-row__head">
          <span class="lane-row__name">{{ lane.label }}</span>
          <span class="lane-row__stat">{{ blocksForLane(activeDay, lane.key).length }} 个</span>
        </header>

        <div v-if="blocksForLane(activeDay, lane.key).length === 0" class="lane-row__empty">
          将模板或节点拖拽到此泳道
        </div>

        <div v-else class="lane-row__blocks">
          <article
            v-for="block in blocksForLane(activeDay, lane.key)"
            :key="block.id"
            class="timeline-node"
            :class="{ active: activeBlockId === block.id, linking: linkSourceId === block.id }"
            draggable="true"
            @dragstart="onNodeDragStart($event, block)"
            @click="emit('select-block', block)"
          >
            <div class="timeline-node__top">
              <span class="timeline-node__kind" :style="{ color: getBlockConfig(block.blockType).color }">
                {{ getBlockConfig(block.blockType).icon }} {{ getBlockConfig(block.blockType).label }}
              </span>
              <span class="timeline-node__state">{{ statusLabel(block.status) }}</span>
            </div>

            <BlockContainer
              v-if="block.isContainer && block.children?.length"
              :block="block"
              :active-block-id="activeBlockId"
              @select="emit('select-block', $event)"
              @edit="emit('edit-block', $event)"
              @delete="emit('delete-block', $event)"
              @ungroup="emit('ungroup-block', $event)"
            />
            <BlockCard
              v-else
              :block="block"
              :active="activeBlockId === block.id"
              @select="emit('select-block', $event)"
              @edit="emit('edit-block', $event)"
              @delete="emit('delete-block', $event)"
            />

            <div class="timeline-node__meta">
              <span>{{ formatMinute(block.startMinute) }} - {{ formatMinute(block.endMinute) }}</span>
              <span>优先级 {{ block.priority }}</span>
              <span>风险 {{ block.riskLevel }}</span>
            </div>

            <div class="timeline-node__actions">
              <button class="node-btn" @click.stop="emit('edit-block', block)">编辑</button>
              <button class="node-btn danger" @click.stop="emit('delete-block', block)">删除</button>
              <button class="node-btn link" @click.stop="toggleDependencySource(block)">设为依赖</button>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.timeline-track {
  --line: rgba(134, 170, 222, 0.24);
  --line-strong: rgba(134, 170, 222, 0.42);
  --text-main: #eef5ff;
  --text-sub: #9fb7db;
  --surface-main: rgba(11, 22, 40, 0.95);
  --surface-soft: rgba(20, 35, 61, 0.82);
  --surface-node: rgba(10, 22, 43, 0.88);
  --accent: #5fc8ff;

  display: flex;
  flex-direction: column;
  min-height: 360px;
  height: 100%;
  background: linear-gradient(180deg, rgba(10, 20, 38, 0.92) 0%, rgba(7, 15, 29, 0.94) 100%);
  color: var(--text-main);
}

.timeline-track__toolbar {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-main);
}

.timeline-track__days {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.day-tab {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
}

.day-tab.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px rgba(95, 200, 255, 0.35) inset;
}

.day-tab__label {
  font-weight: 700;
}

.day-tab__meta {
  font-size: 11px;
  color: var(--text-sub);
}

.timeline-track__filters {
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeline-track__filter-label {
  font-size: 12px;
  color: var(--text-sub);
}

.timeline-track__lane-select {
  min-width: 140px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-main);
  padding: 6px 8px;
}

.timeline-track__dependency-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-soft);
}

.dependency-label {
  font-size: 12px;
  color: var(--text-sub);
  white-space: nowrap;
}

.dependency-hint {
  font-size: 12px;
  color: #ffd28c;
  white-space: nowrap;
}

.dependency-chip {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.05);
  white-space: nowrap;
}

.dependency-more {
  color: var(--text-sub);
  font-size: 12px;
}

.timeline-track__canvas {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.lane-row {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface-soft);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.lane-row.dragover {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px rgba(95, 200, 255, 0.35);
}

.lane-row__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
}

.lane-row__name {
  font-weight: 700;
  letter-spacing: 0.02em;
}

.lane-row__stat {
  font-size: 12px;
  color: var(--text-sub);
}

.lane-row__empty {
  padding: 18px;
  color: var(--text-sub);
  font-size: 13px;
}

.lane-row__blocks {
  display: grid;
  gap: 10px;
  padding: 10px;
}

.timeline-node {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-node);
  padding: 8px;
}

.timeline-node.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px rgba(95, 200, 255, 0.35);
}

.timeline-node.linking {
  border-color: #ffd27a;
}

.timeline-node__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.timeline-node__kind {
  font-size: 12px;
  font-weight: 700;
}

.timeline-node__state {
  font-size: 11px;
  color: var(--text-sub);
}

.timeline-node__meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--text-sub);
  margin-top: 8px;
}

.timeline-node__actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.node-btn {
  border: 1px solid var(--line);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-main);
  padding: 5px 8px;
  font-size: 12px;
  cursor: pointer;
}

.node-btn.danger {
  color: #ffb5b5;
}

.node-btn.link {
  color: #ffd28c;
}

@media (max-width: 980px) {
  .timeline-track__toolbar {
    grid-template-columns: 1fr;
  }
}
</style>
