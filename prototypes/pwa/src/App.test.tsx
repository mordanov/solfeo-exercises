// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { i18n } from "./i18n";
import { clearShare, readShare } from "./storage";
import { registerWorker } from "./register";

vi.mock("./storage", () => ({ readShare: vi.fn(), clearShare: vi.fn() }));
vi.mock("./register", () => ({ registerWorker: vi.fn() }));

beforeEach(async () => {
  await i18n.changeLanguage("en");
  window.history.replaceState({}, "", "/prototype-share/");
  vi.mocked(readShare).mockResolvedValue(null);
  vi.mocked(clearShare).mockResolvedValue(undefined);
  vi.mocked(registerWorker).mockResolvedValue(undefined);
});
afterEach(cleanup);

it("shows readiness and an empty receipt", async () => {
  render(<App />);
  expect(
    await screen.findByText("Ready to receive shares"),
  ).toBeInTheDocument();
  expect(await screen.findByText("No file stored")).toBeInTheDocument();
});

it("shows stored metadata and clears only after storage succeeds", async () => {
  vi.mocked(readShare).mockResolvedValue({
    name: "voice.opus",
    type: "audio/ogg",
    size: 42,
    receivedAt: Date.now(),
    file: new Blob(["audio"]),
  });
  render(<App />);
  expect(await screen.findByText("voice.opus")).toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Clear stored file" }),
  );
  expect(await screen.findByText("No file stored")).toBeInTheDocument();
  expect(clearShare).toHaveBeenCalledOnce();
});

it("surfaces read failures", async () => {
  vi.mocked(readShare).mockRejectedValue(new Error("blocked storage"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Browser storage failed",
  );
});

it("does not hide a failed clear", async () => {
  vi.mocked(readShare).mockResolvedValue({
    name: "voice.opus",
    type: "",
    size: 1,
    receivedAt: Date.now(),
    file: new Blob(["x"]),
  });
  vi.mocked(clearShare).mockRejectedValue(new Error("blocked"));
  render(<App />);
  await screen.findByText("voice.opus");
  await userEvent.click(
    screen.getByRole("button", { name: "Clear stored file" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Browser storage failed",
  );
  expect(screen.getByText("voice.opus")).toBeInTheDocument();
});

it("shows a failed share rather than a success message", async () => {
  window.history.replaceState(
    {},
    "",
    "/prototype-share/share?error=EMPTY_SHARE",
  );
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No audio file was received",
  );
});

it("shows registration failure and translated UI", async () => {
  vi.mocked(registerWorker).mockRejectedValue(new Error("unsupported"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Service worker unavailable",
  );
  await userEvent.selectOptions(screen.getByLabelText("Language"), "es");
  await waitFor(() =>
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Prototipo",
    ),
  );
});
