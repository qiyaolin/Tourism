<script setup lang="ts">
import { computed, ref } from "vue";

import type { Block } from "../../types/block";
import { BLOCK_TYPE_CONFIGS } from "../../types/block";
import BlockCard from "./BlockCard.vue";

const props = defineProps<{
  block: Block;
  activeBlockId: string;
}>();

const emit = defineEmits<{
  (e: "select", block: Block): void;
  (e: "toggle-expand", block: Block): void;
  (e: "edit", block: Block): void;
  (e: "delete", block: Block): void;
  (e: "ungroup", block: Block): void;
}>();

const expanded = ref(false);

const config = computed(
  () =>
    BLOCK_TYPE_CONFIGS[props.block.blockType as keyof typeof BLOCK_TYPE_CONFIGS] ??
    BLOCK_TYPE_CONFIGS.scenic
);
const childCount = computed(() => props.block.children?.length || 0);

const totalDuration = computed(() => {
  let sum = props.block.durationMinutes || 0;
  for (const child of props.block.children || []) sum += child.durationMinutes || 0;
  return sum;
});

const totalCost = computed(() => {
  let sum = props.block.cost || 0;
  for (const child of props.block.children || []) sum += child.cost || 0;
  return sum;
});

function toggleExpand() {
  expanded.value = !expanded.value;
}

function formatDuration(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h${m > 0 ? m + "m" : ""}` : `${m}m`;
}
</script>

<template>
  <div
    class="block-container"
    :class="{ expanded, active: activeBlockId === block.id }"
    :style="{ '--bc-accent': config.color, '--bc-bg': config.bgColor, '--bc-border': config.borderColor }"
  >
    <div class="block-container__header" @click="emit('select', block)">
      <button class="block-container__toggle" @click.stop="toggleExpand">
        <span class="block-container__arrow" :class="{ rotated: expanded }">▶</span>
      </button>
      <span class="block-container__icon">{{ config.icon }}</span>
      <span class="block-container__title">{{ block.title }}</span>
      <span class="block-container__count">{{ childCount }} 项</span>
      <span v-if="totalDuration" class="block-container__stat">{{ formatDuration(totalDuration) }}</span>
      <span v-if="totalCost" class="block-container__stat">¥{{ totalCost }}</span>

      <div class="block-container__actions">
        <button class="action-btn" title="编辑" @click.stop="emit('edit', block)">编辑</button>
        <button class="action-btn" title="解组" @click.stop="emit('ungroup', block)">解组</button>
        <button class="action-btn" title="删除" @click.stop="emit('delete', block)">删除</button>
      </div>
    </div>

    <transition name="expand">
      <div v-if="expanded" class="block-container__children">
        <template v-for="child in block.children" :key="child.id">
          <BlockContainer
            v-if="child.isContainer && child.children?.length"
            :block="child"
            :active-block-id="activeBlockId"
            @select="emit('select', $event)"
            @toggle-expand="emit('toggle-expand', $event)"
            @edit="emit('edit', $event)"
            @delete="emit('delete', $event)"
            @ungroup="emit('ungroup', $event)"
          />
          <BlockCard
            v-else
            :block="child"
            :active="activeBlockId === child.id"
            @select="emit('select', $event)"
            @toggle-expand="emit('toggle-expand', $event)"
            @edit="emit('edit', $event)"
            @delete="emit('delete', $event)"
          />
        </template>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.block-container {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-left: 4px solid var(--bc-border);
  border-radius: 10px;
  background: var(--bc-bg);
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.block-container.active {
  box-shadow: 0 0 0 2px var(--bc-accent), 0 4px 16px rgba(0, 0, 0, 0.15);
}

.block-container__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.block-container__header:hover {
  background: rgba(255, 255, 255, 0.04);
}

.block-container__toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  color: var(--text-secondary, #a0a0a0);
  font-size: 13px;
}

.block-container__arrow {
  display: inline-block;
  transition: transform 0.2s;
}

.block-container__arrow.rotated {
  transform: rotate(90deg);
}

.block-container__icon {
  font-size: 16px;
}

.block-container__title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary, #e8e8e8);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.block-container__count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  background: var(--bc-accent);
  color: #fff;
  flex-shrink: 0;
}

.block-container__stat {
  font-size: 12px;
  color: var(--text-secondary, #a0a0a0);
}

.block-container__actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.block-container__header:hover .block-container__actions {
  opacity: 1;
}

.action-btn {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary, #e8e8e8);
  cursor: pointer;
  font-size: 11px;
  padding: 2px 6px;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.block-container__children {
  padding: 6px 12px 12px 24px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
