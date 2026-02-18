import { computed, ref } from "vue";
import { login, me, sendCode, type AuthUser, type LoginResponse, type SendCodeResponse } from "../services/auth";

const TOKEN_KEY = "atlas_access_token";

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
    loadMe
  };
}

