<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import BountySubmitDialog from "../components/BountySubmitDialog.vue";
import {
  claimBounty,
  fetchBounties,
  fetchMyBountySubmissions,
  submitBounty,
  type BountySubmissionResponse,
  type BountyTaskResponse
} from "../api";
import { useAuth } from "../composables/useAuth";

type ScopeTab = "all" | "nearby" | "mine";

const scope = ref<ScopeTab>("all");
const loading = ref(false);
const claimingTaskId = ref("");
const submitting = ref(false);
const error = ref("");
const success = ref("");
const tasks = ref<BountyTaskResponse[]>([]);
const submissions = ref<BountySubmissionResponse[]>([]);
const nearbyHint = ref<BountyTaskResponse[]>([]);
const nearbyRadiusMeters = ref<number | null>(null);
const currentLongitude = ref<number | null>(null);
const currentLatitude = ref<number | null>(null);
const showSubmitDialog = ref(false);
const activeTask = ref<BountyTaskResponse | null>(null);

const { token, user, loadMe } = useAuth();

const sortedTasks = computed(() =>
  tasks.value.slice().sort((a, b) => (a.generated_at < b.generated_at ? 1 : -1))
);

const sortedSubmissions = computed(() =>
  submissions.value.slice().sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
);

function statusText(status: BountyTaskResponse["status"]) {
  if (status === "open") return "待领取";
  if (status === "claimed") return "已领取";
  if (status === "submitted") return "待审核";
  if (status === "approved") return "已通过";
  if (status === "rejected") return "已驳回";
  return "已过期";
}

function reviewStatusText(status: BountySubmissionResponse["review_status"]) {
  if (status === "approved") return "已通过";
  if (status === "rejected") return "已驳回";
  return "待人工审核";
}

function formatDistance(value: number | null): string {
  if (value === null) return "-";
  return `${value.toFixed(0)}m`;
}

function canSubmit(task: BountyTaskResponse): boolean {
  return task.status === "claimed" && task.claimed_by_user_id === user.value?.id;
}

async function locateUser(): Promise<void> {
  if (!navigator.geolocation) {
    throw new Error("当前浏览器不支持定位。");
  }
  await new Promise<void>((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        currentLongitude.value = pos.coords.longitude;
        currentLatitude.value = pos.coords.latitude;
        resolve();
      },
      (err) => reject(new Error(err.message || "定位失败，请检查定位权限。")),
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
    );
  });
}

async function loadNearbyHint() {
  if (!token.value) return;
  try {
    await locateUser();
    if (currentLongitude.value === null || currentLatitude.value === null) return;
    const result = await fetchBounties(token.value, {
      scope: "nearby",
      offset: 0,
      limit: 3,
      longitude: currentLongitude.value,
      latitude: currentLatitude.value
    });
    nearbyHint.value = result.items;
    nearbyRadiusMeters.value = result.nearby_radius_meters;
  } catch {
    nearbyHint.value = [];
  }
}

async function loadTasks() {
  if (!token.value) return;
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    if (scope.value === "nearby") {
      await locateUser();
    }
    const result = await fetchBounties(token.value, {
      scope: scope.value,
      offset: 0,
      limit: 40,
      longitude: currentLongitude.value ?? undefined,
      latitude: currentLatitude.value ?? undefined
    });
    tasks.value = result.items;
    nearbyRadiusMeters.value = result.nearby_radius_meters;

    if (scope.value === "mine") {
      const submissionResult = await fetchMyBountySubmissions(token.value, 0, 30);
      submissions.value = submissionResult.items;
    } else {
      submissions.value = [];
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载赏金任务失败";
  } finally {
    loading.value = false;
  }
}

function openSubmit(task: BountyTaskResponse) {
  activeTask.value = task;
  showSubmitDialog.value = true;
}

async function handleClaim(taskId: string) {
  if (!token.value) return;
  claimingTaskId.value = taskId;
  error.value = "";
  success.value = "";
  try {
    const task = await claimBounty(taskId, token.value);
    success.value = `已领取任务：${task.poi_name}`;
    await loadTasks();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "领取任务失败";
  } finally {
    claimingTaskId.value = "";
  }
}

async function handleSubmit(payload: {
  submit_longitude: number;
  submit_latitude: number;
  details: string | null;
  photo: File;
}) {
  if (!token.value || !activeTask.value) return;
  submitting.value = true;
  error.value = "";
  success.value = "";
  try {
    const result = await submitBounty(activeTask.value.id, token.value, payload);
    showSubmitDialog.value = false;
    success.value = result.auto_approved
      ? "任务已自动通过，奖励积分已入账。"
      : "任务已提交，进入人工审核队列。";
    await loadTasks();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "提交任务失败";
  } finally {
    submitting.value = false;
  }
}

