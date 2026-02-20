<script setup lang="ts">
import { computed, ref } from "vue";

import {
  fetchPoiCorrectionTypes,
  fetchPricingAudiences,
  submitPoiCorrection,
  type PoiCorrectionResponse,
  type PoiCorrectionType,
  type PricingAudienceItem
} from "../api";

type DraftRule = {
  audience_code: string;
  ticket_type: string;
  time_slot: string;
  price: string;
  conditions: string;
};

const props = defineProps<{
  poiId: string;
  poiName: string;
  token: string;
  sourceItineraryId?: string | null;
}>();

const open = ref(false);
const loadingTypes = ref(false);
const loadingAudiences = ref(false);
const submitting = ref(false);
const error = ref("");
const success = ref("");
const typeOptions = ref<PoiCorrectionType[]>([]);
const audiences = ref<PricingAudienceItem[]>([]);
const selectedTypeCode = ref("");
const proposedValue = ref("");
const openingStart = ref("");
const openingEnd = ref("");
const details = ref("");
const photoFile = ref<File | null>(null);
const ruleRows = ref<DraftRule[]>([]);

const selectedType = computed(
  () => typeOptions.value.find((item) => item.code === selectedTypeCode.value) || null
);

const isTicketPriceType = computed(() => selectedType.value?.input_mode === "ticket_rules");
const isOpeningHoursType = computed(() => selectedType.value?.input_mode === "time_range");

const normalizedRules = computed(() =>
  ruleRows.value
    .map((row) => ({
      audience_code: row.audience_code.trim(),
      ticket_type: row.ticket_type.trim(),
      time_slot: row.time_slot.trim(),
      price: Number(row.price),
      currency: "CNY",
      conditions: row.conditions.trim() || null,
      is_active: true
    }))
    .filter(
      (row) =>
        row.audience_code &&
        row.ticket_type &&
        row.time_slot &&
        Number.isFinite(row.price) &&
        row.price >= 0
    )
);

const rowErrors = computed(() =>
  ruleRows.value.map((row) => ({
    ticket_type: !row.ticket_type.trim(),
    time_slot: !row.time_slot.trim(),
    price: !Number.isFinite(Number(row.price)) || Number(row.price) < 0
  }))
);

const validRuleCount = computed(() => normalizedRules.value.length);

function isTimeRangeValid() {
  if (!openingStart.value || !openingEnd.value) {
    return false;
  }
  return openingEnd.value > openingStart.value;
}

const canSubmit = computed(() => {
  if (!props.token || !selectedType.value) {
    return false;
  }
  if (isTicketPriceType.value) {
    return ruleRows.value.length > 0 && validRuleCount.value === ruleRows.value.length;
  }
  if (isOpeningHoursType.value) {
    return isTimeRangeValid();
  }
  return Boolean(proposedValue.value.trim());
});

function addRuleRow() {
  const defaultAudience = audiences.value[0]?.code || "adult";
  ruleRows.value.push({
    audience_code: defaultAudience,
    ticket_type: "标准票",
    time_slot: "全天",
    price: "",
    conditions: ""
  });
}

function removeRuleRow(index: number) {
  ruleRows.value.splice(index, 1);
}

