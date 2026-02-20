<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { fetchNotifications } from "./api";
import { useAuth } from "./composables/useAuth";

const TEXT = {
  explore: "\u63a2\u7d22\u5e7f\u573a",
  mine: "\u6211\u7684\u884c\u7a0b",
  editor: "\u7f16\u8f91\u5668",
  myCorrections: "\u6211\u7684\u7ea0\u9519",
  review: "\u7ea0\u9519\u5ba1\u6838",
  signal: "\u9884\u8b66\u4e2d\u5fc3",
  traveler: "\u65c5\u884c\u8005",
  logout: "\u9000\u51fa",
  login: "\u767b\u5f55"
} as const;

const route = useRoute();
const router = useRouter();
const { isLoggedIn, user, token, clearAuth, loadMe } = useAuth();
const unreadCount = ref(0);

function isActive(path: string): boolean {
  return route.path === path;
}

async function loadUnreadCount() {
  if (!token.value) {
    unreadCount.value = 0;
    return;
  }
  try {
    const data = await fetchNotifications(token.value, 0, 1, false);
    unreadCount.value = data.unread_count;
  } catch {
    unreadCount.value = 0;
  }
}

async function handleLogout() {
  clearAuth();
  unreadCount.value = 0;
  await router.push("/explore");
}

onMounted(() => {
  void loadMe();
  void loadUnreadCount();
});

watch(
  () => route.fullPath,
  () => {
    void loadUnreadCount();
  }
);
</script>

<template>
  <div>
    <header class="site-nav">
      <div class="site-nav-inner">
        <RouterLink class="site-brand" to="/explore">Project Atlas</RouterLink>
        <nav class="site-links">
          <RouterLink :class="['site-link', { active: isActive('/explore') }]" to="/explore">{{ TEXT.explore }}</RouterLink>
          <RouterLink :class="['site-link', { active: isActive('/mine') }]" to="/mine">{{ TEXT.mine }}</RouterLink>
          <RouterLink :class="['site-link', { active: isActive('/editor') }]" to="/editor">{{ TEXT.editor }}</RouterLink>
          <RouterLink :class="['site-link', { active: isActive('/corrections/mine') }]" to="/corrections/mine">{{ TEXT.myCorrections }}</RouterLink>
          <RouterLink :class="['site-link', { active: isActive('/corrections/review') }]" to="/corrections/review">{{ TEXT.review }}</RouterLink>
          <RouterLink :class="['site-link', { active: isActive('/notifications') }]" to="/notifications">
            {{ TEXT.signal }}
            <span v-if="unreadCount > 0" class="nav-badge">{{ unreadCount }}</span>
          </RouterLink>
        </nav>
        <div class="site-user">
          <template v-if="isLoggedIn">
            <span>{{ user?.nickname || TEXT.traveler }}</span>
            <button class="btn ghost" @click="handleLogout">{{ TEXT.logout }}</button>
          </template>
          <RouterLink v-else class="btn" to="/login">{{ TEXT.login }}</RouterLink>
        </div>
      </div>
    </header>
    <RouterView />
  </div>
</template>
