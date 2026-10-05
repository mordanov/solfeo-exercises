import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import { type Task } from "../api/hooks";
import { playNotes } from "../audio/synth";
import PlayScreen from "./PlayScreen";

vi.mock("../audio/synth", () => ({
  playNotes: vi.fn(),
}));

const notes = [
  { name: "C", octave: 4 },
  { name: "G", octave: 4 },
  { name: "A", octave: 5 },
  { name: "F", octave: 4 },
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
    next_task: { index: 1, clef: "bass", notes: [{ name: "F", octave: 4 }] },
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
  options: {
    noteNaming?: "solfege" | "letters";
    showSoundHint?: boolean;
    showCorrectAnswer?: boolean;
  } = {},
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
        {...options}
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

it("accounts for server clock skew and expires using the absolute deadline", async () => {
  const serverNow = Date.now() + 60000;
  mount({
    index: 0,
    clef: "treble",
    notes: [{ name: "C", octave: 4 }],
    server_time: new Date(serverNow).toISOString(),
    issued_at: new Date(serverNow - 2000).toISOString(),
    deadline_at: new Date(serverNow + 1000).toISOString(),
    time_limit_ms: 3000,
  });
  await act(async () => vi.advanceTimersByTimeAsync(1100));
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toMatchObject({
    task_index: 0,
    timed_out: true,
  });
});

it("aligns the next task with its issued time instead of granting extra network time", async () => {
  const serverNow = Date.now() + 60000;
  fetchMock.mockImplementationOnce(async () =>
    Response.json({
      is_correct: true,
      correct_answers: [{ name: "C", octave: 4 }],
      score_delta: 1,
      next_task: {
        index: 1,
        clef: "treble",
        notes: [{ name: "D", octave: 4 }],
        server_time: new Date(serverNow).toISOString(),
        issued_at: new Date(serverNow + 500).toISOString(),
        deadline_at: new Date(serverNow + 1500).toISOString(),
        time_limit_ms: 1000,
      },
      result: null,
    }),
  );
  mount(
    {
      index: 0,
      clef: "treble",
      notes: [{ name: "C", octave: 4 }],
      server_time: new Date(serverNow).toISOString(),
    },
    7000,
    {
      noteNaming: "letters",
    },
  );
  await click("C");
  await act(async () => vi.advanceTimersByTimeAsync(550));
  expect(screen.getByRole("button", { name: "D" })).toBeEnabled();
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toMatchObject({
    task_index: 1,
    timed_out: true,
  });
});

it("does not extend a cached next-task deadline when its response arrives late", async () => {
  const serverNow = Date.now() + 60000;
  fetchMock.mockImplementationOnce(
    () =>
      new Promise<Response>((resolve) => {
        setTimeout(
          () =>
            resolve(
              Response.json({
                is_correct: true,
                correct_answers: [{ name: "C", octave: 4 }],
                score_delta: 1,
                next_task: {
                  index: 1,
                  clef: "treble",
                  notes: [{ name: "D", octave: 4 }],
                  server_time: new Date(serverNow).toISOString(),
                  issued_at: new Date(serverNow + 900).toISOString(),
                  deadline_at: new Date(serverNow + 1900).toISOString(),
                  time_limit_ms: 1000,
                },
                result: null,
              }),
            ),
          2000,
        );
      }),
  );
  mount(
    {
      index: 0,
      clef: "treble",
      notes: [{ name: "C", octave: 4 }],
      server_time: new Date(serverNow).toISOString(),
      deadline_at: new Date(serverNow + 7000).toISOString(),
      time_limit_ms: 7000,
    },
    7000,
    { noteNaming: "letters" },
  );
  await click("C");
  await act(async () => vi.advanceTimersByTimeAsync(2100));
  await act(async () => vi.advanceTimersByTimeAsync(50));
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toMatchObject({
    task_index: 1,
    timed_out: true,
  });
});

it("shows server-authoritative timeout feedback for an answer that arrived too late", async () => {
  fetchMock.mockImplementationOnce(async () =>
    Response.json({
      is_correct: false,
      timed_out: true,
      correct_answers: [{ name: "C", octave: 4 }],
      score_delta: -1,
      next_task: {
        index: 1,
        clef: "treble",
        notes: [{ name: "D", octave: 4 }],
      },
      result: null,
    }),
  );
  mount({ index: 0, clef: "treble", notes: [{ name: "C", octave: 4 }] }, 7000, {
    noteNaming: "letters",
  });
  await click("C");
  expect(screen.getByRole("alert")).toHaveTextContent(i18n.t("game.timeout"));
  expect(screen.getByRole("alert")).not.toHaveTextContent(i18n.t("game.wrong"));
});

it("preserves a cached accepted answer even when the client submits a timeout", async () => {
  fetchMock.mockImplementationOnce(async () =>
    Response.json({
      is_correct: true,
      timed_out: false,
      correct_answers: [{ name: "C", octave: 4 }],
      score_delta: 1,
      next_task: {
        index: 1,
        clef: "treble",
        notes: [{ name: "D", octave: 4 }],
      },
      result: null,
    }),
  );
  mount({ index: 0, clef: "treble", notes: [{ name: "C", octave: 4 }] }, 1000, {
    noteNaming: "letters",
  });
  await act(async () => vi.advanceTimersByTimeAsync(1100));
  expect(screen.getByRole("alert")).toHaveTextContent(i18n.t("game.correct"));
  expect(screen.getByRole("alert")).not.toHaveTextContent(
    i18n.t("game.timeout"),
  );
});

it("can hide the sound hint without removing the answer controls", () => {
  mount(undefined, 7000, { showSoundHint: false, noteNaming: "letters" });
  expect(
    screen.queryByRole("button", { name: "Listen to notes" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "C" })).toBeEnabled();
});

it("plays repeated note names in their written octaves and submits the chosen names", async () => {
  const mixed = [
    { name: "C", octave: 4 },
    { name: "C", octave: 5 },
  ];
  mount({ index: 0, clef: "bass", notes: mixed }, 7000, {
    noteNaming: "letters",
  });
  await click("Listen to notes");
  const hintSignal = playbackSignal;
  await click("C");
  expect(hintSignal.aborted).toBe(true);
  expect(playNotes).toHaveBeenLastCalledWith(
    [mixed[0]],
    expect.any(AbortSignal),
  );
  await click("C");
  expect(playNotes).toHaveBeenLastCalledWith(
    [mixed[1]],
    expect.any(AbortSignal),
  );
  expect(
    JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body)).answers,
  ).toEqual(mixed);
});

