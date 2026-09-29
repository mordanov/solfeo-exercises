import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../../api/journal";
import { i18n } from "../../i18n";
import { Journal } from "./Journal";
vi.mock("../../api/journal");
const row = {
  id: 1,
  session_id: "session",
  user_id: 2,
  username: "student",
  first_name: "First",
  last_name: "Last",
  exercise_id: 3,
  exercise_title: "Deleted scale",
  exercise_deleted: true,
  started_at: "2026-09-29T10:00:00Z",
  last_heartbeat_at: "2026-09-29T10:00:05Z",
  ended_at: null,
  max_position_sec: 5,
  audio_duration_sec: 20,
  completed: false,
};
beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.listJournal).mockResolvedValue({ sessions: [row], total: 51 });
  vi.mocked(api.journalOptions).mockResolvedValue({
    students: [{ id: 2, label: "Student two", deleted: false }],
    exercises: [{ id: 3, label: "Scale", deleted: true }],
  });
});
function mount() {
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false, gcTime: 0 } },
          })
        }
      >
        <Journal />
      </QueryClientProvider>
    </I18nextProvider>,
  );
}
it("shows incomplete closed-tab rows and deleted exercise snapshots", async () => {
  mount();
  expect(await screen.findByText("Deleted scale")).toBeInTheDocument();
  expect(screen.getByText("No end event received")).toBeInTheDocument();
  expect(screen.getByText("No", { selector: "td" })).toBeInTheDocument();
});
it("filters on student and exercise and paginates", async () => {
  mount();
  await screen.findByText("Deleted scale");
  await userEvent.selectOptions(screen.getByLabelText("Student"), "2");
  await userEvent.selectOptions(screen.getByLabelText("Exercise"), "3");
  await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
  await waitFor(() =>
    expect(api.listJournal).toHaveBeenCalledWith(
      expect.objectContaining({ student_id: "2", exercise_id: "3" }),
      0,
      expect.any(AbortSignal),
    ),
  );
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() =>
    expect(api.listJournal).toHaveBeenCalledWith(
      expect.any(Object),
      50,
      expect.any(AbortSignal),
    ),
  );
});
