import { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it } from "vitest";
import { getContrastRatio, useTheme } from "@mui/material/styles";
import { AppTheme, createAppearanceTheme, useAppearance } from "./theme";
import { defaultAppearance, palettes, schemes } from "./appearance";

it("keeps every paired palette readable without depending on text size", () => {
  for (const scheme of Object.values(palettes))
    for (const palette of Object.values(scheme)) {
      for (const background of [
        palette.background.default,
        palette.background.paper,
      ]) {
        for (const color of [
          palette.text.primary,
          palette.text.secondary,
          palette.primary.main,
          palette.secondary.main,
        ])
          expect(getContrastRatio(color, background)).toBeGreaterThanOrEqual(
            4.5,
          );
      }
      expect(
        getContrastRatio(palette.outline, palette.background.paper),
      ).toBeGreaterThanOrEqual(3);
      for (const button of [palette.primary, palette.secondary])
        expect(
          getContrastRatio(button.main, button.contrastText),
        ).toBeGreaterThanOrEqual(4.5);
    }
});
it("keeps contained button labels readable in hover states", () => {
  for (const scheme of schemes)
    for (const mode of ["light", "dark"] as const) {
      const theme = createAppearanceTheme(
        { ...defaultAppearance, light_scheme: scheme, dark_scheme: scheme },
        mode,
      );
      for (const button of [theme.palette.primary, theme.palette.secondary])
        expect(
          getContrastRatio(button.dark, button.contrastText),
        ).toBeGreaterThanOrEqual(4.5);
    }
});
it("keeps light and dark selections independent and supports each font and size", () => {
  for (const ui_font of ["roboto", "system", "serif"] as const)
    for (const ui_font_size of [16, 18, 20] as const) {
      const theme = createAppearanceTheme({
        ...defaultAppearance,
        light_scheme: "forest",
        dark_scheme: "plum",
        ui_font,
        ui_font_size,
      });
      expect(theme.colorSchemes.light?.palette.primary.main).toBe(
        palettes.forest.light.primary.main,
      );
      expect(theme.colorSchemes.dark?.palette.primary.main).toBe(
        palettes.plum.dark.primary.main,
      );
      expect(theme.typography.fontFamily).toBeTruthy();
    }
});
it("changes appearance without remounting audio or losing form values", async () => {
  function Content() {
    const [text, setText] = useState("");
    const { setAppearance } = useAppearance();
    const theme = useTheme();
    return (
      <>
        <input
          aria-label="Preserved form"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <audio data-testid="audio" />
        <output>{theme.typography.fontFamily}</output>
        <button
          onClick={() =>
            setAppearance({
              ...defaultAppearance,
              light_scheme: "warm",
              dark_scheme: "forest",
              ui_font: "serif",
              ui_font_size: 20,
            })
          }
        >
          Apply
        </button>
      </>
    );
  }
  render(
    <AppTheme>
      <Content />
    </AppTheme>,
  );
  const audio = screen.getByTestId("audio");
  fireEvent.change(screen.getByLabelText("Preserved form"), {
    target: { value: "unchanged" },
  });
  fireEvent.click(screen.getByText("Apply"));
  await waitFor(() =>
    expect(screen.getByRole("status")).toHaveTextContent("Georgia"),
  );
  expect(screen.getByTestId("audio")).toBe(audio);
  expect(screen.getByLabelText("Preserved form")).toHaveValue("unchanged");
  expect(getComputedStyle(document.documentElement).fontSize).toBe("20px");
});
