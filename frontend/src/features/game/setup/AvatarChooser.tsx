import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
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
} from "../api/hooks";
import AvatarImage from "./AvatarImage";
import { animals } from "./avatars";

export default function AvatarChooser({
  playerId,
  csrf,
  onClose,
}: {
  playerId: number;
  csrf: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [custom, setCustom] = useState(false);
  const [description, setDescription] = useState("");
  const [newJobId, setJobId] = useState<number | null>(null);
  const choose = useChooseAvatar(playerId);
  const generate = useGenerateAvatar();
  const accept = useAcceptAvatar(playerId);
  const discard = useDiscardAvatar();
  const quota = useAvatarQuota();
  const jobs = useAvatarJobs(playerId);
  const jobId = newJobId ?? jobs.data?.[0]?.id ?? null;
  const status = useAvatarStatus(jobId);
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
    <Dialog open onClose={busy ? undefined : onClose} fullWidth maxWidth="sm">
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
            onClick={() => setCustom(true)}
            disabled={busy}
            sx={{ flexDirection: "column", minWidth: 0 }}
          >
            <AvatarImage animalId="custom" selection size={72} />
            {t("game.avatar.generate")}
          </Button>
        </Box>
        {jobs.isError && <ErrorMessage error={jobs.error} />}
        {(custom || jobId !== null) && (
          <Box sx={{ mt: 2 }}>
            <Typography>{t("game.avatar.generationHint")}</Typography>
            {quota.isError && <ErrorMessage error={quota.error} />}
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
            {jobId &&
              (status.isPending || status.data?.status === "pending") && (
                <Typography role="status">
                  {t("game.avatar.generating")}
                </Typography>
              )}
            {status.isError && <ErrorMessage error={status.error} />}
            {status.data?.status === "failed" && (
              <Alert severity="error">
                {t(
                  status.data.error_code === "MODERATION_FLAGGED"
                    ? "game.avatar.flagged"
                    : "game.avatar.error",
                )}
              </Alert>
            )}
            {status.data?.status === "ready" && (
              <>
                <Typography>{t("game.avatar.ready")}</Typography>
                <AvatarImage
                  animalId="custom"
                  customAvatarId={jobId}
                  size={144}
                />
                <Button
                  disabled={busy}
                  onClick={() => {
                    if (jobId !== null)
                      accept.mutate({ csrf, jobId }, { onSuccess: onClose });
                  }}
                >
                  {t("game.avatar.use")}
                </Button>
              </>
            )}
            {jobId && status.data?.status !== "pending" && (
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
