<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  fetchAdminTerritoryApplications,
  rebuildTerritories,
  reviewAdminTerritoryApplication,
  type TerritoryGuardianApplicationResponse,
} from "../api";
import { useAuth } from "../composables/useAuth";

const loading = ref(false);
const rebuilding = ref(false);
const reviewingId = ref("");
const error = ref("");
const success = ref("");
const appItems = ref<TerritoryGuardianApplicationResponse[]>([]);
const commentById = ref<Record<string, string>>({});

const { token, user, loadMe } = useAuth();

const statusFilter = ref<"pending" | "approved" | "rejected" | "all">("pending");

async function loadData() {
  if (!token.value) {
    error.value = "请先登录";
    return;
  }
  if (user.value?.role !== "admin") {
    error.value = "仅管理员可访问";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const apps = await fetchAdminTerritoryApplications(token.value, statusFilter.value, 0, 100);
    appItems.value = apps.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载管理员数据失败";
  } finally {
    loading.value = false;
  }
}

async function handleReview(applicationId: string, action: "approve" | "reject") {
  if (!token.value) return;
  reviewingId.value = applicationId;
  error.value = "";
  success.value = "";
  try {
    await reviewAdminTerritoryApplication(applicationId, token.value, {
      action,
      review_comment: commentById.value[applicationId]?.trim() || null
    });
    success.value = action === "approve" ? "已通过申请并授予守护资格。" : "已驳回申请。";
    await loadData();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "审核申请失败";
  } finally {
    reviewingId.value = "";
  }
}

async function handleRebuild() {
  if (!token.value) return;
  rebuilding.value = true;
  error.value = "";
  success.value = "";
  try {
    const result = await rebuildTerritories(token.value);
    success.value = `区域重建完成：新增 ${result.generated_regions}，分配 POI ${result.assigned_pois}，停用 ${result.inactive_regions}`;
    await loadData();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "重建区域失败";
  } finally {
    rebuilding.value = false;
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
        <h1>领地管理台</h1>
      </div>
      <div class="action-row">
        <button class="btn ghost" :disabled="loading" @click="loadData">刷新</button>
        <button class="btn primary" :disabled="rebuilding" @click="handleRebuild">重建领地区域</button>
      </div>
    </header>

    <p class="subtle">管理员负责区域重建与守护者申请审核。角色晋升由系统根据贡献自动计算。</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="hint">{{ success }}</p>
    <p v-if="loading" class="subtle">加载中...</p>

    <section class="territory-admin-section">
      <div class="action-row">
        <label class="field-label">申请状态过滤</label>
        <select v-model="statusFilter" class="input territory-filter" @change="loadData">
          <option value="pending">待审核</option>
          <option value="approved">已通过</option>
          <option value="rejected">已驳回</option>
          <option value="all">全部</option>
        </select>
      </div>
      <article v-for="item in appItems" :key="item.id" class="mine-card">
        <h3>{{ item.territory_name }} · @{{ item.applicant_nickname }}</h3>
        <p class="subtle">状态：{{ item.status }} · 提交时间：{{ new Date(item.created_at).toLocaleString() }}</p>
        <p class="subtle">申请说明：{{ item.reason || "无" }}</p>
        <label class="field-label">审核备注</label>
        <input v-model="commentById[item.id]" class="input" placeholder="可选：填写审核备注">
        <div v-if="item.status === 'pending'" class="action-row">
          <button class="btn primary" :disabled="reviewingId === item.id" @click="handleReview(item.id, 'approve')">
            通过
          </button>
          <button class="btn danger" :disabled="reviewingId === item.id" @click="handleReview(item.id, 'reject')">
            驳回
          </button>
        </div>
      </article>
      <p v-if="!loading && appItems.length === 0" class="subtle">当前筛选条件下无申请。</p>
    </section>
  </main>
</template>
