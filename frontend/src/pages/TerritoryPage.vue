<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import {
  fetchMyTerritoryProfile,
  fetchTerritories,
  fetchTerritoryOpportunities,
  submitTerritoryApplication,
  type TerritoryOpportunityResponse,
  type TerritoryRegionResponse,
  type UserTerritoryProfileResponse
} from "../api";
import { useAuth } from "../composables/useAuth";
import { useAmap } from "../composables/useAmap";

const loading = ref(false);
const error = ref("");
const territories = ref<TerritoryRegionResponse[]>([]);
const profile = ref<UserTerritoryProfileResponse | null>(null);
const activeTab = ref<"explore" | "profile">("explore");
const activeRegionId = ref<string | null>(null);
const activeOpportunities = ref<TerritoryOpportunityResponse | null>(null);

const showApplyModal = ref(false);
const applyingTerritoryId = ref("");
const applyingTerritoryName = ref("");
const applyReason = ref("");
const applyLoading = ref(false);
const applyError = ref("");
const applySuccess = ref("");

const { token, isLoggedIn, loadMe } = useAuth();
const mapContainer = ref<HTMLElement | null>(null);
const { initMap, renderPolygons, checkPolygon, destroyMap } = useAmap(mapContainer);

const ROLE_LABELS: Record<string, string> = {
  regular: "常客",
  local_expert: "在地达人",
  area_guide: "区域向导",
  city_ambassador: "城市大使"
};

const STATE_LABELS: Record<string, string> = {
  active: "活跃",
  dormant: "休眠",
  honorary: "荣誉"
};

const TASK_TYPE_LABELS: Record<string, string> = {
  pending_review: "待审核纠错",
  poi_verification: "信息待验证",
  nearby_opportunity: "附近机会",
  bounty: "赏金任务"
};

function roleLabel(role: string): string {
  return ROLE_LABELS[role] || role;
}

function stateLabel(state: string): string {
  return STATE_LABELS[state] || state;
}

function taskTypeLabel(taskType: string): string {
  return TASK_TYPE_LABELS[taskType] || taskType;
}

function progressPercent(progress: number): string {
  return Math.round(progress * 100) + "%";
}

function checkCanApply(territoryId: string): boolean {
  if (!isLoggedIn.value) return false;
  if (!profile.value) return true;
  return !profile.value.roles.some((role) => role.territory_id === territoryId);
}

function openApplyModal(territory: TerritoryRegionResponse): void {
  applyingTerritoryId.value = territory.id;
  applyingTerritoryName.value = territory.name;
  applyReason.value = "";
  applyError.value = "";
  applySuccess.value = "";
  showApplyModal.value = true;
}

function closeApplyModal(): void {
  showApplyModal.value = false;
}

async function submitApply(): Promise<void> {
  if (!token.value) return;
  applyLoading.value = true;
  applyError.value = "";
  applySuccess.value = "";
  try {
    await submitTerritoryApplication(token.value, {
      territory_id: applyingTerritoryId.value,
      reason: applyReason.value
    });
    applySuccess.value = "申请已提交，等待管理员审核。";
  } catch (err) {
    applyError.value = err instanceof Error ? err.message : "提交申请失败";
  } finally {
    applyLoading.value = false;
  }
}

async function loadAll(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const result = await fetchTerritories();
    territories.value = result.items;

    if (mapContainer.value) {
      await initMap();
      renderPolygons(territories.value, handlePolygonClick);
    }

    if (token.value) {
      profile.value = await fetchMyTerritoryProfile(token.value).catch(() => null);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载领地数据失败";
  } finally {
    loading.value = false;
  }
}

async function loadOpportunities(regionId: string): Promise<void> {
  try {
    activeOpportunities.value = await fetchTerritoryOpportunities(regionId);
  } catch {
    activeOpportunities.value = null;
  }
}

function handlePolygonClick(id: string): void {
  focusTerritory(id);
}

