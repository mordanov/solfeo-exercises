import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../i18n";
import type { User } from "../../api/auth";
import * as api from "../../api/omr";
import { Spoken } from "./Spoken";
import { SpeechPlayer } from "./player";

vi.mock("../../api/omr");
vi.mock("./player");
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
};
beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
});
function mount() {
  return render(
    <I18nextProvider i18n={i18n}>
      <Spoken id={1} version="version" user={user} highlight={vi.fn()} />
    </I18nextProvider>,
  );
}
it("starts only on click and checks current approval before reading the score", async () => {
  mount();
  expect(SpeechPlayer.prototype.play).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Speak notes" }));
  expect(SpeechPlayer.prototype.play).toHaveBeenCalled();
  const load = vi.mocked(SpeechPlayer.prototype.play).mock.calls[0][0];
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
  await waitFor(() =>
    expect(SpeechPlayer.prototype.stop).toHaveBeenCalledTimes(4),
  );
});
