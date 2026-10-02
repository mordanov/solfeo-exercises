import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../i18n";
import { AuthArea } from "./AuthArea";
import { AppTheme } from "../../theme";
import { defaultAppearance } from "../../appearance";

const manager = {
  ...defaultAppearance,
  id: 1,
  username: "manager",
  first_name: "First",
  last_name: "Last",
  role: "manager",
  is_active: true,
  is_emergency: false,
  must_change_password: false,
  ui_language: "en",
  note_naming: "letters",
};
const student = { ...manager, id: 2, username: "student", role: "student" };
const auth = (user = manager) => ({ user, csrf_token: "test-csrf" });
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status });

beforeEach(async () => {
  window.history.replaceState({}, "", "/");
  await i18n.changeLanguage("en");
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
          <AuthArea />
        </AppTheme>
      </QueryClientProvider>
    </I18nextProvider>,
  );
}

it("signs in and sends credentials only in the JSON request body", async () => {
  const fetch = vi.fn().mockImplementation(async (url: string) => {
    if (url === "/api/auth/me") return json({ error: "AUTH_REQUIRED" }, 401);
    if (url === "/api/auth/login") return json(auth());
    return json({ users: [manager], total: 1 });
  });
  vi.stubGlobal("fetch", fetch);
  mount();
  await userEvent.type(await screen.findByLabelText("Username"), "manager");
  await userEvent.type(screen.getByLabelText("Password"), "private-password");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(
    await screen.findByRole("heading", { name: "Users" }),
  ).toBeInTheDocument();
  const call = fetch.mock.calls.find(([url]) => url === "/api/auth/login");
  expect(call?.[1]).toMatchObject({
    method: "POST",
    credentials: "same-origin",
    body: JSON.stringify({ username: "manager", password: "private-password" }),
  });
});

it("does not render a login form when session lookup fails", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot connect");
  expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
});

it("applies saved account appearance and restores the standard appearance on logout", async () => {
  window.history.replaceState({}, "", "/settings");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (url: string) =>
      url === "/api/auth/me"
        ? json(
            auth({
              ...manager,
              light_scheme: "forest",
              dark_scheme: "plum",
              ui_font: "serif",
              ui_font_size: 20,
            }),
          )
        : json({ status: "ok" }),
    ),
  );
  mount();
  await waitFor(() =>
    expect(getComputedStyle(document.documentElement).fontSize).toBe("20px"),
  );
  await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
  expect(await screen.findByLabelText("Username")).toBeInTheDocument();
  await waitFor(() =>
    expect(getComputedStyle(document.documentElement).fontSize).toBe("16px"),
  );
});

it("guards manager URLs from students", async () => {
  window.history.replaceState({}, "", "/manager/users");
  const fetch = vi.fn().mockResolvedValue(json(auth(student)));
  vi.stubGlobal("fetch", fetch);
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent("permission");
  expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("guards exercise management from students", async () => {
  window.history.replaceState({}, "", "/manager/exercises");
  const fetch = vi.fn().mockResolvedValue(json(auth(student)));
  vi.stubGlobal("fetch", fetch);
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent("permission");
  expect(
    screen.queryByRole("link", { name: "Exercises" }),
  ).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(["/manager/journal", "/manager/telegram"])(
  "guards %s from students",
  async (path) => {
    window.history.replaceState({}, "", path);
    const fetch = vi.fn().mockResolvedValue(json(auth(student)));
    vi.stubGlobal("fetch", fetch);
    mount();
    expect(await screen.findByRole("alert")).toHaveTextContent("permission");
    expect(
      screen.queryByRole("link", { name: "Listening journal" }),
    ).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  },
);

it("saves language and note naming and applies the returned language", async () => {
  window.history.replaceState({}, "", "/settings");
  const fetch = vi
    .fn()
    .mockImplementation(async (url: string, options: RequestInit = {}) => {
      if (url === "/api/auth/me") return json(auth(student));
      if (typeof options.body !== "string")
        throw new Error("Missing settings body");
      const values: unknown = JSON.parse(options.body);
      if (typeof values !== "object" || values === null)
        throw new Error("Invalid settings body");
      return json({ ...student, ...values });
    });
  vi.stubGlobal("fetch", fetch);
  mount();
  await userEvent.selectOptions(
    await screen.findByLabelText("Note naming"),
    "solfege",
  );
  await screen.findByText("Settings saved");
  await userEvent.selectOptions(screen.getByLabelText("Language"), "ru");
  expect(await screen.findByText("Настройки сохранены")).toBeInTheDocument();
  const call = fetch.mock.calls
    .filter(([url]) => url === "/api/settings")
    .at(-1);
  expect(call?.[1].headers["X-CSRF-Token"]).toBe("test-csrf");
  expect(JSON.parse(call?.[1].body)).toEqual({
    ui_language: "ru",
    note_naming: "solfege",
  });
});

it("requires a password change before showing protected features", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        json(auth({ ...student, must_change_password: true })),
      ),
  );
  mount();
  expect(
    await screen.findByText("Change your password before continuing."),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Current password")).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Settings" }),
  ).not.toBeInTheDocument();
});

it("creates users with a CSRF token and refreshes the list", async () => {
  let users = [manager];
  const fetch = vi
    .fn()
    .mockImplementation(async (url: string, options: RequestInit = {}) => {
      if (url === "/api/auth/me") return json(auth());
      if (options.method === "POST") {
        users = [manager, student];
        return json(student, 201);
      }
      return json({ users, total: users.length });
    });
  vi.stubGlobal("fetch", fetch);
  mount();
  await userEvent.type(await screen.findByLabelText("Username"), "student");
  await userEvent.type(screen.getByLabelText("First name"), "First");
  await userEvent.type(screen.getByLabelText("Last name"), "Last");
  await userEvent.type(
    screen.getByLabelText("Temporary password"),
    "private-password",
  );
  await userEvent.click(screen.getByRole("button", { name: "Create user" }));
  expect(await screen.findByText("student")).toBeInTheDocument();
  const call = fetch.mock.calls.find(
    ([url, options]) => url === "/api/users" && options.method === "POST",
  );
  expect(call?.[1].headers["X-CSRF-Token"]).toBe("test-csrf");
});

it("removes protected data after logout", async () => {
  const fetch = vi.fn().mockImplementation(async (url: string) => {
    if (url === "/api/auth/me") return json(auth());
    if (url === "/api/auth/logout") return json({ status: "ok" });
    return json({ users: [manager], total: 1 });
  });
  vi.stubGlobal("fetch", fetch);
  mount();
  await userEvent.click(
    await screen.findByRole("button", { name: "Sign out" }),
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );
  expect(
    screen.queryByRole("heading", { name: "Users" }),
  ).not.toBeInTheDocument();
});
