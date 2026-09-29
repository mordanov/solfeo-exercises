import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { fetchHealth, HealthError } from "../../api/health";
import { config } from "../../config";

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
    <section aria-labelledby="health-title">
      <h2 id="health-title">{t("health.title")}</h2>
      {health.isFetching || health.isPending ? (
        <p role="status">{t("health.pending")}</p>
      ) : health.isError ? (
        <p role="alert">{t(errorKey)}</p>
      ) : (
        <p role="status">{t("health.ok")}</p>
      )}
      <p>{t("health.scope")}</p>
      <button
        disabled={health.isFetching}
        onClick={() => void health.refetch()}
      >
        {t("health.retry")}
      </button>
    </section>
  );
}
