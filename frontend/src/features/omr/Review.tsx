import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type Auth } from "../../api/auth";
import type { Exercise } from "../../api/exercises";
import { fetchOmr, rerunOmr, reviewOmr } from "../../api/omr";
import { ErrorMessage } from "../../components/AccountUi";
import { Score } from "./Score";
import { Button, Panel } from "../../components/Ui";
import Alert from "@mui/material/Alert";

export function Review({
  exercise,
  auth,
  close,
}: {
  exercise: Exercise;
  auth: Auth;
  close: () => void;
}) {
  const { t } = useTranslation();
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["omr", exercise.id, "status"],
    queryFn: ({ signal }) => fetchOmr(exercise.id, signal),
    retry: false,
  });
  const job = query.data;
  const mutation = useMutation({
    mutationFn: (action: "approve" | "reject" | "rerun") =>
      action === "rerun"
        ? rerunOmr(exercise.id, auth.csrf_token)
        : reviewOmr(exercise.id, job?.job_id ?? "", action, auth.csrf_token),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["omr", exercise.id] });
      await cache.invalidateQueries({ queryKey: ["exercises"] });
    },
  });
  const rendered =
    job &&
    (job.status === "needs_review" ||
      job.status === "approved" ||
      job.status === "rejected");
  return (
    <Panel aria-label={t("omr.review")}>
      <h4>{t("omr.review")}</h4>
      <p>{t("omr.reviewHint")}</p>
      <Button onClick={close}>{t("common.close")}</Button>
      <Button disabled={query.isFetching} onClick={() => void query.refetch()}>
        {t("omr.refresh")}
      </Button>
      {query.isPending && <p>{t("common.loading")}</p>}
      {query.isError && <ErrorMessage error={query.error} />}
      {job && (
        <Alert severity="info" role="status">
          {t(`omr.status.${job.status}`)}
        </Alert>
      )}
      {job?.last_error && <ErrorMessage error={new ApiError(job.last_error)} />}
      {rendered && job.job_id && (
        <Score
          id={exercise.id}
          version={job.job_id}
          user={auth.user}
          approved={job.status === "approved"}
        />
      )}
      <Button
        disabled={!rendered || mutation.isPending}
        onClick={() => mutation.mutate("approve")}
      >
        {t("omr.approve")}
      </Button>
      <Button
        disabled={!rendered || mutation.isPending}
        onClick={() => mutation.mutate("reject")}
      >
        {t("omr.reject")}
      </Button>
      <Button
        disabled={
          !job ||
          mutation.isPending ||
          job.status === "pending" ||
          job.status === "processing"
        }
        onClick={() => mutation.mutate("rerun")}
      >
        {t("omr.rerun")}
      </Button>
      {mutation.isError && <ErrorMessage error={mutation.error} />}
    </Panel>
  );
}
