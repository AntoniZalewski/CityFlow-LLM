"use client";

import { fetchState } from "@/lib/api";
import type { SimState } from "@/lib/types";

type Listener = (state: SimState) => void;
const FALLBACK_INTERVAL_MS = 500;

export function connectStateStream(listener: Listener): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  let socket: WebSocket | null = null;
  let stopped = false;
  let fallbackTimer: number | null = null;
  let reconnectTimer: number | null = null;
  let controller: AbortController | null = null;

  const wsEndpoint = buildWsUrl();

  const stopFallback = () => {
    if (fallbackTimer !== null) {
      window.clearTimeout(fallbackTimer);
      fallbackTimer = null;
    }
    if (controller) {
      controller.abort();
      controller = null;
    }
  };

  const pollState = async () => {
    if (stopped) {
      return;
    }
    controller?.abort();
    controller = new AbortController();
    try {
      const state = await fetchState(controller.signal);
      if (state) {
        listener(state);
      }
    } catch (error) {
      console.warn("State fallback request failed", error);
    }
    fallbackTimer = window.setTimeout(pollState, FALLBACK_INTERVAL_MS);
  };

  const ensureFallback = () => {
    if (fallbackTimer === null) {
      pollState();
    }
  };

  const scheduleReconnect = () => {
    if (reconnectTimer !== null || stopped) {
      return;
    }
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connectSocket();
    }, 3000);
  };

  const connectSocket = () => {
    if (stopped) {
      return;
    }
    try {
      socket = new WebSocket(wsEndpoint);
    } catch (error) {
      console.warn("Unable to open WebSocket", error);
      ensureFallback();
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      stopFallback();
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const state = payload?.state ?? payload;
        if (state) {
          listener(state);
        }
      } catch (err) {
        console.error("Failed to parse state payload", err);
      }
    };

    socket.onerror = (event) => {
      console.warn("State stream error", event);
      ensureFallback();
    };

    socket.onclose = () => {
      ensureFallback();
      scheduleReconnect();
    };
  };

  const cleanup = () => {
    stopped = true;
    stopFallback();
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket?.close();
  };

  connectSocket();

  return cleanup;
}

function buildWsUrl(): string {
  const override = process.env.NEXT_PUBLIC_WS_STATE_URL;
  if (override) {
    return override;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.hostname || "localhost";
    const port = process.env.NEXT_PUBLIC_WS_PORT ?? "8000";
    return `${protocol}://${host}:${port}/ws/state`;
  }
  return "ws://localhost:8000/ws/state";
}
