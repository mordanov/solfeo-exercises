// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { i18n } from "./i18n";
import { clearShare, readShare, readAttempt, clearAttempt } from "./storage";
import { registerWorker } from "./register";

vi.mock("./storage", () => ({
  readShare: vi.fn(),
  clearShare: vi.fn(),
  readAttempt: vi.fn(),
  clearAttempt: vi.fn(),
}));
vi.mock("./register", () => ({ registerWorker: vi.fn() }));

beforeEach(async () => {
  await i18n.changeLanguage("en");
  window.history.replaceState({}, "", "/prototype-share/");
  vi.mocked(readShare).mockResolvedValue(null);
  vi.mocked(readAttempt).mockResolvedValue(null);
  vi.mocked(clearAttempt).mockResolvedValue(undefined);
  vi.mocked(clearShare).mockResolvedValue(undefined);
  vi.mocked(registerWorker).mockResolvedValue(undefined);
});
afterEach(cleanup);

it("shows the failed attempt separately from the successful file and clears only diagnostics", async () => {
  vi.mocked(readShare).mockResolvedValue({
    name: "previous.opus",
    type: "audio/ogg",
    size: 42,
    receivedAt: 1,
    file: new Blob(["audio"]),
  });
  vi.mocked(readAttempt).mockResolvedValue({
    receivedAt: 2,
    outcome: "TEXT_ONLY_SHARE",
    fields: [{ field: "text", kind: "text", nonempty: true }],
  });
  render(<App />);
  expect(await screen.findByText("previous.opus")).toBeInTheDocument();
  expect(
    await screen.findByText(
      /Text or a link was received without an audio file/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Text field: nonempty; contents not retained."),
  ).toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Clear diagnostics" }),
  );
  expect(
    await screen.findByText("No diagnostic attempt recorded"),
  ).toBeInTheDocument();
  expect(screen.getByText("previous.opus")).toBeInTheDocument();
  expect(clearAttempt).toHaveBeenCalledOnce();
  expect(clearShare).not.toHaveBeenCalled();
});

it("surfaces diagnostic read failures", async () => {
  vi.mocked(readAttempt).mockRejectedValueOnce(new Error("blocked"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Browser storage failed",
  );
});

it("keeps diagnostics visible when clearing fails", async () => {
  vi.mocked(readAttempt).mockResolvedValue({
    receivedAt: 1,
    outcome: "EMPTY_SHARE",
    fields: [],
  });
  vi.mocked(clearAttempt).mockRejectedValueOnce(new Error("blocked"));
  render(<App />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Clear diagnostics" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Browser storage failed",
  );
  expect(screen.getByText("No form fields received")).toBeInTheDocument();
});

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