function focusTerritory(id: string): void {
  activeRegionId.value = id;
  checkPolygon(id);
  void loadOpportunities(id);

  const element = document.getElementById("territory-card-" + id);
  if (element) {
    element.scrollIntoView({ behavior: "smooth", block: "center" });
    element.classList.add("highlighted-card");
    setTimeout(() => {
      element.classList.remove("highlighted-card");
    }, 1500);
  }
}

function clearFocus(): void {
  activeRegionId.value = null;
  activeOpportunities.value = null;
}

onMounted(async () => {
  await loadMe();
  await loadAll();
});

onUnmounted(() => {
  destroyMap();
});
</script>

<template>
  <main class="atlas-root full-height-layout">
    <div class="split-view">
      <aside class="sidebar-pane">
        <header class="sidebar-header">
          <p class="kicker">Territory Network</p>
          <h1>在地向导网络</h1>
          <p class="subtle header-tip">探索区域边界，积累贡献，自动升级向导等级。</p>
        </header>

        <div class="tabs">
          <button :class="{ active: activeTab === 'explore' }" @click="activeTab = 'explore'">
            探索区域
          </button>
          <button :class="{ active: activeTab === 'profile' }" @click="activeTab = 'profile'">
            我的角色
          </button>
        </div>

        <div class="tab-content">
          <p v-if="loading" class="subtle section-padding">正在加载领地数据...</p>
          <p v-if="error" class="error section-padding">{{ error }}</p>

          <template v-if="activeTab === 'explore' && !loading">
            <div class="explore-list">
              <button class="btn ghost clear-focus-btn" v-if="activeRegionId" @click="clearFocus">
                返回全览
              </button>

              <template v-for="territory in territories" :key="territory.id">
                <article
                  v-show="!activeRegionId || activeRegionId === territory.id"
                  :id="'territory-card-' + territory.id"
                  class="mine-card interactive-region-card"
                  :class="{ 'is-active': activeRegionId === territory.id }"
                  @click="focusTerritory(territory.id)"
                >
                  <div class="card-header">
                    <h3>{{ territory.name }}</h3>
                    <span class="poi-badge">{{ territory.poi_count }} 个 POI</span>
                  </div>

                  <p v-if="territory.sample_pois.length > 0" class="subtle small sample-pois">
                    包含地标：{{ territory.sample_pois.join("、") }}
                  </p>

                  <div v-if="activeRegionId === territory.id" class="active-region-details fade-in">
                    <hr class="divider" />
                    <h4>当前向导</h4>
                    <p v-if="territory.guardians.length === 0" class="subtle small">
                      该区域目前没有专属向导，这是参与建设的好机会。
                    </p>
                    <ul v-else class="mini-list small">
                      <li v-for="guardian in territory.guardians" :key="`${territory.id}-${guardian.user_id}`">
                        @{{ guardian.nickname }} ·
                        <span :class="'role-text-' + guardian.role">{{ roleLabel(guardian.role) }}</span>
                      </li>
                    </ul>

                    <div class="action-row">
                      <button
                        v-if="checkCanApply(territory.id)"
                        class="btn outline primary full-width"
                        @click.stop="openApplyModal(territory)"
                      >
                        申请成为向导
                      </button>
                    </div>

                    <div v-if="activeOpportunities" class="opportunities-section">
                      <h4>区域机会</h4>
                      <p v-if="activeOpportunities.items.length === 0" class="subtle small">
                        暂无待处理任务。
                      </p>
                      <div v-else class="opportunity-list">
                        <div
                          v-for="opportunity in activeOpportunities.items"
                          :key="opportunity.target_id || opportunity.title"
                          class="opportunity-item"
                        >
                          <span class="opp-type">{{ taskTypeLabel(opportunity.task_type) }}</span>
                          <span class="opp-title">{{ opportunity.title }}</span>
                          <span class="opp-pts">+{{ opportunity.points }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              </template>

              <p v-if="territories.length === 0" class="subtle section-padding">
                暂无活跃区域。系统已尝试自动初始化；若仍为空，请使用管理员账号在“守护审核”执行“重建领地区域”。
              </p>
            </div>
          </template>

          <template v-if="activeTab === 'profile' && !loading">
            <div class="profile-tab section-padding">
              <template v-if="!isLoggedIn">
                <p class="subtle">请先登录以查看你的向导档案。</p>
              </template>
              <template v-else-if="profile && profile.roles.length > 0">
                <div class="profile-stats">
                  <div class="stat-box">
                    <span class="val">{{ profile.total_contributions }}</span>
                    <span class="lbl">总贡献</span>
                  </div>
                  <div class="stat-box">
                    <span class="val">{{ profile.total_thanks }}</span>
                    <span class="lbl">被感谢</span>
                  </div>
                </div>

                <h3 class="section-title">我管理的区域</h3>
                <article v-for="role in profile.roles" :key="role.territory_id" class="mine-card">
                  <div class="role-header">
                    <span class="role-badge" :class="'role-' + role.role">{{ roleLabel(role.role) }}</span>
                    <span class="state-tag" :class="'state-' + role.state">{{ stateLabel(role.state) }}</span>
                  </div>
                  <h4 class="territory-name">{{ role.territory_name }}</h4>
                  <p class="subtle small">贡献 {{ role.contribution_count }} 次 · 被感谢 {{ role.thanks_received }} 次</p>

                  <div v-if="role.next_role" class="progress-section">
                    <div class="progress-row">
                      <span class="subtle small">距离 {{ roleLabel(role.next_role) }}</span>
                      <span class="subtle small">{{ progressPercent(role.next_role_progress) }}</span>
                    </div>
                    <div class="progress-bar-track">
                      <div class="progress-bar-fill" :style="{ width: progressPercent(role.next_role_progress) }" />
                    </div>
                  </div>
                  <p v-else class="success-text small">已达最高等级</p>
                </article>
              </template>
              <template v-else>
                <p class="subtle">你还没有成为任何区域的在地向导。</p>
                <div class="empty-state-card">
                  <h4>如何成为向导</h4>
                  <ol class="small subtle">
                    <li>在地图上探索并选择你熟悉的区域。</li>
                    <li>在区域详情中完成纠错或验证任务。</li>
                    <li>累计有效贡献后将自动升级角色。</li>
                  </ol>
                  <button class="btn primary full-width" @click="activeTab = 'explore'">去探索区域</button>
                </div>
              </template>
            </div>
          </template>
        </div>
      </aside>

      <section class="map-pane">
        <div class="map-container" ref="mapContainer" />
      </section>
    </div>

    <div v-if="showApplyModal" class="modal-overlay">
      <div class="modal-content">
        <h2>申请认领「{{ applyingTerritoryName }}」</h2>
        <p class="subtle modal-tip">
          说明你在该区域的熟悉程度和贡献计划，审核通过后即可获得向导身份。
        </p>

        <label class="field-label">申请理由（必填）</label>
        <textarea
          v-model="applyReason"
          class="input"
          rows="4"
          placeholder="例如：我长期在本地生活，熟悉景点和交通，愿意持续维护信息。"
        />

        <p v-if="applyError" class="error">{{ applyError }}</p>
        <p v-if="applySuccess" class="hint success-text">{{ applySuccess }}</p>

        <div class="action-row actions-end">
          <button class="btn ghost" @click="closeApplyModal" :disabled="applyLoading">取消</button>
          <button class="btn primary" @click="submitApply" :disabled="applyLoading || !!applySuccess || !applyReason.trim()">
            提交申请
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.full-height-layout {
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.split-view {
  display: flex;
  flex: 1;
  overflow: hidden;
  flex-direction: column-reverse;
}

@media (min-width: 768px) {
  .split-view {
    flex-direction: row;
  }
}

.sidebar-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid var(--border, #e5e7eb);
}

@media (min-width: 768px) {
  .sidebar-pane {
    flex: 0 0 420px;
    max-width: 420px;
  }
}

.sidebar-header {
  padding: 1.5rem 1.5rem 1rem;
  border-bottom: 1px solid var(--border, #e5e7eb);
}

.header-tip {
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

.tabs {
  display: flex;
  border-bottom: 1px solid var(--border, #e5e7eb);
  background: var(--surface-hover, #f9fafb);
}

.tabs button {
  flex: 1;
  padding: 0.75rem 0;
  border: 0;
  background: transparent;
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tabs button.active {
  color: var(--color-primary, #3b82f6);
  border-bottom-color: var(--color-primary, #3b82f6);
  background: #fff;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  background: var(--background, #f9fafb);
}

.section-padding {
  padding: 1rem;
}

.explore-list {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.clear-focus-btn {
  align-self: flex-start;
}

.interactive-region-card {
  cursor: pointer;
  border: 2px solid transparent;
}

.interactive-region-card.is-active {
  border-color: var(--color-primary, #3b82f6);
}

.highlighted-card {
  background: #eff6ff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.card-header h3 {
  margin: 0;
}

.poi-badge {
  background: #f3f4f6;
  color: #4b5563;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.sample-pois {
  margin-top: 0.5rem;
}

.divider {
  border: 0;
  height: 1px;
  background: var(--border, #e5e7eb);
  margin: 1rem 0;
}

.active-region-details {
  margin-top: 1rem;
}

.fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.action-row {
  margin-top: 1rem;
}

.full-width {
  width: 100%;
}

.opportunities-section {
  margin-top: 1rem;
  background: #fffbe6;
  border: 1px solid #fef08a;
  border-radius: 0.5rem;
  padding: 1rem;
}

.opportunity-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.opportunity-item {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
}

.opp-type {
  background: #e0f2fe;
  color: #0284c7;
  padding: 0.15rem 0.4rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-weight: 600;
  margin-right: 0.5rem;
}

.opp-title {
  flex: 1;
  color: #374151;
}

.opp-pts {
  font-weight: 700;
  color: var(--color-success, #10b981);
}

.profile-stats {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.stat-box {
  flex: 1;
  background: #fff;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-box .val {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary, #3b82f6);
}

.stat-box .lbl {
  font-size: 0.85rem;
  color: var(--text-secondary, #6b7280);
  font-weight: 600;
}

.section-title {
  margin: 1.5rem 0 1rem;
}

.role-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.territory-name {
  margin: 0.5rem 0;
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

.role-text-regular {
  color: #1e40af;
  font-weight: 600;
}

.role-text-local_expert {
  color: #065f46;
  font-weight: 600;
}

.role-text-area_guide {
  color: #92400e;
  font-weight: 600;
}

.role-text-city_ambassador {
  color: #9d174d;
  font-weight: 600;
}

.state-tag {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 500;
}

.state-active {
  background: #d1fae5;
  color: #065f46;
}

.state-dormant {
  background: #e5e7eb;
  color: #6b7280;
}

.state-honorary {
  background: #ede9fe;
  color: #5b21b6;
}

.progress-section {
  margin-top: 0.75rem;
}

.progress-row {
  display: flex;
  justify-content: space-between;
}

.progress-bar-track {
  height: 6px;
  background: var(--border, #e5e7eb);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 0.25rem;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
}

.success-text {
  color: var(--color-success, #10b981);
}

.empty-state-card {
  background: #fff;
  border: 1px dashed var(--border, #e5e7eb);
  border-radius: 0.5rem;
  padding: 1rem;
  margin-top: 1rem;
}

.empty-state-card ol {
  padding-left: 1.25rem;
  line-height: 1.6;
}

.map-pane {
  flex: 1;
  position: relative;
  background: #e5e5e5;
}

.map-container {
  width: 100%;
  height: 100%;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  padding: 1.5rem;
  border-radius: 0.75rem;
  width: 90%;
  max-width: 480px;
}

.modal-tip {
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.field-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.actions-end {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
</style>
