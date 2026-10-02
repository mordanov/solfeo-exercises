import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import { browserLanguage } from "../configuration";
import en from "./locales/en.json";
import ru from "./locales/ru.json";
import es from "./locales/es.json";

export const i18n = i18next.createInstance();
void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ru: { translation: ru },
    es: { translation: es },
  },
  lng: browserLanguage(),
  fallbackLng: "en",
  keySeparator: false,
  interpolation: { escapeValue: false },
  initImmediate: false,
});
