export interface ModelConfigStatus {
  configured: boolean;
  provider: string;
  base_url: string;
  model: string;
  has_api_key: boolean;
}

export interface ModelConfigUpdate {
  api_key: string;
  provider: string;
  base_url: string;
  model: string;
}

async function detail(response: Response) {
  const data = await response.json().catch(() => null);
  return typeof data?.detail === "string"
    ? data.detail
    : "本地配置服务暂时不可用，请确认后端已经启动";
}

export async function fetchModelConfig(): Promise<ModelConfigStatus> {
  const response = await fetch("/api/config");
  if (!response.ok) throw new Error(await detail(response));
  return response.json();
}

export async function saveModelConfig(
  value: ModelConfigUpdate,
): Promise<ModelConfigStatus> {
  const response = await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  });
  if (!response.ok) throw new Error(await detail(response));
  return response.json();
}
