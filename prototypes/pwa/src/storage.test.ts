import "fake-indexeddb/auto";
import { beforeEach, expect, it } from "vitest";
import { deleteDB, openDB } from "idb";
import { handleShare } from "./share";
import {
  clearShare,
  readShare,
  saveShare,
  readAttempt,
  saveAttempt,
  clearAttempt,
} from "./storage";

beforeEach(async () => {
  await clearShare();
  await clearAttempt();
});

it("persists the original file and its metadata across connections", async () => {
  const file = new File(["test audio"], "voice.opus", { type: "audio/ogg" });
  await saveShare(file);
  const stored = await readShare();
  expect(stored).toMatchObject({
    name: "voice.opus",
    type: "audio/ogg",
    size: 10,
  });
  expect(await stored?.file.text()).toBe("test audio");
});

it("keeps only the latest successful share", async () => {
  await saveShare(new File(["first"], "first.opus"));
  await saveShare(new File(["second"], "second.opus"));
  expect((await readShare())?.name).toBe("second.opus");
});

it("clears the stored file persistently", async () => {
  await saveShare(new File(["test"], "voice.opus"));
  await clearShare();
  expect(await readShare()).toBeNull();
});

it("retains a failed attempt separately from the last successful file", async () => {
  await saveShare(new File(["test"], "voice.opus"));
  await saveAttempt({ receivedAt: 1, outcome: "TEXT_ONLY_SHARE", fields: [] });
  expect((await readShare())?.name).toBe("voice.opus");
  expect((await readAttempt())?.outcome).toBe("TEXT_ONLY_SHARE");
  await saveAttempt({ receivedAt: 2, outcome: "EMPTY_SHARE", fields: [] });
  expect((await readAttempt())?.receivedAt).toBe(2);
  await clearAttempt();
  expect(await readAttempt()).toBeNull();
  expect((await readShare())?.name).toBe("voice.opus");
});

it("saves file and successful diagnostic metadata together", async () => {
  const attempt = { receivedAt: 1, outcome: "RECEIVED" as const, fields: [] };
  await saveShare(new File(["test"], "voice.opus"), attempt);
  expect(await readAttempt()).toEqual(attempt);
  await clearShare();
  expect(await readAttempt()).toEqual(attempt);
});

it("upgrades the deployed version 1 database without losing the file", async () => {
  await deleteDB("solfeo-pwa-prototype");
  const previous = await openDB("solfeo-pwa-prototype", 1, {
    upgrade(database) {
      database.createObjectStore("shares");
    },
  });
  await previous.put(
    "shares",
    {
      file: new Blob(["old"]),
      name: "old.opus",
      type: "audio/ogg",
      size: 3,
      receivedAt: 1,
    },
    "latest",
  );
  previous.close();
  expect((await readShare())?.name).toBe("old.opus");
  expect(await readAttempt()).toBeNull();
});

it("records a real failed share without replacing the successful file", async () => {
  await saveShare(new File(["previous"], "previous.opus"));
  const body = new FormData();
  body.append("text", "private message");
  await handleShare(
    new Request("https://solfeo.example/prototype-share/receive", {
      method: "POST",
      body,
    }),
  );
  expect((await readShare())?.name).toBe("previous.opus");
  expect((await readAttempt())?.outcome).toBe("TEXT_ONLY_SHARE");
  expect(JSON.stringify(await readAttempt())).not.toContain("private");
});
