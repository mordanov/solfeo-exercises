import { basePath, workerTimeout } from "./config";

export async function registerWorker(): Promise<void> {
  if (!window.isSecureContext || !("serviceWorker" in navigator)) {
    throw new Error("A secure context and service-worker support are required");
  }
  const script = import.meta.env.DEV ? "src/sw.ts" : "sw.js";
  const url = new URL(`${basePath}${script}`, window.location.origin).href;
  await navigator.serviceWorker.register(url, {
    type: "module",
    scope: basePath,
    updateViaCache: "none",
  });
  if (navigator.serviceWorker.controller?.scriptURL === url) return;
  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      navigator.serviceWorker.removeEventListener("controllerchange", changed);
      reject(new Error("Service worker did not take control in time"));
    }, workerTimeout);
    function changed() {
      if (navigator.serviceWorker.controller?.scriptURL !== url) return;
      window.clearTimeout(timeout);
      navigator.serviceWorker.removeEventListener("controllerchange", changed);
      resolve();
    }
    navigator.serviceWorker.addEventListener("controllerchange", changed);
    changed();
  });
}
