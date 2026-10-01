import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { fetchHealth, HealthError } from "../../api/health";
import { config } from "../../config";
import { Button, Panel } from "../../components/Ui";
import Alert from "@mui/material/Alert";

export function HealthStatus() {
  const { t } = useTranslation();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal, config.healthTimeoutMs),
    retry: false,
    refetchOnWindowFocus: false,
    networkMode: "always",
  });
  const errorKey =
    health.error instanceof HealthError
      ? `errors.${health.error.code}`
      : "errors.UNKNOWN";

  return (
    <Panel aria-labelledby="health-title">
      <h2 id="health-title">{t("health.title")}</h2>
      {health.isFetching || health.isPending ? (
        <Alert severity="info" role="status">
          {t("health.pending")}
        </Alert>
      ) : health.isError ? (
        <Alert severity="error">{t(errorKey)}</Alert>
      ) : (
        <Alert severity="success" role="status">
          {t("health.ok")}
        </Alert>
      )}
      <p>{t("health.scope")}</p>
      <Button
        disabled={health.isFetching}
        onClick={() => void health.refetch()}
      >
        {t("health.retry")}
      </Button>
    </Panel>
  );
}
