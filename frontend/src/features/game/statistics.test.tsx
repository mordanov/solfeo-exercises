import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { defaultAppearance } from "../../appearance";
import type { Auth } from "../../api/auth";
import { i18n } from "../../i18n";
import GameArea from "./index";

const auth: Auth = {
  csrf_token: "statistics-test-token",
  user: {
    ...defaultAppearance,
    id: 1,
    username: "statistics-manager",
    first_name: "Statistics",
    last_name: "Test",
    role: "manager",
    is_active: true,
    is_emergency: false,
    must_change_password: false,
    ui_language: "en",
    note_naming: "solfege",
  },
};
const players = [1, 2].map((id) => ({
  id,
  name: `Player ${id}`,
  avatar_animal: "dragon",
  custom_avatar_id: null,
  xp: 150,
  avatar_level: 4,
  trophies: [20],
}));
const seasons = [
  {
    id: 100,
    player_id: 1,
    number: 1,
    started_at: "2026-10-01T10:00:00Z",
    ended_at: "2026-10-02T10:00:00Z",
  },
  {
    id: 101,
    player_id: 1,
    number: 2,
    started_at: "2026-10-02T10:00:00Z",
    ended_at: null,
  },
];
let resetFailed = false;
let statsFailed = false;
const resetPlayers = new Set<number>();
const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
  const playerId = Number(url.match(/\/players\/(\d+)/)?.[1]);
  if (url === "/api/game/players") return Response.json(players);
  if (/^\/api\/game\/players\/\d+$/.test(url)) return Response.json(players[0]);
  if (url.endsWith("/seasons"))
    return Response.json(
      resetPlayers.has(playerId)
        ? [
            ...seasons.map((season) => ({
              ...season,
              ended_at: season.ended_at ?? "2026-10-04T10:00:00Z",
            })),
            { ...seasons[1], id: 102, number: 3 },
          ]
        : seasons,
    );
  if (url.includes("/stats")) {
    if (statsFailed)
      return Response.json({ error: "SERVICE_UNAVAILABLE" }, { status: 503 });
    const historic = url.includes("season_id=100");
    if (!historic && resetPlayers.has(playerId)) return Response.json({});
    return Response.json({
      easy: {
        "1": {
          rounds: historic ? 4 : 2,
          wins: historic ? 3 : 1,
          total_correct: 10,
          total_score: historic ? 12 : 6,
          avg_score: 3,
          win_rate: historic ? 75 : 50,
        },
      },
    });
  }
  if (url.includes("/confusion")) {
    if (!url.includes("season_id=") && resetPlayers.has(playerId))
      return Response.json({
        heatmap: {},
        top_confusions: [],
        round_top_confusions: [],
        missed_notes: [],
      });
    return Response.json({
      heatmap: { D: { F: 3 } },
      top_confusions: [{ expected: "D", given: "F", count: 3 }],
      round_top_confusions: [{ expected: "D", given: "F", count: 2 }],
      missed_notes: [{ name: "C", count: 2 }],
    });
  }
  if (options?.method === "POST" && url.includes("reset")) {
    if (resetFailed)
      return Response.json({ error: "SERVICE_UNAVAILABLE" }, { status: 503 });
    if (url.endsWith("reset-all"))
      players.forEach((player) => resetPlayers.add(player.id));
    else resetPlayers.add(playerId);
    return Response.json(url.endsWith("reset-all") ? seasons : seasons[1]);
  }
  throw new Error(`Unexpected statistics request ${url}`);
});

beforeEach(async () => {
  window.history.replaceState(null, "", "/game");
  resetFailed = false;
  statsFailed = false;
  resetPlayers.clear();
  fetchMock.mockClear();
  vi.stubGlobal("fetch", fetchMock);
  await i18n.changeLanguage("en");
});

function mount(role: "manager" | "student" = "manager") {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <GameArea auth={{ ...auth, user: { ...auth.user, role } }} />
    </QueryClientProvider>,
  );
}

it("opens player statistics from the selector and browses preserved seasons", async () => {
  mount();
  fireEvent.click(
    (await screen.findAllByRole("button", { name: "Statistics" }))[0],
  );
  expect(window.location.pathname).toBe("/game/profile/1");
  expect(await screen.findByText("Rounds played: 2")).toBeInTheDocument();
  expect(screen.getByText("Wins: 1")).toBeInTheDocument();
  expect(screen.getByText("Win rate: 50%")).toBeInTheDocument();
  expect(screen.getByText("150 XP")).toBeInTheDocument();
  expect(screen.getByText(/20 completed rounds/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Season"), {
    target: { value: "100" },
  });
  expect(await screen.findByText("Rounds played: 4")).toBeInTheDocument();
  expect(screen.getByText("Win rate: 75%")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Back to players" }));
  expect(await screen.findByText("Who's playing?")).toBeInTheDocument();
});

it("uses one atomic reset-all request, preserves errors and permits retry", async () => {
  resetFailed = true;
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Player management" }),
  );
  fireEvent.click(await screen.findByRole("button", { name: "Reset all" }));
  const dialog = await screen.findByRole("dialog");
  expect(
    within(dialog).getByText(/XP, levels, trophies and avatars are preserved/),
  ).toBeInTheDocument();
  expect(
    within(dialog).getByRole("button", { name: "Reset all" }),
  ).toBeDisabled();
  fireEvent.change(within(dialog).getByLabelText("Type RESET to confirm"), {
    target: { value: "RESET" },
  });
  fireEvent.click(within(dialog).getByRole("button", { name: "Reset all" }));
  expect(await within(dialog).findByRole("alert")).toBeInTheDocument();
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  resetFailed = false;
  fireEvent.click(within(dialog).getByRole("button", { name: "Reset all" }));
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  expect(screen.getByRole("status")).toHaveTextContent("Season reset");
  const posts = fetchMock.mock.calls.filter(
    ([, options]) => options?.method === "POST",
  );
  expect(posts).toHaveLength(2);
  expect(posts.every(([url]) => url === "/api/game/seasons/reset-all")).toBe(
    true,
  );
  expect(posts[0][1]?.headers).toEqual(
    expect.objectContaining({
      "X-CSRF-Token": auth.csrf_token,
    }),
  );
});

