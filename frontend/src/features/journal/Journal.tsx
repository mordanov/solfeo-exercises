import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  dateBoundary,
  journalOptions,
  listJournal,
  type JournalEntry,
  type JournalFilters,
} from "../../api/journal";
import { ErrorMessage } from "../../components/AccountUi";
import { Button, Field, Form, Input, Panel, Select } from "../../components/Ui";
import { ReadOnlyGrid } from "../../components/ReadOnlyGrid";
import type { GridColDef } from "@mui/x-data-grid";

export function Journal() {
  const { t, i18n } = useTranslation();
  const [student, setStudent] = useState("");
  const [exercise, setExercise] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [filters, setFilters] = useState<JournalFilters>({});
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["journal", filters, offset],
    queryFn: ({ signal }) => listJournal(filters, offset, signal),
    retry: false,
  });
  const options = useQuery({
    queryKey: ["journal-options"],
    queryFn: ({ signal }) => journalOptions(signal),
    retry: false,
  });
  const date = (value: string) =>
    new Intl.DateTimeFormat(i18n.language, {
      dateStyle: "medium",
      timeStyle: "medium",
    }).format(new Date(value));
  const number = (value: number) =>
    new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1 }).format(
      value,
    );
  const columns: GridColDef<JournalEntry>[] = [
    {
      field: "student",
      headerName: t("journal.student"),
      minWidth: 180,
      flex: 1,
      renderCell: ({ row }) => (
        <span>
          {row.first_name} {row.last_name} ({row.username})
        </span>
      ),
    },
    {
      field: "exercise",
      headerName: t("journal.exercise"),
      minWidth: 180,
      flex: 1,
      renderCell: ({ row }) => (
        <div>
          {row.exercise_title}
          {row.exercise_deleted && <p>{t("journal.deleted")}</p>}
        </div>
      ),
    },
    {
      field: "started",
      headerName: t("journal.started"),
      minWidth: 190,
      renderCell: ({ row }) => date(row.started_at),
    },
    {
      field: "heartbeat",
      headerName: t("journal.heartbeat"),
      minWidth: 190,
      renderCell: ({ row }) => date(row.last_heartbeat_at),
    },
    {
      field: "ended",
      headerName: t("journal.ended"),
      minWidth: 190,
      renderCell: ({ row }) =>
        row.ended_at ? date(row.ended_at) : t("journal.noEnd"),
    },
    {
      field: "position",
      headerName: t("journal.position"),
      minWidth: 160,
      renderCell: ({ row }) => number(row.max_position_sec),
    },
    {
      field: "duration",
      headerName: t("journal.duration"),
      minWidth: 130,
      renderCell: ({ row }) => number(row.audio_duration_sec),
    },
    {
      field: "completed",
      headerName: t("journal.completed"),
      minWidth: 130,
      renderCell: ({ row }) => t(row.completed ? "journal.yes" : "journal.no"),
    },
  ];
  return (
    <Panel>
      <h2>{t("journal.title")}</h2>
      <p>
        {t("journal.timezone", {
          zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        })}
      </p>
      <Form
        onSubmit={(event) => {
          event.preventDefault();
          setOffset(0);
          setFilters({
            student_id: student,
            exercise_id: exercise,
            started_from: dateBoundary(from),
            started_to: dateBoundary(to, true),
          });
        }}
      >
        <Field>
          {t("journal.student")}
          <Select
            value={student}
            onChange={(event) => setStudent(event.target.value)}
          >
            <option value="">{t("journal.all")}</option>
            {options.data?.students.map((value) => (
              <option key={value.id} value={value.id}>
                {value.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field>
          {t("journal.exercise")}
          <Select
            value={exercise}
            onChange={(event) => setExercise(event.target.value)}
          >
            <option value="">{t("journal.all")}</option>
            {options.data?.exercises.map((value) => (
              <option key={value.id} value={value.id}>
                {value.label}
                {value.deleted ? ` (${t("journal.deleted")})` : ""}
              </option>
            ))}
          </Select>
        </Field>
        <Field>
          {t("journal.from")}
          <Input
            type="date"
            value={from}
            max={to || undefined}
            onChange={(event) => setFrom(event.target.value)}
          />
        </Field>
        <Field>
          {t("journal.to")}
          <Input
            type="date"
            value={to}
            min={from || undefined}
            onChange={(event) => setTo(event.target.value)}
          />
        </Field>
        <Button>{t("journal.filter")}</Button>
      </Form>
      <Button
        onClick={() => {
          void query.refetch();
          void options.refetch();
        }}
      >
        {t("journal.refresh")}
      </Button>
      {query.isPending && <p>{t("common.loading")}</p>}
      {query.isError && <ErrorMessage error={query.error} />}
      {options.isError && <ErrorMessage error={options.error} />}
      {query.data && (
        <>
          <p>{t("journal.total", { total: number(query.data.total) })}</p>
          <ReadOnlyGrid
            rows={query.data.sessions}
            columns={columns}
            label={t("journal.title")}
          />
          {query.data.total === 0 && <p>{t("journal.empty")}</p>}
          <Button
            disabled={offset === 0}
            onClick={() => setOffset((value) => Math.max(0, value - 50))}
          >
            {t("common.previous")}
          </Button>{" "}
          <Button
            disabled={offset + 50 >= query.data.total}
            onClick={() => setOffset((value) => value + 50)}
          >
            {t("common.next")}
          </Button>
        </>
      )}
    </Panel>
  );
}
