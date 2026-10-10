import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ErrorMessage } from "../../../components/AccountUi";
import {
  useAcceptAvatar,
  useAvatarQuota,
  useAvatarStatus,
  useAvatarJobs,
  useChooseAvatar,
  useDiscardAvatar,
  useGenerateAvatar,
  useSavedAvatars,
} from "../api/hooks";
import AvatarImage from "./AvatarImage";
import { animals } from "./avatars";

export default function AvatarChooser({
  playerId,
  csrf,
  onClose,
  isManager = false,
}: {
  playerId: number;
  csrf: string;
  onClose: () => void;
  isManager?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const [custom, setCustom] = useState(false);
  const [description, setDescription] = useState("");
  const [newJobId, setJobId] = useState<number | null | undefined>();
  const [savedOffset, setSavedOffset] = useState(0);
  const [previewLevel, setPreviewLevel] = useState(1);
  const choose = useChooseAvatar(playerId);
  const generate = useGenerateAvatar();
  const accept = useAcceptAvatar(playerId);
  const discard = useDiscardAvatar();
  const quota = useAvatarQuota();
  const jobs = useAvatarJobs(playerId);
  const saved = useSavedAvatars(playerId, savedOffset);
  const jobId =
    newJobId === undefined ? (jobs.data?.[0]?.id ?? null) : newJobId;
  const status = useAvatarStatus(jobId);
  const cache = useQueryClient();
  const customPanel = useRef<HTMLDivElement>(null);
  const revealCustomPanel = useCallback(() => {
    if (custom || jobId !== null)
      customPanel.current?.scrollIntoView?.({ block: "start" });
  }, [custom, jobId]);
  useEffect(revealCustomPanel, [revealCustomPanel, status.isSuccess]);
  const refetchSaved = saved.refetch;
  useEffect(() => {
    if (status.data?.status === "ready") {
      void refetchSaved();
      if (status.data.review_status !== undefined) {
        void cache.invalidateQueries({
          queryKey: ["game", "player", playerId],
        });
        void cache.invalidateQueries({ queryKey: ["game", "players"] });
      }
    }
  }, [
    status.data?.status,
    status.data?.review_status,
    refetchSaved,
    cache,
    playerId,
  ]);
  useEffect(() => {
    if (saved.data && savedOffset > 0 && savedOffset >= saved.data.total)
      setSavedOffset(0);
  }, [saved.data, savedOffset]);
  const number = new Intl.NumberFormat(i18n.resolvedLanguage ?? "en");
  const busy =
    choose.isPending ||
    generate.isPending ||
    accept.isPending ||
    discard.isPending;
  const exhausted =
    quota.data?.limit !== null &&
    quota.data?.limit !== undefined &&
    quota.data.used >= quota.data.limit;
  return (
    <Dialog
      open
      onClose={busy ? undefined : onClose}
      fullWidth
      maxWidth="sm"
      slotProps={{ transition: { onEntered: revealCustomPanel } }}
    >
      <DialogTitle>{t("game.avatar.choose")}</DialogTitle>
      <DialogContent>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))",
            gap: 1,
          }}
        >
          {animals.map((animal) => (
            <Button
              key={animal}
              aria-label={t(`game.avatar.animal.${animal}`)}
              disabled={busy}
              onClick={() =>
                choose.mutate({ csrf, animal }, { onSuccess: onClose })
              }
              sx={{ flexDirection: "column", minWidth: 0, px: 1 }}
            >
              <AvatarImage animalId={animal} selection size={72} />
              {t(`game.avatar.animal.${animal}`)}
            </Button>
          ))}
          <Button
            aria-label={t("game.avatar.generate")}
            onClick={() => {
              setCustom(true);
              setJobId(null);
            }}
            disabled={busy}
            sx={{ flexDirection: "column", minWidth: 0 }}
          >
            <AvatarImage animalId="custom" selection size={72} />
            {t("game.avatar.generate")}
          </Button>
        </Box>
        {jobs.isError && <ErrorMessage error={jobs.error} />}
        {saved.isError && (
          <>
            <ErrorMessage error={saved.error} />
            <Button onClick={() => void saved.refetch()}>
              {t("common.retry")}
            </Button>
          </>
        )}
        {saved.data && saved.data.total > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6">{t("game.avatar.savedTitle")}</Typography>
            <Typography>{t("game.avatar.sharedHint")}</Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))",
                gap: 1,
              }}
            >
              {saved.data.jobs.map((job) => (
                <Button
                  key={job.id}
                  aria-label={t("game.avatar.savedChoice", {
                    number: number.format(job.id),
                  })}
                  disabled={busy}
                  onClick={() => {
                    setJobId(job.id);
                    setCustom(true);
                    setPreviewLevel(1);
                  }}
                >
                  <AvatarImage
                    animalId="custom"
                    customAvatarId={job.id}
                    portrait
                    reviewStatus={isManager ? undefined : job.review_status}
                    size={72}
                  />
                </Button>
              ))}
            </Box>
            {saved.data.total > 12 && (
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  disabled={busy || saved.isFetching || savedOffset === 0}
                  onClick={() =>
                    setSavedOffset((value) => Math.max(0, value - 12))
                  }
                >
                  {t("common.previous")}
                </Button>
                <Button
                  disabled={
                    busy ||
                    saved.isFetching ||
                    savedOffset + 12 >= saved.data.total
                  }
                  onClick={() => setSavedOffset((value) => value + 12)}
                >
                  {t("common.next")}
                </Button>
              </Box>
            )}
          </Box>
        )}
        {(custom || jobId !== null) && (
          <Box ref={customPanel} sx={{ mt: 2 }}>
            <Typography>{t("game.avatar.generationHint")}</Typography>
            {quota.isError && <ErrorMessage error={quota.error} />}
            {quota.data?.generation_available === false && (
              <Alert severity="info">{t("game.avatar.notConfigured")}</Alert>
            )}
            {quota.data?.limit != null && (
              <Typography>
                {t("game.avatar.quota", {
                  remaining: quota.data.limit - quota.data.used,
                })}
              </Typography>
            )}
            {exhausted && (
              <Alert severity="warning">
                {t("game.avatar.quotaExhausted")}
              </Alert>
            )}
            {!jobId && (
              <>
                <TextField
                  fullWidth
                  label={t("game.avatar.describe")}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  slotProps={{ htmlInput: { maxLength: 1000 } }}
                  sx={{ my: 2 }}
                />
                <Button
                  disabled={
                    busy ||
                    quota.isPending ||
                    quota.isError ||
                    jobs.isPending ||
                    jobs.isError ||
                    exhausted ||
                    quota.data?.generation_available !== true ||
                    !description.trim()
                  }
                  onClick={() =>
                    generate.mutate(
                      {
                        csrf,
                        player_id: playerId,
                        description: description.trim(),
                      },
                      {
                        onSuccess: (data) => {
                          setJobId(data.job_id);
                          void quota.refetch();
                        },
                      },
                    )
                  }
                >
                  {t("game.avatar.generate")}
                </Button>
              </>
            )}
            {jobId && status.isPending && (
              <Typography role="status">{t("common.loading")}</Typography>
            )}
            {status.data?.status === "pending" && (
              <Box role="status" aria-live="polite" sx={{ my: 2 }}>
                <Typography>
                  {t(`game.avatar.phase.${status.data.phase}`)}
                </Typography>
                <Typography>
                  {t("game.avatar.progress", {
                    count: number.format(status.data.completed_images),
                    total: number.format(status.data.total_images),
                  })}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={
                    (status.data.completed_images / status.data.total_images) *
                    100
                  }
                  aria-label={t("game.avatar.progressLabel")}
                  sx={{ my: 1 }}
                />
                <Typography>
                  {status.data.estimated_seconds_remaining !== null
                    ? t("game.avatar.eta", {
                        seconds: number.format(
                          status.data.estimated_seconds_remaining,
                        ),
                      })
                    : t("game.avatar.etaUnknown")}
                </Typography>
                {status.data.phase === "generating" && (
                  <Typography>{t("game.avatar.sheetHint")}</Typography>
                )}
              </Box>
            )}
            {status.isError && (
              <>
                <ErrorMessage error={status.error} />
                <Button onClick={() => void status.refetch()}>
                  {t("common.retry")}
                </Button>
              </>
            )}
            {status.data?.status === "failed" && (
              <Alert severity="error">
                {t(`errors.${status.data.error_code}`, {
                  defaultValue: t("game.avatar.error"),
                })}
              </Alert>
            )}
            {status.data?.status === "ready" &&
              status.data.review_status === "pending" && (
                <Alert severity="info">{t("game.avatar.awaitingReview")}</Alert>
              )}
            {status.data?.status === "ready" &&
              status.data.review_status === "rejected" && (
                <Alert severity="warning">
                  {t("game.avatar.reviewRejected")}
                </Alert>
              )}
            {status.data?.status === "ready" &&
              (isManager ||
                status.data.review_status === undefined ||
                status.data.review_status === "approved") && (
                <>
                  <Typography>{t("game.avatar.ready")}</Typography>
                  <Typography>
                    {t("game.avatar.progress", {
                      count: number.format(status.data.completed_images),
                      total: number.format(status.data.total_images),
                    })}
                  </Typography>
                  {status.data.asset_version === 1 && (
                    <Alert severity="info">{t("game.avatar.legacy")}</Alert>
                  )}
                  <TextField
                    select
                    label={t("game.avatar.previewLevel")}
                    value={previewLevel}
                    onChange={(event) =>
                      setPreviewLevel(Number(event.target.value))
                    }
                    slotProps={{ select: { native: true } }}
                    fullWidth
                    sx={{ my: 1 }}
                  >
                    {Array.from({ length: 10 }, (_, index) => (
                      <option key={index} value={index + 1}>
                        {t("game.profile.level", { level: index + 1 })}
                      </option>
                    ))}
                  </TextField>
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                      gap: 1,
                    }}
                  >
                    {(["neutral", "happy", "sad"] as const).map((mood) => (
                      <Box key={mood} sx={{ textAlign: "center" }}>
                        <AvatarImage
                          animalId="custom"
                          customAvatarId={jobId}
                          stage={previewLevel}
                          mood={mood}
                          size={144}
                        />
                        <Typography>{t(`game.avatar.mood.${mood}`)}</Typography>
                      </Box>
                    ))}
                  </Box>
                  <Button
                    disabled={
                      busy ||
                      status.data.review_status === "pending" ||
                      status.data.review_status === "rejected"
                    }
                    onClick={() => {
                      if (jobId !== null)
                        accept.mutate({ csrf, jobId }, { onSuccess: onClose });
                    }}
                  >
                    {t("game.avatar.use")}
                  </Button>
                </>
              )}
            {jobId &&
              status.data?.can_discard &&
              status.data.status !== "pending" && (
                <Button
                  disabled={busy}
                  onClick={() =>
                    discard.mutate(
                      { csrf, jobId },
                      {
                        onSuccess: async () => {
                          await jobs.refetch();
                          setJobId(null);
                        },
                      },
                    )
                  }
                >
                  {t("game.avatar.discard")}
                </Button>
              )}
          </Box>
        )}
        {[choose, generate, accept, discard].map((mutation, index) =>
          mutation.isError ? (
            <ErrorMessage key={index} error={mutation.error} />
          ) : null,
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>
          {t("common.close")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
