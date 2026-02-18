<script setup lang="ts">
import { computed, ref, watch } from "vue";
import draggable from "vuedraggable";
import type { PoiResponse } from "../api";
import type { AddTimelineBlockPayload, TimelineDraftItem, TimelineItemPatch } from "../types/timeline";
import AddTimelineBlockDialog from "./AddTimelineBlockDialog.vue";
import TimelineBlock from "./TimelineBlock.vue";

const props = defineProps<{
  days: number;
  items: TimelineDraftItem[];
  activeDay: number;
  activeItemClientId: string;
  pois: PoiResponse[];
  poiLoading: boolean;
  poiError: string;
}>();

const emit = defineEmits<{
  (event: "update:activeDay", day: number): void;
  (event: "select-item", clientId: string): void;
  (event: "delete-item", clientId: string): void;
  (event: "patch-item", payload: { clientId: string; patch: TimelineItemPatch }): void;
  (event: "reorder-day", payload: { dayIndex: number; orderedClientIds: string[] }): void;
  (event: "add-item", payload: AddTimelineBlockPayload): void;
}>();

const showAddDialog = ref(false);
const draggableItems = ref<TimelineDraftItem[]>([]);

const dayItems = computed(() =>
  props.items
    .filter((item) => item.dayIndex === props.activeDay)
    .slice()
    .sort((a, b) => a.sortOrder - b.sortOrder)
);

watch(
  dayItems,
  (value) => {
    draggableItems.value = value.slice();
  },
  { immediate: true }
);

function handleDragEnd() {
  emit("reorder-day", {
    dayIndex: props.activeDay,
    orderedClientIds: draggableItems.value.map((item) => item.clientId)
  });
}

function handleConfirmAdd(payload: AddTimelineBlockPayload) {
  emit("add-item", payload);
  showAddDialog.value = false;
}
</script>

<template>
  <section class="timeline-card">
    <header class="timeline-head">
      <div>
        <h2>时间轴编辑器</h2>
        <p class="subtle">
          按天编辑行程顺序，支持拖拽排序与地图联动。
        </p>
      </div>
      <button
        class="btn primary"
        type="button"
        :disabled="poiLoading"
        @click="showAddDialog = true"
      >
        添加时间块
      </button>
    </header>

    <p
      v-if="poiError"
      class="error"
    >
      {{ poiError }}
    </p>

    <nav class="day-tabs">
      <button
        v-for="day in days"
        :key="day"
        type="button"
        class="day-tab"
        :class="{ active: day === activeDay }"
        @click="emit('update:activeDay', day)"
      >
        Day {{ day }}
      </button>
    </nav>

    <p
      v-if="draggableItems.length === 0"
      class="empty-note"
    >
      当前天暂无时间块，请点击“添加时间块”。
    </p>

    <draggable
      v-model="draggableItems"
      item-key="clientId"
      handle=".timeline-block-head"
      class="timeline-list"
      ghost-class="timeline-block-ghost"
      @end="handleDragEnd"
    >
      <template #item="{ element }">
        <TimelineBlock
          :item="element"
          :active="element.clientId === activeItemClientId"
          @select="emit('select-item', $event)"
          @delete="emit('delete-item', $event)"
          @patch="emit('patch-item', $event)"
        />
      </template>
    </draggable>

    <AddTimelineBlockDialog
      :open="showAddDialog"
      :pois="pois"
      :days="days"
      :active-day="activeDay"
      @close="showAddDialog = false"
      @confirm="handleConfirmAdd"
    />
  </section>
</template>
