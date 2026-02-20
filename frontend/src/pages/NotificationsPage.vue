<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type UserNotificationResponse
} from "../api";
import { useAuth } from "../composables/useAuth";

const TEXT = {
  kicker: "\u52a8\u6001\u9884\u8b66",
  title: "\u9884\u8b66\u4e2d\u5fc3",
  unreadOnly: "\u4ec5\u770b\u672a\u8bfb",
  markAllRead: "\u5168\u90e8\u6807\u8bb0\u5df2\u8bfb",
  refreshing: "\u5237\u65b0\u4e2d...",
  refresh: "\u5237\u65b0",
  unread: "\u672a\u8bfb",
  loadFailed: "\u52a0\u8f7d\u901a\u77e5\u5931\u8d25",
  updateFailed: "\u66f4\u65b0\u901a\u77e5\u72b6\u6001\u5931\u8d25",
  markUnread: "\u6807\u8bb0\u672a\u8bfb",
  markRead: "\u6807\u8bb0\u5df2\u8bfb",
  emptyTitle: "\u6682\u65e0\u901a\u77e5",
  emptyDesc: "\u5f53\u524d\u6ca1\u6709\u9700\u8981\u5904\u7406\u7684\u9884\u8b66\u3002",
  levelCritical: "\u7d27\u6025",
  levelWarning: "\u6ce8\u610f",
  levelInfo: "\u53c2\u8003"
} as const;

const { token } = useAuth();
const loading = ref(false);
const actionLoading = ref("");
const error = ref("");
const unreadOnly = ref(false);
const notifications = ref<UserNotificationResponse[]>([]);
const unreadCount = ref(0);

const hasData = computed(() => notifications.value.length > 0);

function severityLabel(level: UserNotificationResponse["severity"]): string {
  if (level === "critical") return TEXT.levelCritical;
  if (level === "warning") return TEXT.levelWarning;
  return TEXT.levelInfo;
}

async function loadNotifications() {
  if (!token.value) return;
  loading.value = true;
  error.value = "";
  try {
    const data = await fetchNotifications(token.value, 0, 80, unreadOnly.value);
    notifications.value = data.items;
    unreadCount.value = data.unread_count;
  } catch (e) {
    error.value = e instanceof Error ? e.message : TEXT.loadFailed;
  } finally {
    loading.value = false;
  }
}

async function handleMarkRead(item: UserNotificationResponse, read: boolean) {
  if (!token.value) return;
  actionLoading.value = item.id;
  try {
    await markNotificationRead(item.id, token.value, read);
    await loadNotifications();
  } catch (e) {
    error.value = e instanceof Error ? e.message : TEXT.updateFailed;
  } finally {
    actionLoading.value = "";
  }
}

async function handleMarkAllRead() {
  if (!token.value) return;
  actionLoading.value = "all";
  try {
    await markAllNotificationsRead(token.value);
    await loadNotifications();
  } catch (e) {
    error.value = e instanceof Error ? e.message : TEXT.updateFailed;
  } finally {
    actionLoading.value = "";
  }
}

onMounted(() => {
  void loadNotifications();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">{{ TEXT.kicker }}</p>
        <h1>{{ TEXT.title }}</h1>
      </div>
      <div class="notify-actions">
        <label class="notify-toggle">
          <input v-model="unreadOnly" type="checkbox" @change="loadNotifications">
          {{ TEXT.unreadOnly }}
        </label>
        <button class="btn ghost" :disabled="loading || actionLoading === 'all'" @click="handleMarkAllRead">
          {{ TEXT.markAllRead }}
        </button>
        <button class="btn ghost" :disabled="loading" @click="loadNotifications">
          {{ loading ? TEXT.refreshing : TEXT.refresh }}
        </button>
      </div>
    </header>

    <p class="subtle">{{ TEXT.unread }}：{{ unreadCount }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="hasData" class="notify-list">
      <article
        v-for="item in notifications"
        :key="item.id"
        :class="['notify-card', `level-${item.severity}`, { unread: !item.is_read }]"
      >
        <header class="notify-head">
          <div>
            <strong>{{ item.title }}</strong>
            <p class="subtle">{{ item.content }}</p>
          </div>
          <span class="notify-level">{{ severityLabel(item.severity) }}</span>
        </header>
        <footer class="notify-foot">
          <p class="subtle">{{ new Date(item.created_at).toLocaleString() }}</p>
          <button class="btn ghost" :disabled="actionLoading === item.id" @click="handleMarkRead(item, !item.is_read)">
            {{ item.is_read ? TEXT.markUnread : TEXT.markRead }}
          </button>
        </footer>
      </article>
    </section>

    <section v-else-if="!loading && !error" class="panel-card">
      <h2>{{ TEXT.emptyTitle }}</h2>
      <p class="empty-note">{{ TEXT.emptyDesc }}</p>
    </section>
  </main>
</template>
