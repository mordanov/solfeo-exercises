import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { defaultAppearance } from "../../appearance";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import type { Auth } from "../../api/auth";
import * as chaptersApi from "../../api/chapters";
import * as eventsApi from "../../api/listening";
import * as runsApi from "../../api/listeningRuns";
import { i18n } from "../../i18n";
import { Listening } from "./Listening";
import { AppTheme } from "../../theme";
import { ThemeToggle } from "../../components/ThemeToggle";
import { Score } from "../omr/Score";

vi.mock("../../api/chapters");
vi.mock("../../api/listening");
vi.mock("../../api/listeningRuns");
vi.mock("../omr/Score", () => ({
  Score: vi.fn(() => <section data-testid="approved-score" />),
}));

const auth: Auth = {
  csrf_token: "csrf",
  user: {
    id: 1,
    username: "student",
    first_name: "First",
    last_name: "Last",
    role: "student",
    is_active: true,
    is_emergency: false,
    must_change_password: false,
    ui_language: "en",
    note_naming: "letters",
    ...defaultAppearance,
  },
};

const exercise = {
  id: 1,
  chapter_id: 10,
  chapter_number: 1,
  title: "First exercise",
  category: null,
  description: "Practice",
  position: 0,
  omr: {
    status: "none" as const,
    job_id: null,
    image_id: null,
    attempts: 0,
    last_error: null,
  },
  image: null,
  audio: {
    id: "audio",
    mime_type: "audio/mp4",
    size_bytes: 100,
    duration_seconds: 10,
  },
};

const secondExercise = {
  ...exercise,
  id: 2,
  chapter_id: 20,
  chapter_number: 2,
  title: "Second exercise",
};

const run: runsApi.ListeningRun = {
  id: 7,
  status: "active",
  chapter_numbers: [1, 2],
  current_index: 0,
  items: [
    { position: 0, chapter_number: 1, exercise },
    { position: 1, chapter_number: 2, exercise: secondExercise },
  ],
};

const chapters: chaptersApi.Chapter[] = [
  { id: 10, number: 1, active_exercise_count: 1, assigned_exercise_count: 1 },
  { id: 20, number: 2, active_exercise_count: 1, assigned_exercise_count: 1 },
];

const approvedExercise = {
  ...exercise,
  image: {
    id: "image",
    mime_type: "image/png",
    size_bytes: 100,
    duration_seconds: null,
  },
  omr: {
    status: "approved" as const,
    job_id: "job",
    image_id: "image",
    attempts: 1,
    last_error: null,
  },
};

beforeEach(async () => {
  vi.resetAllMocks();
  vi.mocked(Score).mockImplementation(() => (
    <section data-testid="approved-score" />
  ));
  localStorage.clear();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  await i18n.changeLanguage("en");
  vi.mocked(chaptersApi.listListeningChapters).mockResolvedValue(chapters);
  vi.mocked(runsApi.getActiveListeningRun).mockResolvedValue(null);
  vi.mocked(runsApi.createListeningRun).mockResolvedValue(run);
  vi.mocked(runsApi.navigateListeningRun).mockResolvedValue(run);
  vi.mocked(runsApi.cancelListeningRun).mockResolvedValue({
    ...run,
    status: "cancelled",
  });
  vi.mocked(eventsApi.sendListeningEvent).mockResolvedValue();
});

function mount() {
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: {
              queries: { retry: false, gcTime: 0 },
              mutations: { retry: false },
            },
          })
        }
      >
        <AppTheme>
          <ThemeToggle />
          <Listening auth={auth} />
        </AppTheme>
      </QueryClientProvider>
    </I18nextProvider>,
  );
}

async function selectChaptersAndStart(selectedNumbers: number[] = [1, 2]) {
  const user = userEvent.setup();
  mount();
  for (const number of selectedNumbers)
    await user.click(
      await screen.findByRole("checkbox", { name: `Chapter ${number}` }),
    );
  await user.click(screen.getByRole("button", { name: "Start listening" }));
  return user;
}

