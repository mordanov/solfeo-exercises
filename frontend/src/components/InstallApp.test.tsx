import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../i18n";
import { InstallApp } from "./InstallApp";

function device(mobile = true, standalone = false) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches:
      query === "(pointer: coarse)"
        ? mobile
        : query === "(display-mode: standalone)" && standalone,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}
beforeEach(async () => {
  await i18n.changeLanguage("en");
  device();
});
it("offers installation on mobile with browser instructions when no native prompt is available", () => {
  render(<InstallApp />);
  fireEvent.click(screen.getByRole("button", { name: "Install app" }));
  expect(screen.getByRole("status")).toHaveTextContent(
    "Open your browser menu",
  );
  fireEvent.click(screen.getByRole("button", { name: "Not now" }));
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
it("provides Safari instructions on an iPad with a desktop user agent", () => {
  vi.stubGlobal("navigator", {
    userAgent: "Macintosh Safari",
    platform: "MacIntel",
    maxTouchPoints: 5,
  });
  render(<InstallApp />);
  fireEvent.click(screen.getByRole("button", { name: "Install app" }));
  expect(screen.getByRole("status")).toHaveTextContent("In Safari, open Share");
});
it.each([
  [false, false],
  [true, true],
])(
  "does not offer installation on desktop or when already standalone (%s,%s)",
  (mobile, standalone) => {
    device(mobile, standalone);
    render(<InstallApp />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  },
);
it("opens the browser prompt only on a click and hides the offer after installation", async () => {
  render(<InstallApp />);
  const event = Object.assign(
    new Event("beforeinstallprompt", { cancelable: true }),
    {
      prompt: vi.fn().mockResolvedValue(undefined),
      userChoice: Promise.resolve({ outcome: "accepted", platform: "web" }),
    },
  );
  fireEvent(window, event);
  expect(event.defaultPrevented).toBe(true);
  expect(event.prompt).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Install app" }));
  await waitFor(() => expect(event.prompt).toHaveBeenCalledTimes(1));
  await waitFor(() =>
    expect(screen.queryByRole("button")).not.toBeInTheDocument(),
  );
});
it("reports prompt failure instead of claiming installation succeeded", async () => {
  render(<InstallApp />);
  const event = Object.assign(
    new Event("beforeinstallprompt", { cancelable: true }),
    {
      prompt: vi.fn().mockRejectedValue(new Error("unavailable")),
      userChoice: Promise.resolve({ outcome: "dismissed", platform: "web" }),
    },
  );
  const logging = vi.spyOn(console, "error").mockImplementation(() => {});
  fireEvent(window, event);
  fireEvent.click(screen.getByRole("button", { name: "Install app" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The installation prompt could not be opened",
  );
  logging.mockRestore();
});
it("handles native dismissal, installation events and listener cleanup", async () => {
  const view = render(<InstallApp />);
  const event = Object.assign(
    new Event("beforeinstallprompt", { cancelable: true }),
    {
      prompt: vi.fn().mockResolvedValue(undefined),
      userChoice: Promise.resolve({ outcome: "dismissed", platform: "web" }),
    },
  );
  fireEvent(window, event);
  fireEvent.click(screen.getByRole("button", { name: "Install app" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Open your browser menu",
  );
  fireEvent(window, new Event("appinstalled"));
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  view.unmount();
  const later = Object.assign(
    new Event("beforeinstallprompt", { cancelable: true }),
    {
      prompt: vi.fn(),
      userChoice: Promise.resolve({ outcome: "accepted" }),
    },
  );
  fireEvent(window, later);
  expect(later.defaultPrevented).toBe(false);
});
