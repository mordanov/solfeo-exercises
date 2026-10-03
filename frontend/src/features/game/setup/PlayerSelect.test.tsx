import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { defaultAppearance } from "../../../appearance";
import { type Auth } from "../../../api/auth";
import { i18n } from "../../../i18n";
import PlayerSelect from "./PlayerSelect";

const manager = {
  ...defaultAppearance,
  id: 1,
  username: "manager",
  first_name: "Manager",
  last_name: "Test",
  role: "manager" as const,
  is_active: true,
  is_emergency: false,
  must_change_password: false,
  ui_language: "en" as const,
  note_naming: "letters" as const,
};
const student = {
  ...manager,
  id: 2,
  username: "student",
  first_name: "Student",
  role: "student" as const,
};
let players: object[] = [];
let failed = false;
let accountsFailed = false;
let createFailed = false;
let paginated = false;
const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
  if (url.startsWith("/api/users?")) {
    if (accountsFailed)
      return Response.json({ error: "SERVICE_UNAVAILABLE" }, { status: 503 });
    if (paginated)
      return Response.json({
        users: url.includes("offset=50")
          ? [student]
          : [
              manager,
              ...Array.from({ length: 49 }, (_, index) => ({
                ...student,
                id: index + 10,
                username: `user${index}`,
              })),
            ],
        total: 51,
      });
    return Response.json({ users: [manager, student], total: 2 });
  }
  if (url === "/api/game/players" && options?.method === "POST") {
    if (createFailed)
      return Response.json({ error: "PLAYER_NAME_TAKEN" }, { status: 409 });
    const body = JSON.parse(String(options.body));
    const player = {
      ...body,
      id: 4,
      avatar_level: 1,
      xp: 0,
      custom_avatar_id: null,
    };
    players.push(player);
    return Response.json(player);
  }
  if (url === "/api/game/players")
    return failed
      ? Response.json({ error: "SERVICE_UNAVAILABLE" }, { status: 503 })
      : Response.json(players);
  throw new Error(`Unexpected request ${url}`);
});
beforeEach(async () => {
  fetchMock.mockClear();
  players = [];
  failed = false;
  accountsFailed = false;
  createFailed = false;
  paginated = false;
  await i18n.changeLanguage("en");
  vi.stubGlobal("fetch", fetchMock);
});
function mount(role: "manager" | "student" = "manager") {
  const auth: Auth = {
    user: role === "manager" ? manager : student,
    csrf_token: "synthetic-token",
  };
  const select = vi.fn();
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
      <PlayerSelect auth={auth} onSelect={select} />
    </QueryClientProvider>,
  );
  return select;
}
it("lets a manager create the first profile for a student and select it", async () => {
  const select = mount();
  expect(
    await screen.findByText(
      "No player profiles yet. Create a profile to start playing.",
    ),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Create player" }));
  await screen.findByRole("option", { name: "Student Test (student)" });
  fireEvent.change(screen.getByLabelText("Account"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("Player name"), {
    target: { value: "First player" },
  });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Create player" }).at(-1)!,
  );
  const card = await screen.findByRole("button", { name: /First player/ });
  fireEvent.click(card);
  expect(select).toHaveBeenCalledWith(4);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/game/players",
    expect.objectContaining({
      body: JSON.stringify({
        name: "First player",
        avatar_animal: "unicorn",
        account_id: 2,
      }),
    }),
  );
});
it("explains a student's empty list without granting profile creation", async () => {
  mount("student");
  expect(
    await screen.findByText(
      "Ask a manager to create a player profile for your account.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Create player" }),
  ).not.toBeInTheDocument();
  expect(
    fetchMock.mock.calls.some(([url]) => url.startsWith("/api/users")),
  ).toBe(false);
});
it("reports a failed request instead of claiming the list is empty and can retry", async () => {
  failed = true;
  mount("student");
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(
    screen.queryByText(
      "Ask a manager to create a player profile for your account.",
    ),
  ).not.toBeInTheDocument();
  failed = false;
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await waitFor(() =>
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(),
  );
  expect(
    await screen.findByText(
      "Ask a manager to create a player profile for your account.",
    ),
  ).toBeInTheDocument();
});

it("reaches student accounts beyond the first page", async () => {
  paginated = true;
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "Create player" }));
  await screen.findByRole("option", { name: "Student Test (user0)" });
  expect(
    screen.queryByRole("option", { name: "Student Test (student)" }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByRole("option", { name: "Student Test (student)" });
  fireEvent.change(screen.getByLabelText("Account"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("Player name"), {
    target: { value: "Later account" },
  });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Create player" }).at(-1)!,
  );
  expect(
    await screen.findByRole("button", { name: /Later account/ }),
  ).toBeInTheDocument();
  expect(players[0]).toMatchObject({ account_id: 2 });
});

it("keeps the creation form after a duplicate name error", async () => {
  createFailed = true;
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "Create player" }));
  await screen.findByRole("option", { name: "Student Test (student)" });
  fireEvent.change(screen.getByLabelText("Player name"), {
    target: { value: "Existing player" },
  });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Create player" }).at(-1)!,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "This account already has a player with that name.",
  );
  expect(screen.getByLabelText("Player name")).toHaveValue("Existing player");
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  createFailed = false;
  fireEvent.change(screen.getByLabelText("Player name"), {
    target: { value: "New player" },
  });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Create player" }).at(-1)!,
  );
  expect(
    await screen.findByRole("button", { name: /New player/ }),
  ).toBeInTheDocument();
});

it("reports account lookup errors and retries without submitting", async () => {
  accountsFailed = true;
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "Create player" }));
  await screen.findByRole("alert");
  fireEvent.change(screen.getByLabelText("Player name"), {
    target: { value: "First player" },
  });
  expect(
    screen.getAllByRole("button", { name: "Create player" }).at(-1),
  ).toBeDisabled();
  expect(players).toEqual([]);
  accountsFailed = false;
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByRole("option", { name: "Student Test (student)" });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(
    screen.getAllByRole("button", { name: "Create player" }).at(-1),
  ).toBeEnabled();
});