async function ensureTypesLoaded() {
  if (typeOptions.value.length > 0 || loadingTypes.value) {
    return;
  }
  loadingTypes.value = true;
  error.value = "";
  try {
    const result = await fetchPoiCorrectionTypes();
    typeOptions.value = result.items;
    if (!selectedTypeCode.value && result.items.length > 0) {
      selectedTypeCode.value = result.items[0].code;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载纠错类型失败";
  } finally {
    loadingTypes.value = false;
  }
}

async function ensureAudiencesLoaded() {
  if (audiences.value.length > 0 || loadingAudiences.value) {
    return;
  }
  loadingAudiences.value = true;
  error.value = "";
  try {
    const result = await fetchPricingAudiences();
    audiences.value = result.items;
    if (ruleRows.value.length === 0) {
      addRuleRow();
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载票价人群失败";
  } finally {
    loadingAudiences.value = false;
  }
}

function resetFormByType() {
  proposedValue.value = "";
  openingStart.value = "";
  openingEnd.value = "";
  if (isTicketPriceType.value && ruleRows.value.length === 0) {
    addRuleRow();
  }
}

function toggleOpen() {
  open.value = !open.value;
  if (open.value) {
    void Promise.all([ensureTypesLoaded(), ensureAudiencesLoaded()]).then(() => {
      resetFormByType();
    });
  }
}

function handlePhotoChange(event: Event) {
  const input = event.target as HTMLInputElement;
  photoFile.value = input.files?.[0] || null;
}

async function compressImage(file: File): Promise<File> {
  if (!file.type.startsWith("image/")) {
    return file;
  }
  const bitmap = await createImageBitmap(file);
  const maxEdge = 1600;
  const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.floor(bitmap.width * scale));
  canvas.height = Math.max(1, Math.floor(bitmap.height * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return file;
  }
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const mimeType = file.type === "image/png" ? "image/png" : "image/jpeg";
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob((value) => resolve(value), mimeType, 0.82)
  );
  if (!blob) {
    return file;
  }
  return new File([blob], file.name, { type: blob.type });
}

async function handleSubmit() {
  if (!canSubmit.value || !selectedType.value) {
    return;
  }
  submitting.value = true;
  error.value = "";
  success.value = "";
  try {
    let uploadFile = photoFile.value;
    if (uploadFile) {
      uploadFile = await compressImage(uploadFile);
    }

    const proposed = isTicketPriceType.value
      ? JSON.stringify(normalizedRules.value)
      : isOpeningHoursType.value
        ? `${openingStart.value}-${openingEnd.value}`
        : proposedValue.value.trim();

    const result: PoiCorrectionResponse = await submitPoiCorrection(props.poiId, props.token, {
      type_code: selectedTypeCode.value,
      proposed_value: proposed || null,
      details: details.value.trim() || null,
      photo: uploadFile,
      source_itinerary_id: props.sourceItineraryId || null
    });

    success.value = `提交成功，状态：${result.status}`;
    proposedValue.value = "";
    openingStart.value = "";
    openingEnd.value = "";
    details.value = "";
    photoFile.value = null;
    if (isTicketPriceType.value) {
      ruleRows.value = [];
      addRuleRow();
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "提交纠错失败";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="panel-card correction-panel">
    <div class="panel-head">
      <h2>纠错反馈</h2>
      <button class="btn ghost" @click="toggleOpen">
        {{ open ? "收起" : "发起纠错" }}
      </button>
    </div>
    <p class="subtle">景点：{{ poiName }}</p>

    <div v-if="open" class="correction-form">
      <p v-if="loadingTypes || loadingAudiences" class="subtle">加载中...</p>
      <template v-else>
        <label class="field-label">纠错类型</label>
        <select v-model="selectedTypeCode" class="input" @change="resetFormByType">
          <option v-for="item in typeOptions" :key="item.code" :value="item.code">
            {{ item.label }}
          </option>
        </select>
        <p v-if="selectedType?.help_text" class="subtle correction-help">{{ selectedType.help_text }}</p>

        <template v-if="isTicketPriceType">
          <section class="ticket-change-section">
            <div class="ticket-change-head">
              <h3>票价规则</h3>
              <p class="subtle">已录入 {{ validRuleCount }} / {{ ruleRows.length }} 条有效规则</p>
            </div>
            <div class="ticket-rules-table-wrap">
              <table class="ticket-rules-table">
                <thead>
                  <tr>
                    <th>人群</th>
                    <th>票种</th>
                    <th>适用时段</th>
                    <th>使用条件</th>
                    <th>票价(元)</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in ruleRows" :key="index">
                    <td>
                      <select v-model="row.audience_code" class="input">
                        <option v-for="aud in audiences" :key="aud.code" :value="aud.code">{{ aud.label }}</option>
                      </select>
                    </td>
                    <td>
                      <input v-model="row.ticket_type" class="input" placeholder="如标准票/半价票">
                      <p v-if="rowErrors[index]?.ticket_type" class="error ticket-rule-cell-error">请填写票种</p>
                    </td>
                    <td>
                      <input v-model="row.time_slot" class="input" placeholder="如工作日/节假日/夜场">
                      <p v-if="rowErrors[index]?.time_slot" class="error ticket-rule-cell-error">请填写适用时段</p>
                    </td>
                    <td>
                      <input v-model="row.conditions" class="input" placeholder="如需学生证，可不填">
                    </td>
                    <td>
                      <input v-model="row.price" class="input" type="number" min="0" step="0.01" placeholder="0.00">
                      <p v-if="rowErrors[index]?.price" class="error ticket-rule-cell-error">票价需为不小于 0 的数字</p>
                    </td>
                    <td>
                      <button class="btn ghost danger" type="button" @click="removeRuleRow(index)">删除</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="action-row">
              <button class="btn ghost" type="button" @click="addRuleRow">新增一条票价规则</button>
            </div>
          </section>
        </template>

        <template v-else>
          <template v-if="isOpeningHoursType">
            <label class="field-label">营业时间（24小时制）</label>
            <div class="opening-hours-row">
              <input v-model="openingStart" class="input" type="time">
              <span>至</span>
              <input v-model="openingEnd" class="input" type="time">
            </div>
            <p class="subtle">将按 `HH:MM-HH:MM` 格式提交并用于审核后直接应用。</p>
          </template>
          <template v-else>
            <label class="field-label">更正内容</label>
            <input
              v-model="proposedValue"
              class="input"
              :placeholder="selectedType?.placeholder || '请输入更正内容'"
            >
          </template>
        </template>

        <label class="field-label">补充说明</label>
        <textarea
          v-model="details"
          class="input correction-textarea"
          placeholder="可选：补充证据或说明"
        ></textarea>

        <label class="field-label">图片证据（可选）</label>
        <input class="input" type="file" accept="image/jpeg,image/png,image/webp" @change="handlePhotoChange">

        <div class="action-row">
          <button class="btn primary" :disabled="!canSubmit || submitting" @click="handleSubmit">
            {{ submitting ? "提交中..." : isTicketPriceType ? "提交票价变动纠错" : "提交纠错" }}
          </button>
        </div>
      </template>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="success" class="hint">{{ success }}</p>
    </div>
  </section>
</template>
