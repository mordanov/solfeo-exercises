import { Box, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";

interface Props {
  totalMs: number;
  onExpire: () => void;
  paused?: boolean;
}

export default function Timer({ totalMs, onExpire, paused = false }: Props) {
  const startRef = useRef(Date.now());
  const pausedAtRef = useRef<number | null>(null);
  const [remaining, setRemaining] = useState(totalMs);
  const expiredRef = useRef(false);

  useEffect(() => {
    if (paused) {
      pausedAtRef.current = Date.now();
      return;
    }
    if (pausedAtRef.current !== null) {
      startRef.current += Date.now() - pausedAtRef.current;
      pausedAtRef.current = null;
    }

    const tick = () => {
      const elapsed = Date.now() - startRef.current;
      const left = Math.max(0, totalMs - elapsed);
      setRemaining(left);
      if (left <= 0 && !expiredRef.current) {
        expiredRef.current = true;
        onExpire();
      }
    };
    const id = setInterval(tick, 50);
    return () => clearInterval(id);
  }, [paused, totalMs, onExpire]);

  useEffect(() => {
    const handler = () => {
      if (document.hidden) {
        pausedAtRef.current = Date.now();
      } else if (pausedAtRef.current !== null) {
        startRef.current += Date.now() - pausedAtRef.current;
        pausedAtRef.current = null;
      }
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, []);

  const pct = (remaining / totalMs) * 100;
  const hurry = remaining < 2000;

  return (
    <Box sx={{ mb: 2 }}>
      {hurry && (
        <Typography
          variant="caption"
          sx={{ display: "block", textAlign: "center", color: "#e55" }}
        >
          🔥 {Math.ceil(remaining / 1000)}
        </Typography>
      )}
      <Box
        sx={{
          height: 14,
          borderRadius: 99,
          overflow: "hidden",
          background: "#eee",
          position: "relative",
          "@media (prefers-reduced-motion: reduce)": {
            "& > div": { transition: "none" },
          },
        }}
      >
        <Box
          sx={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: `${pct}%`,
            background: hurry ? "#FF6B35" : "#6BCB77",
            transition: "width 0.05s linear, background 0.3s",
          }}
        />
      </Box>
    </Box>
  );
}
