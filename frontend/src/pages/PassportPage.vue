<template>
  <div class="passport-page">
    <div class="passport-header">
      <h1>我的数字护照</h1>
      <button class="export-btn" @click="exportPassport">导出海报</button>
    </div>

    <div v-if="loading" class="state-panel">加载中...</div>
    <div v-else-if="error" class="state-panel error">{{ error }}</div>

    <div v-else-if="passport" ref="passportContainer" class="passport-content">
      <div class="user-summary">
        <div class="avatar-placeholder">
          {{ userNickname?.[0] || "U" }}
        </div>
        <div class="stats">
          <h2>{{ userNickname }}的护照</h2>
          <div class="summary-badges">
            <span class="stat-badge">等级 Lv.{{ passport.level }}</span>
            <span class="stat-badge">总积分 {{ passport.total_points }}</span>
          </div>
        </div>
      </div>

      <section v-if="profile && profile.roles.length > 0" class="section-block">
        <h3 class="section-title section-title-guide">在地向导角色</h3>
        <div class="role-list">
          <div v-for="role in profile.roles" :key="role.territory_id" class="territory-role-card">
            <h4>{{ role.territory_name }}</h4>
            <span class="role-badge" :class="'role-' + role.role">{{ roleLabel(role.role) }}</span>
            <p>贡献 {{ role.contribution_count }} 次</p>
          </div>
        </div>
      </section>

      <section class="section-block">
        <h3 class="section-title section-title-badge">签证徽章墙</h3>
        <div v-if="passport.badges.length === 0" class="empty-panel">暂未解锁任何徽章</div>
        <div v-else class="badge-grid">
          <BadgeItem
            v-for="badge in passport.badges"
            :key="badge.id"
            :badge="badge.badge_def"
            :unlocked="true"
            :unlocked-at="badge.created_at"
          />
        </div>
      </section>

      <section class="section-block">
        <h3 class="section-title section-title-record">近期贡献记录</h3>
        <ul v-if="passport.recent_contributions.length > 0" class="record-list">
          <li v-for="contrib in passport.recent_contributions" :key="contrib.id" class="record-item">
            <div>
              <span class="record-action">{{ formatActionType(contrib.action_type) }}</span>
              <span class="record-time">{{ new Date(contrib.created_at).toLocaleString() }}</span>
            </div>
            <span class="record-points">+{{ contrib.points }}</span>
          </li>
        </ul>
        <div v-else class="empty-record">暂无记录</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  fetchMyPassport,
  fetchMyTerritoryProfile,
  type PassportResponse,
  type UserTerritoryProfileResponse
} from "../api";
import BadgeItem from "../components/BadgeItem.vue";
import { useAuth } from "../composables/useAuth";

const { user, token } = useAuth();
const loading = ref(true);
const error = ref<string | null>(null);
const passport = ref<PassportResponse | null>(null);
const profile = ref<UserTerritoryProfileResponse | null>(null);
const passportContainer = ref<HTMLElement | null>(null);

const userNickname = computed(() => user.value?.nickname || "未知用户");

const ROLE_LABELS: Record<string, string> = {
  regular: "常客",
  local_expert: "在地达人",
  area_guide: "区域向导",
  city_ambassador: "城市大使"
};

function roleLabel(role: string): string {
  return ROLE_LABELS[role] || role;
}

function formatActionType(type: string): string {
  const actionLabels: Record<string, string> = {
    first_contribution: "首次贡献",
    correction_accepted: "纠错采纳",
    itinerary_published: "发布行程",
    itinerary_forked: "行程被借鉴",
    bounty_completed: "赏金任务完成"
  };
  return actionLabels[type] || type;
}

async function loadData(): Promise<void> {
  if (!token.value) return;
  try {
    loading.value = true;
    error.value = null;
    const [passportResult, profileResult] = await Promise.all([
      fetchMyPassport(token.value),
      fetchMyTerritoryProfile(token.value).catch(() => null)
    ]);
    passport.value = passportResult;
    profile.value = profileResult;
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : "获取护照失败";
  } finally {
    loading.value = false;
  }
}

function exportPassport(): void {
  if (!passportContainer.value) return;
  alert("海报导出入口已就绪，后续接入导出依赖后可直接下载。");
}

onMounted(loadData);
</script>

<style scoped>
.passport-page {
  margin: 0 auto;
  max-width: 800px;
  padding: 2rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.passport-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.passport-header h1 {
  font-size: 2rem;
  margin: 0;
}

.state-panel {
  text-align: center;
  padding: 4rem;
}

.state-panel.error {
  color: #dc2626;
}

.passport-content {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 2rem;
}

.user-summary {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}

.avatar-placeholder {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #ebf5ff;
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: bold;
}

.stats h2 {
  font-size: 1.5rem;
  margin: 0 0 0.5rem 0;
}

.summary-badges {
  display: flex;
  gap: 1rem;
  color: #666;
}

.stat-badge {
  background: #ebf5ff;
  color: #2563eb;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.875rem;
}

.section-block {
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.25rem;
  margin: 0 0 1rem 0;
  padding-left: 0.75rem;
  border-left: 4px solid;
}

.section-title-guide {
  border-left-color: #f59e0b;
}

.section-title-badge {
  border-left-color: #3b82f6;
}

.section-title-record {
  border-left-color: #10b981;
}

.role-list {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.territory-role-card {
  padding: 1rem;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  min-width: 150px;
}

.territory-role-card h4 {
  margin: 0 0 0.5rem 0;
  color: #92400e;
}

.territory-role-card p {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  color: #b45309;
}

.badge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.empty-panel {
  color: #999;
  text-align: center;
  padding: 2rem;
  background: #f9fafb;
  border-radius: 4px;
}

.record-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.record-action {
  font-weight: 500;
}

.record-time {
  font-size: 0.75rem;
  color: #888;
  margin-left: 0.5rem;
}

.record-points {
  color: #10b981;
  font-weight: bold;
}

.empty-record {
  color: #999;
  padding: 1rem;
}

.export-btn {
  background-color: #3b82f6;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-weight: 600;
  cursor: pointer;
}

.export-btn:hover {
  background-color: #2563eb;
}

.role-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.6rem;
  border-radius: 0.375rem;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
}

.role-regular {
  background: #dbeafe;
  color: #1e40af;
}

.role-local_expert {
  background: #d1fae5;
  color: #065f46;
}

.role-area_guide {
  background: #fef3c7;
  color: #92400e;
}

.role-city_ambassador {
  background: #fce7f3;
  color: #9d174d;
}
</style>
