import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { defaultAppearance } from "../../appearance";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import type { Auth } from "../../api/auth";
import * as api from "../../api/listening";
import { i18n } from "../../i18n";
import { Listening } from "./Listening";
import { AppTheme } from "../../theme";
import { ThemeToggle } from "../../components/ThemeToggle";
import { Score } from "../omr/Score";

vi.mock("../../api/listening");
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

it.each([
  "none",
  "pending",
  "processing",
  "needs_review",
  "rejected",
  "failed",
] as const)("keeps the original image for a %s score", async (status) => {
  vi.mocked(api.currentExercise).mockResolvedValue({
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
  });
  mount();
  expect(await screen.findByRole("img")).toBeInTheDocument();
  expect(screen.queryByTestId("approved-score")).not.toBeInTheDocument();
});

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

it("shows both the original image and approved score", async () => {
  vi.mocked(api.currentExercise).mockResolvedValue(approvedExercise);
  mount();
  expect(await screen.findByTestId("approved-score")).toBeInTheDocument();
  expect(
    screen.getByRole("img", { name: "Score image: First exercise" }),
  ).toHaveAttribute("src", "/api/exercises/1/files/image");
  expect(screen.getAllByRole("img")).toHaveLength(1);
});
it("shows an available approved score independently of the original image", async () => {
  vi.mocked(api.currentExercise).mockResolvedValue({
    ...approvedExercise,
    image: null,
    audio: null,
  });
  mount();
  expect(await screen.findByTestId("approved-score")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByText(/spoken notes above/)).toBeInTheDocument();
});
it("retains one original image and reports score rendering failures", async () => {
  vi.mocked(api.currentExercise).mockResolvedValue(approvedExercise);
  vi.mocked(Score).mockImplementation(({ fallback }) => (
    <section role="alert">Recognition unavailable{fallback}</section>
  ));
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Recognition unavailable",
  );
  expect(screen.getAllByRole("img")).toHaveLength(1);
});
it("reports an original-image load failure beside an approved score", async () => {
  vi.mocked(api.currentExercise).mockResolvedValue(approvedExercise);
  mount();
  fireEvent.error(await screen.findByRole("img"));
  expect(screen.getByRole("alert")).toBeInTheDocument();
  expect(screen.getByTestId("approved-score")).toBeInTheDocument();
});
it("does not render a score without an approved version", async () => {
  vi.mocked(api.currentExercise).mockResolvedValue({
    ...approvedExercise,
    omr: { ...approvedExercise.omr, job_id: null },
  });
  mount();
  expect(await screen.findByRole("img")).toBeInTheDocument();
  expect(screen.queryByTestId("approved-score")).not.toBeInTheDocument();
});
beforeEach(async () => {
  vi.resetAllMocks();
  vi.mocked(Score).mockImplementation(() => (
    <section data-testid="approved-score" />
  ));
  localStorage.clear();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  await i18n.changeLanguage("en");
  vi.mocked(api.currentExercise).mockResolvedValue(exercise);
  vi.mocked(api.sendListeningEvent).mockResolvedValue();
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
it("does not pause, remount or end a listening session when switching themes", async () => {
  mount();
  const audio = await screen.findByLabelText("Audio: First exercise");
  if (!(audio instanceof HTMLAudioElement)) throw new Error("Missing audio");
  audio.currentTime = 4;
  fireEvent.play(audio);
  await waitFor(() => expect(api.sendListeningEvent).toHaveBeenCalledTimes(1));
  await userEvent.click(screen.getByRole("button", { name: "Use dark theme" }));
  expect(screen.getByLabelText("Audio: First exercise")).toBe(audio);
  expect(audio.currentTime).toBe(4);
  expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
  expect(api.sendListeningEvent).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.sendListeningEvent).mock.calls[0][0]).toMatchObject({
    event: "start",
  });
});
it("does not create a journal row before play and keeps one session through pause", async () => {
  mount();
  const audio = await screen.findByLabelText("Audio: First exercise");
  expect(audio).not.toHaveAttribute("autoplay");
  expect(api.sendListeningEvent).not.toHaveBeenCalled();
  fireEvent.play(audio);
  await waitFor(() => expect(api.sendListeningEvent).toHaveBeenCalled());
  fireEvent.pause(audio);
  fireEvent.play(audio);
  fireEvent.ended(audio);
  await waitFor(() =>
    expect(vi.mocked(api.sendListeningEvent).mock.calls.at(-1)?.[0].event).toBe(
      "ended",
    ),
  );
  expect(
    new Set(
      vi
        .mocked(api.sendListeningEvent)
        .mock.calls.map(([data]) => data.session_id),
    ).size,
  ).toBe(1);
});
it("stops speech on recorded playback without marking it complete", async () => {
  mount();
  const audio = await screen.findByLabelText("Audio: First exercise");
  expect(api.sendListeningEvent).not.toHaveBeenCalled();
  const stop = vi.fn();
  window.addEventListener("solfeo:stop-spoken", stop);
  fireEvent.play(audio);
  await waitFor(() => expect(api.sendListeningEvent).toHaveBeenCalled());
  expect(stop).toHaveBeenCalledTimes(1);
  fireEvent.pause(audio);
  expect(
    vi
      .mocked(api.sendListeningEvent)
      .mock.calls.every(([data]) => data.event !== "ended"),
  ).toBe(true);
  window.removeEventListener("solfeo:stop-spoken", stop);
});
it("finishes before navigating and does not autoplay the next exercise", async () => {
  vi.mocked(api.selectExercise).mockResolvedValue({
    ...exercise,
    id: 2,
    title: "Second exercise",
  });
  mount();
  fireEvent.play(await screen.findByLabelText("Audio: First exercise"));
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(
    await screen.findByLabelText("Audio: Second exercise"),
  ).not.toHaveAttribute("autoplay");
  expect(api.selectExercise).toHaveBeenCalledWith(
    "csrf",
    "sequential",
    "next",
    1,
    undefined,
  );
  expect(vi.mocked(api.sendListeningEvent).mock.calls.at(-1)?.[0].event).toBe(
    "end",
  );
});
it("flushes a terminal beacon on pagehide", async () => {
  mount();
  fireEvent.play(await screen.findByLabelText("Audio: First exercise"));
  fireEvent(window, new Event("pagehide"));
  expect(api.beaconListeningEvent).toHaveBeenCalledWith(
    expect.objectContaining({ event: "end", csrf_token: "csrf" }),
    expect.any(Function),
  );
});
it("supports image-only exercises without inventing listening sessions", async () => {
  vi.mocked(api.currentExercise).mockResolvedValue({
    ...exercise,
    audio: null,
    image: {
      id: "image",
      mime_type: "image/png",
      size_bytes: 100,
      duration_seconds: null,
    },
  });
  mount();
  expect(await screen.findByText(/image only/)).toBeInTheDocument();
  expect(api.sendListeningEvent).not.toHaveBeenCalled();
});
it("points to the spoken notes instead when an approved score has no recorded audio", async () => {
  vi.mocked(api.currentExercise).mockResolvedValue({
    ...exercise,
    audio: null,
    image: {
      id: "image",
      mime_type: "image/png",
      size_bytes: 100,
      duration_seconds: null,
    },
    omr: {
      status: "approved",
      job_id: "job",
      image_id: "image",
      attempts: 1,
      last_error: null,
    },
  });
  mount();
  expect(await screen.findByTestId("approved-score")).toBeInTheDocument();
  expect(await screen.findByText(/spoken notes above/)).toBeInTheDocument();
  expect(screen.queryByText(/image only/)).not.toBeInTheDocument();
  expect(api.sendListeningEvent).not.toHaveBeenCalled();
});
