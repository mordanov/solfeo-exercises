import { expect, it } from "vitest";
import { parseOmr } from "./omr";

it("requires a valid score status and version", () => {
  const result = {
    status: "approved",
    job_id: "job",
    image_id: "image",
    attempts: 1,
    last_error: null,
  };
  expect(parseOmr(result)).toEqual(result);
  expect(() => parseOmr({ ...result, status: "unknown" })).toThrow(
    "INVALID_RESPONSE",
  );
  expect(() => parseOmr({ ...result, job_id: null })).toThrow(
    "INVALID_RESPONSE",
  );
  expect(() => parseOmr({ ...result, attempts: -1 })).toThrow(
    "INVALID_RESPONSE",
  );
  expect(() => parseOmr(undefined)).toThrow("INVALID_RESPONSE");
});
