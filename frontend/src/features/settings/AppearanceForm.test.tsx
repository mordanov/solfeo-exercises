import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../i18n";
import { defaultAppearance } from "../../appearance";
import { AppTheme } from "../../theme";
import { ThemeToggle } from "../../components/ThemeToggle";
import type { User } from "../../api/auth";
import * as api from "../../api/auth";
import { AppearanceForm } from "./AppearanceForm";
import { useState } from "react";

vi.mock("../../api/auth", async (original) => ({
  ...(await original<typeof import("../../api/auth")>()),
  saveAppearance: vi.fn(),
}));
const user: User = {
  id: 1,
  username: "student",
  first_name: "First",
  last_name: "Last",
  role: "student",
  is_active: true,
  is_emergency: false,
  must_change_password: false,
  ui_language: "en",
  note_naming: "letters",
  ...defaultAppearance,
};
beforeEach(async () => {
  vi.clearAllMocks();
  localStorage.clear();
  await i18n.changeLanguage("en");
});
function mount() {
  const onChange = vi.fn();
  function Content() {
    const [profile, setProfile] = useState(user);
    return (
      <AppearanceForm
        auth={{ user: profile, csrf_token: "csrf" }}
        onChange={(value) => {
          onChange(value);
          setProfile(value);
        }}
      />
    );
  }
  const view = render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { mutations: { retry: false } } })
        }
      >
        <AppTheme>
          <ThemeToggle />
          <Content />
        </AppTheme>
      </QueryClientProvider>
    </I18nextProvider>,
  );
  return { ...view, onChange };
}
it("previews independent palettes and fonts without changing the application mode or saving a draft", () => {
  mount();
  fireEvent.change(screen.getByLabelText("Light theme scheme"), {
    target: { value: "forest" },
  });
  fireEvent.change(screen.getByLabelText("Dark theme scheme"), {
    target: { value: "plum" },
  });
  fireEvent.change(screen.getByLabelText("Font"), {
    target: { value: "serif" },
  });
  fireEvent.change(screen.getByLabelText("Font size"), {
    target: { value: "20" },
  });
  fireEvent.change(screen.getByLabelText("Preview theme"), {
    target: { value: "dark" },
  });
  const panel = screen.getByRole("region", { name: "Appearance preview" });
  expect(
    within(panel).getByRole("button", { name: "Primary action" }),
  ).toBeInTheDocument();
  expect(getComputedStyle(within(panel).getByRole("textbox")).fontSize).toBe(
    "20px",
  );
  expect(document.documentElement).toHaveAttribute(
    "data-color-scheme",
    "light",
  );
  expect(api.saveAppearance).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Save appearance" })).toBeEnabled();
});
it("saves the entire appearance draft and resets only appearance", async () => {
  const view = mount();
  const changed = {
    ...user,
    light_scheme: "forest" as const,
    ui_font: "serif" as const,
    ui_font_size: 20 as const,
  };
  vi.mocked(api.saveAppearance).mockResolvedValue(changed);
  fireEvent.change(screen.getByLabelText("Light theme scheme"), {
    target: { value: "forest" },
  });
  fireEvent.change(screen.getByLabelText("Font"), {
    target: { value: "serif" },
  });
  fireEvent.change(screen.getByLabelText("Font size"), {
    target: { value: "20" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save appearance" }));
  await waitFor(() => expect(view.onChange).toHaveBeenCalledWith(changed));
  expect(api.saveAppearance).toHaveBeenLastCalledWith("csrf", {
    ...defaultAppearance,
    light_scheme: "forest",
    ui_font: "serif",
    ui_font_size: 20,
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Restore standard appearance" }),
  );
  vi.mocked(api.saveAppearance).mockResolvedValue(user);
  fireEvent.click(screen.getByRole("button", { name: "Save appearance" }));
  await waitFor(() =>
    expect(api.saveAppearance).toHaveBeenLastCalledWith(
      "csrf",
      defaultAppearance,
    ),
  );
});
it("reports failed saving without claiming success or discarding the selected draft", async () => {
  mount();
  vi.mocked(api.saveAppearance).mockRejectedValue(
    new api.ApiError("NETWORK_ERROR"),
  );
  fireEvent.change(screen.getByLabelText("Dark theme scheme"), {
    target: { value: "warm" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save appearance" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot connect");
  expect(screen.getByLabelText("Dark theme scheme")).toHaveValue("warm");
  expect(screen.queryByText("Appearance saved")).not.toBeInTheDocument();
});
it.each(["ru", "en", "es"])(
  "localizes the complete appearance panel in %s",
  async (language) => {
    await i18n.changeLanguage(language);
    mount();
    expect(
      screen.getByRole("region", { name: i18n.t("appearance.title") }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: i18n.t("appearance.preview.title") }),
    ).toBeInTheDocument();
  },
);
