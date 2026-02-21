<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { resolveCollabCode } from "../api";
import { useAuth } from "../composables/useAuth";

const route = useRoute();
const router = useRouter();
const { token, setCollabGrant } = useAuth();

const shareCode = ref("");
const loading = ref(false);
const error = ref("");
const success = ref("");

onMounted(() => {
  if (typeof route.query.code === "string") {
    shareCode.value = route.query.code.trim().toUpperCase();
  }
});

async function handleJoin() {
  if (!token.value) {
    error.value = "请先登录后再加入协作";
    return;
  }
  const code = shareCode.value.trim().toUpperCase();
  if (!code) {
    error.value = "请输入分享码";
    return;
  }
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    const result = await resolveCollabCode(code, token.value);
    setCollabGrant(result.itinerary_id, {
      grant: result.collab_grant,
      permission: result.permission,
      itineraryTitle: result.itinerary_title,
      expiresIn: result.expires_in
    });
    success.value = `已加入《${result.itinerary_title}》协作，正在跳转编辑器`;
    await router.push(`/editor?itinerary_id=${encodeURIComponent(result.itinerary_id)}`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加入协作失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="atlas-root">
    <section class="auth-shell">
      <h2>输入分享码加入协作</h2>
      <p class="subtle">
        输入拥有者提供的分享码后，可自动进入可编辑/可查看的行程编辑器。
      </p>
      <label class="field-label">分享码</label>
      <input
        v-model="shareCode"
        class="input"
        placeholder="例如：A9K3M2QX"
      >
      <div class="action-row">
        <button
          class="btn primary"
          :disabled="loading"
          @click="handleJoin"
        >
          {{ loading ? "加入中..." : "加入协作" }}
        </button>
      </div>
      <p
        v-if="success"
        class="hint"
      >
        {{ success }}
      </p>
      <p
        v-if="error"
        class="error"
      >
        {{ error }}
      </p>
    </section>
  </main>
</template>
