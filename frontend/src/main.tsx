import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { App } from "./App";
import { i18n } from "./i18n";
import "./style.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing application root");
}

createRoot(root).render(
  <StrictMode>
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={new QueryClient()}>
        <App />
      </QueryClientProvider>
    </I18nextProvider>
  </StrictMode>,
);
