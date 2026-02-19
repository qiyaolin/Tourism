<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { deleteItinerary, fetchItineraries, updateItinerary, type ItineraryResponse } from "../api";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import { useAuth } from "../composables/useAuth";

const loading = ref(false);
const error = ref("");
const actionPendingId = ref("");
const items = ref<ItineraryResponse[]>([]);
const coverDraftById = ref<Record<string, string>>({});
const discardDialogOpen = ref(false);
const discardTargetId = ref("");

const { token, user, loadMe } = useAuth();

const draftItems = computed(() => items.value.filter((item) => item.status === "draft"));
const progressItems = computed(() => items.value.filter((item) => item.status === "in_progress"));
const publishedItems = computed(() => items.value.filter((item) => item.status === "published"));

function fillCoverDraft(data: ItineraryResponse[]) {
  coverDraftById.value = data.reduce<Record<string, string>>((acc, itinerary) => {
    acc[itinerary.id] = itinerary.cover_image_url || "";
    return acc;
  }, {});
}

async function loadItineraryList() {
  if (!token.value) {
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const result = await fetchItineraries(token.value);
    items.value = result.items;
    fillCoverDraft(result.items);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载我的行程失败";
  } finally {
    loading.value = false;
  }
}

async function patchItinerary(itineraryId: string, payload: Parameters<typeof updateItinerary>[1]) {
  if (!token.value) {
    return;
  }
  actionPendingId.value = itineraryId;
  error.value = "";
  try {
    await updateItinerary(itineraryId, payload, token.value);
    await loadItineraryList();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "更新行程失败";
  } finally {
    actionPendingId.value = "";
  }
}

async function publishItinerary(itineraryId: string) {
  await patchItinerary(itineraryId, { status: "published", visibility: "public" });
}

async function unpublishItinerary(itineraryId: string) {
  await patchItinerary(itineraryId, { status: "in_progress", visibility: "private" });
}

async function saveCover(itineraryId: string) {
  const value = coverDraftById.value[itineraryId]?.trim() ?? "";
  await patchItinerary(itineraryId, { cover_image_url: value || null });
}

function openDiscardDialog(itineraryId: string) {
  discardTargetId.value = itineraryId;
  discardDialogOpen.value = true;
}

function closeDiscardDialog() {
  discardDialogOpen.value = false;
  discardTargetId.value = "";
}

async function discardItinerary() {
  if (!token.value) {
    return;
  }
  if (!discardTargetId.value) {
    return;
  }
  const itineraryId = discardTargetId.value;
  actionPendingId.value = itineraryId;
  error.value = "";
  try {
    await deleteItinerary(itineraryId, token.value);
    await loadItineraryList();
    closeDiscardDialog();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "作废行程失败";
  } finally {
    actionPendingId.value = "";
  }
}

const discardTargetTitle = computed(() => {
  const target = items.value.find((item) => item.id === discardTargetId.value);
  return target?.title || "该行程";
});

onMounted(async () => {
  await loadMe();
  await loadItineraryList();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">
          My Trips
        </p>
        <h1>我的行程</h1>
      </div>
      <RouterLink
        class="btn primary"
        to="/editor"
      >
        进入编辑器
      </RouterLink>
    </header>
    <p class="subtle">
      当前用户：{{ user?.nickname || "未登录" }}。在这里管理发布状态和封面图链接。
    </p>
    <p
      v-if="error"
      class="error"
    >
      {{ error }}
    </p>

    <section class="mine-sections">
      <div class="panel-card">
        <h2>草稿箱</h2>
        <div
          v-if="draftItems.length === 0"
          class="empty-note"
        >
          暂无草稿行程。
        </div>
        <article
          v-for="item in draftItems"
          :key="item.id"
          class="mine-card"
        >
          <h3>{{ item.title }}</h3>
          <p class="subtle">
            {{ item.destination }} · {{ item.days }} 天
          </p>
          <button
            class="btn"
            :disabled="actionPendingId === item.id"
            @click="patchItinerary(item.id, { status: 'in_progress' })"
          >
            开始推进
          </button>
          <button
            class="btn danger"
            :disabled="actionPendingId === item.id"
            @click="openDiscardDialog(item.id)"
          >
            作废行程
          </button>
        </article>
      </div>

      <div class="panel-card">
        <h2>进行中</h2>
        <div
          v-if="progressItems.length === 0"
          class="empty-note"
        >
          暂无进行中行程。
        </div>
        <article
          v-for="item in progressItems"
          :key="item.id"
          class="mine-card"
        >
          <h3>{{ item.title }}</h3>
          <p class="subtle">
            {{ item.destination }} · {{ item.days }} 天
          </p>
          <p
            v-if="item.fork_source_itinerary_id"
            class="subtle"
          >
            派生自 @{{ item.fork_source_author_nickname || "未知作者" }} 的《{{ item.fork_source_title || "未命名行程" }}》
          </p>
          <label class="field-label">封面图 URL</label>
          <input
            v-model="coverDraftById[item.id]"
            class="input"
            placeholder="https://..."
          >
          <div class="action-row">
            <button
              class="btn"
              :disabled="actionPendingId === item.id"
              @click="saveCover(item.id)"
            >
              保存封面
            </button>
            <button
              class="btn primary"
              :disabled="actionPendingId === item.id"
              @click="publishItinerary(item.id)"
            >
              发布到广场
            </button>
            <button
              class="btn danger"
              :disabled="actionPendingId === item.id"
              @click="openDiscardDialog(item.id)"
            >
              作废行程
            </button>
          </div>
        </article>
      </div>

      <div class="panel-card">
        <h2>已发布</h2>
        <div
          v-if="publishedItems.length === 0"
          class="empty-note"
        >
          暂无已发布行程。
        </div>
        <article
          v-for="item in publishedItems"
          :key="item.id"
          class="mine-card"
        >
          <h3>{{ item.title }}</h3>
          <p class="subtle">
            {{ item.destination }} · {{ item.days }} 天 · 已公开
          </p>
          <p
            v-if="item.fork_source_itinerary_id"
            class="subtle"
          >
            派生自 @{{ item.fork_source_author_nickname || "未知作者" }} 的《{{ item.fork_source_title || "未命名行程" }}》
          </p>
          <div class="action-row">
            <RouterLink
              class="btn ghost"
              :to="`/itineraries/${item.id}`"
            >
              预览公开页
            </RouterLink>
            <button
              class="btn danger"
              :disabled="actionPendingId === item.id"
              @click="unpublishItinerary(item.id)"
            >
              撤回发布
            </button>
            <button
              class="btn danger"
              :disabled="actionPendingId === item.id"
              @click="openDiscardDialog(item.id)"
            >
              作废行程
            </button>
          </div>
        </article>
      </div>
    </section>

    <p
      v-if="loading"
      class="subtle"
    >
      加载中...
    </p>

    <ConfirmDialog
      :open="discardDialogOpen"
      title="确认作废行程"
      :message="`确认作废《${discardTargetTitle}》？作废后无法恢复。`"
      confirm-text="确认作废"
      cancel-text="暂不作废"
      :danger="true"
      :loading="Boolean(actionPendingId)"
      @cancel="closeDiscardDialog"
      @confirm="discardItinerary"
    />
  </main>
</template>
