import { useState } from "react";

import { type Auth } from "../../api/auth";
import { type Task } from "./api/hooks";
import { DEFAULT_GAME_OPTIONS, DIFFICULTIES, type GameOptions } from "./notes";
import AdminPlayerDetail from "./admin/AdminPlayerDetail";
import AdminScreen from "./admin/AdminScreen";
import PlayScreen, { type RoundResult } from "./play/PlayScreen";
import ProfileScreen from "./profile/ProfileScreen";
import ResultScreen from "./result/ResultScreen";
import GameTheme from "./GameTheme";
import GameSetup from "./setup/GameSetup";
import PlayerSelect from "./setup/PlayerSelect";

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
      options: GameOptions;
    }
  | { name: "result"; roundId: number; result: RoundResult; playerId: number }
  | { name: "profile"; playerId: number; xp: number }
  | { name: "admin" }
  | { name: "admin-detail"; playerId: number };

interface Props {
  auth: Auth;
}

export default function GameArea({ auth }: Props) {
  const [options, setOptions] = useState(DEFAULT_GAME_OPTIONS);
  const [screen, setScreen] = useState<Screen>(() => {
    const path = window.location.pathname;
    const setup = path.match(/^\/game\/setup\/(\d+)/);
    if (setup) return { name: "setup", playerId: Number(setup[1]) };
    if (path === "/game/admin") return { name: "admin" };
    const adminDetail = path.match(/^\/game\/admin\/(\d+)/);
    if (adminDetail)
      return { name: "admin-detail", playerId: Number(adminDetail[1]) };
    return { name: "players" };
  });

  return (
    <GameTheme>
      {screen.name === "players" && (
        <PlayerSelect
          auth={auth}
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
          initialOptions={options}
          onRoundStarted={(
            roundId,
            firstTask,
            noteCount,
            difficulty,
            roundOptions,
          ) => {
            setOptions(roundOptions);
            window.history.pushState(null, "", `/game/play/${roundId}`);
            setScreen({
              name: "play",
              roundId,
              firstTask,
              noteCount,
              difficulty,
              timeLimitMs:
                DIFFICULTIES.find((item) => item.name === difficulty)?.timeMs ??
                10000,
              playerId: screen.playerId,
              options: roundOptions,
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
          noteNaming={auth.user.note_naming}
          {...screen.options}
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
          playerId={screen.playerId}
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
      {screen.name === "profile" && (
        <ProfileScreen playerId={screen.playerId} xp={screen.xp} />
      )}
      {screen.name === "admin" && (
        <AdminScreen
          csrf={auth.csrf_token}
          onPlayerDetail={(playerId) => {
            window.history.pushState(null, "", `/game/admin/${playerId}`);
            setScreen({ name: "admin-detail", playerId });
          }}
        />
      )}
      {screen.name === "admin-detail" && (
        <AdminPlayerDetail playerId={screen.playerId} />
      )}
    </GameTheme>
  );
}
