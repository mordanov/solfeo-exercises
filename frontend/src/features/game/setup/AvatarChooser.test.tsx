import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import AvatarChooser from "./AvatarChooser";
import ResultScreen from "../result/ResultScreen";
import { useSubmitTask, type AvatarReviewStatus } from "../api/hooks";

const player = {
  id: 1,
  name: "Hero",
  avatar_animal: "rhino",
  avatar_level: 6,
  xp: 400,
  custom_avatar_id: null,
};
let jobStatus = "ready";
let unavailable = false;
let resumeJob = false;
let savedJob = false;
let generationAvailable = true;
let completedImages = 0;
let reviewStatus: AvatarReviewStatus | undefined;
const job = (id: number) => ({
  id,
  status: jobStatus,
  phase: jobStatus === "ready" ? "complete" : "generating",
  asset_version: 2,
  completed_images: jobStatus === "ready" ? 30 : completedImages,
  total_images: 30,
  estimated_seconds_remaining: 90,
  error_code: null,
  review_status: reviewStatus,
});
const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
  if (url.endsWith("/quota"))
    return Response.json({
      used: 0,
      limit: 3,
      resets_at: null,
      generation_available: generationAvailable,
      generation_reason: null,
      image_count: 30,
    });
  if (url.includes("/avatars/saved?"))
    return Response.json({
      jobs: savedJob ? [job(10)] : [],
      total: savedJob ? 1 : 0,
    });
  if (url.endsWith("/avatars?player_id=1"))
    return Response.json(resumeJob ? [job(9)] : []);
  if (url.endsWith("/generate"))
    return unavailable
      ? Response.json(
          { error: "AVATAR_GENERATION_UNAVAILABLE" },
          { status: 503 },
        )
      : Response.json({ job_id: 9 });
  if (/\/(9|10)\/status$/.test(url))
    return Response.json(job(url.includes("/10/") ? 10 : 9));
  if (url.endsWith("/1/avatar"))
    return Response.json({
      ...player,
      avatar_animal: JSON.parse(String(options?.body)).avatar_animal,
    });
  if (url.endsWith("/1/submit"))
    return Response.json({
      correct: true,
      score: 100,
      next_task: null,
      result: { correct_count: 7 },
    });
  if (options?.method === "DELETE") {
    savedJob = false;
    return Response.json({ ok: true });
  }
  if (/\/(9|10)\/use$/.test(url)) return Response.json({ ok: true });
  if (url.endsWith("/players")) return Response.json([player]);
  if (url.endsWith("/players/1")) return Response.json(player);
  throw new Error(`Unexpected game request: ${url}`);
});
function mount(ui: React.ReactNode) {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(<QueryClientProvider client={cache}>{ui}</QueryClientProvider>);
  return cache;
}
beforeEach(async () => {
  await i18n.changeLanguage("en");
  jobStatus = "ready";
  unavailable = false;
  resumeJob = false;
  savedJob = false;
  generationAvailable = true;
  completedImages = 0;
  reviewStatus = undefined;
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it.each(["Lion", "Panda", "Rhino"])(
  "offers %s from the supplied art and persists the choice",
  async (name) => {
    const close = vi.fn();
    mount(
      <AvatarChooser playerId={1} csrf="synthetic-token" onClose={close} />,
    );
    const button = screen.getByRole("button", { name });
    expect(within(button).getByRole("img")).toHaveAttribute(
      "src",
      `/assets/avatars/selection/${name.toLowerCase()}.png`,
    );
    fireEvent.click(button);
    await waitFor(() => expect(close).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/game/players/1/avatar",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ avatar_animal: name.toLowerCase() }),
      }),
    );
  },
);
it("opens custom creation from the question card without an automatic paid request", async () => {
  const close = vi.fn();
  mount(<AvatarChooser playerId={1} csrf="synthetic-token" onClose={close} />);
  expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  const question = screen.getByRole("button", { name: "Create avatar" });
  expect(within(question).getByRole("img")).toHaveAttribute(
    "src",
    "/assets/avatars/selection/custom.png",
  );
  fireEvent.click(question);
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/generate"))).toBe(
    false,
  );
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "An original rainbow animal" },
  });
  await waitFor(() =>
    expect(
      screen.getAllByRole("button", { name: "Create avatar" })[1],
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getAllByRole("button", { name: "Create avatar" })[1]);
  const accept = await screen.findByRole("button", { name: "Use it" });
  expect(
    screen
      .getAllByRole("img")
      .some(
        (image) =>
          image.getAttribute("src") ===
          "/api/game/avatars/9/files/neutral?level=1",
      ),
  ).toBe(true);
  fireEvent.click(accept);
  await waitFor(() => expect(close).toHaveBeenCalledOnce());
});
it("explains disabled generation before a failed paid request", async () => {
  generationAvailable = false;
  mount(
    <AvatarChooser playerId={1} csrf="synthetic-token" onClose={() => {}} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Create avatar" }));
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "Original creature" },
  });
  expect(await screen.findByText(/not configured/i)).toBeInTheDocument();
  expect(
    screen.getAllByRole("button", { name: "Create avatar" })[1],
  ).toBeDisabled();
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/generate"))).toBe(
    false,
  );
});
it("shows actual saved-frame progress and an explicitly approximate estimate", async () => {
  resumeJob = true;
  jobStatus = "pending";
  completedImages = 8;
  mount(
    <AvatarChooser playerId={1} csrf="synthetic-token" onClose={() => {}} />,
  );
  expect(await screen.findByText("8 of 30 images saved")).toBeInTheDocument();
  expect(screen.getByText(/Approximate time remaining/)).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Use it" }),
  ).not.toBeInTheDocument();
});
it("reuses a saved avatar and previews any level without a generation request", async () => {
  savedJob = true;
  mount(
    <AvatarChooser playerId={1} csrf="synthetic-token" onClose={() => {}} />,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Saved avatar 10" }),
  );
  expect(await screen.findByRole("button", { name: "Use it" })).toBeEnabled();
  fireEvent.change(screen.getByLabelText("Preview level"), {
    target: { value: "10" },
  });
  for (const state of ["neutral", "happy", "sad"]) {
    expect(
      screen
        .getAllByRole("img")
        .some(
          (image) =>
            image.getAttribute("src") ===
            `/api/game/avatars/10/files/${state}?level=10`,
        ),
    ).toBe(true);
  }
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/generate"))).toBe(
    false,
  );
});
it("keeps a ready avatar private until the manager approves it", async () => {
  resumeJob = true;
  reviewStatus = "pending";
  mount(
    <AvatarChooser playerId={1} csrf="synthetic-token" onClose={() => {}} />,
  );
  expect(
    await screen.findByText(i18n.t("game.avatar.awaitingReview")),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Use it" }),
  ).not.toBeInTheDocument();
  expect(
    screen
      .getAllByRole("img")
      .some((image) =>
        image.getAttribute("src")?.startsWith("/api/game/avatars/9/"),
      ),
  ).toBe(false);
  expect(screen.getByRole("button", { name: "Discard" })).toBeEnabled();
});

