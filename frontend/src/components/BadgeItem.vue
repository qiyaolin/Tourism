<template>
  <div class="badge-item" :class="{ 'is-locked': !unlocked }">
    <div class="icon-wrapper">
      <img v-if="badge.icon_url" :src="badge.icon_url" alt="徽章图标" class="badge-icon" />
      <div v-else class="default-icon" title="No matching icon">🎖️</div>
    </div>
    <div class="badge-info">
      <h4>{{ badge.name }}</h4>
      <p>{{ badge.description }}</p>
      <span v-if="unlocked" class="unlock-date">解锁于: {{ formatDate(unlockedAt) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';
import type { BadgeDefResponse } from '../api';

defineProps<{
  badge: BadgeDefResponse;
  unlocked?: boolean;
  unlockedAt?: string;
}>();

const formatDate = (dateString?: string) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
};
</script>

<style scoped>
.badge-item {
  display: flex;
  align-items: center;
  padding: 1rem;
  border-radius: 8px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  transition: all 0.3s ease;
  gap: 1rem;
}
.badge-item.is-locked {
  filter: grayscale(100%);
  opacity: 0.6;
}
.icon-wrapper {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  overflow: hidden;
  flex-shrink: 0;
}
.badge-icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.badge-info h4 {
  margin: 0 0 0.25rem 0;
  color: #2b2b2b;
}
.badge-info p {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #666;
}
.unlock-date {
  font-size: 0.75rem;
  color: #aaa;
}
</style>
