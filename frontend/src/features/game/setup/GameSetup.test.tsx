import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import { preparePiano } from "../audio/synth";
import GameSetup from "./GameSetup";

vi.mock("../audio/synth", () => ({ preparePiano: vi.fn() }));
const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
  if (url.endsWith("/achievements"))
    return Response.json({ earned: [], catalog: [] });
  if (url === "/api/game/players/1")
    return Response.json({
      id: 1,
      name: "Piano player",
      avatar_animal: "panda",
      avatar_level: 1,
      xp: 0,
      custom_avatar_id: null,
    });
  if (url === "/api/game/rounds" && options?.method === "POST")
    return Response.json({
      round_id: 7,
      task: { index: 0, clef: "treble", notes: [{ name: "C", octave: 4 }] },
    });
  throw new Error(`Unexpected request ${url}`);
});
beforeEach(async () => {
  await i18n.changeLanguage("en");
  fetchMock.mockClear();
  vi.stubGlobal("fetch", fetchMock);
  vi.mocked(preparePiano).mockReset().mockResolvedValue();
});
function mount() {
  const started = vi.fn();
  const result = render(
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
      <GameSetup playerId={1} csrf="synthetic-token" onRoundStarted={started} />
    </QueryClientProvider>,
  );
  return { ...result, started };
}
it("keeps prizes and their request out of round preparation", async () => {
  mount();
  await screen.findByText("Piano player");
  expect(
    screen.queryByRole("region", { name: i18n.t("game.prizes.title") }),
  ).not.toBeInTheDocument();
  expect(
    fetchMock.mock.calls.some(([url]) => url.endsWith("/achievements")),
  ).toBe(false);
});
it("explains difficulty and passes both independent options into the round", async () => {
  const { started } = mount();
  await screen.findByText("Piano player");
  expect(screen.getByRole("note").textContent).toBe("13 seconds per question");
  fireEvent.click(screen.getByRole("button", { name: "Hard" }));
  expect(screen.getByRole("note").textContent).toBe("7 seconds per question");
  fireEvent.click(screen.getByLabelText(/Show the sound hint/));
  fireEvent.click(screen.getByLabelText(/Show the correct answer/));
  fireEvent.click(screen.getByRole("button", { name: "Let's go!" }));
  await waitFor(() => expect(started).toHaveBeenCalledOnce());
  expect(started.mock.calls[0][4]).toEqual({
    showSoundHint: false,
    showCorrectAnswer: true,
  });
  expect(preparePiano).toHaveBeenCalledOnce();
  expect(
    JSON.parse(
      String(
        fetchMock.mock.calls.find(([url]) => url === "/api/game/rounds")?.[1]
          ?.body,
      ),
    ),
  ).toMatchObject({
    show_sound_hint: false,
    show_correct_answer: true,
  });
});
it("shows zero or one point independently for each switch", async () => {
  mount();
  await screen.findByText("Piano player");
  expect(screen.getByLabelText(/Show the sound hint/)).toHaveAccessibleName(
    "Show the sound hint — 0 points",
  );
  expect(screen.getByLabelText(/Show the correct answer/)).toHaveAccessibleName(
    "Show the correct answer — +1 point",
  );
  fireEvent.click(screen.getByLabelText(/Show the sound hint/));
  fireEvent.click(screen.getByLabelText(/Show the correct answer/));
  expect(screen.getByLabelText(/Show the sound hint/)).toHaveAccessibleName(
    "Show the sound hint — +1 point",
  );
  expect(screen.getByLabelText(/Show the correct answer/)).toHaveAccessibleName(
    "Show the correct answer — 0 points",
  );
});
it("does not start the scored round while piano loading is pending", async () => {
  let ready: () => void = () => {};
  vi.mocked(preparePiano).mockImplementationOnce(
    () =>
      new Promise<void>((resolve) => {
        ready = resolve;
      }),
  );
  const { started } = mount();
  await screen.findByText("Piano player");
  fireEvent.click(screen.getByRole("button", { name: "Let's go!" }));
  expect(
    await screen.findByRole("button", { name: "Loading piano…" }),
  ).toBeDisabled();
  expect(screen.getByRole("button", { name: "Hard" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "4" })).toBeDisabled();
  expect(screen.getByLabelText(/Show the sound hint/)).toBeDisabled();
  expect(screen.getByLabelText(/Show the correct answer/)).toBeDisabled();
  expect(
    fetchMock.mock.calls.some(([, options]) => options?.method === "POST"),
  ).toBe(false);
  ready();
  await waitFor(() => expect(started).toHaveBeenCalledOnce());
});
it("shows loading failures and allows retry without consuming a round", async () => {
  vi.mocked(preparePiano).mockRejectedValueOnce(new Error("Piano unavailable"));
  const { started } = mount();
  await screen.findByText("Piano player");
  fireEvent.click(screen.getByRole("button", { name: "Let's go!" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Sound could not play",
  );
  expect(started).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Let's go!" }));
  await waitFor(() => expect(started).toHaveBeenCalledOnce());
});
it("does not create a round after leaving during piano loading", async () => {
  let ready: () => void = () => {};
  vi.mocked(preparePiano).mockImplementationOnce(
    () =>
      new Promise<void>((resolve) => {
        ready = resolve;
      }),
  );
  const { unmount } = mount();
  await screen.findByText("Piano player");
  fireEvent.click(screen.getByRole("button", { name: "Let's go!" }));
  unmount();
  ready();
  await waitFor(() => expect(preparePiano).toHaveBeenCalledOnce());
  expect(
    fetchMock.mock.calls.some(([, options]) => options?.method === "POST"),
  ).toBe(false);
});
