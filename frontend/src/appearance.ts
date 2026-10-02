export const schemes = ["classic", "forest", "warm", "plum"] as const;
export type ColorScheme = (typeof schemes)[number];
export type UiFont = "roboto" | "system" | "serif";
export type UiFontSize = 16 | 18 | 20;
export type Appearance = {
  light_scheme: ColorScheme;
  dark_scheme: ColorScheme;
  ui_font: UiFont;
  ui_font_size: UiFontSize;
};
export const defaultAppearance: Appearance = {
  light_scheme: "classic",
  dark_scheme: "classic",
  ui_font: "roboto",
  ui_font_size: 16,
};
export const fonts = {
  roboto: '"Roboto", sans-serif',
  system:
    'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  serif: 'Georgia, "Times New Roman", serif',
};
export function isColorScheme(value: unknown): value is ColorScheme {
  return schemes.some((scheme) => scheme === value);
}
export function isUiFont(value: unknown): value is UiFont {
  return value === "roboto" || value === "system" || value === "serif";
}
export function isUiFontSize(value: unknown): value is UiFontSize {
  return value === 16 || value === 18 || value === 20;
}
export function sameAppearance(left: Appearance, right: Appearance): boolean {
  return (
    left.light_scheme === right.light_scheme &&
    left.dark_scheme === right.dark_scheme &&
    left.ui_font === right.ui_font &&
    left.ui_font_size === right.ui_font_size
  );
}

type Palette = {
  primary: { main: string; dark?: string; contrastText: string };
  secondary: { main: string; dark?: string; contrastText: string };
  background: { default: string; paper: string };
  text: { primary: string; secondary: string };
  divider: string;
  outline: string;
};
export const palettes: Record<
  ColorScheme,
  Record<"light" | "dark", Palette>
> = {
  classic: {
    light: {
      primary: { main: "#435b83", contrastText: "#ffffff" },
      secondary: { main: "#596579", contrastText: "#ffffff" },
      background: { default: "#f4f6fa", paper: "#ffffff" },
      text: { primary: "#1e293b", secondary: "#526077" },
      divider: "#d6dde8",
      outline: "#8491a6",
    },
    dark: {
      primary: { main: "#adc7f3", contrastText: "#172238" },
      secondary: { main: "#bac5da", contrastText: "#172238" },
      background: { default: "#111827", paper: "#1c2637" },
      text: { primary: "#edf2fa", secondary: "#bcc8db" },
      divider: "#46546b",
      outline: "#73839c",
    },
  },
  forest: {
    light: {
      primary: { main: "#28664a", contrastText: "#ffffff" },
      secondary: { main: "#4c6354", contrastText: "#ffffff" },
      background: { default: "#f1f7f2", paper: "#ffffff" },
      text: { primary: "#21352a", secondary: "#4e6657" },
      divider: "#d2dfd5",
      outline: "#718a77",
    },
    dark: {
      primary: { main: "#9ed6b0", dark: "#75a082", contrastText: "#172c20" },
      secondary: { main: "#b4cfbd", dark: "#849b8c", contrastText: "#172c20" },
      background: { default: "#121d17", paper: "#1c2c23" },
      text: { primary: "#e8f4eb", secondary: "#b4cbbd" },
      divider: "#435b4b",
      outline: "#718f7b",
    },
  },
  warm: {
    light: {
      primary: { main: "#7b4b24", contrastText: "#ffffff" },
      secondary: { main: "#705a43", contrastText: "#ffffff" },
      background: { default: "#fbf7ef", paper: "#fffdf8" },
      text: { primary: "#33291f", secondary: "#62513e" },
      divider: "#dfd1bb",
      outline: "#a07e58",
    },
    dark: {
      primary: { main: "#efbe88", contrastText: "#2d1c10" },
      secondary: { main: "#d9c2a7", contrastText: "#2d1c10" },
      background: { default: "#211b16", paper: "#302720" },
      text: { primary: "#f8eee2", secondary: "#d5c2ad" },
      divider: "#64503f",
      outline: "#ab8d71",
    },
  },
  plum: {
    light: {
      primary: { main: "#75508b", contrastText: "#ffffff" },
      secondary: { main: "#675b79", contrastText: "#ffffff" },
      background: { default: "#f8f3fa", paper: "#fffaff" },
      text: { primary: "#34283e", secondary: "#68566f" },
      divider: "#e1d4e8",
      outline: "#91779e",
    },
    dark: {
      primary: { main: "#d4b7ed", contrastText: "#2c1838" },
      secondary: { main: "#c9bfd3", contrastText: "#2c1838" },
      background: { default: "#211727", paper: "#30223a" },
      text: { primary: "#f5ebfa", secondary: "#d1bfdc" },
      divider: "#665071",
      outline: "#9b83ad",
    },
  },
};
