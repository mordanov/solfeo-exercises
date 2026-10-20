import { expect, it, vi } from "vitest";
import {
  createChapter,
  deleteChapter,
  listChapters,
  listListeningChapters,
} from "./chapters";

const chapters = [
  {
    id: 4,
    number: 2,
    active_exercise_count: 3,
    assigned_exercise_count: 4,
  },
];

it("lists manager chapters and student chapters from their endpoints", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ chapters })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ chapters })));
  vi.stubGlobal("fetch", fetch);

  await expect(listChapters()).resolves.toEqual(chapters);
  await expect(listListeningChapters()).resolves.toEqual(chapters);

  expect(fetch.mock.calls.map(([url]) => url)).toEqual([
    "/api/chapters",
    "/api/listening/chapters",
  ]);
});

it("creates and deletes chapters with CSRF protection", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(chapters[0])))
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" })));
  vi.stubGlobal("fetch", fetch);

  await expect(createChapter("csrf")).resolves.toEqual(chapters[0]);
  await expect(deleteChapter("csrf", chapters[0].id)).resolves.toBeUndefined();
  expect(fetch.mock.calls).toMatchObject([
    [
      "/api/chapters",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "csrf" }),
      }),
    ],
    [
      `/api/chapters/${chapters[0].id}`,
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({ "X-CSRF-Token": "csrf" }),
      }),
    ],
  ]);
});

it.each([
  null,
  {},
  { chapters: {} },
  { chapters: [{ ...chapters[0], id: 0 }] },
  { chapters: [{ ...chapters[0], number: 0 }] },
  { chapters: [{ ...chapters[0], active_exercise_count: -1 }] },
  { chapters: [{ ...chapters[0], assigned_exercise_count: 1.5 }] },
])("rejects malformed chapter responses: %j", async (response) => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(response))),
  );

  await expect(listChapters()).rejects.toMatchObject({
    code: "INVALID_RESPONSE",
  });
});
