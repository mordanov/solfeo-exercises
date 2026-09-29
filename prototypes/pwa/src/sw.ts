/// <reference lib="webworker" />
import { handleShare, isShareRequest } from "./share";

declare const self: ServiceWorkerGlobalScope;

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  if (isShareRequest(event.request, self.location.origin)) {
    event.respondWith(handleShare(event.request));
  }
});
