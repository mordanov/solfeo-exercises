import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import AvatarReviewQueue from "./AvatarReviewQueue";

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

it("disables decisions during review and preserves failures for an explicit retry", async () => {
  let complete: (response: Response) => void = () => {};
  const fetchMock = vi.fn(async (_url: string, options?: RequestInit) => {
    if (options?.method === "POST")
      return new Promise<Response>((resolve) => {
        complete = resolve;
      });
    return Response.json({
      jobs: [
        {
          id: 42,
          player_id: 1,
          player_name: "Mia",
          status: "ready",
          review_status: "pending",
        },
      ],
      total: 1,
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <AvatarReviewQueue csrf="token" />
    </QueryClientProvider>,
  );
  fireEvent.click(await screen.findByRole("button", { name: "Mia" }));
  const reject = screen.getByRole("button", {
    name: i18n.t("game.avatar.review.reject"),
  });
  fireEvent.click(reject);
  await waitFor(() => expect(reject).toBeDisabled());
  expect(
    screen.getByRole("button", { name: i18n.t("game.avatar.review.approve") }),
  ).toBeDisabled();
  await act(async () =>
    complete(Response.json({ error: "INTERNAL_ERROR" }, { status: 500 })),
  );
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(reject).toBeEnabled();
  fireEvent.click(reject);
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"),
    ).toHaveLength(2),
  );
  await act(async () =>
    complete(
      Response.json({ id: 42, status: "ready", review_status: "rejected" }),
    ),
  );
  expect(await screen.findByRole("status")).toHaveTextContent(
    i18n.t("game.avatar.review.rejected"),
  );
});

it("lets managers inspect all thirty images and explicitly approve a job", async () => {
  const fetchMock = vi.fn(async (url: string) =>
    Response.json(
      url.includes("/review?")
        ? {
            jobs: [
              {
                id: 42,
                player_id: 1,
                player_name: "Mia",
                status: "ready",
                review_status: "pending",
              },
            ],
            total: 1,
          }
        : {},
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <AvatarReviewQueue csrf="token" />
    </QueryClientProvider>,
  );
  expect(await screen.findByText("Mia")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Mia" }));
  expect(screen.getAllByRole("img")).toHaveLength(30);
  expect(
    screen.getByRole("link", { name: i18n.t("game.avatar.review.sheet") }),
  ).toHaveAttribute("href", "/api/game/avatars/42/review-sheet");
  fireEvent.click(
    screen.getByRole("button", { name: i18n.t("game.avatar.review.approve") }),
  );
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/game/avatars/42/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ decision: "approved" }),
      }),
    ),
  );
});