it("lets a manager preview a pending avatar but not activate it before review", async () => {
  resumeJob = true;
  reviewStatus = "pending";
  mount(
    <AvatarChooser
      playerId={1}
      csrf="synthetic-token"
      isManager
      onClose={() => {}}
    />,
  );
  expect(await screen.findByRole("button", { name: "Use it" })).toBeDisabled();
  expect(
    screen
      .getAllByRole("img")
      .some(
        (image) =>
          image.getAttribute("src") ===
          "/api/game/avatars/9/files/neutral?level=1",
      ),
  ).toBe(true);
});

it("celebrates every new prize and localizes note hints without adding prize XP", async () => {
  mount(
    <ResultScreen
      playerId={1}
      noteNaming="solfege"
      result={{
        score: 12,
        correct_count: 6,
        is_win: true,
        xp_gained: 12,
        level_up: false,
        new_trophy: null,
        new_achievements: ["first_round", "first_win"],
        practice_hint: { expected: "C", given: "D" },
      }}
      onPlayAgain={() => {}}
      onChangePlayer={() => {}}
    />,
  );
  expect(screen.getAllByRole("status")).toHaveLength(2);
  expect(screen.getAllByRole("status")[0]).toHaveTextContent(
    i18n.t("game.prizes.codes.first_round"),
  );
  expect(screen.getAllByRole("status")[1]).toHaveTextContent(
    i18n.t("game.prizes.codes.first_win"),
  );
  expect(
    screen.getByText(
      i18n.t("game.result.practiceHint", { expected: "Do", given: "Re" }),
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(i18n.t("game.result.xpGained", { xp: 12 })),
  ).toBeInTheDocument();
});
it("reports generation unavailability without closing the chooser", async () => {
  unavailable = true;
  const close = vi.fn();
  mount(<AvatarChooser playerId={1} csrf="synthetic-token" onClose={close} />);
  fireEvent.click(screen.getByRole("button", { name: "Create avatar" }));
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "Original creature" },
  });
  await waitFor(() =>
    expect(
      screen.getAllByRole("button", { name: "Create avatar" })[1],
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getAllByRole("button", { name: "Create avatar" })[1]);
  expect(await screen.findByRole("alert")).toHaveTextContent("unavailable");
  expect(close).not.toHaveBeenCalled();
});
it("removes a discarded saved avatar from the gallery and refreshes the player", async () => {
  savedJob = true;
  const cache = mount(
    <AvatarChooser playerId={1} csrf="synthetic-token" onClose={() => {}} />,
  );
  cache.setQueryData(["game", "player", 1], {
    ...player,
    custom_avatar_id: 10,
  });
  fireEvent.click(
    await screen.findByRole("button", { name: "Saved avatar 10" }),
  );
  fireEvent.click(await screen.findByRole("button", { name: "Discard" }));
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: "Saved avatar 10" }),
    ).not.toBeInTheDocument(),
  );
  expect(cache.getQueryState(["game", "player", 1])?.isInvalidated).toBe(true);
});
it("resumes a finished generation when the chooser reopens", async () => {
  resumeJob = true;
  mount(
    <AvatarChooser playerId={1} csrf="synthetic-token" onClose={() => {}} />,
  );
  expect(await screen.findByRole("button", { name: "Use it" })).toBeEnabled();
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/generate"))).toBe(
    false,
  );
});
it.each([0, 1, 2, 3, 4, 5, 6, 7])(
  "shows the authoritative level and correct emotion for %i answers",
  async (correct) => {
    mount(
      <ResultScreen
        playerId={1}
        result={{
          score: 100,
          correct_count: correct,
          is_win: correct >= 5,
          xp_gained: 1,
          level_up: false,
          new_trophy: null,
          practice_hint: null,
        }}
        onPlayAgain={() => {}}
        onChangePlayer={() => {}}
      />,
    );
    expect(await screen.findByRole("img")).toHaveAttribute(
      "src",
      `/assets/avatars/rhino/rhino_06_${correct >= 5 ? "happy" : correct >= 3 ? "neutral" : "sad"}.png`,
    );
  },
);
it("refreshes both player caches after a completed round", async () => {
  function Submit() {
    const submit = useSubmitTask(1);
    return (
      <button
        onClick={() =>
          submit.mutate({
            csrf: "synthetic-token",
            task_index: 6,
            answers: [{ name: "C", octave: 4 }],
          })
        }
      >
        Submit
      </button>
    );
  }
  const cache = mount(<Submit />);
  cache.setQueryData(["game", "players"], [{ ...player, avatar_level: 5 }]);
  cache.setQueryData(["game", "player", 1], { ...player, avatar_level: 5 });
  fireEvent.click(screen.getByRole("button"));
  await waitFor(() =>
    expect(cache.getQueryState(["game", "players"])?.isInvalidated).toBe(true),
  );
  expect(cache.getQueryState(["game", "player", 1])?.isInvalidated).toBe(true);
});
