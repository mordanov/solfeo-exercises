import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { gameFetch } from "./client";
import type { User } from "../../../api/auth";

// ── Types ──────────────────────────────────────────────────────────────────

export interface Player {
  id: number;
  name: string;
  avatar_animal: string | null;
  custom_avatar_id: number | null;
  xp: number;
  avatar_level: number;
}

export interface Note {
  name: string;
  octave: number;
}

export interface Task {
  index: number;
  clef: string;
  notes: Note[];
}

export interface SubmitResponse {
  is_correct: boolean;
  correct_answers: Note[];
  score_delta: number;
  next_task: Task | null;
  result: RoundResult | null;
}

export interface RoundResult {
  score: number;
  correct_count: number;
  is_win: boolean;
  xp_gained: number;
  level_up: boolean;
  new_trophy: number | null;
  practice_hint: string;
}

export interface StatsMatrix {
  [difficulty: string]: {
    [noteCount: string]: {
      rounds: number;
      total_correct: number;
      avg_score: number;
    };
  };
}

export interface ConfusionData {
  heatmap: Record<string, Record<string, number>>;
  top_confusions: Array<{ expected: string; given: string; count: number }>;
}

export interface QuotaData {
  used: number;
  limit: number | null;
  resets_at: string | null;
}

export interface AvatarJob {
  id: number;
  status: string;
  base_path?: string;
  happy_path?: string;
  sad_path?: string;
  error_code?: string;
}

export interface Season {
  id: number;
  player_id: number;
  number: number;
  started_at: string;
  ended_at: string | null;
}

// ── Players ────────────────────────────────────────────────────────────────

export type EligibleAccount = Pick<
  User,
  "id" | "username" | "first_name" | "last_name"
>;
export const useEligibleAccounts = (offset: number) =>
  useQuery({
    queryKey: ["game", "eligible-accounts", offset],
    queryFn: ({ signal }) =>
      gameFetch.get<{ users: EligibleAccount[]; total: number }>(
        `/players/accounts?offset=${offset}`,
        signal,
      ),
  });

export const usePlayers = () =>
  useQuery({
    queryKey: ["game", "players"],
    queryFn: () => gameFetch.get<Player[]>("/players"),
  });

export const useCreatePlayer = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      csrf,
      ...body
    }: {
      csrf: string;
      name: string;
      avatar_animal?: string;
      account_id?: number;
    }) => gameFetch.post<Player>("/players", csrf, body),
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["game", "players"] }),
        qc.invalidateQueries({ queryKey: ["game", "eligible-accounts"] }),
      ]),
    onError: () => {
      void qc.invalidateQueries({ queryKey: ["game", "eligible-accounts"] });
    },
  });
};

// ── Rounds ─────────────────────────────────────────────────────────────────

export const useStartRound = () =>
  useMutation({
    mutationFn: ({
      csrf,
      ...body
    }: {
      csrf: string;
      player_id: number;
      difficulty: string;
      note_count: number;
    }) =>
      gameFetch.post<{ round_id: number; task: Task }>("/rounds", csrf, body),
  });

export const useSubmitTask = (roundId: number) => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({
      csrf,
      ...body
    }: {
      csrf: string;
      task_index: number;
      answers?: Note[] | null;
      timed_out?: boolean;
    }) =>
      gameFetch.post<SubmitResponse>(`/rounds/${roundId}/submit`, csrf, body),
    onSuccess: (data) => {
      if (data.result) {
        void cache.invalidateQueries({ queryKey: ["game", "players"] });
        void cache.invalidateQueries({ queryKey: ["game", "player"] });
      }
    },
  });
};

export const usePlayer = (playerId: number) =>
  useQuery({
    queryKey: ["game", "player", playerId],
    queryFn: () => gameFetch.get<Player>(`/players/${playerId}`),
  });

export const useChooseAvatar = (playerId: number) => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({ csrf, animal }: { csrf: string; animal: string }) =>
      gameFetch.post<Player>(`/players/${playerId}/avatar`, csrf, {
        avatar_animal: animal,
      }),
    onSuccess: (player) => {
      cache.setQueryData(["game", "player", playerId], player);
      void cache.invalidateQueries({ queryKey: ["game", "players"] });
    },
  });
};

export const useAcceptAvatar = (playerId: number) => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({ csrf, jobId }: { csrf: string; jobId: number }) =>
      gameFetch.post(`/avatars/${jobId}/use`, csrf),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["game", "player", playerId] });
      void cache.invalidateQueries({ queryKey: ["game", "players"] });
    },
  });
};

export const useDiscardAvatar = () =>
  useMutation({
    mutationFn: ({ csrf, jobId }: { csrf: string; jobId: number }) =>
      gameFetch.delete(`/avatars/${jobId}`, csrf),
  });

// ── Stats ──────────────────────────────────────────────────────────────────

export const usePlayerStats = (playerId: number) =>
  useQuery({
    queryKey: ["game", "stats", playerId],
    queryFn: () => gameFetch.get<StatsMatrix>(`/players/${playerId}/stats`),
  });

export const usePlayerConfusion = (playerId: number) =>
  useQuery({
    queryKey: ["game", "confusion", playerId],
    queryFn: () =>
      gameFetch.get<ConfusionData>(`/players/${playerId}/confusion`),
  });

// ── Avatars ────────────────────────────────────────────────────────────────

export const useAvatarQuota = () =>
  useQuery({
    queryKey: ["game", "avatar-quota"],
    queryFn: () => gameFetch.get<QuotaData>("/avatars/quota"),
  });

export const useGenerateAvatar = () =>
  useMutation({
    mutationFn: ({
      csrf,
      ...body
    }: {
      csrf: string;
      player_id: number;
      description: string;
    }) => gameFetch.post<{ job_id: number }>("/avatars/generate", csrf, body),
  });

export const useAvatarStatus = (jobId: number | null) =>
  useQuery({
    queryKey: ["game", "avatar-status", jobId],
    queryFn: () => gameFetch.get<AvatarJob>(`/avatars/${jobId}/status`),
    enabled: jobId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" ? 2000 : false,
  });

export const useAvatarJobs = (playerId: number) =>
  useQuery({
    queryKey: ["game", "avatar-jobs", playerId],
    queryFn: () => gameFetch.get<AvatarJob[]>(`/avatars?player_id=${playerId}`),
  });

// ── Seasons ────────────────────────────────────────────────────────────────

export const useSeasons = (playerId: number) =>
  useQuery({
    queryKey: ["game", "seasons", playerId],
    queryFn: () => gameFetch.get<Season[]>(`/players/${playerId}/seasons`),
  });

export const useResetSeason = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      csrf,
      playerId,
      confirmation,
    }: {
      csrf: string;
      playerId: number;
      confirmation: string;
    }) =>
      gameFetch.post(`/players/${playerId}/seasons/reset`, csrf, {
        confirmation,
      }),
    onSuccess: (_, { playerId }) => {
      void qc.invalidateQueries({ queryKey: ["game", "seasons", playerId] });
      void qc.invalidateQueries({ queryKey: ["game", "stats", playerId] });
    },
  });
};
