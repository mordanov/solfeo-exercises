import { act, fireEvent, render } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Timer from "./Timer";

afterEach(() => vi.useRealTimers());

it("uses the server deadline even when the tab is hidden", async () => {
  vi.useFakeTimers();
  const expire = vi.fn();
  render(
    <Timer totalMs={10000} deadlineMs={Date.now() + 1000} onExpire={expire} />,
  );
  fireEvent(document, new Event("visibilitychange"));
  await act(async () => vi.advanceTimersByTimeAsync(1100));
  expect(expire).toHaveBeenCalledOnce();
});

it("expires immediately when resuming after the absolute deadline", async () => {
  vi.useFakeTimers();
  const expire = vi.fn();
  render(
    <Timer totalMs={10000} deadlineMs={Date.now() - 1} onExpire={expire} />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(50));
  expect(expire).toHaveBeenCalledOnce();
});
