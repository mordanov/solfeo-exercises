import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import type { Auth } from "../../api/auth";
import type { Exercise } from "../../api/exercises";
import * as api from "../../api/omr";
import { i18n } from "../../i18n";
import { Review } from "./Review";

vi.mock("../../api/omr");
vi.mock("./Score", () => ({
  Score: () => <div data-testid="rendered-score" />,
}));
const job: api.Omr = {
  job_id: "job",
  image_id: "image",
  status: "needs_review",
  attempts: 1,
  last_error: null,
};
const exercise: Exercise = {
  id: 1,
  title: "Exercise",
  description: "",
  category: null,
  position: 0,
  image: {
    id: "image",
    mime_type: "image/png",
    size_bytes: 100,
    duration_seconds: null,
  },
  audio: null,
  omr: job,
};
const auth: Auth = {
  csrf_token: "csrf",
  user: {
    id: 1,
    username: "manager",
    first_name: "Test",
    last_name: "Manager",
    role: "manager",
    is_active: true,
    is_emergency: false,
    must_change_password: false,
    ui_language: "en",
    note_naming: "letters",
  },
};
beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.fetchOmr).mockResolvedValue(job);
  vi.mocked(api.reviewOmr).mockResolvedValue({ ...job, status: "approved" });
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
        <Review exercise={exercise} auth={auth} close={vi.fn()} />
      </QueryClientProvider>
    </I18nextProvider>,
  );
}
it("shows only the score and reviews the exact version", async () => {
  mount();
  expect(await screen.findByTestId("rendered-score")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Approve" }));
  await waitFor(() =>
    expect(api.reviewOmr).toHaveBeenCalledWith(1, "job", "approve", "csrf"),
  );
  await userEvent.click(screen.getByRole("button", { name: "Reject" }));
  await waitFor(() =>
    expect(api.reviewOmr).toHaveBeenCalledWith(1, "job", "reject", "csrf"),
  );
});
it("prevents approving queued jobs and offers status refresh", async () => {
  vi.mocked(api.fetchOmr).mockResolvedValue({ ...job, status: "pending" });
  mount();
  await screen.findByText("Recognition queued");
  expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Run recognition" }),
  ).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Refresh status" }));
  await waitFor(() => expect(api.fetchOmr).toHaveBeenCalledTimes(2));
});
