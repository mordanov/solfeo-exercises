import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  dateBoundary,
  journalOptions,
  listJournal,
  type JournalFilters,
} from "../../api/journal";
import { ErrorMessage } from "../../components/AccountUi";

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
  return (
    <section>
      <h2>{t("journal.title")}</h2>
      <p>
        {t("journal.timezone", {
          zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        })}
      </p>
      <form
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
        <label>
          {t("journal.student")}
          <select
            value={student}
            onChange={(event) => setStudent(event.target.value)}
          >
            <option value="">{t("journal.all")}</option>
            {options.data?.students.map((value) => (
              <option key={value.id} value={value.id}>
                {value.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("journal.exercise")}
          <select
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
          </select>
        </label>
        <label>
          {t("journal.from")}
          <input
            type="date"
            value={from}
            max={to || undefined}
            onChange={(event) => setFrom(event.target.value)}
          />
        </label>
        <label>
          {t("journal.to")}
          <input
            type="date"
            value={to}
            min={from || undefined}
            onChange={(event) => setTo(event.target.value)}
          />
        </label>
        <button>{t("journal.filter")}</button>
      </form>
      <button
        onClick={() => {
          void query.refetch();
          void options.refetch();
        }}
      >
        {t("journal.refresh")}
      </button>
      {query.isPending && <p>{t("common.loading")}</p>}
      {query.isError && <ErrorMessage error={query.error} />}
      {options.isError && <ErrorMessage error={options.error} />}
      {query.data && (
        <>
          <p>{t("journal.total", { total: number(query.data.total) })}</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {[
                    "student",
                    "exercise",
                    "started",
                    "heartbeat",
                    "ended",
                    "position",
                    "duration",
                    "completed",
                  ].map((key) => (
                    <th key={key}>{t(`journal.${key}`)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {query.data.sessions.map((row) => (
                  <tr key={row.id}>
                    <td>
                      {row.first_name} {row.last_name} ({row.username})
                    </td>
                    <td>
                      {row.exercise_title}
                      {row.exercise_deleted && <p>{t("journal.deleted")}</p>}
                    </td>
                    <td>{date(row.started_at)}</td>
                    <td>{date(row.last_heartbeat_at)}</td>
                    <td>
                      {row.ended_at ? date(row.ended_at) : t("journal.noEnd")}
                    </td>
                    <td>{number(row.max_position_sec)}</td>
                    <td>{number(row.audio_duration_sec)}</td>
                    <td>{t(row.completed ? "journal.yes" : "journal.no")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {query.data.total === 0 && <p>{t("journal.empty")}</p>}
          <button
            disabled={offset === 0}
            onClick={() => setOffset((value) => Math.max(0, value - 50))}
          >
            {t("common.previous")}
          </button>{" "}
          <button
            disabled={offset + 50 >= query.data.total}
            onClick={() => setOffset((value) => value + 50)}
          >
            {t("common.next")}
          </button>
        </>
      )}
    </section>
  );
}
