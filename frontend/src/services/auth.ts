const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export type AuthUser = {
  id: string;
  nickname: string;
  avatar_url: string | null;
  role: string;
  created_at: string;
};

export type SendCodeResponse = {
  success: boolean;
  ttl_seconds: number;
  debug_code?: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

async function parseJsonResponse<T>(response: Response, requestLabel: string): Promise<T> {
  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `${requestLabel} failed with ${response.status}. Response: ${text.slice(0, 160)}`
    );
  }
  if (!contentType.includes("application/json")) {
    const text = await response.text();
    throw new Error(
      `${requestLabel} expected JSON but got "${contentType || "unknown"}". Response: ${text.slice(0, 160)}`
    );
  }
  return (await response.json()) as T;
}

export async function sendCode(phone: string): Promise<SendCodeResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/send-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone })
  });
  return parseJsonResponse<SendCodeResponse>(response, "Send code");
}

export async function login(
  phone: string,
  code: string,
  nickname?: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, code, nickname: nickname || undefined })
  });
  return parseJsonResponse<LoginResponse>(response, "Login");
}

export async function me(token: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return parseJsonResponse<AuthUser>(response, "Get current user");
}

