// Minimal Streamlit custom-component protocol (no extra dependency).
import { useEffect, useState } from "react";

const send = (type, data = {}) =>
  window.parent.postMessage({ isStreamlitMessage: true, type, ...data }, "*");

export const setValue = (value) =>
  send("streamlit:setComponentValue", { value, dataType: "json" });

export function useStreamlitArgs() {
  const [args, setArgs] = useState(null);
  useEffect(() => {
    const onMessage = (event) => {
      if (event.data?.type === "streamlit:render") setArgs(event.data.args || {});
    };
    window.addEventListener("message", onMessage);
    send("streamlit:componentReady", { apiVersion: 1 });
    return () => window.removeEventListener("message", onMessage);
  }, []);
  return args;
}

// Keep the iframe exactly as tall as its content.
export function useAutoHeight() {
  useEffect(() => {
    const update = () => send("streamlit:setFrameHeight", { height: Math.ceil(document.body.scrollHeight) });
    const observer = new ResizeObserver(update);
    observer.observe(document.body);
    update();
    return () => observer.disconnect();
  }, []);
}
