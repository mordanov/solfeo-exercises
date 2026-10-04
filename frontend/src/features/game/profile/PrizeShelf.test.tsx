import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import PrizeShelf from "./PrizeShelf";

it.each(["ru", "en", "es"])(
  "shows colored earned artwork and gray locked artwork in %s",
  async (language) => {
    await i18n.changeLanguage(language);
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
    const earned = await screen.findByRole("img", {
      name: i18n.t("game.prizes.codes.first_round"),
    });
    const locked = screen.getByRole("img", {
      name: i18n.t("game.prizes.codes.first_win"),
    });
    expect(earned).toHaveAttribute("src", "/assets/prizes/first_round.png");
    expect(earned).toHaveStyle({ filter: "none", opacity: "1" });
    expect(locked).toHaveAttribute("src", "/assets/prizes/first_win.png");
    expect(locked).toHaveStyle({ filter: "grayscale(1)", opacity: "0.45" });
  },
);

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