async function resumeSavedRun(savedRun: runsApi.ListeningRun = run) {
  vi.mocked(runsApi.getActiveListeningRun).mockResolvedValue(savedRun);
  mount();
  await userEvent.click(await screen.findByRole("button", { name: "Resume" }));
}

it("lets students select multiple chapters and starts the saved randomized queue", async () => {
  await selectChaptersAndStart();

  expect(runsApi.createListeningRun).toHaveBeenCalledWith("csrf", [10, 20]);
  expect(
    await screen.findByRole("heading", { name: "First exercise" }),
  ).toBeVisible();
  expect(screen.getByLabelText("Audio: First exercise")).not.toHaveAttribute(
    "autoplay",
  );
  expect(eventsApi.sendListeningEvent).not.toHaveBeenCalled();
});

it("shows the saved queue on load and resumes it without autoplay", async () => {
  await resumeSavedRun();

  expect(screen.getByText("First exercise")).toBeVisible();
  expect(screen.getAllByRole("listitem")[1]).toHaveTextContent(
    "Second exercise",
  );
  expect(
    screen.getAllByRole("listitem").map((item) => item.textContent?.trim()),
  ).toEqual(["First exercise (Chapter 1)", "Second exercise (Chapter 2)"]);
  expect(screen.getByLabelText("Audio: First exercise")).not.toHaveAttribute(
    "autoplay",
  );
});

it("moves to the previous saved item without autoplay", async () => {
  const user = userEvent.setup();
  await resumeSavedRun({ ...run, current_index: 1 });
  vi.mocked(runsApi.navigateListeningRun).mockResolvedValueOnce(run);

  await user.click(screen.getByRole("button", { name: "Previous" }));

  expect(
    await screen.findByLabelText("Audio: First exercise"),
  ).not.toHaveAttribute("autoplay");
  expect(runsApi.navigateListeningRun).toHaveBeenCalledWith(
    "csrf",
    7,
    "previous",
  );
});

it("finishes the current playback before moving in the saved queue", async () => {
  vi.mocked(runsApi.navigateListeningRun).mockResolvedValueOnce({
    ...run,
    current_index: 1,
  });
  const user = await selectChaptersAndStart();
  const audio = await screen.findByLabelText("Audio: First exercise");
  fireEvent.play(audio);
  await waitFor(() => expect(eventsApi.sendListeningEvent).toHaveBeenCalled());

  await user.click(screen.getByRole("button", { name: "Next" }));

  expect(
    await screen.findByLabelText("Audio: Second exercise"),
  ).not.toHaveAttribute("autoplay");
  expect(runsApi.navigateListeningRun).toHaveBeenCalledWith("csrf", 7, "next");
  expect(
    vi.mocked(eventsApi.sendListeningEvent).mock.calls.at(-1)?.[0].event,
  ).toBe("end");
});

it("disables Previous at the first item and shows completion after the final item", async () => {
  const completed = { ...run, status: "completed" as const, current_index: 2 };
  vi.mocked(runsApi.navigateListeningRun).mockResolvedValueOnce(completed);
  const user = await selectChaptersAndStart([1]);

  expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Next" }));

  expect(await screen.findByText("Listening run complete")).toBeVisible();
  expect(
    screen.queryByLabelText("Audio: First exercise"),
  ).not.toBeInTheDocument();
});

