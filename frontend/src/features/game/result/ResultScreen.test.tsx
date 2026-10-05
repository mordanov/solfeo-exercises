import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import ResultScreen from "./ResultScreen";

it.each(["ru", "en", "es"])(
  "celebrates new prizes with their artwork and localized names in %s",
  async (language) => {
    await i18n.changeLanguage(language);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          id: 7,
          name: "Player",
          avatar_animal: "dragon",
          custom_avatar_id: null,
          avatar_level: 2,
          xp: 30,
        }),
      ),
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
            new_achievements: ["first_round", "perfect_round"],
          }}
          onPlayAgain={vi.fn()}
          onChangePlayer={vi.fn()}
        />
      </QueryClientProvider>,
    );
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
