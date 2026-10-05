import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import ResultScreen from "./ResultScreen";

function mountResult(newAchievements: string[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/achievements"))
        return Response.json({
          earned: ["first_round", "perfect_round"].map((code) => ({
            code,
            awarded_at: "2026-10-04T12:00:00Z",
          })),
          catalog: ["first_round", "perfect_round", "first_win"].map(
            (code) => ({ code }),
          ),
        });
      if (url.endsWith("/players/7"))
        return Response.json({
          id: 7,
          name: "Player",
          avatar_animal: "dragon",
          custom_avatar_id: null,
          avatar_level: 2,
          xp: 30,
        });
      throw new Error(`Unexpected request ${url}`);
    }),
  );
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ResultScreen
        playerId={7}
        result={{
          score: 7,
          correct_count: 7,
          is_win: true,
          xp_gained: 7,
          level_up: false,
          new_trophy: null,
          practice_hint: null,
          new_achievements: newAchievements,
        }}
        onPlayAgain={vi.fn()}
        onChangePlayer={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

it.each(["ru", "en", "es"])(
  "shows the complete collection after a round without new prizes in %s",
  async (language) => {
    await i18n.changeLanguage(language);
    mountResult([]);
    const shelf = screen.getByRole("region", {
      name: i18n.t("game.prizes.title"),
    });
    await within(shelf).findByRole("img", {
      name: i18n.t("game.prizes.codes.first_round"),
    });
    expect(within(shelf).getAllByRole("img")).toHaveLength(3);
    expect(
      within(shelf).getByRole("img", {
        name: i18n.t("game.prizes.codes.first_win"),
      }),
    ).toHaveStyle({ filter: "grayscale(1)" });
  },
);

it.each(["ru", "en", "es"])(
  "celebrates new prizes with their artwork and localized names in %s",
  async (language) => {
    await i18n.changeLanguage(language);
    mountResult(["first_round", "perfect_round"]);
    for (const code of ["first_round", "perfect_round"]) {
      const caption = i18n.t("game.prizes.newPrize", {
        name: i18n.t(`game.prizes.codes.${code}`),
      });
      const announcement = screen
        .getAllByRole("status")
        .find((element) => element.textContent === caption);
      expect(announcement).toBeDefined();
      if (!announcement) throw new Error("Missing prize announcement");
      const image = within(announcement).getByRole("img", {
        name: i18n.t(`game.prizes.codes.${code}`),
      });
      expect(image).toHaveAttribute("src", `/assets/prizes/${code}.png`);
      expect(image).toHaveStyle({ filter: "none", opacity: "1" });
    }
  },
);