it.each([
  ["en", "letters", "C"],
  ["en", "solfege", "Do"],
  ["ru", "solfege", "До"],
  ["es", "solfege", "Do"],
] as const)(
  "labels both answers and the correct answer using %s/%s",
  async (language, naming, label) => {
    await i18n.changeLanguage(language);
    mount(
      {
        index: 0,
        clef: "treble",
        notes: [{ name: "C", octave: 4 }],
      },
      7000,
      { noteNaming: naming, showCorrectAnswer: true },
    );

    await click(label);
    const section = screen.getByRole("region", {
      name: i18n.t("game.correctAnswer"),
    });
    expect(section).toHaveTextContent(label);
    expect(section).toHaveTextContent(
      naming === "letters" ? "A" : language === "ru" ? "Ля" : "La",
    );
    expect(section).not.toHaveTextContent(/[245]/);
    expect(section.parentElement).not.toContainElement(
      screen.getByRole("img", { name: /.+/ }),
    );
  },
);

it("plays wrong bass choices in the current octave and restores that octave after backspace", async () => {
  mount(
    {
      index: 0,
      clef: "bass",
      notes: [
        { name: "E", octave: 2 },
        { name: "G", octave: 3 },
        { name: "C", octave: 4 },
      ],
    },
    7000,
    { noteNaming: "letters" },
  );
  await click("C");
  expect(playNotes).toHaveBeenLastCalledWith(
    [{ name: "C", octave: 2 }],
    expect.any(AbortSignal),
  );
  await click("D");
  expect(playNotes).toHaveBeenLastCalledWith(
    [{ name: "D", octave: 3 }],
    expect.any(AbortSignal),
  );
  await click("Remove last note");
  await click("B");
  expect(playNotes).toHaveBeenLastCalledWith(
    [{ name: "B", octave: 3 }],
    expect.any(AbortSignal),
  );
  expect(fetchMock).not.toHaveBeenCalled();
  await click("C");
  expect(playNotes).toHaveBeenLastCalledWith(
    [{ name: "C", octave: 4 }],
    expect.any(AbortSignal),
  );
  expect(
    JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body)).answers,
  ).toEqual([
    { name: "C", octave: 2 },
    { name: "B", octave: 3 },
    { name: "C", octave: 4 },
  ]);
});

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
  mount({ index: 0, clef: "bass", notes: [{ name: "F", octave: 4 }] });
  await click("Listen to notes");
  const hintSignal = playbackSignal;
  await click("Fa");
  expect(hintSignal.aborted).toBe(true);
  expect(
    screen.getByRole("button", { name: "Listen to notes" }),
  ).toBeDisabled();
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
    task_index: 0,
    answers: [{ name: "F", octave: 4 }],
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(900);
  });
  await click("Listen to notes");
  expect(playNotes).toHaveBeenLastCalledWith(
    [{ name: "F", octave: 4 }],
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
  const hintSignal = playbackSignal;
  await click("Do");
  expect(hintSignal.aborted).toBe(true);
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
