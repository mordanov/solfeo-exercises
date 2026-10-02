import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { defaultAppearance } from "../../appearance";
import { describe, expect, it, vi } from "vitest";
import { Telegram } from "./Telegram";
import * as api from "../../api/telegram";
import * as exercises from "../../api/exercises";
import type { Auth } from "../../api/auth";
import "../../i18n";

vi.mock("../../api/telegram");
vi.mock("../../api/exercises");
const auth: Auth = {
  csrf_token: "csrf",
  user: {
    id: 1,
    username: "manager",
    first_name: "A",
    last_name: "B",
    role: "manager",
    is_active: true,
    is_emergency: false,
    must_change_password: false,
    ui_language: "en",
    note_naming: "letters",
    ...defaultAppearance,
  },
};

describe("Telegram imports", () => {
  it("shows a one-time linking code and applies an import once", async () => {
    vi.mocked(api.status).mockResolvedValue({
      linked: false,
      available: true,
      bot_username: "example_bot",
    });
    vi.mocked(api.listImports).mockResolvedValue({
      imports: [
        {
          id: 12,
          title: "Imported",
          description: "Caption",
          status: "ready",
          last_error: null,
          exercise_id: null,
          received_at: "2026-09-29T20:00:00Z",
        },
      ],
      total: 1,
    });
    vi.mocked(exercises.listExercises).mockResolvedValue({
      exercises: [],
      total: 0,
    });
    vi.mocked(api.createCode).mockResolvedValue({
      code: "one-time",
      expires_at: "2026-09-29T21:00:00Z",
    });
    vi.mocked(api.applyImport).mockResolvedValue(42);
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <Telegram auth={auth} />
      </QueryClientProvider>,
    );
    fireEvent.click(
      await screen.findByRole("button", { name: "Create linking code" }),
    );
    expect(await screen.findByText("/start one-time")).toBeInTheDocument();
    fireEvent.click(
      await screen.findByRole("button", { name: "Save exercise" }),
    );
    await waitFor(() =>
      expect(api.applyImport).toHaveBeenCalledWith("csrf", 12, {
        exercise_id: null,
        title: "Imported",
        description: "Caption",
      }),
    );
    expect(await screen.findByText("Exercise saved.")).toBeInTheDocument();
  });
});
