import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../i18n";
import type { User } from "../../api/auth";
import * as api from "../../api/omr";
import { Spoken } from "./Spoken";
import { SpeechPlayer } from "./player";
import { AppTheme, useAppearance } from "../../theme";
import { ThemeToggle } from "../../components/ThemeToggle";
import { defaultAppearance } from "../../appearance";

vi.mock("../../api/omr");
const speech = vi.hoisted(() => ({
  stop: vi.fn<SpeechPlayer["stop"]>(),
  play: vi.fn<SpeechPlayer["play"]>(),
}));
vi.mock("./player", async (original) => ({
  ...(await original<typeof import("./player")>()),
  SpeechPlayer: vi.fn(
    class {
      stop = speech.stop;
      play = speech.play;
    },
  ),
}));
const xml = `<score-partwise><part><measure><attributes><divisions>1</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note></measure></part></score-partwise>`;
const user: User = {
  id: 1,
  username: "student",
  first_name: "A",
  last_name: "B",
  role: "student",
  is_active: true,
  is_emergency: false,
  must_change_password: false,
  ui_language: "en",
  note_naming: "letters",
  ...defaultAppearance,
};
beforeEach(async () => {
  vi.resetAllMocks();
  localStorage.clear();
  await i18n.changeLanguage("en");
});
afterEach(() => vi.restoreAllMocks());
function AppearanceChange() {
  const { setAppearance } = useAppearance();
  return (
    <button
      onClick={() =>
        setAppearance({
          ...defaultAppearance,
          light_scheme: "forest",
          dark_scheme: "plum",
          ui_font: "serif",
          ui_font_size: 20,
        })
      }
    >
      Change appearance
    </button>
  );
}
function mount(score = xml, id = 1, version = "version") {
  return render(
    <I18nextProvider i18n={i18n}>
      <AppTheme>
        <ThemeToggle />
        <AppearanceChange />
        <Spoken
          id={id}
          version={version}
          score={score}
          user={user}
          highlight={vi.fn()}
        />
      </AppTheme>
    </I18nextProvider>,
  );
}
it("keeps the speech player and tempo unchanged across theme switches", () => {
  mount();
  fireEvent.change(screen.getByRole("slider"), { target: { value: "90" } });
  fireEvent.click(screen.getByRole("button", { name: "Speak notes" }));
  const stops = speech.stop.mock.calls.length;
  const players = vi.mocked(SpeechPlayer).mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "Use dark theme" }));
  expect(screen.getByRole("slider")).toHaveValue("90");
  expect(speech.stop).toHaveBeenCalledTimes(stops);
  expect(SpeechPlayer).toHaveBeenCalledTimes(players);
  fireEvent.click(screen.getByRole("button", { name: "Change appearance" }));
  expect(screen.getByRole("slider")).toHaveValue("90");
  expect(speech.stop).toHaveBeenCalledTimes(stops);
  expect(SpeechPlayer).toHaveBeenCalledTimes(players);
});
it("starts only on click and checks current approval before reading the score", async () => {
  mount();
  expect(speech.play).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Speak notes" }));
  expect(speech.play).toHaveBeenCalled();
  const load = speech.play.mock.calls[0][0];
  vi.mocked(api.fetchOmr).mockResolvedValue({
    job_id: "version",
    image_id: "image",
    status: "rejected",
    attempts: 1,
    last_error: null,
  });
  await expect(load(new AbortController().signal)).rejects.toThrow("OMR_STALE");
  expect(api.fetchScore).not.toHaveBeenCalled();
});
it("stops on tempo change, page exit, competing playback, and unmount", async () => {
  const view = mount();
  fireEvent.change(screen.getByRole("slider"), { target: { value: "90" } });
  expect(screen.getByText("Tempo: 90 BPM")).toBeInTheDocument();
  window.dispatchEvent(new Event("pagehide"));
  window.dispatchEvent(new Event("solfeo:stop-spoken"));
  view.unmount();
  await waitFor(() => expect(speech.stop).toHaveBeenCalledTimes(4));
});
it("coordinates manager previews as well as the student recording", () => {
  const pause = vi
    .spyOn(HTMLMediaElement.prototype, "pause")
    .mockImplementation(() => {});
  render(
    <I18nextProvider i18n={i18n}>
      <audio aria-label="Manager preview" />
      <Spoken
        id={1}
        version="version"
        score={xml}
        user={{ ...user, role: "manager" }}
        highlight={vi.fn()}
      />
    </I18nextProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Speak notes" }));
  expect(pause).toHaveBeenCalledOnce();
  const calls = speech.stop.mock.calls.length;
  fireEvent.play(screen.getByLabelText("Manager preview"));
  expect(speech.stop).toHaveBeenCalledTimes(calls + 1);
});
it("chooses a fitting tempo before the first click and remembers it per exercise version", () => {
  const short = xml.replace("<divisions>1", "<divisions>8");
  let view = mount(short);
  const chosen = Number((screen.getByRole("slider") as HTMLInputElement).value);
  expect(chosen).toBeLessThan(40);
  expect(Number(screen.getByRole("slider").getAttribute("min"))).toBeLessThan(
    chosen,
  );
  fireEvent.change(screen.getByRole("slider"), {
    target: { value: String(chosen - 1) },
  });
  expect(screen.getByRole("slider")).toHaveValue(String(chosen - 1));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(speech.play).not.toHaveBeenCalled();
  view.unmount();
  view = mount(short);
  expect(screen.getByRole("slider")).toHaveValue(String(chosen - 1));
  view.unmount();
  view = mount();
  fireEvent.change(screen.getByRole("slider"), { target: { value: "90" } });
  view.unmount();
  view = mount();
  expect(screen.getByRole("slider")).toHaveValue("90");
  view.unmount();
  view = mount(xml, 2);
  expect(screen.getByRole("slider")).toHaveValue("72");
  view.unmount();
  mount(xml, 1, "new-version");
  expect(screen.getByRole("slider")).toHaveValue("72");
});
it("reports storage failures without silently claiming that tempo is remembered", () => {
  mount();
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(console, "error").mockImplementation(() => {});
  fireEvent.change(screen.getByRole("slider"), { target: { value: "90" } });
  expect(screen.getByRole("alert")).toHaveTextContent(
    "The tempo cannot be remembered in this browser",
  );
});
