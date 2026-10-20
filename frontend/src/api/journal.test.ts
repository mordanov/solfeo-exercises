import { expect, it, vi } from "vitest";
import { listJournal, journalOptions, parseJournal } from "./journal";

const entry = {
  id: 8,
  session_id: "session",
  user_id: 3,
  username: "student",
  first_name: "First",
  last_name: "Last",
  exercise_id: 7,
  exercise_title: "Scale",
  exercise_deleted: false,
  chapter_number: 2,
  started_at: "2026-10-20T10:00:00Z",
  last_heartbeat_at: "2026-10-20T10:00:05Z",
  ended_at: null,
  max_position_sec: 5,
  audio_duration_sec: 30,
  completed: false,
};

it("parses the chapter snapshot on journal entries", () => {
  expect(parseJournal(entry)).toMatchObject({
    exercise_id: 7,
    chapter_number: 2,
  });
  expect(() => parseJournal({ ...entry, chapter_number: 0 })).toThrow(
    "INVALID_RESPONSE",
  );
});

it("serializes the selected chapter in journal filters", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify({ sessions: [entry], total: 1 })),
    );
  vi.stubGlobal("fetch", fetch);

  await expect(listJournal({ chapter_number: "2" }, 10)).resolves.toMatchObject(
    { sessions: [entry], total: 1 },
  );
  expect(fetch.mock.calls[0][0]).toBe(
    "/api/journal?offset=10&limit=50&chapter_number=2",
  );
});

it("parses journal chapter filter options", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          students: [],
          exercises: [],
          chapters: [{ chapter_number: 2 }],
        }),
      ),
    ),
  );

  await expect(journalOptions()).resolves.toEqual({
    students: [],
    exercises: [],
    chapters: [{ chapter_number: 2 }],
  });
});

it("rejects invalid chapter options", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          students: [],
          exercises: [],
          chapters: [{ chapter_number: 1.5 }],
        }),
      ),
    ),
  );

  await expect(journalOptions()).rejects.toMatchObject({
    code: "INVALID_RESPONSE",
  });
});
