import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { i18n } from "./i18n";

beforeEach(async () => {
  window.history.replaceState({}, "", "/");
  await i18n.changeLanguage("en");
});

function mockHealth(health: () => Promise<Response>) {
  vi.stubGlobal("fetch", (url: string) =>
    url === "/api/auth/me"
      ? Promise.resolve(
          new Response('{"error":"AUTH_REQUIRED"}', { status: 401 }),
        )
      : health(),
  );
}

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    </I18nextProvider>,
  );
}

it("shows pending state rather than claiming the backend is healthy", () => {
  mockHealth(vi.fn(() => new Promise<Response>(() => {})));
  renderApp();
  expect(screen.getByRole("status")).toHaveTextContent("Checking the backend");
  expect(screen.queryByText("Backend is available")).not.toBeInTheDocument();
});

it("shows a successful health check", async () => {
  mockHealth(vi.fn().mockResolvedValue(new Response('{"status":"ok"}')));
  renderApp();
  expect(await screen.findByText("Backend is available")).toBeInTheDocument();
  expect(screen.getByText(/does not check the database/)).toBeInTheDocument();
});

it("shows failure and recovers on explicit retry", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(new Response("unavailable", { status: 503 }))
    .mockResolvedValueOnce(new Response('{"status":"ok"}'));
  mockHealth(fetch);
  renderApp();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Backend is unavailable",
  );
  await userEvent.click(screen.getByRole("button", { name: "Check again" }));
  expect(await screen.findByText("Backend is available")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("switches all visible status text and document metadata to Russian and Spanish", async () => {
  mockHealth(
    vi.fn().mockImplementation(async () => new Response('{"status":"ok"}')),
  );
  renderApp();
  await screen.findByText("Backend is available");
  await userEvent.selectOptions(await screen.findByLabelText("Language"), "ru");
  expect(await screen.findByText("Сервер доступен")).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("ru");
  expect(document.title).toBe("Тренажёр сольфеджио");
  await userEvent.selectOptions(screen.getByLabelText("Язык"), "es");
  await waitFor(() => expect(document.documentElement.lang).toBe("es"));
  expect(
    await screen.findByText("El servidor está disponible"),
  ).toBeInTheDocument();
});

it("does not show stale success after a failed recheck", async () => {
  mockHealth(
    vi
      .fn()
      .mockResolvedValueOnce(new Response('{"status":"ok"}'))
      .mockRejectedValueOnce(new TypeError("offline")),
  );
  renderApp();
  await screen.findByText("Backend is available");
  await userEvent.click(screen.getByRole("button", { name: "Check again" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Cannot connect to the backend",
  );
  expect(screen.queryByText("Backend is available")).not.toBeInTheDocument();
});

it("shows an anonymous localized 404 with a home link, without API requests", async () => {
  window.history.replaceState({}, "", "/missing-page?language=ru");
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  renderApp();
  expect(
    screen.getByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Go to home" })).toHaveAttribute(
    "href",
    "/",
  );
  expect(
    screen.queryByRole("button", { name: "Sign in" }),
  ).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.selectOptions(screen.getByLabelText("Language"), "ru");
  expect(
    screen.getByRole("heading", { name: "Страница не найдена" }),
  ).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("ru");
  await userEvent.selectOptions(screen.getByLabelText("Язык"), "es");
  expect(
    screen.getByRole("heading", { name: "Página no encontrada" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Ir al inicio" })).toHaveAttribute(
    "href",
    "/",
  );
});

it.each([
  "/login/",
  "/settings",
  "/manager/users",
  "/manager/exercises/",
  "/manager/journal",
  "/manager/telegram",
  "/student/",
])(
  "keeps direct navigation to %s on the application instead of the 404",
  async (path) => {
    window.history.replaceState({}, "", path);
    mockHealth(async () => new Response('{"status":"ok"}'));
    renderApp();
    expect(
      await screen.findByRole("button", { name: "Sign in" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Page not found")).not.toBeInTheDocument();
  },
);
