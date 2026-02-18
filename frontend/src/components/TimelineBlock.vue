<script setup lang="ts">
import type { TimelineDraftItem, TimelineItemPatch } from "../types/timeline";

const props = defineProps<{
  item: TimelineDraftItem;
  active: boolean;
}>();

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
    :class="{ active }"
    @click="emit('select', item.clientId)"
  >
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
