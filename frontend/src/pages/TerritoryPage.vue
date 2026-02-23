<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  fetchTerritories,
  submitTerritoryApplication,
  territoryGuardianCheckIn,
  type TerritoryRegionResponse
} from "../api";
import { useAuth } from "../composables/useAuth";

const loading = ref(false);
const submittingId = ref("");
const checkingInId = ref("");
const error = ref("");
const success = ref("");
const territories = ref<TerritoryRegionResponse[]>([]);
const reasonByTerritoryId = ref<Record<string, string>>({});

const { token, user, isLoggedIn, loadMe } = useAuth();

async function loadTerritories() {
  loading.value = true;
  error.value = "";
  try {
    const result = await fetchTerritories();
    territories.value = result.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载领地区域失败";
  } finally {
    loading.value = false;
  }
}

function guardianLabel(state: string): string {
  if (state === "active") return "活跃守护者";
  if (state === "honorary") return "荣誉守护者";
  if (state === "suspended") return "暂停审核权";
  return state;
}

function myGuardianState(item: TerritoryRegionResponse): string | null {
  if (!user.value) return null;
  const row = item.guardians.find((guardian) => guardian.user_id === user.value?.id);
  return row?.state || null;
}

async function handleApply(territoryId: string) {
  if (!token.value) {
    error.value = "请先登录后申请守护者";
    return;
  }
  submittingId.value = territoryId;
  error.value = "";
  success.value = "";
  try {
    await submitTerritoryApplication(token.value, {
      territory_id: territoryId,
      reason: reasonByTerritoryId.value[territoryId]?.trim() || null
    });
    success.value = "申请已提交，等待管理员审核。";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "提交申请失败";
  } finally {
    submittingId.value = "";
  }
}

async function handleCheckIn(territoryId: string) {
  if (!token.value) {
    return;
  }
  checkingInId.value = territoryId;
  error.value = "";
  success.value = "";
  try {
    await territoryGuardianCheckIn(territoryId, token.value);
    success.value = "巡检打卡成功，活跃度已更新。";
    await loadTerritories();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "巡检打卡失败";
  } finally {
    checkingInId.value = "";
  }
}

onMounted(async () => {
  await loadMe();
  await loadTerritories();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">Territory</p>
        <h1>领地认领计划</h1>
      </div>
      <button class="btn ghost" :disabled="loading" @click="loadTerritories">刷新</button>
    </header>

    <p class="subtle">守护者可优先审核本区域纠错；若近期无审核任务，请执行“巡检打卡”维持活跃状态。</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="hint">{{ success }}</p>
    <p v-if="loading" class="subtle">加载中...</p>

    <section v-else class="mine-sections">
      <article v-for="territory in territories" :key="territory.id" class="mine-card">
        <h3>{{ territory.name }}</h3>
        <p class="subtle">POI 数量：{{ territory.poi_count }} · 状态：{{ territory.status === "active" ? "可认领" : "已停用" }}</p>

        <p v-if="territory.guardians.length === 0" class="subtle">暂无守护者。</p>
        <ul v-else class="mini-list">
          <li v-for="guardian in territory.guardians" :key="`${territory.id}-${guardian.user_id}`">
            @{{ guardian.nickname }} · {{ guardianLabel(guardian.state) }}
          </li>
        </ul>

        <template v-if="isLoggedIn && territory.status === 'active'">
          <label class="field-label">申请说明</label>
          <textarea
            v-model="reasonByTerritoryId[territory.id]"
            class="input correction-textarea"
            placeholder="说明你对该区域的维护经验和计划（可选）"
          />
          <div class="action-row">
            <button class="btn primary" :disabled="submittingId === territory.id" @click="handleApply(territory.id)">
              提交守护申请
            </button>
            <button
              v-if="myGuardianState(territory) === 'active' || myGuardianState(territory) === 'honorary'"
              class="btn ghost"
              :disabled="checkingInId === territory.id"
              @click="handleCheckIn(territory.id)"
            >
              巡检打卡
            </button>
          </div>
        </template>
      </article>
    </section>
  </main>
</template>
