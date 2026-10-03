import { useState } from "react";

import { type Auth } from "../../api/auth";
import { type Task } from "./api/hooks";
import { unlockAudio } from "./audio/synth";
import PlayScreen, { type RoundResult } from "./play/PlayScreen";
import ResultScreen from "./result/ResultScreen";
import GameTheme from "./GameTheme";
import GameSetup from "./setup/GameSetup";
import PlayerSelect from "./setup/PlayerSelect";

const TIME_LIMIT_MS: Record<string, number> = {
  easy: 13000,
  medium: 10000,
  hard: 7000,
};

type Screen =
  | { name: "players" }
  | { name: "setup"; playerId: number }
  | {
      name: "play";
      roundId: number;
      firstTask: Task;
      noteCount: number;
      difficulty: string;
      timeLimitMs: number;
      playerId: number;
    }
  | { name: "result"; roundId: number; result: RoundResult; playerId: number };

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
          onRoundStarted={(roundId, firstTask, noteCount, difficulty) => {
            unlockAudio();
            window.history.pushState(null, "", `/game/play/${roundId}`);
            setScreen({
              name: "play",
              roundId,
              firstTask,
              noteCount,
              difficulty,
              timeLimitMs: TIME_LIMIT_MS[difficulty] ?? 10000,
              playerId: screen.playerId,
            });
          }}
        />
      )}
      {screen.name === "play" && (
        <PlayScreen
          roundId={screen.roundId}
          csrf={auth.csrf_token}
          initialTask={screen.firstTask}
          noteCount={screen.noteCount}
          difficulty={screen.difficulty}
          timeLimitMs={screen.timeLimitMs}
          onResult={(result) => {
            window.history.pushState(
              null,
              "",
              `/game/result/${screen.roundId}`,
            );
            setScreen({
              name: "result",
              roundId: screen.roundId,
              result,
              playerId: screen.playerId,
            });
          }}
        />
      )}
      {screen.name === "result" && (
        <ResultScreen
          result={screen.result}
          onPlayAgain={() => {
            window.history.pushState(
              null,
              "",
              `/game/setup/${screen.playerId}`,
            );
            setScreen({ name: "setup", playerId: screen.playerId });
          }}
          onChangePlayer={() => {
            window.history.pushState(null, "", "/game");
            setScreen({ name: "players" });
          }}
        />
      )}
    </GameTheme>
  );
}
