<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { PoiResponse } from "../api";
import type { AddTimelineBlockPayload } from "../types/timeline";

const props = defineProps<{
  open: boolean;
  pois: PoiResponse[];
  days: number;
  activeDay: number;
}>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "confirm", payload: AddTimelineBlockPayload): void;
}>();

const selectedPoiId = ref("");
const dayIndex = ref(1);
const startTime = ref("");
const durationMinutes = ref("");
const cost = ref("");
const tips = ref("");
const submitError = ref("");

const selectedPoi = computed(() => props.pois.find((item) => item.id === selectedPoiId.value) || null);

watch(
  () => props.open,
  (opened) => {
    if (!opened) {
      return;
    }
    selectedPoiId.value = props.pois[0]?.id || "";
    dayIndex.value = props.activeDay;
    startTime.value = "";
    durationMinutes.value = "";
    cost.value = "";
    tips.value = "";
    submitError.value = "";
  }
);

function parseNumber(value: unknown): number | null {
  if (value == null) {
    return null;
  }
  if (typeof value === "string" && !value.trim()) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function submit() {
  submitError.value = "";
  if (!selectedPoiId.value || !selectedPoi.value) {
    submitError.value = "请先选择景点";
    return;
  }
  if (!Number.isInteger(dayIndex.value) || dayIndex.value < 1 || dayIndex.value > props.days) {
    submitError.value = "请选择有效天数";
    return;
  }
  emit("confirm", {
    poiId: selectedPoiId.value,
    poi: selectedPoi.value,
    dayIndex: dayIndex.value,
    startTime: startTime.value || null,
    durationMinutes: parseNumber(durationMinutes.value),
    cost: parseNumber(cost.value),
    tips: tips.value.trim() || null
  });
}
</script>

<template>
  <div
    v-if="open"
    class="dialog-backdrop"
    @click.self="emit('close')"
  >
    <section class="dialog-card">
      <header class="dialog-head">
        <h3>新增时间块</h3>
        <button
          class="btn ghost"
          type="button"
          @click="emit('close')"
        >
          关闭
        </button>
      </header>

      <label>
        选择景点
        <select
          v-model="selectedPoiId"
          class="input"
        >
          <option
            v-for="poi in pois"
            :key="poi.id"
            :value="poi.id"
          >{{ poi.name }} · {{ poi.type }}</option>
        </select>
      </label>

      <label>
        所属天数
        <select
          v-model.number="dayIndex"
          class="input"
        >
          <option
            v-for="day in days"
            :key="day"
            :value="day"
          >第 {{ day }} 天</option>
        </select>
      </label>

      <div class="dialog-grid">
        <label>
          开始时间
          <input
            v-model="startTime"
            class="input"
            type="time"
          >
        </label>
        <label>
          停留时长(分钟)
          <input
            v-model="durationMinutes"
            class="input"
            type="number"
            min="1"
          >
        </label>
        <label>
          预算花费(元)
          <input
            v-model="cost"
            class="input"
            type="number"
            min="0"
            step="0.01"
          >
        </label>
      </div>

      <label>
        备注
        <input
          v-model="tips"
          class="input"
          type="text"
          placeholder="可选"
        >
      </label>

      <p
        v-if="selectedPoi"
        class="subtle"
      >
        已选：{{ selectedPoi.name }}（{{ selectedPoi.address || "地址未提供" }}）
      </p>
      <p
        v-if="submitError"
        class="error"
      >
        {{ submitError }}
      </p>

      <footer class="dialog-actions">
        <button
          class="btn"
          type="button"
          @click="emit('close')"
        >
          取消
        </button>
        <button
          class="btn primary"
          type="button"
          :disabled="!selectedPoiId"
          @click="submit"
        >
          确认添加景点
        </button>
      </footer>
    </section>
  </div>
</template>
