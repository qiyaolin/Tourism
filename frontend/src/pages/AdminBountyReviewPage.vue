<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  fetchAdminBountySubmissions,
  reviewAdminBountySubmission,
  type BountySubmissionResponse
} from "../api";
import { useAuth } from "../composables/useAuth";

const loading = ref(false);
const actionLoading = ref("");
const error = ref("");
const success = ref("");
const statusFilter = ref<"pending" | "approved" | "rejected" | "all">("pending");
const items = ref<BountySubmissionResponse[]>([]);
const reviewCommentById = ref<Record<string, string>>({});

const { token, loadMe } = useAuth();

function reviewStatusText(status: BountySubmissionResponse["review_status"]) {
  if (status === "approved") return "已通过";
  if (status === "rejected") return "已驳回";
  return "待审核";
}

async function loadData() {
  if (!token.value) return;
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    const result = await fetchAdminBountySubmissions(token.value, statusFilter.value, 0, 50);
    items.value = result.items;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载审核列表失败";
  } finally {
    loading.value = false;
  }
}

async function handleReview(submissionId: string, action: "approve" | "reject") {
  if (!token.value) return;
  actionLoading.value = submissionId;
  error.value = "";
  success.value = "";
  try {
    await reviewAdminBountySubmission(submissionId, token.value, {
      action,
      review_comment: reviewCommentById.value[submissionId]?.trim() || null
    });
    success.value = action === "approve" ? "已通过任务提交。" : "已驳回任务提交。";
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "提交审核失败";
  } finally {
    actionLoading.value = "";
  }
}

onMounted(async () => {
  await loadMe();
  await loadData();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">Admin</p>
        <h1>赏金任务审核台</h1>
      </div>
      <div class="action-row">
        <select v-model="statusFilter" class="input" @change="loadData">
          <option value="pending">待审核</option>
          <option value="approved">已通过</option>
          <option value="rejected">已驳回</option>
          <option value="all">全部</option>
        </select>
        <button class="btn ghost" :disabled="loading" @click="loadData">刷新</button>
      </div>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="hint success-text">{{ success }}</p>
    <p v-if="loading" class="subtle">加载中...</p>
    <p v-else-if="items.length === 0" class="subtle">当前没有符合筛选条件的提交。</p>

    <section class="mine-sections">
      <article v-for="item in items" :key="item.id" class="mine-card">
        <h3>{{ item.poi_name }}</h3>
        <p class="subtle">状态：{{ reviewStatusText(item.review_status) }}</p>
        <p class="subtle">任务状态：{{ item.task_status }}</p>
        <p class="subtle">风险等级：{{ item.risk_level }}</p>
        <p class="subtle">GPS 距离：{{ item.distance_meters.toFixed(0) }}m</p>
        <p class="subtle">提交时间：{{ new Date(item.created_at).toLocaleString() }}</p>
        <a v-if="item.photo_url" class="btn ghost" :href="item.photo_url" target="_blank" rel="noreferrer">查看照片</a>

        <template v-if="item.review_status === 'pending'">
          <label class="field-label">审核备注</label>
          <input v-model="reviewCommentById[item.id]" class="input" placeholder="可选：填写审核备注">
          <div class="action-row">
            <button class="btn primary" :disabled="actionLoading === item.id" @click="handleReview(item.id, 'approve')">
              通过
            </button>
            <button class="btn danger" :disabled="actionLoading === item.id" @click="handleReview(item.id, 'reject')">
              驳回
            </button>
          </div>
        </template>
      </article>
    </section>
  </main>
</template>

<style scoped>
.success-text {
  color: var(--color-success, #10b981);
}
</style>
