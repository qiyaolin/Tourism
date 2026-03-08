<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { BountyTaskResponse } from "../api";

const props = defineProps<{
  open: boolean;
  task: BountyTaskResponse | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [
    {
      submit_longitude: number;
      submit_latitude: number;
      details: string | null;
      photo: File;
    }
  ];
}>();

const details = ref("");
const locationError = ref("");
const submitError = ref("");
const photoFile = ref<File | null>(null);
const longitude = ref<number | null>(null);
const latitude = ref<number | null>(null);
const locating = ref(false);

const canSubmit = computed(() => {
  return (
    !props.loading &&
    photoFile.value !== null &&
    longitude.value !== null &&
    latitude.value !== null
  );
});

watch(
  () => props.open,
  (next) => {
    if (!next) {
      details.value = "";
      locationError.value = "";
      submitError.value = "";
      photoFile.value = null;
      longitude.value = null;
      latitude.value = null;
      locating.value = false;
    }
  }
);

function choosePhoto(event: Event) {
  const input = event.target as HTMLInputElement;
  photoFile.value = input.files?.[0] || null;
}

function closeDialog() {
  emit("close");
}

function captureLocation() {
  locationError.value = "";
  if (!navigator.geolocation) {
    locationError.value = "当前浏览器不支持定位。";
    return;
  }
  locating.value = true;
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      longitude.value = pos.coords.longitude;
      latitude.value = pos.coords.latitude;
      locating.value = false;
    },
    (err) => {
      locationError.value = err.message || "定位失败，请检查浏览器定位权限。";
      locating.value = false;
    },
    {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 0
    }
  );
}

function submit() {
  submitError.value = "";
  if (!photoFile.value || longitude.value === null || latitude.value === null) {
    submitError.value = "请先上传照片并完成定位。";
    return;
  }
  emit("submit", {
    submit_longitude: longitude.value,
    submit_latitude: latitude.value,
    details: details.value.trim() || null,
    photo: photoFile.value
  });
}
</script>

<template>
  <div v-if="open" class="modal-overlay">
    <div class="modal-content">
      <h2>提交赏金任务</h2>
      <p class="subtle" v-if="task">
        目标：{{ task.poi_name }} · 奖励 {{ task.reward_points }} 积分
      </p>

      <label class="field-label">现场照片（必填）</label>
      <input type="file" accept="image/jpeg,image/png,image/webp" class="input" @change="choosePhoto">

      <label class="field-label">补充说明（可选）</label>
      <textarea v-model="details" class="input" rows="3" placeholder="填写补充信息，例如营业时间变化。"></textarea>

      <div class="location-row">
        <button class="btn ghost" :disabled="locating || loading" @click="captureLocation">
          {{ locating ? "定位中..." : "获取当前位置" }}
        </button>
        <p v-if="longitude !== null && latitude !== null" class="subtle small">
          已定位：{{ longitude.toFixed(6) }}, {{ latitude.toFixed(6) }}
        </p>
      </div>

      <p v-if="locationError" class="error">{{ locationError }}</p>
      <p v-if="submitError" class="error">{{ submitError }}</p>

      <div class="action-row">
        <button class="btn ghost" :disabled="loading" @click="closeDialog">取消</button>
        <button class="btn primary" :disabled="!canSubmit" @click="submit">
          {{ loading ? "提交中..." : "提交核验" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}

.modal-content {
  width: min(560px, calc(100vw - 2rem));
  background: #fff;
  border-radius: 12px;
  padding: 1rem 1.25rem;
}

.field-label {
  display: block;
  margin: 0.75rem 0 0.35rem;
  font-size: 0.9rem;
}

.location-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.action-row {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.75rem;
}
</style>
