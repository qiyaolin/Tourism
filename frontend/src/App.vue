<script setup lang="ts">
import { onMounted } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { useAuth } from "./composables/useAuth";

const route = useRoute();
const router = useRouter();
const { isLoggedIn, user, clearAuth, loadMe } = useAuth();

function isActive(path: string): boolean {
  return route.path === path;
}

async function handleLogout() {
  clearAuth();
  await router.push("/explore");
}

onMounted(() => {
  void loadMe();
});
</script>

<template>
  <div>
    <header class="site-nav">
      <div class="site-nav-inner">
        <RouterLink
          class="site-brand"
          to="/explore"
        >
          Project Atlas
        </RouterLink>
        <nav class="site-links">
          <RouterLink
            :class="['site-link', { active: isActive('/explore') }]"
            to="/explore"
          >
            探索广场
          </RouterLink>
          <RouterLink
            :class="['site-link', { active: isActive('/mine') }]"
            to="/mine"
          >
            我的行程
          </RouterLink>
          <RouterLink
            :class="['site-link', { active: isActive('/editor') }]"
            to="/editor"
          >
            编辑器
          </RouterLink>
        </nav>
        <div class="site-user">
          <template v-if="isLoggedIn">
            <span>{{ user?.nickname || "Traveler" }}</span>
            <button
              class="btn ghost"
              @click="handleLogout"
            >
              退出
            </button>
          </template>
          <RouterLink
            v-else
            class="btn"
            to="/login"
          >
            登录
          </RouterLink>
        </div>
      </div>
    </header>
    <RouterView />
  </div>
</template>
