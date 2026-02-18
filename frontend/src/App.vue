<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchLiveHealth, fetchReadyHealth } from "./api";

const loading = ref(true);
const error = ref("");
const live = ref("");
const ready = ref("");

async function loadHealth() {
  loading.value = true;
  error.value = "";
  try {
    const [liveData, readyData] = await Promise.all([fetchLiveHealth(), fetchReadyHealth()]);
    live.value = JSON.stringify(liveData, null, 2);
    ready.value = JSON.stringify(readyData, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Unknown error";
  } finally {
    loading.value = false;
  }
}

onMounted(loadHealth);
</script>

<template>
  <main class="container">
    <h1>Project Atlas - Phase 1.1</h1>
    <p class="sub">Frontend and backend connectivity check.</p>

    <button class="btn" @click="loadHealth">Refresh Health</button>

    <p v-if="loading">Loading...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <section v-else class="grid">
      <article>
        <h2>GET /health/live</h2>
        <pre>{{ live }}</pre>
      </article>
      <article>
        <h2>GET /health/ready</h2>
        <pre>{{ ready }}</pre>
      </article>
    </section>
  </main>
</template>

