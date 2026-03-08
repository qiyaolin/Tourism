<script setup lang="ts">
import { computed } from "vue";
import type { Block, BlockType } from "../../types/block";
import { BLOCK_TYPE_CONFIGS } from "../../types/block";

const props = defineProps<{
  block: Block;
  active: boolean;
  compact?: boolean;
  draggable?: boolean;
}>();

const emit = defineEmits<{
  (e: "select", block: Block): void;
  (e: "toggle-expand", block: Block): void;
  (e: "edit", block: Block): void;
  (e: "delete", block: Block): void;
}>();

const config = computed(() => BLOCK_TYPE_CONFIGS[props.block.blockType as BlockType]);

const summary = computed(() => {
  const parts: string[] = [];
  if (props.block.durationMinutes) {
    const h = Math.floor(props.block.durationMinutes / 60);
    const m = props.block.durationMinutes % 60;
    parts.push(h > 0 ? `${h}h${m > 0 ? m + "m" : ""}` : `${m}m`);
  }
  if (props.block.cost != null) {
    parts.push(`¥${props.block.cost}`);
  }
  return parts.join(" · ");
});

const typeLabel = computed(() => {
  const td = props.block.typeData;
  if (!td) return "";
  switch (props.block.blockType) {
    case "transit":
      return td.method ? String(td.method) : "";
    case "dining":
      return td.cuisine_type ? String(td.cuisine_type) : "";
    case "lodging":
      return td.room_type ? String(td.room_type) : "";
    default:
      return "";
  }
});

const childCount = computed(() => props.block.children?.length || 0);
</script>

<template>
  <div
    class="block-card"
    :class="{
      active: active,
      compact: compact,
      container: block.isContainer,
      draggable: draggable,
    }"
    :style="{
      '--bc-accent': config.color,
      '--bc-bg': config.bgColor,
      '--bc-border': config.borderColor,
    }"
    @click="emit('select', block)"
    @dblclick="block.isContainer && emit('toggle-expand', block)"
  >
    <div class="block-card__left-bar" />

    <div class="block-card__body">
      <div class="block-card__header">
        <span class="block-card__icon">{{ config.icon }}</span>
        <span class="block-card__title">{{ block.title }}</span>
        <span v-if="block.isContainer" class="block-card__badge" @click.stop="emit('toggle-expand', block)">
          {{ childCount }} 项
        </span>
      </div>

      <div v-if="!compact" class="block-card__meta">
        <span v-if="summary" class="block-card__summary">{{ summary }}</span>
        <span v-if="typeLabel" class="block-card__type-label">{{ typeLabel }}</span>
      </div>

      <div v-if="!compact && block.tips" class="block-card__tips">
        {{ block.tips }}
      </div>
    </div>

    <div class="block-card__actions">
      <button class="block-card__btn" title="编辑" @click.stop="emit('edit', block)">✏️</button>
      <button class="block-card__btn" title="删除" @click.stop="emit('delete', block)">🗑️</button>
    </div>
  </div>
</template>

<style scoped>
.block-card {
  display: flex;
  align-items: stretch;
  gap: 0;
  background: var(--bc-bg, rgba(255,255,255,0.04));
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.15s;
  position: relative;
  min-width: 180px;
}

.block-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.12);
  transform: translateY(-1px);
}

.block-card.active {
  box-shadow: 0 0 0 2px var(--bc-accent), 0 4px 16px rgba(0,0,0,0.15);
}

.block-card.compact {
  min-width: 120px;
}

.block-card.draggable {
  cursor: grab;
}
.block-card.draggable:active {
  cursor: grabbing;
}

.block-card__left-bar {
  width: 4px;
  min-height: 100%;
  background: var(--bc-border);
  flex-shrink: 0;
  border-radius: 10px 0 0 10px;
}

.block-card__body {
  flex: 1;
  padding: 10px 12px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.block-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.block-card__icon {
  font-size: 16px;
  flex-shrink: 0;
}

.block-card__title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary, #e8e8e8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.block-card__badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  background: var(--bc-accent);
  color: #fff;
  flex-shrink: 0;
  cursor: pointer;
}

.block-card__meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary, #a0a0a0);
}

.block-card__summary {
  opacity: 0.9;
}

.block-card__type-label {
  padding: 0 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  font-size: 11px;
}

.block-card__tips {
  font-size: 12px;
  color: var(--text-secondary, #a0a0a0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.7;
}

.block-card__actions {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  padding: 4px 6px;
  opacity: 0;
  transition: opacity 0.2s;
}

.block-card:hover .block-card__actions {
  opacity: 1;
}

.block-card__btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.15s;
}

.block-card__btn:hover {
  background: rgba(255,255,255,0.1);
}
</style>
