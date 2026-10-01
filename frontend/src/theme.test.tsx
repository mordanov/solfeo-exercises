import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it } from "vitest";
import { getContrastRatio } from "@mui/material/styles";
import { i18n } from "./i18n";
import { AppTheme, fieldOutline, theme } from "./theme";
import { ThemeToggle } from "./components/ThemeToggle";

beforeEach(async () => {
  localStorage.clear();
  await i18n.changeLanguage("en");
});

it("preserves form state and audio identity when switching and remembers the theme", async () => {
  function Content() {
    const [value, setValue] = useState("");
    return (
      <>
        <ThemeToggle />
        <input
          aria-label="Preserved input"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <audio data-testid="preserved-audio" />
      </>
    );
  }
  render(
    <I18nextProvider i18n={i18n}>
      <AppTheme>
        <Content />
      </AppTheme>
    </I18nextProvider>,
  );
  const audio = screen.getByTestId("preserved-audio");
  await userEvent.type(screen.getByLabelText("Preserved input"), "unchanged");
  await userEvent.click(screen.getByRole("button", { name: "Use dark theme" }));
  expect(screen.getByLabelText("Preserved input")).toHaveValue("unchanged");
  expect(screen.getByTestId("preserved-audio")).toBe(audio);
  expect(localStorage.getItem("solfeo-theme")).toBe("dark");
  expect(document.documentElement).toHaveAttribute("data-color-scheme", "dark");
  await userEvent.click(
    screen.getByRole("button", { name: "Use light theme" }),
  );
  expect(localStorage.getItem("solfeo-theme")).toBe("light");
});

it.each(["en", "ru", "es"])(
  "localizes the theme control in %s",
  async (language) => {
    await i18n.changeLanguage(language);
    render(
      <I18nextProvider i18n={i18n}>
        <AppTheme>
          <ThemeToggle />
        </AppTheme>
      </I18nextProvider>,
    );
    expect(screen.getByRole("button")).toHaveAccessibleName(
      i18n.t("theme.dark"),
    );
  },
);

it.each(["light", "dark"] as const)(
  "keeps readable palette contrast in %s",
  (mode) => {
    const palette = theme.colorSchemes[mode];
    if (!palette) throw new Error(`Missing ${mode} scheme`);
    for (const background of [
      palette.palette.background.default,
      palette.palette.background.paper,
    ]) {
      for (const text of [
        palette.palette.text.primary,
        palette.palette.text.secondary,
        palette.palette.primary.main,
      ]) {
        expect(getContrastRatio(text, background)).toBeGreaterThanOrEqual(4.5);
      }
    }
    expect(
      getContrastRatio(
        palette.palette.primary.main,
        palette.palette.primary.contrastText,
      ),
    ).toBeGreaterThanOrEqual(4.5);
    expect(
      getContrastRatio(fieldOutline[mode], palette.palette.background.paper),
    ).toBeGreaterThanOrEqual(3);
  },
);
