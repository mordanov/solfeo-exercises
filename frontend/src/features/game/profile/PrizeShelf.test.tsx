import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import PrizeShelf from "./PrizeShelf";

it("renders earned and locked prizes from the server catalog", async () => {
  await i18n.changeLanguage("en");
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      Response.json({
        earned: [{ code: "first_round", awarded_at: "2026-10-01T00:00:00Z" }],
        catalog: [{ code: "first_round" }, { code: "first_win" }],
      }),
    ),
  );
  render(
    <QueryClientProvider client={new QueryClient()}>
      <PrizeShelf playerId={7} />
    </QueryClientProvider>,
  );
  expect(
    (
      await screen.findByText(
        new RegExp(i18n.t("game.prizes.codes.first_round")),
      )
    ).parentElement,
  ).toHaveAttribute(
    "title",
    `${i18n.t("game.prizes.earned")} — ${i18n.t("game.prizes.descriptions.first_round")}`,
  );
  expect(
    screen.getByText(new RegExp(i18n.t("game.prizes.codes.first_win")))
      .parentElement,
  ).toHaveAttribute(
    "title",
    `${i18n.t("game.prizes.locked")} — ${i18n.t("game.prizes.descriptions.first_win")}`,
  );
});
