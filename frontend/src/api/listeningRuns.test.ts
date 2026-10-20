import { expect, it, vi } from "vitest";
import {
  cancelListeningRun,
  createListeningRun,
  getActiveListeningRun,
  navigateListeningRun,
  type ListeningRun,
} from "./listeningRuns";

const run: ListeningRun = {
  id: 9,
  status: "active",
  chapter_numbers: [2],
  current_index: 0,
  items: [
    {
      position: 0,
      chapter_number: 2,
      exercise: {
        id: 7,
        chapter_id: 4,
        chapter_number: 2,
        title: "Scale",
        description: "",
        category: null,
        position: 0,
        image: {
          id: "image",
          mime_type: "image/png",
          size_bytes: 10,
          duration_seconds: null,
        },
        audio: null,
        omr: {
          status: "none",
          job_id: null,
          image_id: null,
          attempts: 0,
          last_error: null,
        },
      },
    },
  ],
};

function mockRunResponse() {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(run)));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

it("retrieves the active saved run, including an empty active-run response", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(run)))
    .mockResolvedValueOnce(new Response("null"));
  vi.stubGlobal("fetch", fetch);

  await expect(getActiveListeningRun()).resolves.toEqual(run);
  await expect(getActiveListeningRun()).resolves.toBeNull();
  expect(fetch.mock.calls.map(([url]) => url)).toEqual([
    "/api/listening/run",
    "/api/listening/run",
  ]);
});

it("creates a run with the selected chapter IDs", async () => {
  const fetch = mockRunResponse();

  await expect(createListeningRun("csrf", [4, 6])).resolves.toEqual(run);
  expect(fetch.mock.calls[0]).toMatchObject([
    "/api/listening/run",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ chapter_ids: [4, 6] }),
      headers: expect.objectContaining({ "X-CSRF-Token": "csrf" }),
    }),
  ]);
});

it.each(["next", "previous"] as const)(
  "navigates a saved run in the %s direction",
  async (direction) => {
    const fetch = mockRunResponse();

    await expect(
      navigateListeningRun("csrf", run.id, direction),
    ).resolves.toEqual(run);
    expect(fetch.mock.calls[0]).toMatchObject([
      `/api/listening/run/${run.id}/navigate`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ direction }),
      }),
    ]);
  },
);

it("cancels a saved run", async () => {
  const fetch = mockRunResponse();

  await expect(cancelListeningRun("csrf", run.id)).resolves.toEqual(run);
  expect(fetch.mock.calls[0]).toMatchObject([
    `/api/listening/run/${run.id}/cancel`,
    expect.objectContaining({ method: "POST" }),
  ]);
});

it("accepts a cancelled run whose current queue item was deleted", async () => {
  const cancelled = {
    ...run,
    status: "cancelled" as const,
    current_index: 1,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(cancelled))),
  );

  await expect(getActiveListeningRun()).resolves.toEqual(cancelled);
});

it.each([
  { ...run, id: 0 },
  { ...run, id: 1.5 },
  { ...run, status: "paused" },
  { ...run, chapter_numbers: [0] },
  { ...run, current_index: 1 },
  { ...run, current_index: 0.5 },
  {
    ...run,
    items: [{ ...run.items[0], position: -1 }],
  },
  {
    ...run,
    items: [{ ...run.items[0], chapter_number: 3 }],
  },
  {
    ...run,
    items: [
      {
        ...run.items[0],
        exercise: { ...run.items[0].exercise, chapter_id: 0 },
      },
    ],
  },
  { ...run, items: {} },
])("rejects malformed saved-run responses: %j", async (response) => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(response))),
  );

  await expect(getActiveListeningRun()).rejects.toMatchObject({
    code: "INVALID_RESPONSE",
  });
});
