import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { createChapter, deleteChapter, listChapters } from "../../api/chapters";
import { ErrorMessage } from "../../components/AccountUi";
import { Button, Panel } from "../../components/Ui";
import Box from "@mui/material/Box";

export function ChapterManager({ csrf }: { csrf: string }) {
  const { t } = useTranslation();
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["chapters"],
    queryFn: ({ signal }) => listChapters(signal),
    retry: false,
  });
  const refresh = () => cache.invalidateQueries({ queryKey: ["chapters"] });
  const create = useMutation({
    mutationFn: () => createChapter(csrf),
    onSuccess: refresh,
  });
  const deletion = useMutation({
    mutationFn: (id: number) => deleteChapter(csrf, id),
    onSuccess: refresh,
  });

  return (
    <Panel>
      <h3>{t("chapters.title")}</h3>
      <Button
        type="button"
        disabled={create.isPending || deletion.isPending}
        onClick={() => create.mutate()}
      >
        {t("chapters.create")}
      </Button>
      {query.isPending && <p>{t("common.loading")}</p>}
      {query.isError && (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
      {create.isError && <ErrorMessage error={create.error} />}
      {deletion.isError && <ErrorMessage error={deletion.error} />}
      {query.data && (
        <Box component="ol" sx={{ pl: 3 }}>
          {query.data.map((chapter) => {
            const label = t("chapters.numbered", { number: chapter.number });
            return (
              <Box component="li" key={chapter.id}>
                {label}{" "}
                <Button
                  type="button"
                  disabled={
                    chapter.assigned_exercise_count > 0 ||
                    create.isPending ||
                    deletion.isPending
                  }
                  aria-label={t("chapters.deleteNamed", { chapter: label })}
                  onClick={() => deletion.mutate(chapter.id)}
                >
                  {t("chapters.delete")}
                </Button>
              </Box>
            );
          })}
        </Box>
      )}
    </Panel>
  );
}
