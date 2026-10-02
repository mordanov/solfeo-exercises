import {
  createContext,
  useCallback,
  createElement,
  Fragment,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import CssBaseline from "@mui/material/CssBaseline";
import type {} from "@mui/material/themeCssVarsAugmentation";
import { createTheme, ThemeProvider, type Shadows } from "@mui/material/styles";
import {
  defaultAppearance,
  fonts,
  palettes,
  sameAppearance,
  type Appearance,
} from "./appearance";

const shadows: Shadows = [...createTheme().shadows];
for (let index = 1; index < shadows.length; index++) {
  shadows[index] =
    `0 ${Math.ceil(index / 2)}px ${8 + index * 2}px rgba(15, 23, 42, 0.08)`;
}

export const fieldOutline = {
  light: palettes.classic.light.outline,
  dark: palettes.classic.dark.outline,
};

export function createAppearanceTheme(
  appearance: Appearance,
  previewMode?: "light" | "dark",
) {
  const light = palettes[appearance.light_scheme].light;
  const dark = palettes[appearance.dark_scheme].dark;
  return createTheme({
    cssVariables: previewMode
      ? false
      : { colorSchemeSelector: "[data-color-scheme='%s']" },
    ...(previewMode
      ? {
          palette: {
            ...(previewMode === "light" ? light : dark),
            mode: previewMode,
          },
        }
      : {
          colorSchemes: { light: { palette: light }, dark: { palette: dark } },
        }),
    shape: { borderRadius: 12 },
    shadows,
    typography: {
      fontFamily: fonts[appearance.ui_font],
      h1: { fontSize: "2.25rem", fontWeight: 700, lineHeight: 1.2 },
      h2: { fontSize: "1.65rem", fontWeight: 700, lineHeight: 1.3 },
      h3: { fontSize: "1.2rem", fontWeight: 600, lineHeight: 1.4 },
      h4: { fontSize: "1.1rem", fontWeight: 600, lineHeight: 1.4 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: (theme) => ({
          html: { fontSize: appearance.ui_font_size },
          body: { overflowWrap: "anywhere" },
          h1: theme.typography.h1,
          h2: theme.typography.h2,
          h3: theme.typography.h3,
          h4: theme.typography.h4,
          "h1, h2, h3, h4": { marginTop: 0, marginBottom: "1rem" },
          p: { lineHeight: 1.65 },
          a: { color: (theme.vars?.palette ?? theme.palette).primary.main },
          audio: { maxWidth: "100%", width: "100%" },
          ":focus-visible": {
            outline: `3px solid ${(theme.vars?.palette ?? theme.palette).primary.main}`,
            outlineOffset: 3,
          },
          [theme.breakpoints.down("sm")]: {
            h1: { fontSize: "1.75rem" },
            h2: { fontSize: "1.5rem" },
          },
        }),
      },
      MuiTypography: {
        styleOverrides: {
          h1: ({ theme }) => ({
            [theme.breakpoints.down("sm")]: { fontSize: "1.75rem" },
          }),
        },
      },
      MuiButton: {
        defaultProps: { variant: "contained", disableElevation: true },
        styleOverrides: {
          root: ({ theme }) => ({
            minHeight: 44,
            paddingInline: 18,
            marginBlock: 4,
            marginInlineEnd: 8,
            [theme.breakpoints.down("sm")]: {
              maxWidth: "100%",
              marginInlineEnd: 0,
            },
            "&:focus-visible": {
              outline: `3px solid ${(theme.vars?.palette ?? theme.palette).primary.main}`,
              outlineOffset: 3,
            },
          }),
        },
      },
      MuiCheckbox: {
        styleOverrides: {
          root: ({ theme }) => ({
            [theme.breakpoints.down("sm")]: {
              minWidth: 44,
              minHeight: 44,
            },
            "&.Mui-focusVisible": {
              outline: `3px solid ${(theme.vars?.palette ?? theme.palette).primary.main}`,
              outlineOffset: 2,
            },
          }),
        },
      },
      MuiCard: {
        defaultProps: { elevation: 1 },
        styleOverrides: {
          root: ({ theme }) => ({
            minWidth: 0,
            backgroundImage: "none",
            padding: "clamp(16px, 3vw, 28px)",
            marginBlock: 20,
            overflow: "visible",
            [theme.breakpoints.down("sm")]: {
              padding: 12,
              marginBlock: 16,
              "& .MuiCard-root": {
                paddingInline: 0,
                boxShadow: "none",
              },
            },
          }),
        },
      },
      MuiTextField: {
        defaultProps: { variant: "outlined", size: "small" },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: ({ theme }) => ({
            minHeight: 44,
            minWidth: 0,
            "& .MuiOutlinedInput-notchedOutline": {
              borderColor: light.outline,
            },
            ...theme.applyStyles("dark", {
              "& .MuiOutlinedInput-notchedOutline": {
                borderColor: dark.outline,
              },
            }),
          }),
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: { borderRadius: 12, backgroundImage: "none" },
        },
      },
      MuiAlert: {
        styleOverrides: { root: { marginBlock: 12 } },
      },
      MuiLink: {
        defaultProps: { underline: "hover" },
        styleOverrides: {
          root: ({ theme }) => ({
            [theme.breakpoints.down("sm")]: {
              display: "inline-flex",
              alignItems: "center",
              minWidth: 44,
              minHeight: 44,
            },
          }),
        },
      },
    },
  });
}
export const theme = createAppearanceTheme(defaultAppearance);
const AppearanceContext = createContext<{
  appearance: Appearance;
  setAppearance: (value: Appearance) => void;
} | null>(null);

export function useAppearance() {
  const context = useContext(AppearanceContext);
  if (!context) throw new Error("APPEARANCE_PROVIDER_MISSING");
  return context;
}

export function AppTheme({ children }: { children: ReactNode }) {
  const [appearance, update] = useState(defaultAppearance);
  const setAppearance = useCallback((value: Appearance) => {
    update((previous) => (sameAppearance(previous, value) ? previous : value));
  }, []);
  const context = useMemo(
    () => ({
      appearance,
      setAppearance,
    }),
    [appearance, setAppearance],
  );
  const selectedTheme = useMemo(
    () => createAppearanceTheme(appearance),
    [appearance],
  );
  return createElement(
    AppearanceContext.Provider,
    { value: context },
    createElement(
      ThemeProvider,
      {
        theme: selectedTheme,
        defaultMode: "light",
        modeStorageKey: "solfeo-theme",
        disableTransitionOnChange: true,
      },
      createElement(Fragment, null, createElement(CssBaseline), children),
    ),
  );
}