it("resets only the chosen player after explicit confirmation", async () => {
  window.history.replaceState(null, "", "/game/admin");
  mount();
  fireEvent.click(
    (await screen.findAllByRole("button", { name: "Reset statistics" }))[1],
  );
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByText(/Player 2/)).toBeInTheDocument();
  fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  expect(
    fetchMock.mock.calls.some(([, options]) => options?.method === "POST"),
  ).toBe(false);
  fireEvent.click(
    screen.getAllByRole("button", { name: "Reset statistics" })[1],
  );
  fireEvent.change(screen.getByLabelText("Type RESET to confirm"), {
    target: { value: "RESET" },
  });
  fireEvent.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Reset statistics",
    }),
  );
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/game/players/2/seasons/reset",
    expect.objectContaining({
      body: JSON.stringify({ confirmation: "RESET" }),
    }),
  );
});

it("blocks direct manager routes for students without requesting analysis", async () => {
  window.history.replaceState(null, "", "/game/admin/1");
  mount("student");
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Back to players" }));
  expect(await screen.findByText("Who's playing?")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Player management" }),
  ).not.toBeInTheDocument();
});

it("localizes mistake analysis and supports a clef filter", async () => {
  window.history.replaceState(null, "", "/game/admin/1");
  mount();
  expect(await screen.findByText("Fa instead of Re ×3")).toBeInTheDocument();
  expect(screen.getByText("Fa instead of Re ×2")).toBeInTheDocument();
  expect(screen.getByText("Do: 2")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Clef"), {
    target: { value: "bass" },
  });
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(
        ([url]) => url.includes("/confusion") && url.includes("clef=bass"),
      ),
    ).toBe(true),
  );
  expect(
    await screen.findByRole("columnheader", { name: "Fa" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("columnheader", { name: "F" }),
  ).not.toBeInTheDocument();
});

it("renders direct profile routes and responds to browser navigation", async () => {
  window.history.replaceState(null, "", "/game/profile/1");
  mount("student");
  expect(await screen.findByText("Rounds played: 2")).toBeInTheDocument();
  window.history.pushState(null, "", "/game");
  fireEvent(window, new PopStateEvent("popstate"));
  expect(await screen.findByText("Who's playing?")).toBeInTheDocument();
});

it("does not disguise a failed statistics request as an empty season", async () => {
  statsFailed = true;
  window.history.replaceState(null, "", "/game/profile/1");
  mount();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(
    screen.queryByText("No completed rounds in this season."),
  ).not.toBeInTheDocument();
  statsFailed = false;
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("Rounds played: 2")).toBeInTheDocument();
});

it("refreshes cached statistics and analysis after a season reset", async () => {
  window.history.replaceState(null, "", "/game/admin/1");
  mount();
  expect(await screen.findByText("Fa instead of Re ×3")).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Back to player management" }),
  );
  fireEvent.click(
    (await screen.findAllByRole("button", { name: "Reset statistics" }))[0],
  );
  fireEvent.change(screen.getByLabelText("Type RESET to confirm"), {
    target: { value: "RESET" },
  });
  fireEvent.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Reset statistics",
    }),
  );
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByRole("button", { name: "Statistics" })[0]);
  expect(
    await screen.findByText("No completed rounds in this season."),
  ).toBeInTheDocument();
  expect(screen.getByText("Rounds played: 0")).toBeInTheDocument();
  expect(await screen.findByText("No missed notes.")).toBeInTheDocument();
  expect(screen.queryByText("Fa instead of Re ×3")).not.toBeInTheDocument();
  expect(screen.getByText("150 XP")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Season"), {
    target: { value: "100" },
  });
  expect(await screen.findByText("Rounds played: 4")).toBeInTheDocument();
});

it("does not reuse another player's selected historical season during navigation", async () => {
  window.history.replaceState(null, "", "/game/profile/1");
  mount();
  expect(await screen.findByText("Rounds played: 2")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Season"), {
    target: { value: "100" },
  });
  expect(await screen.findByText("Rounds played: 4")).toBeInTheDocument();
  window.history.pushState(null, "", "/game/profile/2");
  fireEvent(window, new PopStateEvent("popstate"));
  expect(await screen.findByText("Rounds played: 2")).toBeInTheDocument();
  expect(screen.getByLabelText("Season")).toHaveValue("");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/game/players/2/stats",
    expect.anything(),
  );
});
