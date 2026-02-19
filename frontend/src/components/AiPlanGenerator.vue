<script setup lang="ts">
import { computed, ref } from "vue";
import {
  isAiPreviewValidationError,
  importAiPlan,
  previewAiPlan,
  type AiPreviewItem,
  type AiPreviewValidationErrorPayload,
  type AiPreviewResponse
} from "../api";

const props = defineProps<{
  token: string;
  itineraryId: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (event: "imported"): void;
}>();

const rawText = ref("");
const preview = ref<AiPreviewResponse | null>(null);
const pendingPreview = ref(false);
const pendingImport = ref(false);
const errorText = ref("");
const successText = ref("");
const validationError = ref<AiPreviewValidationErrorPayload | null>(null);

const canGenerate = computed(() => !props.disabled && rawText.value.trim().length > 0);
const groupedByDay = computed<Record<number, AiPreviewItem[]>>(() => {
  if (!preview.value) {
    return {};
  }
  return preview.value.items.reduce<Record<number, AiPreviewItem[]>>((acc, item) => {
    if (!acc[item.day_index]) {
      acc[item.day_index] = [];
    }
    acc[item.day_index].push(item);
    return acc;
  }, {});
});

async function handleGenerate() {
  const text = rawText.value.trim();
  if (!text || !props.itineraryId) {
    return;
  }
  pendingPreview.value = true;
  errorText.value = "";
  successText.value = "";
  validationError.value = null;
  preview.value = null;
  try {
    preview.value = await previewAiPlan({ raw_text: text, itinerary_id: props.itineraryId }, props.token);
  } catch (error) {
    if (isAiPreviewValidationError(error)) {
      errorText.value = error.payload.reason;
      validationError.value = error.payload;
    } else {
      errorText.value = error instanceof Error ? error.message : "AI 预览生成失败";
    }
  } finally {
    pendingPreview.value = false;
  }
}

async function handleImport() {
  if (!preview.value || !props.itineraryId) {
    return;
  }
  pendingImport.value = true;
  errorText.value = "";
  successText.value = "";
  validationError.value = null;
  try {
    const result = await importAiPlan({ itinerary_id: props.itineraryId, preview: preview.value }, props.token);
    successText.value = `已导入 ${result.imported_count} 个时间块`;
    emit("imported");
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "AI 导入失败";
  } finally {
    pendingImport.value = false;
  }
}

function continueManualEditing() {
  errorText.value = "";
  validationError.value = null;
}
</script>

<template>
  <section class="panel-card ai-card">
    <div class="panel-head">
      <h2>AI 内容引擎（预览）</h2>
    </div>
    <p class="subtle">
      粘贴游记文字后生成结构化行程预览；确认后仅追加导入到当前行程。
    </p>
    <textarea
      v-model="rawText"
      class="input ai-textarea"
      rows="5"
      placeholder="粘贴游记、聊天记录或备忘录内容..."
      :disabled="disabled || pendingPreview || pendingImport"
    />
    <div class="action-row">
      <button
        class="btn primary"
        :disabled="!canGenerate || pendingPreview || pendingImport || !itineraryId"
        @click="handleGenerate"
      >
        {{ pendingPreview ? "生成中..." : "一键生成预览" }}
      </button>
      <button
        class="btn"
        :disabled="!preview || pendingPreview || pendingImport || !itineraryId"
        @click="handleImport"
      >
        {{ pendingImport ? "导入中..." : "确认导入（仅追加）" }}
      </button>
    </div>
    <p
      v-if="errorText"
      class="error"
    >
      {{ errorText }}
    </p>
    <div
      v-if="validationError"
      class="panel-card ai-error-card"
    >
      <p class="subtle">
        原文摘要：{{ validationError.raw_excerpt || "无" }}
      </p>
      <ul>
        <li
          v-for="action in validationError.suggested_actions"
          :key="action"
        >
          {{ action }}
        </li>
      </ul>
      <div class="action-row">
        <button
          class="btn"
          :disabled="pendingPreview || pendingImport"
          @click="continueManualEditing"
        >
          继续手动编辑
        </button>
      </div>
    </div>
    <p
      v-if="successText"
      class="hint"
    >
      {{ successText }}
    </p>

    <div
      v-if="preview"
      class="ai-preview"
    >
      <p><strong>{{ preview.title }}</strong> · {{ preview.destination }} · {{ preview.days }} 天</p>
      <div
        v-for="(items, day) in groupedByDay"
        :key="day"
        class="ai-day"
      >
        <h3>第 {{ day }} 天</h3>
        <ul>
          <li
            v-for="item in items"
            :key="`${item.day_index}-${item.sort_order}-${item.poi.name}`"
          >
            {{ item.sort_order }}. {{ item.poi.name }}
            <span class="subtle">（{{ item.poi.match_source }}）</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
