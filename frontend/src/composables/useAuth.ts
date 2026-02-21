import { computed, ref } from "vue";
import { login, me, sendCode, type AuthUser, type LoginResponse, type SendCodeResponse } from "../services/auth";

const TOKEN_KEY = "atlas_access_token";
const COLLAB_GRANT_PREFIX = "atlas_collab_grant:";

const token = ref<string>(localStorage.getItem(TOKEN_KEY) || "");
const user = ref<AuthUser | null>(null);
const loading = ref(false);
const error = ref("");
const debugCode = ref("");

const isLoggedIn = computed(() => Boolean(token.value));

function setToken(value: string) {
  token.value = value;
  localStorage.setItem(TOKEN_KEY, value);
}

function clearAuth() {
  token.value = "";
  user.value = null;
  localStorage.removeItem(TOKEN_KEY);
  if (typeof sessionStorage !== "undefined") {
    const keys = Object.keys(sessionStorage).filter((key) => key.startsWith(COLLAB_GRANT_PREFIX));
    for (const key of keys) {
      sessionStorage.removeItem(key);
    }
  }
}

type CollabGrantEntry = {
  grant: string;
  permission: "edit" | "read";
  itineraryTitle: string;
  expiresAt: number;
};

function collabGrantKey(itineraryId: string): string {
  return `${COLLAB_GRANT_PREFIX}${itineraryId}`;
}

function setCollabGrant(
  itineraryId: string,
  entry: { grant: string; permission: "edit" | "read"; itineraryTitle: string; expiresIn: number }
) {
  if (typeof sessionStorage === "undefined") {
    return;
  }
  const payload: CollabGrantEntry = {
    grant: entry.grant,
    permission: entry.permission,
    itineraryTitle: entry.itineraryTitle,
    expiresAt: Date.now() + entry.expiresIn * 1000
  };
  sessionStorage.setItem(collabGrantKey(itineraryId), JSON.stringify(payload));
}

function getCollabGrant(itineraryId: string): CollabGrantEntry | null {
  if (!itineraryId || typeof sessionStorage === "undefined") {
    return null;
  }
  const raw = sessionStorage.getItem(collabGrantKey(itineraryId));
  if (!raw) {
    return null;
  }
  try {
    const payload = JSON.parse(raw) as CollabGrantEntry;
    if (!payload.grant || !payload.permission || typeof payload.expiresAt !== "number") {
      sessionStorage.removeItem(collabGrantKey(itineraryId));
      return null;
    }
    if (payload.expiresAt <= Date.now()) {
      sessionStorage.removeItem(collabGrantKey(itineraryId));
      return null;
    }
    return payload;
  } catch {
    sessionStorage.removeItem(collabGrantKey(itineraryId));
    return null;
  }
}

function clearCollabGrant(itineraryId: string) {
  if (!itineraryId || typeof sessionStorage === "undefined") {
    return;
  }
  sessionStorage.removeItem(collabGrantKey(itineraryId));
}

async function sendLoginCode(phone: string): Promise<SendCodeResponse> {
  loading.value = true;
  error.value = "";
  try {
    const result = await sendCode(phone);
    debugCode.value = result.debug_code || "";
    return result;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Send code failed";
    throw e;
  } finally {
    loading.value = false;
  }
}

async function loginWithCode(phone: string, code: string, nickname?: string): Promise<LoginResponse> {
  loading.value = true;
  error.value = "";
  try {
    const result = await login(phone, code, nickname);
    setToken(result.access_token);
    user.value = result.user;
    return result;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Login failed";
    throw e;
  } finally {
    loading.value = false;
  }
}

async function loadMe() {
  if (!token.value) return;
  loading.value = true;
  error.value = "";
  try {
    user.value = await me(token.value);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Get user failed";
    clearAuth();
  } finally {
    loading.value = false;
  }
}

export function useAuth() {
  return {
    token,
    user,
    loading,
    error,
    debugCode,
    isLoggedIn,
    sendLoginCode,
    loginWithCode,
    clearAuth,
    loadMe,
    setCollabGrant,
    getCollabGrant,
    clearCollabGrant
  };
}
