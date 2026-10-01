import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../../api/auth";
import { i18n } from "../../i18n";
import { Users } from "./Users";

vi.mock("../../api/auth", async (original) => ({
  ...(await original<typeof api>()),
  listUsers: vi.fn(),
  updateUser: vi.fn(),
  resetPassword: vi.fn(),
}));

const manager: api.User = {
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
const rows: api.User[] = Array.from({ length: 50 }, (_, index) => ({
  ...manager,
  id: index + 2,
  username: `student${index + 1}`,
  role: "student",
}));

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.listUsers).mockResolvedValue({ users: rows, total: 51 });
  vi.mocked(api.updateUser).mockResolvedValue(rows[49]);
});

function mount() {
  render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false, gcTime: 0 } },
          })
        }
      >
        <Users auth={{ user: manager, csrf_token: "csrf" }} />
      </QueryClientProvider>
    </I18nextProvider>,
  );
}

it("keeps every server-page row, existing pagination and inline editing", async () => {
  mount();
  const grid = await screen.findByRole("grid", { name: "Users" });
  expect(within(grid).getByText("student50")).toBeInTheDocument();
  expect(within(grid).queryByRole("checkbox")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() =>
    expect(api.listUsers).toHaveBeenCalledWith(50, expect.any(AbortSignal)),
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Edit student50" }),
  );
  const editor = screen.getByRole("region", { name: "Edit student50" });
  await userEvent.clear(within(editor).getByLabelText("First name"));
  await userEvent.type(within(editor).getByLabelText("First name"), "Changed");
  await userEvent.click(
    within(editor).getByRole("button", { name: "Save user" }),
  );
  await waitFor(() =>
    expect(api.updateUser).toHaveBeenCalledWith("csrf", 51, {
      first_name: "Changed",
      last_name: "Last",
      role: "student",
    }),
  );
});

it("preserves emergency and current-account action restrictions", async () => {
  vi.mocked(api.listUsers).mockResolvedValue({
    users: [
      manager,
      { ...manager, id: 3, username: "emergency", is_emergency: true },
    ],
    total: 2,
  });
  mount();
  const grid = await screen.findByRole("grid", { name: "Users" });
  expect(within(grid).queryByRole("button")).not.toBeInTheDocument();
});
