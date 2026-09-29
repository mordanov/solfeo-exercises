import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../i18n";
import type { Auth } from "../../api/auth";
import * as api from "../../api/exercises";
import { Exercises } from "./Exercises";

vi.mock("../../api/exercises");
const exercise = {
  id: 1,
  title: "Scale",
  description: "Practice",
  category: null,
  position: 0,
  image: {
    id: "image-id",
    mime_type: "image/png",
    size_bytes: 20,
    duration_seconds: null,
  },
  audio: {
    id: "audio-id",
    mime_type: "audio/mp4",
    size_bytes: 200,
    duration_seconds: 2,
  },
};
const auth: Auth = {
  csrf_token: "csrf",
  user: {
    id: 1,
    username: "manager",
    first_name: "First",
    last_name: "Last",
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
  vi.mocked(api.listExercises).mockResolvedValue({
    exercises: [exercise],
    total: 1,
  });
});
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
        <Exercises auth={auth} />
      </QueryClientProvider>
    </I18nextProvider>,
  );
}
it("shows protected media without autoplay", async () => {
  mount();
  expect(await screen.findByText("Scale")).toBeInTheDocument();
  const image = screen.getByRole("img");
  expect(image).toHaveAttribute("src", "/api/exercises/1/files/image");
  const audio = screen.getByLabelText("Audio: Scale");
  expect(audio).toHaveAttribute("src", "/api/exercises/1/files/audio");
  expect(audio).not.toHaveAttribute("autoplay");
});
it("requires a file and submits multipart data with progress", async () => {
  vi.mocked(api.saveExercise).mockImplementation(
    async (_csrf, _id, _data, progress) => {
      progress(100);
      return exercise;
    },
  );
  mount();
  await userEvent.click(
    await screen.findByRole("button", { name: "Create exercise" }),
  );
  await userEvent.type(screen.getByLabelText("Title"), "New exercise");
  await userEvent.click(screen.getByRole("button", { name: "Save exercise" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("image or audio");
  expect(api.saveExercise).not.toHaveBeenCalled();
  await userEvent.upload(
    screen.getByLabelText("Image"),
    new File(["png"], "notes.png", { type: "image/png" }),
  );
  await userEvent.click(screen.getByRole("button", { name: "Save exercise" }));
  await waitFor(() => expect(api.saveExercise).toHaveBeenCalled());
  const [csrf, id, data] = vi.mocked(api.saveExercise).mock.calls[0];
  expect(csrf).toBe("csrf");
  expect(id).toBeNull();
  expect(data.get("title")).toBe("New exercise");
  expect(data.get("image")).toBeInstanceOf(File);
});
it("edits metadata without losing existing files", async () => {
  vi.mocked(api.saveExercise).mockResolvedValue(exercise);
  mount();
  await userEvent.click(
    await screen.findByRole("button", { name: "Edit Scale" }),
  );
  expect(screen.getByLabelText("Title")).toHaveValue("Scale");
  await userEvent.type(screen.getByLabelText("Category / level"), "Level 1");
  await userEvent.click(screen.getByRole("button", { name: "Save exercise" }));
  await waitFor(() => expect(api.saveExercise).toHaveBeenCalled());
  expect(vi.mocked(api.saveExercise).mock.calls[0][1]).toBe(1);
  expect(vi.mocked(api.saveExercise).mock.calls[0][2].get("category")).toBe(
    "Level 1",
  );
});
it("confirms deletion and refreshes only after success", async () => {
  vi.mocked(api.deleteExercise).mockResolvedValue();
  mount();
  await userEvent.click(
    await screen.findByRole("button", { name: "Delete Scale" }),
  );
  expect(api.deleteExercise).not.toHaveBeenCalled();
  await userEvent.click(
    screen.getByRole("button", { name: "Confirm deletion" }),
  );
  await waitFor(() =>
    expect(api.deleteExercise).toHaveBeenCalledWith("csrf", 1),
  );
});
it("reorders with accessible controls and drag-and-drop", async () => {
  vi.mocked(api.listExercises).mockResolvedValue({
    exercises: [exercise, { ...exercise, id: 2, title: "Second", position: 1 }],
    total: 2,
  });
  vi.mocked(api.reorderExercises).mockResolvedValue();
  mount();
  await userEvent.click(
    await screen.findByRole("button", { name: "Move Scale down" }),
  );
  await waitFor(() =>
    expect(api.reorderExercises).toHaveBeenCalledWith("csrf", [2, 1]),
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Move Scale down" }),
    ).toBeEnabled(),
  );
  fireEvent.dragStart(screen.getByRole("listitem", { name: "Scale" }), {
    dataTransfer: { setData: vi.fn(), effectAllowed: "" },
  });
  fireEvent.drop(screen.getByRole("listitem", { name: "Second" }), {
    dataTransfer: { getData: () => "1" },
  });
  await waitFor(() => expect(api.reorderExercises).toHaveBeenCalledTimes(2));
});
