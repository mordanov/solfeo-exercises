import { Box, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";

interface Props {
  totalMs: number;
  onExpire: () => void;
  paused?: boolean;
  deadlineMs?: number;
}

export default function Timer({
  totalMs,
  onExpire,
  paused = false,
  deadlineMs,
}: Props) {
  const fallbackDeadline = useRef(Date.now() + totalMs);
  const deadline = deadlineMs ?? fallbackDeadline.current;
  const [remaining, setRemaining] = useState(() =>
    Math.max(0, deadline - Date.now()),
  );
  const expiredRef = useRef(false);

  useEffect(() => {
    if (paused) return;

    const tick = () => {
      const left = Math.max(0, deadline - Date.now());
      setRemaining(left);
      if (left <= 0 && !expiredRef.current) {
        expiredRef.current = true;
        onExpire();
      }
    };
    tick();
    const id = setInterval(tick, 50);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [paused, deadline, onExpire]);

  const pct = Math.min(100, (remaining / totalMs) * 100);
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
