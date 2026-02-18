const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export type HealthLiveResponse = {
  status: "ok";
  service: string;
};

export type HealthReadyResponse = {
  status: "ready" | "degraded";
  checks: {
    database: "ok" | "error";
  };
};

export async function fetchLiveHealth(): Promise<HealthLiveResponse> {
  const response = await fetch(`${API_BASE_URL}/health/live`);
  if (!response.ok) {
    throw new Error(`Live health request failed with ${response.status}`);
  }
  return (await response.json()) as HealthLiveResponse;
}

export async function fetchReadyHealth(): Promise<HealthReadyResponse> {
  const response = await fetch(`${API_BASE_URL}/health/ready`);
  if (!response.ok) {
    throw new Error(`Ready health request failed with ${response.status}`);
  }
  return (await response.json()) as HealthReadyResponse;
}

