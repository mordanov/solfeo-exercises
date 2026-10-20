import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../api/auth";
import type { Chapter } from "../../api/chapters";
import * as api from "../../api/chapters";
import { i18n } from "../../i18n";
import { ChapterManager } from "./ChapterManager";

vi.mock("../../api/chapters");

let chapters: Chapter[];

function mount() {
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: {
              queries: { retry: false, gcTime: 0 },
              mutations: { retry: false },
            },
          })
        }
      >
        <ChapterManager csrf="csrf" />
      </QueryClientProvider>
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  chapters = [];
  vi.mocked(api.listChapters).mockImplementation(async () => chapters);
  vi.mocked(api.createChapter).mockImplementation(async () => {
    const nextNumber =
      Math.max(0, ...chapters.map((chapter) => chapter.number)) + 1;
    const chapter = {
      id: nextNumber,
      number: nextNumber,
      active_exercise_count: 0,
      assigned_exercise_count: 0,
    };
    chapters = [...chapters, chapter];
    return chapter;
  });
  vi.mocked(api.deleteChapter).mockImplementation(async (_csrf, id) => {
    chapters = chapters.filter((chapter) => chapter.id !== id);
  });
});

it("creates a chapter and displays its numbered label", async () => {
  mount();

  await userEvent.click(
    await screen.findByRole("button", { name: "Create chapter" }),
  );

  expect(api.createChapter).toHaveBeenCalledWith("csrf");
  expect(await screen.findByText("Chapter 1")).toBeInTheDocument();
});

it("translates the numbered label while keeping the chapter number stable", async () => {
  chapters = [
    {
      id: 7,
      number: 7,
      active_exercise_count: 0,
      assigned_exercise_count: 0,
    },
  ];
  mount();

  expect(await screen.findByText("Chapter 7")).toBeInTheDocument();
  await i18n.changeLanguage("ru");
  expect(await screen.findByText("Глава 7")).toBeInTheDocument();
  await i18n.changeLanguage("es");
  expect(await screen.findByText("Unidad 7")).toBeInTheDocument();
});

it("deletes an empty chapter", async () => {
  chapters = [
    {
      id: 4,
      number: 4,
      active_exercise_count: 0,
      assigned_exercise_count: 0,
    },
  ];
  mount();

  const deleteButton = await screen.findByRole("button", {
    name: "Delete Chapter 4",
  });
  expect(deleteButton).toBeEnabled();
  await userEvent.click(deleteButton);

  await waitFor(() =>
    expect(api.deleteChapter).toHaveBeenCalledWith("csrf", 4),
  );
  await waitFor(() => expect(screen.queryByText("Chapter 4")).toBeNull());
});

it("disables deletion when the chapter has assigned exercises", async () => {
  chapters = [
    {
      id: 4,
      number: 4,
      active_exercise_count: 0,
      assigned_exercise_count: 1,
    },
  ];
  mount();

  const deleteButton = await screen.findByRole("button", {
    name: "Delete Chapter 4",
  });
  expect(deleteButton).toBeDisabled();
  fireEvent.click(deleteButton);
  expect(api.deleteChapter).not.toHaveBeenCalled();
});

it("explains when a chapter cannot be deleted because it has assigned exercises", async () => {
  chapters = [
    {
      id: 4,
      number: 4,
      active_exercise_count: 0,
      assigned_exercise_count: 0,
    },
  ];
  vi.mocked(api.deleteChapter).mockRejectedValue(
    new ApiError("CHAPTER_NOT_EMPTY"),
  );
  mount();

  await userEvent.click(
    await screen.findByRole("button", { name: "Delete Chapter 4" }),
  );

  expect(
    await screen.findByText(
      "A chapter with assigned exercises cannot be deleted.",
    ),
  ).toBeInTheDocument();
});
