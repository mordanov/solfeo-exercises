import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError, type User } from "../../api/auth";
import * as api from "../../api/omr";
import { i18n } from "../../i18n";
import { Score } from "./Score";

vi.mock("../../api/omr");
const renderer = vi.hoisted(() => ({
  load: vi.fn(),
  render: vi.fn(),
  clear: vi.fn(),
}));
vi.mock("opensheetmusicdisplay", () => ({
  OpenSheetMusicDisplay: class {
    load = renderer.load;
    render = renderer.render;
    clear = renderer.clear;
  },
}));
const user: User = {
  id: 1,
  username: "student",
  first_name: "Test",
  last_name: "Student",
  role: "student",
  is_active: true,
  is_emergency: false,
  must_change_password: false,
  ui_language: "ru",
  note_naming: "solfege",
};
const xml = `<score-partwise><part><measure><note><pitch><step>D</step><octave>4</octave></pitch></note></measure></part></score-partwise>`;
beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.fetchScore).mockResolvedValue(xml);
  renderer.load.mockResolvedValue(undefined);
});
function mount(approved = false) {
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false, gcTime: 0 } },
          })
        }
      >
        <Score
          approved={approved}
          id={1}
          version="job"
          user={user}
          fallback={<img alt="original" />}
        />
      </QueryClientProvider>
    </I18nextProvider>,
  );
}
it("loads the protected score and injects names from persisted settings", async () => {
  mount();
  await waitFor(() => expect(renderer.load).toHaveBeenCalledWith(xml));
  await userEvent.click(
    screen.getByRole("checkbox", { name: "Show note names" }),
  );
  await waitFor(() =>
    expect(renderer.load).toHaveBeenLastCalledWith(
      expect.stringContaining("<text>ре</text>"),
    ),
  );
  await userEvent.click(screen.getByRole("checkbox"));
  await waitFor(() => expect(renderer.load).toHaveBeenLastCalledWith(xml));
  expect(api.fetchScore).toHaveBeenCalledTimes(1);
});
it("reports revoked access and falls back to the original", async () => {
  vi.mocked(api.fetchScore).mockRejectedValue(new ApiError("FORBIDDEN", 403));
  mount();
  expect(
    await screen.findByRole("img", { name: "original" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toBeInTheDocument();
  expect(renderer.render).not.toHaveBeenCalled();
});
it("reports renderer failure instead of hiding the exercise", async () => {
  renderer.load.mockRejectedValue(new Error("renderer failure"));
  mount();
  expect(
    await screen.findByRole("img", { name: "original" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "The score cannot be rendered",
  );
});
it("exposes spoken controls only for approved scores", async () => {
  const view = mount();
  await waitFor(() => expect(renderer.render).toHaveBeenCalled());
  expect(
    screen.queryByRole("button", { name: "Speak notes" }),
  ).not.toBeInTheDocument();
  view.unmount();
  mount(true);
  expect(
    await screen.findByRole("button", { name: "Speak notes" }),
  ).toBeInTheDocument();
});
