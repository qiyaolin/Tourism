<script setup lang="ts">
import { computed } from "vue";
import type { CollabParticipant } from "../api";

const props = defineProps<{
  participants: CollabParticipant[];
  currentUserId: string | null;
}>();

// Generate a deterministic color based on user ID or guest name
function getAvatarColor(participant: CollabParticipant): string {
  const id = participant.participant_user_id || participant.display_name || participant.session_id;
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash % 360);
  return `hsl(${hue}, 70%, 40%)`;
}

function getAvatarInitials(participant: CollabParticipant): string {
  if (participant.display_name) {
    return participant.display_name.slice(0, 1).toUpperCase();
  }
  return "👤"; // Fallback for users depending on API or anonymous
}

const uniqueParticipants = computed(() => {
  // Deduplicate by user ID if possible, keeping the most recent session
  const map = new Map<string, CollabParticipant>();
  for (const p of props.participants) {
    const key = p.participant_user_id || p.display_name || p.session_id;
    map.set(key, p);
  }
  return Array.from(map.values());
});
</script>

<template>
  <div class="collab-avatar-bar">
    <div
      v-for="p in uniqueParticipants"
      :key="p.session_id"
      class="collab-avatar"
      :class="{ 'is-me': p.participant_user_id === currentUserId }"
      :style="{ backgroundColor: getAvatarColor(p) }"
      :title="`${p.display_name || '用户'} (${p.permission === 'edit' ? '可编辑' : '只读'})`"
    >
      {{ getAvatarInitials(p) }}
    </div>
    <span
      v-if="uniqueParticipants.length > 0"
      class="collab-count"
    >
      {{ uniqueParticipants.length }} 人在线
    </span>
  </div>
</template>

<style scoped>
.collab-avatar-bar {
  display: flex;
  align-items: center;
  padding: 0 8px;
}

.collab-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  border: 2px solid var(--surface-default);
  margin-left: -8px;
  cursor: help;
  user-select: none;
  transition: transform 0.2s ease, z-index 0.2s;
  position: relative;
  z-index: 1;
}

.collab-avatar:hover {
  transform: translateY(-2px);
  z-index: 10;
}

.collab-avatar:first-child {
  margin-left: 0;
}

.collab-avatar.is-me {
  border-color: var(--success-default);
}

.collab-count {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
