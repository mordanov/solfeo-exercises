import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import { type Task } from "../api/hooks";
import { playNotes } from "../audio/synth";
import PlayScreen from "./PlayScreen";

vi.mock("../audio/synth", () => ({
  playNote: vi.fn(),
  playNotes: vi.fn(),
}));

const notes = [
  { name: "C", octave: 4 },
  { name: "G", octave: 4 },
  { name: "A", octave: 5 },
  { name: "F", octave: 3 },
];
let finish: () => void;
let fail: (error: Error) => void;
let playbackSignal: AbortSignal;
const fetchMock = vi.fn<
  (url: string, options?: RequestInit) => Promise<Response>
>(async () =>
  Response.json({
    is_correct: true,
    correct_answers: notes,
    score_delta: 1,
    next_task: { index: 1, clef: "bass", notes: [{ name: "F", octave: 3 }] },
    result: null,
  }),
);

beforeEach(async () => {
  await i18n.changeLanguage("en");
  vi.useFakeTimers();
  fetchMock.mockClear();
  vi.stubGlobal("fetch", fetchMock);
  vi.mocked(playNotes)
    .mockReset()
    .mockImplementation((_notes, signal) => {
      playbackSignal = signal;
      return new Promise<void>((resolve, reject) => {
        finish = resolve;
        fail = reject;
        signal.addEventListener("abort", () => resolve(), { once: true });
      });
    });
});
afterEach(() => {
  vi.useRealTimers();
});

function mount(
  task: Task = { index: 0, clef: "treble", notes },
  timeLimitMs = 7000,
) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            mutations: { retry: false },
            queries: { retry: false },
          },
        })
      }
    >
      <PlayScreen
        roundId={9}
        csrf="synthetic-token"
        initialTask={task}
        noteCount={task.notes.length}
        difficulty="hard"
        timeLimitMs={timeLimitMs}
        onResult={vi.fn()}
      />
    </QueryClientProvider>,
  );
}
async function click(name: string) {
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name }));
    await vi.advanceTimersByTimeAsync(0);
  });
}

it("plays the displayed notes without submitting or entering answers", async () => {
  mount();
  await click("Listen to notes");
  expect(playNotes).toHaveBeenCalledWith(notes, expect.any(AbortSignal));
  expect(fetchMock).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Stop listening" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Do" })).toBeEnabled();
  await act(async () => finish());
  expect(screen.getByRole("button", { name: "Listen to notes" })).toBeEnabled();
});

it("stops on another click and permits a fresh replay without overlap", async () => {
  mount();
  await click("Listen to notes");
  const previousSignal = playbackSignal;
  await click("Stop listening");
  expect(previousSignal.aborted).toBe(true);
  await click("Listen to notes");
  expect(playNotes).toHaveBeenCalledTimes(2);
  expect(playbackSignal).not.toBe(previousSignal);
  expect(playbackSignal.aborted).toBe(false);
});

it("stops on an answer without changing the answer behavior", async () => {
  mount({ index: 0, clef: "bass", notes: [{ name: "F", octave: 3 }] });
  await click("Listen to notes");
  await click("Fa");
  expect(playbackSignal.aborted).toBe(true);
  expect(
    screen.getByRole("button", { name: "Listen to notes" }),
  ).toBeDisabled();
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
    task_index: 0,
    answers: [{ name: "F", octave: 3 }],
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(900);
  });
  await click("Listen to notes");
  expect(playNotes).toHaveBeenLastCalledWith(
    [{ name: "F", octave: 3 }],
    expect.any(AbortSignal),
  );
});

it("does not pause the timer and cancels playback at timeout", async () => {
  mount(undefined, 1000);
  await click("Listen to notes");
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1000);
  });
  expect(playbackSignal.aborted).toBe(true);
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(
    screen.getByRole("button", { name: "Listen to notes" }),
  ).toBeDisabled();
});

it("cancels playback when leaving the round", async () => {
  const { unmount } = mount();
  await click("Listen to notes");
  unmount();
  expect(playbackSignal.aborted).toBe(true);
});

it("cancels playback when the page leaves, including the browser back cache", async () => {
  mount();
  await click("Listen to notes");
  await act(async () => window.dispatchEvent(new Event("pagehide")));
  expect(playbackSignal.aborted).toBe(true);
  expect(screen.getByRole("button", { name: "Listen to notes" })).toBeEnabled();
});

it("replays the whole task after a partial answer", async () => {
  mount();
  await click("Listen to notes");
  await click("Do");
  expect(playbackSignal.aborted).toBe(true);
  expect(fetchMock).not.toHaveBeenCalled();
  await click("Listen to notes");
  expect(playNotes).toHaveBeenLastCalledWith(notes, expect.any(AbortSignal));
});

it("ignores a cancelled playback completing after a fresh replay starts", async () => {
  let finishPrevious: () => void = () => {};
  vi.mocked(playNotes).mockImplementationOnce(
    () =>
      new Promise<void>((resolve) => {
        finishPrevious = resolve;
      }),
  );
  mount();
  await click("Listen to notes");
  await click("Stop listening");
  await click("Listen to notes");
  await act(async () => finishPrevious());
  expect(screen.getByRole("button", { name: "Stop listening" })).toBeEnabled();
});

it("shows playback errors and allows retry", async () => {
  mount();
  await click("Listen to notes");
  await act(async () => fail(new Error("Audio unavailable")));
  expect(screen.getByRole("alert")).toHaveTextContent("Sound could not play");
  await click("Listen to notes");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(playNotes).toHaveBeenCalledTimes(2);
});

it.each([
  ["ru", "Прослушать ноты"],
  ["es", "Escuchar las notas"],
])("localizes the listening control in %s", async (language, label) => {
  await i18n.changeLanguage(language);
  mount();
  expect(screen.getByRole("button", { name: label })).toBeEnabled();
});
