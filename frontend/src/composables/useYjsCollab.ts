import { computed, onBeforeUnmount, ref } from "vue";
import * as Y from "yjs";

import type { CollabParticipant } from "../api";

type CollabState = {
  start_date: string;
  items: unknown[];
};

type UseYjsCollabOptions = {
  itineraryId: () => string;
  authToken: () => string;
  collabGrant: () => string;
  getLocalState: () => CollabState;
  applyRemoteState: (state: CollabState) => void;
};

type JoinedPayload = {
  type: "collab:joined";
  permission: "edit" | "read";
  participants: CollabParticipant[];
  snapshot_update_b64: string | null;
  needs_seed: boolean;
};

type PresencePayload = {
  type: "collab:presence";
  participants: CollabParticipant[];
};

type UpdatePayload = {
  type: "collab:update";
  update_b64: string;
  session_id: string;
  meta?: Record<string, unknown>;
};

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function useYjsCollab(options: UseYjsCollabOptions) {
  const ws = ref<WebSocket | null>(null);
  const ydoc = new Y.Doc();
  const root = ydoc.getMap<unknown>("atlas");

  const participants = ref<CollabParticipant[]>([]);
  const permission = ref<"edit" | "read">("read");
  const connected = ref(false);
  const error = ref("");

  let suppressLocalEmit = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let connectKey = "";

  function normalizeParticipants(items: CollabParticipant[]): CollabParticipant[] {
    const dedup = new Map<string, CollabParticipant>();
    for (const item of items) {
      const key = item.participant_user_id
        ? `user:${item.participant_user_id}`
        : `session:${item.session_id}`;
      const existed = dedup.get(key);
      if (!existed) {
        dedup.set(key, item);
        continue;
      }
      if (Date.parse(item.joined_at) >= Date.parse(existed.joined_at)) {
        dedup.set(key, item);
      }
    }
    return [...dedup.values()].sort((a, b) => Date.parse(a.joined_at) - Date.parse(b.joined_at));
  }

  function extractStateFromDoc(): CollabState {
    const startDate = root.get("start_date");
    const items = root.get("items");
    return {
      start_date: typeof startDate === "string" ? startDate : "",
      items: Array.isArray(items) ? (items as unknown[]) : []
    };
  }

  function pushLocalState(state: CollabState, origin = "local-sync") {
    suppressLocalEmit = true;
    ydoc.transact(() => {
      root.set("start_date", state.start_date || "");
      root.set("items", state.items);
    }, origin);
    suppressLocalEmit = false;
  }

  function sendUpdate(update: Uint8Array, meta: Record<string, unknown> = {}) {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.value.send(
      JSON.stringify({
        type: "collab:update",
        update_b64: bytesToBase64(update),
        meta
      })
    );
  }

  function scheduleReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    reconnectTimer = setTimeout(() => {
      connect();
    }, 1500);
  }

  function disconnect() {
    connectKey = "";
    connected.value = false;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws.value) {
      ws.value.onopen = null;
      ws.value.onmessage = null;
      ws.value.onerror = null;
      ws.value.onclose = null;
      ws.value.close();
      ws.value = null;
    }
  }

  function connect() {
    const itineraryId = options.itineraryId();
    if (!itineraryId) {
      return;
    }
    const token = options.authToken();
    const collabGrant = options.collabGrant();
    const nextKey = `${itineraryId}::${token}::${collabGrant}`;
    if (
      ws.value &&
      connectKey === nextKey &&
      (ws.value.readyState === WebSocket.OPEN || ws.value.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    disconnect();
    connectKey = nextKey;
    const apiBase = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/api\/v1$/, "");
    const wsBase = apiBase.replace(/^http/, "ws");
    const url = new URL(`${wsBase}/api/v1/itineraries/${itineraryId}/collab/ws`);
    if (token) {
      url.searchParams.set("token", token);
    }
    if (collabGrant) {
      url.searchParams.set("collab_grant", collabGrant);
    }

    ws.value = new WebSocket(url.toString());
    ws.value.onopen = () => {
      connected.value = true;
      error.value = "";
    };
    ws.value.onclose = () => {
      connected.value = false;
      scheduleReconnect();
    };
    ws.value.onerror = () => {
      error.value = "实时协作连接失败";
    };
    ws.value.onmessage = (event) => {
      let payload: unknown = null;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!payload || typeof payload !== "object" || !("type" in payload)) {
        return;
      }
      const type = (payload as { type: string }).type;
      if (type === "collab:error") {
        const message = (payload as { message?: string }).message;
        error.value = message || "实时协作错误";
        return;
      }
      if (type === "collab:joined") {
        const joined = payload as JoinedPayload;
        permission.value = joined.permission;
        participants.value = normalizeParticipants(joined.participants || []);
        if (joined.snapshot_update_b64) {
          Y.applyUpdate(ydoc, base64ToBytes(joined.snapshot_update_b64), "remote");
        }
        if (joined.needs_seed) {
          pushLocalState(options.getLocalState(), "seed");
          sendUpdate(Y.encodeStateAsUpdate(ydoc), { origin: "seed", reason: "seed" });
        } else {
          options.applyRemoteState(extractStateFromDoc());
        }
        return;
      }
      if (type === "collab:presence") {
        const presence = payload as PresencePayload;
        participants.value = normalizeParticipants(presence.participants || []);
        return;
      }
      if (type === "collab:update") {
        const updatePayload = payload as UpdatePayload;
        if (!updatePayload.update_b64) {
          return;
        }
        Y.applyUpdate(ydoc, base64ToBytes(updatePayload.update_b64), "remote");
        options.applyRemoteState(extractStateFromDoc());
      }
    };
  }

  ydoc.on("update", (_update: Uint8Array, origin: unknown) => {
    if (suppressLocalEmit) {
      return;
    }
    if (origin === "remote") {
      return;
    }
    if (permission.value !== "edit") {
      return;
    }
    sendUpdate(Y.encodeStateAsUpdate(ydoc), { origin: typeof origin === "string" ? origin : "local" });
  });

  onBeforeUnmount(() => {
    disconnect();
    ydoc.destroy();
  });

  return {
    participants: computed(() => participants.value),
    permission: computed(() => permission.value),
    connected: computed(() => connected.value),
    error: computed(() => error.value),
    connect,
    disconnect,
    pushLocalState
  };
}
