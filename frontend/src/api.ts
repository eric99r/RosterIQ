export type Sport = "NFL" | "NBA";
export interface Player {
  id: string;
  provider: string;
  provider_player_id: string;
  name: string;
  sport: Sport;
  team: string | null;
  position: string | null;
  created_at: string;
}
export interface PlayerPage {
  items: Player[];
  total: number;
  limit: number;
  offset: number;
}

export async function getJson<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(path, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export function listPlayers(
  sport: Sport | "",
  q: string,
  offset: number,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  if (sport) params.set("sport", sport);
  if (q.trim()) params.set("q", q.trim());
  return getJson<PlayerPage>(`/api/v1/players?${params}`, signal);
}
