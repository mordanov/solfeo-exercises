import { Alert, Button } from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Auth } from "../../api/auth";
import { type Task } from "./api/hooks";
import { DEFAULT_GAME_OPTIONS, DIFFICULTIES, type GameOptions } from "./notes";
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
  | { name: "profile"; playerId: number }
  | { name: "admin" }
  | { name: "admin-detail"; playerId: number };

interface Props {
  auth: Auth;
}

function screenFromPath(): Screen {
  const path = window.location.pathname;
  const match = path.match(/^\/game\/(profile|setup|admin)\/(\d+)\/?$/);
  if (match) {
    const name =
      match[1] === "admin"
        ? "admin-detail"
        : match[1] === "profile"
          ? "profile"
          : "setup";
    return { name, playerId: Number(match[2]) };
  }
  return { name: path === "/game/admin" ? "admin" : "players" };
}

export default function GameArea({ auth }: Props) {
  const { t } = useTranslation();
  const [options, setOptions] = useState(DEFAULT_GAME_OPTIONS);
  const [screen, setScreen] = useState<Screen>(screenFromPath);
  useEffect(() => {
    const onBack = () => {
      setScreen(screenFromPath());
    };
    window.addEventListener("popstate", onBack);
    return () => window.removeEventListener("popstate", onBack);
  }, []);

  const backToPlayers = () => {
    window.history.pushState(null, "", "/game");
    setScreen({ name: "players" });
  };
  const toAdmin = () => {
    window.history.pushState(null, "", "/game/admin");
    setScreen({ name: "admin" });
  };
  if (
    (screen.name === "admin" || screen.name === "admin-detail") &&
    auth.user.role !== "manager"
  ) {
    return (
      <GameTheme>
        <Alert severity="error">{t("errors.FORBIDDEN")}</Alert>
        <Button onClick={backToPlayers}>{t("game.stats.backPlayers")}</Button>
      </GameTheme>
    );
  }

  return (
    <GameTheme>
      {screen.name === "players" && (
        <PlayerSelect
          auth={auth}
          onProfile={(playerId) => {
            window.history.pushState(null, "", `/game/profile/${playerId}`);
            setScreen({ name: "profile", playerId });
          }}
          onManage={auth.user.role === "manager" ? toAdmin : undefined}
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
          isManager={auth.user.role === "manager"}
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
          playerId={screen.playerId}
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
          noteNaming={auth.user.note_naming}
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
        <ProfileScreen
          key={screen.playerId}
          playerId={screen.playerId}
          noteNaming={auth.user.note_naming}
          onBack={backToPlayers}
        />
      )}
      {screen.name === "admin" && (
        <AdminScreen
          csrf={auth.csrf_token}
          onBack={backToPlayers}
          onPlayerDetail={(playerId) => {
            window.history.pushState(null, "", `/game/admin/${playerId}`);
            setScreen({ name: "admin-detail", playerId });
          }}
        />
      )}
      {screen.name === "admin-detail" && (
        <ProfileScreen
          key={screen.playerId}
          playerId={screen.playerId}
          noteNaming={auth.user.note_naming}
          showAnalysis
          onBack={toAdmin}
        />
      )}
    </GameTheme>
  );
}
