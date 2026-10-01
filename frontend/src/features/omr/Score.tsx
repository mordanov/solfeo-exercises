import { useCallback, useEffect, useRef, useState } from "react";
import type { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type User } from "../../api/auth";
import { fetchScore } from "../../api/omr";
import { ErrorMessage } from "../../components/AccountUi";
import { injectNoteNames } from "./notes";
import { Spoken } from "../spoken/Spoken";
import { Field, Input, Panel } from "../../components/Ui";
import Box from "@mui/material/Box";

export function Score({
  id,
  version,
  user,
  fallback,
  approved = false,
}: {
  id: number;
  version: string;
  user: User;
  fallback?: React.ReactNode;
  approved?: boolean;
}) {
  const { t } = useTranslation();
  const [labels, setLabels] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const target = useRef<HTMLDivElement>(null);
  const display = useRef<OpenSheetMusicDisplay | null>(null);
  const highlighted = useRef(-1);
  const cursorPosition = useRef(0);
  const highlight = useCallback((index: number) => {
    highlighted.current = index;
    const cursor = display.current?.cursor;
    if (!cursor) return;
    if (index < cursorPosition.current) {
      cursor.reset();
      cursorPosition.current = 0;
    }
    if (index < 0) {
      cursor.hide();
      return;
    }
    while (cursorPosition.current < index) {
      cursor.next();
      cursorPosition.current++;
    }
    cursor.show();
  }, []);
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
        if (renderer.cursor) renderer.cursor.SkipInvisibleNotes = false;
        display.current = renderer;
        cursorPosition.current = 0;
        highlight(highlighted.current);
        setError(null);
      } catch {
        if (!cancelled) setError(new ApiError("OMR_RENDER_FAILED"));
      }
    }
    void draw();
    return () => {
      cancelled = true;
      clear?.();
      display.current = null;
      host.remove();
    };
  }, [query.data, labels, user.note_naming, user.ui_language, highlight]);
  const failed = query.isError || error !== null;
  return (
    <Panel aria-label={t("omr.score")}>
      <Field>
        <Input
          type="checkbox"
          checked={labels}
          onChange={(event) => setLabels(event.target.checked)}
        />
        {t("omr.noteNames")}
      </Field>
      {query.isPending && <p>{t("common.loading")}</p>}
      {failed && (
        <>
          <ErrorMessage error={query.error ?? error} />
          {fallback}
        </>
      )}
      <Box
        ref={target}
        className="score-render"
        hidden={failed}
        sx={{
          overflow: "auto",
          bgcolor: "#fff",
          color: "#000",
          borderRadius: 2,
          my: 2,
        }}
      />
      {approved && query.data && !failed && (
        <Spoken
          key={`${id}-${version}-${user.ui_language}-${user.note_naming}`}
          id={id}
          version={version}
          user={user}
          highlight={highlight}
        />
      )}
    </Panel>
  );
}
