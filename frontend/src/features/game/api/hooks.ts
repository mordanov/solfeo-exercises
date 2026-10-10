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
  trophies?: number[];
  achievements?: string[];
  avatar_review_status?: AvatarReviewStatus;
  avatar_review_job_id?: number | null;
}

export interface Note {
  name: string;
  octave: number;
}

export interface Task {
  index: number;
  clef: string;
  notes: Note[];
  server_time?: string;
  issued_at?: string;
  deadline_at?: string;
  time_limit_ms?: number;
}

export interface SubmitResponse {
  is_correct: boolean;
  timed_out?: boolean;
  correct_answers: Note[];
  score_delta: number;
  next_task: Task | null;
  result: RoundResult | null;
}

export interface RoundResult {
  score: number;
  score_bonus?: number;
  correct_count: number;
  is_win: boolean;
  xp_gained: number;
  level_up: boolean;
  new_trophy: number | null;
  practice_hint: { expected: string; given: string } | null;
  new_achievements?: string[];
  average_score?: number | null;
}

export interface StatsMatrix {
  [difficulty: string]: {
    [noteCount: string]: {
      rounds: number;
      total_correct: number;
      avg_score: number;
      total_score: number;
      wins: number;
      win_rate: number;
    };
  };
}

export interface ConfusionData {
  heatmap: Record<string, Record<string, number>>;
  top_confusions: Array<{ expected: string; given: string; count: number }>;
  round_top_confusions: Array<{
    expected: string;
    given: string;
    count: number;
  }>;
  missed_notes: Array<{ name: string; count: number }>;
}

export interface QuotaData {
  used: number;
  limit: number | null;
  resets_at: string | null;
  generation_available: boolean;
  generation_reason: string | null;
  image_count: number;
}

export type AvatarReviewStatus = "pending" | "approved" | "rejected" | null;

export interface AvatarJob {
  id: number;
  status: string;
  phase:
    | "queued"
    | "moderating"
    | "generating"
    | "splitting"
    | "review"
    | "complete"
    | "failed";
  asset_version: number;
  completed_images: number;
  total_images: number;
  estimated_seconds_remaining: number | null;
  base_path?: string | null;
  happy_path?: string | null;
  sad_path?: string | null;
  error_code?: string | null;
  review_status?: AvatarReviewStatus;
  can_discard: boolean;
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
    refetchInterval: (query) =>
      query.state.data?.some(
        (player) => player.avatar_review_status === "pending",
      )
        ? 2000
        : false,
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
      show_sound_hint: boolean;
      show_correct_answer: boolean;
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
        void cache.invalidateQueries({ queryKey: ["game", "stats"] });
        void cache.invalidateQueries({ queryKey: ["game", "confusion"] });
        void cache.invalidateQueries({ queryKey: ["game", "achievements"] });
      }
    },
  });
};

export const usePlayer = (playerId: number) =>
  useQuery({
    queryKey: ["game", "player", playerId],
    queryFn: () => gameFetch.get<Player>(`/players/${playerId}`),
    refetchInterval: (query) =>
      query.state.data?.avatar_review_status === "pending" ? 2000 : false,
  });

export const useAchievements = (playerId: number) =>
  useQuery({
    queryKey: ["game", "achievements", playerId],
    queryFn: () =>
      gameFetch.get<{
        earned: Array<{ code: string; awarded_at: string }>;
        catalog: Array<{ code: string }>;
      }>(`/players/${playerId}/achievements`),
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
      void cache.invalidateQueries({
        queryKey: ["game", "avatar-jobs", playerId],
      });
    },
  });
};

export const useAcceptAvatar = (playerId: number) => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({ csrf, jobId }: { csrf: string; jobId: number }) =>
      gameFetch.post(`/avatars/${jobId}/use`, csrf, { player_id: playerId }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["game", "player", playerId] });
      void cache.invalidateQueries({ queryKey: ["game", "players"] });
      void cache.invalidateQueries({
        queryKey: ["game", "avatar-jobs", playerId],
      });
    },
  });
};

export const useDiscardAvatar = () => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({ csrf, jobId }: { csrf: string; jobId: number }) =>
      gameFetch.delete(`/avatars/${jobId}`, csrf),
    onSuccess: () =>
      Promise.all([
        cache.invalidateQueries({ queryKey: ["game", "saved-avatars"] }),
        cache.invalidateQueries({ queryKey: ["game", "avatar-jobs"] }),
        cache.invalidateQueries({ queryKey: ["game", "players"] }),
        cache.invalidateQueries({ queryKey: ["game", "player"] }),
      ]),
  });
};

// ── Stats ──────────────────────────────────────────────────────────────────

export const usePlayerStats = (playerId: number, seasonId?: number) =>
  useQuery({
    queryKey: ["game", "stats", playerId, seasonId ?? "current"],
    queryFn: ({ signal }) =>
      gameFetch.get<StatsMatrix>(
        `/players/${playerId}/stats${seasonId ? `?season_id=${seasonId}` : ""}`,
        signal,
      ),
  });

