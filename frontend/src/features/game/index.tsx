import { useState } from "react";

import { type Auth } from "../../api/auth";
import { type Task } from "./api/hooks";
import { unlockAudio } from "./audio/synth";
import GameTheme from "./GameTheme";
import GameSetup from "./setup/GameSetup";
import PlayerSelect from "./setup/PlayerSelect";

type Screen =
  | { name: "players" }
  | { name: "setup"; playerId: number }
  | { name: "play"; roundId: number; firstTask: Task };

interface Props {
  auth: Auth;
}

export default function GameArea({ auth }: Props) {
  const [screen, setScreen] = useState<Screen>(() => {
    const path = window.location.pathname;
    const m = path.match(/^\/game\/setup\/(\d+)/);
    if (m) return { name: "setup", playerId: Number(m[1]) };
    return { name: "players" };
  });

  return (
    <GameTheme>
      {screen.name === "players" && (
        <PlayerSelect
          onSelect={(id) => {
            window.history.pushState(null, "", `/game/setup/${id}`);
            setScreen({ name: "setup", playerId: id });
          }}
        />
      )}
      {screen.name === "setup" && (
        <GameSetup
          playerId={screen.playerId}
          csrf={auth.csrf_token}
          onRoundStarted={(roundId, firstTask) => {
            unlockAudio();
            window.history.pushState(null, "", `/game/play/${roundId}`);
            setScreen({ name: "play", roundId, firstTask });
          }}
        />
      )}
      {screen.name === "play" && (
        <div style={{ padding: 24 }}>Play screen — Task 8</div>
      )}
    </GameTheme>
  );
}