function switchTab(next: ScopeTab) {
  scope.value = next;
  void loadTasks();
}

onMounted(async () => {
  await loadMe();
  await Promise.all([loadNearbyHint(), loadTasks()]);
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">Bounty Board</p>
        <h1>赏金任务</h1>
      </div>
      <button class="btn ghost" :disabled="loading" @click="loadTasks">刷新</button>
    </header>

    <section v-if="nearbyHint.length > 0" class="nearby-hint-card">
      <h3>附近任务提醒</h3>
      <p class="subtle small">
        你附近 {{ nearbyRadiusMeters || 1500 }} 米内有 {{ nearbyHint.length }} 条可领取赏金任务。
      </p>
      <button class="btn primary" @click="switchTab('nearby')">查看附近任务</button>
    </section>

    <div class="tabs">
      <button :class="{ active: scope === 'all' }" @click="switchTab('all')">全部任务</button>
      <button :class="{ active: scope === 'nearby' }" @click="switchTab('nearby')">附近任务</button>
      <button :class="{ active: scope === 'mine' }" @click="switchTab('mine')">我的任务</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="hint success-text">{{ success }}</p>
    <p v-if="loading" class="subtle">加载中...</p>
    <p v-else-if="sortedTasks.length === 0" class="subtle">当前没有可展示的赏金任务。</p>

    <section class="mine-sections" v-else>
      <article v-for="task in sortedTasks" :key="task.id" class="mine-card">
        <div class="card-title-row">
          <h3>{{ task.poi_name }}</h3>
          <span class="status-chip">{{ statusText(task.status) }}</span>
        </div>
        <p class="subtle">区域：{{ task.territory_name || "未归属区域" }}</p>
        <p class="subtle">奖励：{{ task.reward_points }} 积分</p>
        <p class="subtle">数据陈旧：{{ task.stale_days_snapshot }} 天</p>
        <p v-if="scope === 'nearby'" class="subtle">距离：{{ formatDistance(task.distance_meters) }}</p>
        <p class="subtle">发布时间：{{ new Date(task.generated_at).toLocaleString() }}</p>
        <div class="action-row">
          <button
            v-if="task.status === 'open'"
            class="btn primary"
            :disabled="claimingTaskId === task.id"
            @click="handleClaim(task.id)"
          >
            {{ claimingTaskId === task.id ? "领取中..." : "领取任务" }}
          </button>
          <button
            v-if="canSubmit(task)"
            class="btn outline primary"
            @click="openSubmit(task)"
          >
            提交核验
          </button>
        </div>
      </article>
    </section>

    <section v-if="scope === 'mine'" class="submission-section">
      <h2>最近提交记录</h2>
      <p v-if="sortedSubmissions.length === 0" class="subtle">暂无提交记录。</p>
      <article v-for="item in sortedSubmissions" :key="item.id" class="mine-card">
        <h3>{{ item.poi_name }}</h3>
        <p class="subtle">审核状态：{{ reviewStatusText(item.review_status) }}</p>
        <p class="subtle">风险等级：{{ item.risk_level === "manual_review" ? "人工审核" : "自动通过候选" }}</p>
        <p class="subtle">提交距离：{{ item.distance_meters.toFixed(0) }}m</p>
        <p class="subtle">奖励：{{ item.reward_points }} 积分</p>
        <p class="subtle">提交时间：{{ new Date(item.created_at).toLocaleString() }}</p>
        <a v-if="item.photo_url" class="btn ghost" :href="item.photo_url" target="_blank" rel="noreferrer">查看照片</a>
      </article>
    </section>

    <BountySubmitDialog
      :open="showSubmitDialog"
      :task="activeTask"
      :loading="submitting"
      @close="showSubmitDialog = false"
      @submit="handleSubmit"
    />
  </main>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tabs button {
  border: 1px solid var(--border, #d1d5db);
  background: #fff;
  border-radius: 999px;
  padding: 0.4rem 0.8rem;
  cursor: pointer;
  font-weight: 600;
}

.tabs button.active {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}

.nearby-hint-card {
  border: 1px solid #a7f3d0;
  background: #ecfdf5;
  border-radius: 10px;
  padding: 0.9rem;
  margin-bottom: 1rem;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.status-chip {
  background: #e0f2fe;
  color: #075985;
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.78rem;
}

.submission-section {
  margin-top: 1.25rem;
}

.success-text {
  color: var(--color-success, #10b981);
}
</style>
