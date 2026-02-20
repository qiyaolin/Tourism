<script setup lang="ts">
import { onMounted, ref } from "vue";

import { fetchReviewCorrections, reviewPoiCorrection, type PoiCorrectionResponse } from "../api";
import { useAuth } from "../composables/useAuth";

const loading = ref(false);
const actionLoading = ref("");
const error = ref("");
const items = ref<PoiCorrectionResponse[]>([]);
const reviewCommentById = ref<Record<string, string>>({});

const { token, loadMe } = useAuth();

async function loadReviewItems() {
  if (!token.value) {
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const result = await fetchReviewCorrections(token.value, 0, 50);
    items.value = result.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载审核列表失败";
  } finally {
    loading.value = false;
  }
}

async function handleReview(correctionId: string, action: "accepted" | "rejected") {
  if (!token.value) {
    return;
  }
  actionLoading.value = correctionId;
  error.value = "";
  try {
    await reviewPoiCorrection(correctionId, token.value, {
      action,
      review_comment: reviewCommentById.value[correctionId]?.trim() || null
    });
    await loadReviewItems();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "提交审核失败";
  } finally {
    actionLoading.value = "";
  }
}

onMounted(async () => {
  await loadMe();
  await loadReviewItems();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">Corrections</p>
        <h1>纠错审核台</h1>
      </div>
      <button class="btn ghost" :disabled="loading" @click="loadReviewItems">
        刷新
      </button>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading" class="subtle">加载中...</p>
    <p v-else-if="items.length === 0" class="subtle">当前没有待审核纠错。</p>

    <section class="mine-sections">
      <article v-for="item in items" :key="item.id" class="mine-card">
        <h3>{{ item.type_label }}</h3>
        <p class="subtle">POI：{{ item.poi_id }}</p>
        <p class="subtle">提议：{{ item.proposed_value || "未填写" }}</p>
        <p class="subtle">说明：{{ item.details || "无" }}</p>
        <a v-if="item.photo_url" class="btn ghost" :href="item.photo_url" target="_blank" rel="noreferrer">查看图片</a>
        <label class="field-label">审核备注</label>
        <input v-model="reviewCommentById[item.id]" class="input" placeholder="可选：填写备注">
        <div class="action-row">
          <button class="btn primary" :disabled="actionLoading === item.id" @click="handleReview(item.id, 'accepted')">
            采纳
          </button>
          <button class="btn danger" :disabled="actionLoading === item.id" @click="handleReview(item.id, 'rejected')">
            驳回
          </button>
        </div>
      </article>
    </section>
  </main>
</template>