it("ends playback before cancelling and returns to chapter selection", async () => {
  let finishEndEvent = () => {};
  vi.mocked(eventsApi.sendListeningEvent).mockImplementation(async (event) => {
    if (event.event === "end")
      await new Promise<void>((resolve) => {
        finishEndEvent = resolve;
      });
  });
  const user = await selectChaptersAndStart();
  fireEvent.play(await screen.findByLabelText("Audio: First exercise"));
  await waitFor(() => expect(eventsApi.sendListeningEvent).toHaveBeenCalled());

  await user.click(screen.getByRole("button", { name: "Cancel run" }));
  await waitFor(() =>
    expect(
      vi
        .mocked(eventsApi.sendListeningEvent)
        .mock.calls.some(([event]) => event.event === "end"),
    ).toBe(true),
  );
  expect(runsApi.cancelListeningRun).not.toHaveBeenCalled();

  finishEndEvent();
  await waitFor(() =>
    expect(runsApi.cancelListeningRun).toHaveBeenCalledWith("csrf", 7),
  );
  expect(
    await screen.findByRole("checkbox", { name: "Chapter 1" }),
  ).toBeInTheDocument();
});

it("allows a fresh selection after a run is cancelled", async () => {
  const user = await selectChaptersAndStart([1]);
  await user.click(screen.getByRole("button", { name: "Cancel run" }));

  expect(
    await screen.findByRole("checkbox", { name: "Chapter 1" }),
  ).not.toBeChecked();
  expect(
    screen.getByRole("button", { name: "Start listening" }),
  ).toBeDisabled();
});

it("refreshes chapter choices after a run is cancelled", async () => {
  const addedChapter: chaptersApi.Chapter = {
    id: 30,
    number: 3,
    active_exercise_count: 1,
    assigned_exercise_count: 1,
  };
  vi.mocked(chaptersApi.listListeningChapters)
    .mockResolvedValueOnce(chapters)
    .mockResolvedValueOnce([...chapters, addedChapter]);
  const user = await selectChaptersAndStart([1]);

  await user.click(screen.getByRole("button", { name: "Cancel run" }));

  expect(
    await screen.findByRole("checkbox", { name: "Chapter 3" }),
  ).toBeInTheDocument();
});

it("shows the original image and approved score for an image-only run item", async () => {
  const imageOnlyRun: runsApi.ListeningRun = {
    ...run,
    items: [
      {
        ...run.items[0],
        exercise: {
          ...approvedExercise,
          audio: null,
        },
      },
    ],
  };
  vi.mocked(runsApi.createListeningRun).mockResolvedValue(imageOnlyRun);
  await selectChaptersAndStart([1]);

  expect(await screen.findByTestId("approved-score")).toBeInTheDocument();
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/exercises/1/files/image",
  );
  expect(await screen.findByText(/spoken notes above/)).toBeInTheDocument();
  expect(eventsApi.sendListeningEvent).not.toHaveBeenCalled();
});

