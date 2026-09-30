import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type User } from "../../api/auth";
import { fetchScore } from "../../api/omr";
import { ErrorMessage } from "../../components/AccountUi";
import { injectNoteNames } from "./notes";

export function Score({
  id,
  version,
  user,
  fallback,
}: {
  id: number;
  version: string;
  user: User;
  fallback?: React.ReactNode;
}) {
  const { t } = useTranslation();
  const [labels, setLabels] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const target = useRef<HTMLDivElement>(null);
  const query = useQuery({
    queryKey: ["omr", id, "score", version],
    queryFn: ({ signal }) => fetchScore(id, version, signal),
    retry: false,
  });
  useEffect(() => {
    const container = target.current;
    if (!container || !query.data) return;
    let cancelled = false;
    const host = document.createElement("div");
    container.replaceChildren(host);
    let clear: (() => void) | undefined;
    async function draw() {
      try {
        const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
        if (cancelled) return;
        const renderer = new OpenSheetMusicDisplay(host, {
          autoResize: false,
          backend: "svg",
          drawTitle: false,
        });
        clear = () => renderer.clear();
        const xml = labels
          ? injectNoteNames(
              query.data ?? "",
              user.note_naming,
              user.ui_language,
            )
          : query.data;
        await renderer.load(xml ?? "");
        if (cancelled) return;
        renderer.render();
        setError(null);
      } catch {
        if (!cancelled) setError(new ApiError("OMR_RENDER_FAILED"));
      }
    }
    void draw();
    return () => {
      cancelled = true;
      clear?.();
      host.remove();
    };
  }, [query.data, labels, user.note_naming, user.ui_language]);
  const failed = query.isError || error !== null;
  return (
    <section aria-label={t("omr.score")}>
      <label>
        <input
          type="checkbox"
          checked={labels}
          onChange={(event) => setLabels(event.target.checked)}
        />
        {t("omr.noteNames")}
      </label>
      {query.isPending && <p>{t("common.loading")}</p>}
      {failed && (
        <>
          <ErrorMessage error={query.error ?? error} />
          {fallback}
        </>
      )}
      <div ref={target} className="score-render" hidden={failed} />
    </section>
  );
}
