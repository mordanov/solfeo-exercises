import "fake-indexeddb/auto";
import { beforeEach, expect, it } from "vitest";
import { clearShare, readShare, saveShare } from "./storage";

beforeEach(async () => {
  await clearShare();
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