it("renders chapter selection when no saved run exists and prevents an empty start", async () => {
  mount();

  expect(
    await screen.findByRole("checkbox", { name: "Chapter 1" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Start listening" }),
  ).toBeDisabled();
});

it.each([
  "none",
  "pending",
  "processing",
  "needs_review",
  "rejected",
  "failed",
] as const)("keeps the original image for a %s score", async (status) => {
  vi.mocked(runsApi.createListeningRun).mockResolvedValue({
    ...run,
    items: [
      {
        ...run.items[0],
        exercise: {
          ...exercise,
          image: {
            id: "image",
            mime_type: "image/png",
            size_bytes: 100,
            duration_seconds: null,
          },
          omr: {
            status,
            job_id: "job",
            image_id: "image",
            attempts: 1,
            last_error: null,
          },
        },
      },
    ],
  });
  await selectChaptersAndStart([1]);

  expect(await screen.findByRole("img")).toBeInTheDocument();
  expect(screen.queryByTestId("approved-score")).not.toBeInTheDocument();
});

it("reports an original-image load failure beside the saved queue", async () => {
  vi.mocked(runsApi.createListeningRun).mockResolvedValue({
    ...run,
    items: [
      {
        ...run.items[0],
        exercise: {
          ...exercise,
          image: {
            id: "image",
            mime_type: "image/png",
            size_bytes: 100,
            duration_seconds: null,
          },
        },
      },
    ],
  });
  await selectChaptersAndStart([1]);
  fireEvent.error(await screen.findByRole("img"));

  expect(screen.getByRole("alert")).toBeInTheDocument();
});

it("shows image-only guidance without creating a listening session", async () => {
  vi.mocked(runsApi.createListeningRun).mockResolvedValue({
    ...run,
    items: [
      {
        ...run.items[0],
        exercise: {
          ...exercise,
          image: {
            id: "image",
            mime_type: "image/png",
            size_bytes: 100,
            duration_seconds: null,
          },
          audio: null,
        },
      },
    ],
  });
  await selectChaptersAndStart([1]);

  expect(await screen.findByText(/image only/)).toBeInTheDocument();
  expect(eventsApi.sendListeningEvent).not.toHaveBeenCalled();
});

it("retains one image and reports score-rendering failures", async () => {
  vi.mocked(Score).mockImplementation(({ fallback }) => (
    <section role="alert">Recognition unavailable{fallback}</section>
  ));
  vi.mocked(runsApi.createListeningRun).mockResolvedValue({
    ...run,
    items: [{ ...run.items[0], exercise: approvedExercise }],
  });
  await selectChaptersAndStart([1]);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Recognition unavailable",
  );
  expect(screen.getAllByRole("img")).toHaveLength(1);
});

it("does not pause or end playback when switching themes", async () => {
  const user = await selectChaptersAndStart();
  const audio = await screen.findByLabelText("Audio: First exercise");
  if (!(audio instanceof HTMLAudioElement)) throw new Error("Missing audio");
  audio.currentTime = 4;
  fireEvent.play(audio);
  await waitFor(() => expect(eventsApi.sendListeningEvent).toHaveBeenCalled());

  await user.click(screen.getByRole("button", { name: "Use dark theme" }));

  expect(screen.getByLabelText("Audio: First exercise")).toBe(audio);
  expect(audio.currentTime).toBe(4);
  expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
});

it("keeps one listening session through pause and ends it naturally", async () => {
  await selectChaptersAndStart();
  const audio = await screen.findByLabelText("Audio: First exercise");
  fireEvent.play(audio);
  await waitFor(() => expect(eventsApi.sendListeningEvent).toHaveBeenCalled());
  fireEvent.pause(audio);
  fireEvent.play(audio);
  fireEvent.ended(audio);

  await waitFor(() =>
    expect(
      vi.mocked(eventsApi.sendListeningEvent).mock.calls.at(-1)?.[0].event,
    ).toBe("ended"),
  );
  const events = vi
    .mocked(eventsApi.sendListeningEvent)
    .mock.calls.map(([event]) => event);
  expect(new Set(events.map((event) => event.session_id)).size).toBe(1);
  expect(events.every((event) => event.run_id === 7)).toBe(true);
});

it("stops spoken playback when recorded audio starts without marking it complete", async () => {
  await selectChaptersAndStart();
  const audio = await screen.findByLabelText("Audio: First exercise");
  const stop = vi.fn();
  window.addEventListener("solfeo:stop-spoken", stop);

  fireEvent.play(audio);
  await waitFor(() => expect(eventsApi.sendListeningEvent).toHaveBeenCalled());
  fireEvent.pause(audio);

  expect(stop).toHaveBeenCalledOnce();
  expect(
    vi
      .mocked(eventsApi.sendListeningEvent)
      .mock.calls.every(([event]) => event.event !== "ended"),
  ).toBe(true);
  window.removeEventListener("solfeo:stop-spoken", stop);
});

it("flushes a run-bound end beacon when the page is hidden", async () => {
  await selectChaptersAndStart();
  fireEvent.play(await screen.findByLabelText("Audio: First exercise"));
  fireEvent(window, new Event("pagehide"));

  expect(eventsApi.beaconListeningEvent).toHaveBeenCalledWith(
    expect.objectContaining({
      run_id: 7,
      event: "end",
      csrf_token: "csrf",
    }),
    expect.any(Function),
  );
});
