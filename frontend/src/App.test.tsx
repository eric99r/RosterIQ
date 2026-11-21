import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Player } from "./api";

const players: Player[] = Array.from({ length: 22 }, (_, index) => ({
  id: `player-${index}`,
  name:
    index === 0
      ? "Patrick Mahomes"
      : index === 21
        ? "NBA Example"
        : `NFL Player ${index}`,
  sport: index === 21 ? "NBA" : "NFL",
  provider: index === 21 ? "manual" : "sleeper:nfl",
  provider_player_id: String(index),
  team: index === 0 ? "KC" : null,
  position: index === 0 ? "QB" : null,
  created_at: "2026-01-01T00:00:00Z",
}));

function respond(path: string) {
  if (path === "/health/ready") return { status: "ok" };
  if (path.startsWith("/api/v1/players/"))
    return players.find((p) => path.endsWith(p.id));
  const url = new URL(path, "http://localhost");
  const sport = url.searchParams.get("sport");
  const q = url.searchParams.get("q")?.toLowerCase();
  const offset = Number(url.searchParams.get("offset") || 0);
  const limit = Number(url.searchParams.get("limit") || 20);
  const matches = players.filter(
    (p) =>
      (!sport || p.sport === sport) && (!q || p.name.toLowerCase().includes(q)),
  );
  return {
    items: matches.slice(offset, offset + limit),
    total: matches.length,
    offset,
    limit,
  };
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async (path: string) =>
        new Response(JSON.stringify(respond(path)), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    ),
  );
});

describe("player catalog", () => {
  it("shows real API counts, players, and connection status", async () => {
    render(<App />);
    expect(
      await screen.findByRole("button", { name: "Patrick Mahomes" }),
    ).toBeVisible();
    expect(await screen.findByText("Backend connected")).toBeVisible();
    expect(screen.getByText("22 players")).toBeVisible();
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    const summary = screen.getByRole("region", { name: "Catalog summary" });
    expect(within(summary).getByText("22")).toBeVisible();
    expect(within(summary).getByText("21")).toBeVisible();
    expect(within(summary).getByText("1")).toBeVisible();
  });

  it("paginates and resets to the first page when the sport changes", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("button", { name: "Patrick Mahomes" });
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(
      await screen.findByRole("button", { name: "NBA Example" }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "NBA" }));
    await waitFor(() =>
      expect(screen.getByText("1 matching players")).toBeVisible(),
    );
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Patrick Mahomes" }),
    ).not.toBeInTheDocument();
  });

  it("searches by name, shows empty results, and clears filters", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("button", { name: "Patrick Mahomes" });
    const search = screen.getByRole("textbox", {
      name: "Search players by name",
    });
    await user.type(search, "mahomes");
    await screen.findByText("1 matching players");
    expect(
      screen.getByRole("button", { name: "Patrick Mahomes" }),
    ).toBeVisible();
    await user.clear(search);
    await user.type(search, "nobody");
    expect(
      await screen.findByText("No players match your search."),
    ).toBeVisible();
    await user.click(
      screen.getAllByRole("button", { name: "Clear filters" })[0],
    );
    expect(await screen.findByText("22 players")).toBeVisible();
    expect(search).toHaveValue("");
  });

  it("loads player details from the get endpoint and closes the dialog", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Patrick Mahomes" }),
    );
    const dialog = screen.getByRole("dialog", { name: "Player details" });
    expect(
      await within(dialog).findByRole("heading", { name: "Patrick Mahomes" }),
    ).toBeVisible();
    expect(within(dialog).getByText("player-0")).toBeVisible();
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/players/player-0",
      expect.anything(),
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Close player details" }),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows request failures and recovers on retry", async () => {
    const user = userEvent.setup();
    let fail = true;
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (fail) return new Response("", { status: 503 });
      return new Response(JSON.stringify(respond(String(input))), {
        status: 200,
      });
    });
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn’t load the catalog.",
    );
    expect(await screen.findByText("Backend unavailable")).toBeVisible();
    fail = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("button", { name: "Patrick Mahomes" }),
    ).toBeVisible();
    expect(await screen.findByText("Backend connected")).toBeVisible();
  });
});
