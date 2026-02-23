<template>
  <div class="passport-page" style="margin: 0 auto; max-width: 800px; padding: 2rem;">
    <div class="passport-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
      <h1 style="font-size: 2rem; margin: 0;">我的数字护照</h1>
      <button class="export-btn" @click="exportPassport">导出海报</button>
    </div>

    <div v-if="loading" style="text-align: center; padding: 4rem;">
      加载中...
    </div>
    <div v-else-if="error" style="text-align: center; color: red; padding: 4rem;">
      {{ error }}
    </div>
    <div v-else-if="passport" class="passport-content" ref="passportContainer" style="background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 2rem;">
      <div class="user-summary" style="display: flex; align-items: center; gap: 1.5rem; margin-bottom: 2rem; padding-bottom: 2rem; border-bottom: 1px solid #eee;">
        <div class="avatar-placeholder" style="width: 80px; height: 80px; border-radius: 50%; background: #ebf5ff; color: #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: bold;">
          {{ userNickname?.[0] || 'U' }}
        </div>
        <div class="stats">
          <h2 style="font-size: 1.5rem; margin: 0 0 0.5rem 0;">{{ userNickname }}的护照</h2>
          <div style="display: flex; gap: 1rem; color: #666;">
            <span class="stat-badge">等级 Lv.{{ passport.level }}</span>
            <span class="stat-badge">总积分 {{ passport.total_points }}</span>
          </div>
        </div>
      </div>

      <div style="margin-bottom: 2rem;">
        <h3 style="font-size: 1.25rem; margin: 0 0 1rem 0; border-left: 4px solid #3b82f6; padding-left: 0.75rem;">签证徽章墙</h3>
        <div v-if="passport.badges.length === 0" style="color: #999; text-align: center; padding: 2rem; background: #f9fafb; border-radius: 4px;">
          暂未解锁任何徽章
        </div>
        <div v-else style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;">
          <BadgeItem 
            v-for="ub in passport.badges" 
            :key="ub.id"
            :badge="ub.badge_def"
            :unlocked="true"
            :unlocked-at="ub.created_at"
          />
        </div>
      </div>

      <div>
        <h3 style="font-size: 1.25rem; margin: 0 0 1rem 0; border-left: 4px solid #10b981; padding-left: 0.75rem;">近期贡献记录</h3>
        <ul v-if="passport.recent_contributions.length > 0" style="list-style: none; padding: 0; margin: 0;">
          <li v-for="contrib in passport.recent_contributions" :key="contrib.id" style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: #f9fafb; border-radius: 4px; margin-bottom: 0.5rem;">
            <div>
              <span style="font-weight: 500;">{{ formatActionType(contrib.action_type) }}</span>
              <span style="font-size: 0.75rem; color: #888; margin-left: 0.5rem;">{{ new Date(contrib.created_at).toLocaleString() }}</span>
            </div>
            <span style="color: #10b981; font-weight: bold;">+{{ contrib.points }}</span>
          </li>
        </ul>
        <div v-else style="color: #999; padding: 1rem;">暂无记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { fetchMyPassport, type PassportResponse } from '../api';
import { useAuth } from '../composables/useAuth';
import BadgeItem from '../components/BadgeItem.vue';

const { user, token } = useAuth();
const loading = ref(true);
const error = ref<string | null>(null);
const passport = ref<PassportResponse | null>(null);
const passportContainer = ref<HTMLElement | null>(null);

const userNickname = computed(() => user.value?.nickname || '未知用户');

const formatActionType = (type: string) => {
  const map: Record<string, string> = {
    'first_contribution': '首次贡献',
    'correction_accepted': '纠错采纳',
    'itinerary_published': '发布行程',
    'itinerary_forked': '行程被借鉴'
  };
  return map[type] || type;
};

const loadData = async () => {
  if (!token.value) return;
  try {
    loading.value = true;
    error.value = null;
    passport.value = await fetchMyPassport(token.value);
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : '获取护照失败';
  } finally {
    loading.value = false;
  }
};

onMounted(loadData);

const exportPassport = async () => {
  if (!passportContainer.value) return;
  alert('海报导出功能界面已就绪，等待 html2canvas 依赖修复后正式启用！');
  // try {
  //   const canvas = await html2canvas(passportContainer.value, { ... });
  //   ...
  // }
};
</script>

<style scoped>
.passport-page {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.stat-badge {
  background: #ebf5ff;
  color: #2563eb;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.875rem;
}
.export-btn {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}
.export-btn:hover {
  background-color: #2563eb;
}
</style>