export const usePlayerConfusion = (
  playerId: number,
  seasonId?: number,
  clef?: "treble" | "bass",
) =>
  useQuery({
    queryKey: [
      "game",
      "confusion",
      playerId,
      seasonId ?? "current",
      clef ?? "all",
    ],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams();
      if (seasonId) params.set("season_id", String(seasonId));
      if (clef) params.set("clef", clef);
      return gameFetch.get<ConfusionData>(
        `/players/${playerId}/confusion${params.size ? `?${params}` : ""}`,
        signal,
      );
    },
  });

// ── Avatars ────────────────────────────────────────────────────────────────

export const useAvatarQuota = () =>
  useQuery({
    queryKey: ["game", "avatar-quota"],
    queryFn: () => gameFetch.get<QuotaData>("/avatars/quota"),
  });

export const useGenerateAvatar = () => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({
      csrf,
      ...body
    }: {
      csrf: string;
      player_id: number;
      description: string;
    }) => gameFetch.post<{ job_id: number }>("/avatars/generate", csrf, body),
    onSuccess: (_, { player_id }) =>
      Promise.all([
        cache.invalidateQueries({ queryKey: ["game", "avatar-quota"] }),
        cache.invalidateQueries({
          queryKey: ["game", "avatar-jobs", player_id],
        }),
      ]),
  });
};

export const useAvatarStatus = (jobId: number | null) =>
  useQuery({
    queryKey: ["game", "avatar-status", jobId],
    queryFn: () => gameFetch.get<AvatarJob>(`/avatars/${jobId}/status`),
    enabled: jobId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" ||
      query.state.data?.review_status === "pending"
        ? 2000
        : false,
  });

export const useAvatarJobs = (playerId: number) =>
  useQuery({
    queryKey: ["game", "avatar-jobs", playerId],
    queryFn: () => gameFetch.get<AvatarJob[]>(`/avatars?player_id=${playerId}`),
    refetchInterval: (query) =>
      query.state.data?.some(
        (job) => job.status === "pending" || job.review_status === "pending",
      )
        ? 2000
        : false,
  });

export interface AvatarReviewJob extends AvatarJob {
  player_id: number;
  player_name: string;
}

export const useAvatarReviews = (offset: number) =>
  useQuery({
    queryKey: ["game", "avatar-reviews", offset],
    queryFn: () =>
      gameFetch.get<{ jobs: AvatarReviewJob[]; total: number }>(
        `/avatars/review?offset=${offset}`,
      ),
    refetchInterval: 5000,
  });

export const useReviewAvatar = () => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({
      csrf,
      jobId,
      decision,
    }: {
      csrf: string;
      jobId: number;
      decision: "approved" | "rejected";
    }) =>
      gameFetch.post<AvatarJob>(`/avatars/${jobId}/review`, csrf, { decision }),
    onSuccess: () =>
      Promise.all([
        cache.invalidateQueries({ queryKey: ["game", "avatar-reviews"] }),
        cache.invalidateQueries({ queryKey: ["game", "avatar-status"] }),
        cache.invalidateQueries({ queryKey: ["game", "avatar-jobs"] }),
        cache.invalidateQueries({ queryKey: ["game", "saved-avatars"] }),
        cache.invalidateQueries({ queryKey: ["game", "players"] }),
        cache.invalidateQueries({ queryKey: ["game", "player"] }),
      ]),
  });
};

export const useSavedAvatars = (playerId: number, offset: number) =>
  useQuery({
    queryKey: ["game", "saved-avatars", playerId, offset],
    queryFn: ({ signal }) =>
      gameFetch.get<{ jobs: AvatarJob[]; total: number }>(
        `/avatars/saved?player_id=${playerId}&offset=${offset}`,
        signal,
      ),
  });

// ── Seasons ────────────────────────────────────────────────────────────────

export const useSeasons = (playerId: number) =>
  useQuery({
    queryKey: ["game", "seasons", playerId],
    queryFn: ({ signal }) =>
      gameFetch.get<Season[]>(`/players/${playerId}/seasons`, signal),
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
      gameFetch.post<Season>(`/players/${playerId}/seasons/reset`, csrf, {
        confirmation,
      }),
    onSuccess: (_, { playerId }) =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["game", "seasons", playerId] }),
        qc.invalidateQueries({ queryKey: ["game", "stats", playerId] }),
        qc.invalidateQueries({ queryKey: ["game", "confusion", playerId] }),
      ]),
  });
};

export const useResetAllSeasons = () => {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({
      csrf,
      confirmation,
    }: {
      csrf: string;
      confirmation: string;
    }) =>
      gameFetch.post<Season[]>("/seasons/reset-all", csrf, { confirmation }),
    onSuccess: () =>
      Promise.all([
        cache.invalidateQueries({ queryKey: ["game", "seasons"] }),
        cache.invalidateQueries({ queryKey: ["game", "stats"] }),
        cache.invalidateQueries({ queryKey: ["game", "confusion"] }),
      ]),
  });
};
