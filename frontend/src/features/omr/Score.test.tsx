import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { defaultAppearance } from "../../appearance";
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
  zoom: 1,
  cursor: {
    reset: vi.fn(),
    next: vi.fn(),
    show: vi.fn(),
    hide: vi.fn(),
    SkipInvisibleNotes: true,
  },
}));
vi.mock("opensheetmusicdisplay", () => ({
  OpenSheetMusicDisplay: class {
    load = renderer.load;
    render = renderer.render;
    clear = renderer.clear;
    cursor = renderer.cursor;
    set Zoom(value: number) {
      renderer.zoom = value;
    }
  },
}));
vi.mock("../spoken/Spoken", () => ({
  Spoken: ({ highlight }: { highlight: (index: number) => void }) => (
    <button type="button" onClick={() => highlight(3)}>
      Speak notes
    </button>
  ),
}));
const resizeObservers: ScoreResizeObserver[] = [];
class ScoreResizeObserver implements ResizeObserver {
  target?: Element;
  disconnect = vi.fn();
  unobserve = vi.fn();
  observe = vi.fn((target: Element) => {
    this.target = target;
  });
  constructor(private callback: ResizeObserverCallback) {
    resizeObservers.push(this);
  }
  resize(width: number) {
    if (!this.target) throw new Error("The score observer has no target");
    this.callback(
      [
        {
          target: this.target,
          contentRect: new DOMRect(0, 0, width, 200),
          borderBoxSize: [],
          contentBoxSize: [],
          devicePixelContentBoxSize: [],
        },
      ],
      this,
    );
  }
}
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
  ...defaultAppearance,
};
const xml = `<score-partwise><part><measure><note><pitch><step>D</step><octave>4</octave></pitch></note></measure></part></score-partwise>`;
beforeEach(async () => {
  vi.resetAllMocks();
  resizeObservers.length = 0;
  vi.stubGlobal("ResizeObserver", ScoreResizeObserver);
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
it("reflows width changes without reloading the score or remounting spoken controls and restores the cursor", async () => {
  const view = mount(true);
  const speak = await screen.findByRole("button", { name: "Speak notes" });
  await waitFor(() => expect(renderer.render).toHaveBeenCalledTimes(1));
  const observer = resizeObservers.at(-1);
  expect(observer).toBeDefined();
  await userEvent.click(speak);
  expect(renderer.cursor.next).toHaveBeenCalledTimes(3);
  vi.stubGlobal("innerWidth", 320);
  observer?.resize(320);
  expect(renderer.render).toHaveBeenCalledTimes(2);
  expect(renderer.zoom).toBe(0.75);
  expect(renderer.cursor.next).toHaveBeenCalledTimes(6);
  expect(screen.getByRole("button", { name: "Speak notes" })).toBe(speak);
  expect(renderer.load).toHaveBeenCalledTimes(1);
  expect(api.fetchScore).toHaveBeenCalledTimes(1);
  observer?.resize(320);
  observer?.resize(0);
  expect(renderer.render).toHaveBeenCalledTimes(2);
  vi.stubGlobal("innerWidth", 1280);
  observer?.resize(1000);
  expect(renderer.render).toHaveBeenCalledTimes(3);
  expect(renderer.zoom).toBe(1);
  expect(renderer.cursor.next).toHaveBeenCalledTimes(9);
  view.unmount();
  expect(observer?.disconnect).toHaveBeenCalledTimes(1);
});
it("shows the existing fallback when reflow fails", async () => {
  mount();
  await waitFor(() => expect(renderer.render).toHaveBeenCalledTimes(1));
  const observer = resizeObservers.at(-1);
  expect(observer).toBeDefined();
  renderer.render.mockImplementationOnce(() => {
    throw new Error("resize failed");
  });
  observer?.resize(430);
  expect(
    await screen.findByRole("img", { name: "original" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "The score cannot be rendered",
  );
});
