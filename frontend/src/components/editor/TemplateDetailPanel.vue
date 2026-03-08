<script setup lang="ts">
import { ref } from "vue";
import type { TemplateApiResponse } from "../../api";

defineProps<{
  template: TemplateApiResponse | null;
  open: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "rate", data: { score: number; comment: string | null }): void;
  (e: "fork"): void;
}>();

const score = ref(0);
const hoverScore = ref(0);
const comment = ref("");

function handleRate() {
  if (score.value < 1) return;
  emit("rate", {
    score: score.value,
    comment: comment.value.trim() || null,
  });
}

function formatRating(val: number | null): string {
  return val != null ? val.toFixed(1) : "-";
}
</script>

<template>
  <transition name="slide-up">
    <div v-if="open && template" class="template-detail-panel">
      <div class="panel-header">
        <h3 class="panel-title">{{ template.title }}</h3>
        <button class="panel-close" @click="emit('close')">✕</button>
      </div>

      <div class="panel-body">
        <!-- Info -->
        <div class="info-section">
          <div class="info-row">
            <span class="info-label">作者</span>
            <span class="info-value">{{ template.author_nickname || '匿名' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">类型</span>
            <span class="info-value">{{ template.is_group ? '📦 组合' : template.block_type }}</span>
          </div>
          <div v-if="template.description" class="info-row">
            <span class="info-label">描述</span>
            <span class="info-value">{{ template.description }}</span>
          </div>
          <div v-if="template.region_name" class="info-row">
            <span class="info-label">地区</span>
            <span class="info-value">{{ template.region_name }}</span>
          </div>
        </div>

        <!-- Stats -->
        <div class="stats-row">
          <div class="stat">
            <span class="stat-value">⭐ {{ formatRating(template.rating_avg) }}</span>
            <span class="stat-label">评分 ({{ template.rating_count }})</span>
          </div>
          <div class="stat">
            <span class="stat-value">🔄 {{ template.fork_count }}</span>
            <span class="stat-label">使用次数</span>
          </div>
        </div>

        <!-- Tags -->
        <div v-if="template.style_tags?.length" class="tags-row">
          <span v-for="tag in template.style_tags" :key="tag" class="tag">{{ tag }}</span>
        </div>

        <!-- Children preview for groups -->
        <div v-if="template.is_group && template.children_snapshot?.length" class="children-section">
          <div class="section-label">包含 {{ template.children_snapshot.length }} 个子项</div>
          <div v-for="(child, idx) in template.children_snapshot" :key="idx" class="child-item">
            <span>{{ String(child.title || '未命名') }}</span>
            <span class="child-type">{{ String(child.block_type || 'scenic') }}</span>
          </div>
        </div>

        <!-- Rating form -->
        <div class="rating-section">
          <div class="section-label">评分</div>
          <div class="stars">
            <button
              v-for="s in 5"
              :key="s"
              class="star-btn"
              :class="{ filled: s <= (hoverScore || score) }"
              @mouseenter="hoverScore = s"
              @mouseleave="hoverScore = 0"
              @click="score = s"
            >
              ★
            </button>
          </div>
          <textarea v-model="comment" class="rating-comment" rows="2" placeholder="留下评价..." />
          <button
            class="rate-btn"
            :disabled="score < 1"
            @click="handleRate"
          >
            提交评分
          </button>
        </div>
      </div>

      <div class="panel-footer">
        <button class="fork-btn" @click="emit('fork')">📥 添加到我的行程</button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.template-detail-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 340px;
  max-width: 100%;
  height: 100%;
  background: var(--surface-2, #1e1e2e);
  border-left: 1px solid rgba(255,255,255,0.06);
  box-shadow: -4px 0 20px rgba(0,0,0,0.3);
  display: flex;
  flex-direction: column;
  z-index: 10;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.panel-title {
  flex: 1;
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #e8e8e8);
}
.panel-close {
  background: none;
  border: none;
  color: var(--text-secondary, #a0a0a0);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
}
.panel-close:hover { background: rgba(255,255,255,0.08); }

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.info-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
}
.info-label {
  color: var(--text-secondary, #a0a0a0);
  flex-shrink: 0;
  min-width: 40px;
}
.info-value {
  color: var(--text-primary, #e8e8e8);
}

.stats-row {
  display: flex;
  gap: 20px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-value { font-size: 14px; font-weight: 600; }
.stat-label { font-size: 11px; color: var(--text-secondary, #a0a0a0); }

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tag {
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(124,92,255,0.12);
  color: var(--accent, #7c5cff);
  font-size: 11px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #a0a0a0);
  margin-bottom: 4px;
}

.children-section {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 10px;
}
.child-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 8px;
  font-size: 13px;
  color: var(--text-primary, #e8e8e8);
  background: rgba(255,255,255,0.03);
  border-radius: 4px;
  margin-bottom: 3px;
}
.child-type {
  font-size: 11px;
  color: var(--text-secondary, #a0a0a0);
}

.rating-section {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 10px;
}
.stars {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}
.star-btn {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  color: rgba(255,255,255,0.15);
  transition: color 0.15s, transform 0.1s;
}
.star-btn.filled { color: #FFD700; }
.star-btn:hover { transform: scale(1.15); }

.rating-comment {
  width: 100%;
  padding: 8px 10px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-primary, #e8e8e8);
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
  margin-bottom: 8px;
}
.rate-btn {
  width: 100%;
  padding: 8px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-primary, #e8e8e8);
  font-size: 13px;
  cursor: pointer;
}
.rate-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.rate-btn:not(:disabled):hover { background: rgba(255,255,255,0.1); }

.panel-footer {
  padding: 12px 18px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.fork-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: var(--accent, #7c5cff);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.fork-btn:hover { opacity: 0.9; }

.slide-up-enter-active, .slide-up-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.slide-up-enter-from { transform: translateX(100%); opacity: 0; }
.slide-up-leave-to { transform: translateX(100%); opacity: 0; }
</style>
