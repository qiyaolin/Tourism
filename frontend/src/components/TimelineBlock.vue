<script setup lang="ts">
import { computed } from "vue";
import type { TimelineDraftItem, TimelineItemPatch } from "../types/timeline";

const props = defineProps<{
  item: TimelineDraftItem;
  active: boolean;
  remoteCursors?: Map<string, { clientId: string; timestamp: number }>;
}>();

// Simple color hash logic (same as CollabAvatarBar)
function getCursorColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash % 360)}, 70%, 40%)`;
}

// Find all remote users currently selecting this specific item
const activeRemoteCursors = computed(() => {
  if (!props.remoteCursors) return [];
  const result: { id: string; color: string }[] = [];
  const now = Date.now();
  for (const [participantId, cursor] of props.remoteCursors.entries()) {
    // Only show active cursors (updated within the last 2 minutes)
    if (cursor.clientId === props.item.clientId && now - cursor.timestamp < 120000) {
      result.push({
        id: participantId,
        color: getCursorColor(participantId)
      });
    }
  }
  return result;
});

const emit = defineEmits<{
  (event: "select", clientId: string): void;
  (event: "delete", clientId: string): void;
  (event: "patch", payload: { clientId: string; patch: TimelineItemPatch }): void;
}>();

function emitPatch(patch: TimelineItemPatch) {
  emit("patch", {
    clientId: props.item.clientId,
    patch
  });
}

function parseNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}
</script>

<template>
  <article
    class="timeline-block"
    :class="{ active, 'has-remote-cursor': activeRemoteCursors.length > 0 }"
    :style="activeRemoteCursors.length > 0 ? { '--remote-color': activeRemoteCursors[0].color } : {}"
    @click="emit('select', item.clientId)"
  >
    <div
      v-if="activeRemoteCursors.length > 0"
      class="remote-cursor-badges"
    >
      <div
        v-for="cursor in activeRemoteCursors"
        :key="cursor.id"
        class="remote-cursor-badge"
        :style="{ backgroundColor: cursor.color }"
      >
        阅
      </div>
    </div>

    <header class="timeline-block-head">
      <p class="timeline-block-order">
        {{ item.dayIndex }}日 · 第{{ item.sortOrder }}站
      </p>
      <button
        class="btn ghost danger"
        type="button"
        @click.stop="emit('delete', item.clientId)"
      >
        删除
      </button>
    </header>

    <h3 class="timeline-block-title">
      {{ item.poi.name }}
    </h3>
    <p class="timeline-block-type">
      {{ item.poi.type }}
    </p>

    <div class="timeline-grid">
      <label>
        开始时间
        <input
          class="input"
          type="time"
          :value="item.startTime ? item.startTime.slice(0, 5) : ''"
          @input="emitPatch({ startTime: (($event.target as HTMLInputElement).value || null) })"
        >
      </label>
      <label>
        停留时长(分钟)
        <input
          class="input"
          type="number"
          min="1"
          :value="item.durationMinutes ?? ''"
          @input="emitPatch({ durationMinutes: parseNumber(($event.target as HTMLInputElement).value) })"
        >
      </label>
      <label>
        预算花费(元)
        <input
          class="input"
          type="number"
          min="0"
          step="0.01"
          :value="item.cost ?? ''"
          @input="emitPatch({ cost: parseNumber(($event.target as HTMLInputElement).value) })"
        >
      </label>
      <label>
        备注
        <input
          class="input"
          type="text"
          :value="item.tips ?? ''"
          @input="emitPatch({ tips: (($event.target as HTMLInputElement).value || null) })"
        >
      </label>
    </div>
  </article>
</template>

<style scoped>
.timeline-block {
  position: relative;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.timeline-block.has-remote-cursor {
  border-color: var(--remote-color, var(--primary-default));
  box-shadow: 0 0 0 1px var(--remote-color, var(--primary-default));
}

.remote-cursor-badges {
  position: absolute;
  top: -10px;
  right: -10px;
  display: flex;
  gap: 2px;
  z-index: 10;
}

.remote-cursor-badge {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  color: white;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--surface-default);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
</style>
