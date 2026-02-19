<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuth } from "../composables/useAuth";
import { isCnPhone, normalizePhone } from "../utils/validators";

const phone = ref("");
const code = ref("");
const nickname = ref("");
const sendCooldown = ref(0);
const router = useRouter();
const route = useRoute();

const { loading, error, debugCode, sendLoginCode, loginWithCode } = useAuth();

const canSend = computed(() => !loading.value && sendCooldown.value <= 0);

let timer: ReturnType<typeof setInterval> | null = null;

function startCooldown(seconds: number) {
  sendCooldown.value = seconds;
  if (timer) {
    clearInterval(timer);
  }
  timer = setInterval(() => {
    sendCooldown.value -= 1;
    if (sendCooldown.value <= 0) {
      sendCooldown.value = 0;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }
  }, 1000);
}

async function handleSendCode() {
  const normalized = normalizePhone(phone.value);
  if (!isCnPhone(normalized)) {
    return;
  }
  phone.value = normalized;
  const result = await sendLoginCode(normalized);
  startCooldown(60);
  if (result.debug_code) {
    code.value = result.debug_code;
  }
}

async function handleLogin() {
  const normalized = normalizePhone(phone.value);
  if (!isCnPhone(normalized)) {
    return;
  }
  phone.value = normalized;
  await loginWithCode(normalized, code.value.trim(), nickname.value.trim());
  const forkSource = typeof route.query.fork_source === "string" ? route.query.fork_source.trim() : "";
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect.trim() : "";
  if (forkSource) {
    await router.push(`/itineraries/${forkSource}?auto_fork=1`);
    return;
  }
  if (redirect) {
    await router.push(redirect);
    return;
  }
  await router.push("/mine");
}

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
});
</script>

<template>
  <main class="atlas-root">
    <section class="auth-shell">
      <h2>登录 / 注册</h2>
      <p class="subtle">
        登录后管理我的行程、发布探索广场内容。
      </p>
      <label class="field-label">手机号</label>
      <input
        v-model="phone"
        class="input"
        placeholder="请输入中国大陆手机号"
      >
      <div class="action-row">
        <button
          class="btn"
          :disabled="!canSend"
          @click="handleSendCode"
        >
          {{ sendCooldown > 0 ? `${sendCooldown}s 后重试` : "发送验证码" }}
        </button>
      </div>
      <label class="field-label">验证码</label>
      <input
        v-model="code"
        class="input"
        placeholder="请输入 6 位验证码"
      >
      <label class="field-label">昵称（首次注册可选）</label>
      <input
        v-model="nickname"
        class="input"
        placeholder="不填则自动生成"
      >
      <div class="action-row">
        <button
          class="btn primary"
          :disabled="loading"
          @click="handleLogin"
        >
          登录 / 注册
        </button>
      </div>
      <p
        v-if="debugCode"
        class="hint"
      >
        开发模式验证码：{{ debugCode }}
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
