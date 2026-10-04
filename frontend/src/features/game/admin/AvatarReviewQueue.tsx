import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ErrorMessage } from "../../../components/AccountUi";
import {
  useAvatarReviews,
  useReviewAvatar,
  type AvatarReviewJob,
} from "../api/hooks";
import AvatarImage from "../setup/AvatarImage";

export default function AvatarReviewQueue({ csrf }: { csrf: string }) {
  const { t } = useTranslation();
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<AvatarReviewJob | null>(null);
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(
    null,
  );
  const query = useAvatarReviews(offset);
  const review = useReviewAvatar();
  const decide = (value: "approved" | "rejected") => {
    if (!selected || review.isPending) return;
    review.mutate(
      { csrf, jobId: selected.id, decision: value },
      {
        onSuccess: () => {
          setDecision(value);
          setSelected(null);
          if (query.data?.jobs.length === 1 && offset > 0) setOffset(0);
        },
      },
    );
  };
  return (
    <Box
      component="section"
      aria-label={t("game.avatar.review.title")}
      sx={{ my: 3 }}
    >
      <Typography variant="h5">{t("game.avatar.review.title")}</Typography>
      {decision && (
        <Alert severity="success" role="status">
          {t(`game.avatar.review.${decision}`)}
        </Alert>
      )}
      {query.isPending && (
        <Typography role="status">{t("common.loading")}</Typography>
      )}
      {query.isError && (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
      {query.data?.total === 0 && (
        <Typography>{t("game.avatar.review.empty")}</Typography>
      )}
      {query.data?.jobs.map((job) => (
        <Button
          key={job.id}
          onClick={() => {
            setSelected(job);
            review.reset();
          }}
        >
          {job.player_name}
        </Button>
      ))}
      {query.data && query.data.total > 12 && (
        <Box>
          <Button
            disabled={offset === 0 || query.isFetching}
            onClick={() => setOffset(Math.max(0, offset - 12))}
          >
            {t("common.previous")}
          </Button>
          <Button
            disabled={offset + 12 >= query.data.total || query.isFetching}
            onClick={() => setOffset(offset + 12)}
          >
            {t("common.next")}
          </Button>
        </Box>
      )}
      <Dialog
        open={selected !== null}
        onClose={review.isPending ? undefined : () => setSelected(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{selected?.player_name}</DialogTitle>
        <DialogContent>
          {selected && (
            <Button
              component="a"
              href={`/api/game/avatars/${selected.id}/review-sheet`}
              target="_blank"
              rel="noopener"
            >
              {t("game.avatar.review.sheet")}
            </Button>
          )}
          {selected &&
            Array.from({ length: 10 }, (_, index) => (
              <Box key={index} sx={{ mb: 2 }}>
                <Typography>
                  {t("game.profile.level", { level: index + 1 })}
                </Typography>
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
                        customAvatarId={selected.id}
                        stage={index + 1}
                        mood={mood}
                        size={144}
                      />
                      <Typography>{t(`game.avatar.mood.${mood}`)}</Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            ))}
          {review.isError && <ErrorMessage error={review.error} />}
        </DialogContent>
        <DialogActions sx={{ flexWrap: "wrap" }}>
          <Button disabled={review.isPending} onClick={() => setSelected(null)}>
            {t("common.close")}
          </Button>
          <Button
            disabled={review.isPending}
            color="error"
            onClick={() => decide("rejected")}
          >
            {t("game.avatar.review.reject")}
          </Button>
          <Button
            disabled={review.isPending}
            variant="contained"
            onClick={() => decide("approved")}
          >
            {t("game.avatar.review.approve")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
