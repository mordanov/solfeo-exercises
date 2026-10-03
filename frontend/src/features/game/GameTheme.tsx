import "@fontsource/fredoka/400.css";
import "@fontsource/fredoka/600.css";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import type { ReactNode } from "react";

const gameTheme = createTheme({
  palette: {
    primary: { main: "#FF6B6B" }, // coral
    secondary: { main: "#FFD93D" }, // sunflower
    success: { main: "#6BCB77" }, // mint
    background: { default: "#FFF9F0", paper: "#FFFFFF" },
  },
  shape: { borderRadius: 24 },
  typography: {
    fontFamily: "'Fredoka', 'Nunito', 'Comic Sans MS', cursive",
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 600,
          textTransform: "none",
          boxShadow: "0 4px 0 rgba(0,0,0,0.18)",
          "&:active": {
            boxShadow: "0 1px 0 rgba(0,0,0,0.18)",
            transform: "translateY(3px)",
          },
          "@media (prefers-reduced-motion: reduce)": {
            transition: "none",
            transform: "none",
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: { boxShadow: "0 6px 0 rgba(0,0,0,0.12)", borderRadius: 24 },
      },
    },
  },
});

export default function GameTheme({ children }: { children: ReactNode }) {
  return <ThemeProvider theme={gameTheme}>{children}</ThemeProvider>;
}
