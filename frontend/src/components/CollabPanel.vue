<script setup lang="ts">
import type { CollabHistoryItem, CollabLinkResponse, CollabParticipant } from "../api";

defineProps<{
  collabConnected: boolean;
  collabPermission: "edit" | "read";
  canManageCollabLinks: boolean;
  canSaveToServer: boolean;
  collabError: string;
  collabWsError: string;
  collabParticipants: CollabParticipant[];
  
  collabCreatePending: boolean;
  selectedItineraryId: string;
  collabShareCode: string;
  collabShareUrl: string;
  collabLinks: CollabLinkResponse[];
  
  collabHistoryLoading: boolean;
  meaningfulCollabHistory: CollabHistoryItem[];
}>();

const collabPermissionDraft = defineModel<"edit" | "read">("collabPermissionDraft", { default: "read" });

const emit = defineEmits<{
  (event: "createCollabLink"): void;
  (event: "copyShareCode", code: string): void;
  (event: "toggleLinkPermission", id: string, targetPermission: "edit" | "read"): void;
  (event: "revokeLink", id: string): void;
  (event: "loadHistoryMore"): void;
}>();

// Re-use logic for history label if needed, or just format the payload here
function resolveHistoryActionLabel(item: CollabHistoryItem): string {
  const payload = item.payload || {};
  if (typeof payload.description === "string" && payload.description) {
    return payload.description;
  }
  const originFromMeta =
    payload &&
    typeof payload === "object" &&
    payload.meta &&
    typeof payload.meta === "object" &&
    typeof (payload.meta as { origin?: unknown }).origin === "string"
      ? String((payload.meta as { origin?: unknown }).origin)
      : "";
  const origin = originFromMeta || (typeof payload.origin === "string" ? payload.origin : "");
  if (origin === "start-date") {
    return "更新了开始日期";
  }
  if (origin === "draft-items") {
    return "更新了时间轴内容";
  }
  return "编辑了协作内容";
}
</script>

<template>
  <div class="panel-card collab-panel">
    <h2>协作管理</h2>
    
    <div class="collab-status-block">
      <h3>实时协作状态</h3>
      <p class="subtle">
        连接状态：<span :class="collabConnected ? 'text-success' : 'text-danger'">{{ collabConnected ? "已连接" : "未连接" }}</span> · 当前权限：{{ collabPermission === "edit" ? "可编辑" : "只读" }}
      </p>
      <p
        v-if="!canManageCollabLinks"
        class="subtle"
      >
        当前为协作者模式：{{ canSaveToServer ? "可保存到服务器" : "只读协作" }}
      </p>
      <p
        v-if="collabError"
        class="error"
      >
        {{ collabError }}
      </p>
      <p
        v-if="collabWsError"
        class="error"
      >
        {{ collabWsError }}
      </p>
      
      <div class="subtle mt-2">
        在线协作者：{{ collabParticipants.length }}
      </div>
      <ul class="mini-list">
        <li
          v-for="participant in collabParticipants"
          :key="participant.session_id"
        >
          {{ participant.display_name }}（{{ participant.permission === "edit" ? "编辑" : "只读" }}）
        </li>
      </ul>
    </div>
    
    <div class="divider-line" />

    <div class="collab-links-block">
      <h3>分享与权限设置</h3>
      <div class="action-row mt-2">
        <select
          v-model="collabPermissionDraft"
          class="input flex-1"
          :disabled="collabCreatePending || !selectedItineraryId || !canManageCollabLinks"
        >
          <option value="edit">新分享码默认可编辑</option>
          <option value="read">新分享码默认只读</option>
        </select>
        <button
          class="btn primary"
          :disabled="collabCreatePending || !selectedItineraryId || !canManageCollabLinks"
          @click="emit('createCollabLink')"
        >
          {{ collabCreatePending ? "生成中..." : "生成分享码" }}
        </button>
      </div>
      <p v-if="collabShareCode" class="hint mt-2">
        最新分享码：<strong>{{ collabShareCode }}</strong>
      </p>
      <button
        v-if="collabShareCode"
        class="btn ghost block mt-2"
        @click="emit('copyShareCode', collabShareCode)"
      >
        复制最新分享码
      </button>
      
      <h4 v-if="collabLinks.length > 0" class="mt-4 text-sm font-medium">已生效的分享连接</h4>
      <ul class="mini-list mt-2">
        <li
          v-for="link in collabLinks"
          :key="link.id"
          class="flex items-center justify-between"
        >
          <span>
            {{ link.permission === "edit" ? "编辑" : "只读" }} · 码尾 {{ link.share_code_last4 }}
          </span>
          <div class="inline-actions">
            <button
              class="btn ghost small"
              :disabled="!canManageCollabLinks"
              @click="emit('toggleLinkPermission', link.id, link.permission === 'edit' ? 'read' : 'edit')"
            >
              切权限
            </button>
            <button
              class="btn danger small"
              :disabled="!canManageCollabLinks"
              @click="emit('revokeLink', link.id)"
            >
              撤销
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div class="divider-line" />

    <div class="collab-history-block">
      <h3>协作历史</h3>
      <p class="subtle">基于每 10 秒的状态快照差异。</p>
      <p
        v-if="collabHistoryLoading"
        class="subtle mt-2"
      >
        加载记录中...
      </p>
      <ul class="mini-list history-list mt-2">
        <li
          v-for="item in meaningfulCollabHistory"
          :key="item.id"
          class="history-item"
        >
          <span class="subtle time">{{ new Date(item.created_at).toLocaleTimeString() }}</span>
          <span class="author">{{ item.actor_type === "guest" ? (item.guest_name || "访客") : ("用户 " + (item.actor_user_id?.slice(0, 4) || "某人")) }}:</span>
          <span class="action">{{ resolveHistoryActionLabel(item) }}</span>
        </li>
      </ul>
      <button
        v-if="meaningfulCollabHistory.length > 0"
        class="btn ghost block mt-2"
        :disabled="collabHistoryLoading"
        @click="emit('loadHistoryMore')"
      >
        加载更多历史
      </button>
    </div>
  </div>
</template>

<style scoped>
.collab-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

h3 {
  font-size: 14px;
  margin-bottom: 4px;
  color: var(--text-primary);
}

.text-success { color: var(--success-default); }
.text-danger { color: var(--error-default); }
.flex-1 { flex: 1; min-width: 0; }
.block { width: 100%; }
.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }

.history-list {
  max-height: 250px;
  overflow-y: auto;
  padding-right: 4px;
  font-size: 13px;
}

.history-item {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  line-height: 1.4;
  padding: 4px 0;
  border-bottom: 1px dashed var(--border-subtle);
}

.history-item:last-child {
  border-bottom: none;
}

.history-item .time {
  white-space: nowrap;
  font-size: 11px;
}

.history-item .author {
  font-weight: 500;
  color: var(--primary-default);
  white-space: nowrap;
}

.history-item .action {
  color: var(--text-primary);
  word-break: break-all;
}
</style>
