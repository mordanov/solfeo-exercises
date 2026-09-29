import en from "./src/i18n/locales/en.json";
import ru from "./src/i18n/locales/ru.json";
import es from "./src/i18n/locales/es.json";

export const prefix = "/prototype-share/";
export function manifest(language: "en" | "ru" | "es" = "en") {
  return {
    id: prefix,
    name: { en, ru, es }[language].appTitle,
    short_name: { en, ru, es }[language].appTitle,
    lang: language,
    start_url: prefix,
    scope: prefix,
    display: "standalone",
    theme_color: "#172a37",
    background_color: "#f1f5f7",
    icons: [192, 512].map((size) => ({
      src: `${prefix}icon-${size}x${size}.png`,
      sizes: `${size}x${size}`,
      type: "image/png",
      purpose: "any maskable",
    })),
    share_target: {
      action: `${prefix}receive`,
      method: "POST",
      enctype: "multipart/form-data",
      params: {
        files: [
          {
            name: "audio",
            accept: ["audio/*", ".opus", ".ogg", "application/octet-stream"],
          },
        ],
      },
    },
  };
}
