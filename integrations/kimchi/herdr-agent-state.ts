// Tells Herdr that this pane runs Kimchi, so the sidebar can list it.
// Copy to ~/.config/kimchi/harness/extensions/. Does nothing outside Herdr.
// @ts-nocheck

import { spawn } from "node:child_process";

const herdr = process.env.HERDR_BIN_PATH;
const paneId = process.env.HERDR_PANE_ID;
const NAME = "kimchi";

type State = "idle" | "working" | "blocked";

function enabled() {
  return process.env.HERDR_ENV === "1" && !!herdr && !!paneId;
}

// Herdr ignores a report whose seq is not higher than the last one it accepted.
let seq = Date.now() * 1000;

function call(command: string, args: string[]) {
  seq += 1;
  try {
    const child = spawn(
      herdr!,
      ["pane", command, paneId!, "--source", NAME, "--agent", NAME, "--seq", String(seq), ...args],
      { stdio: "ignore", detached: true },
    );
    child.on("error", () => {});
    child.unref();
  } catch {
    // Reporting must never interrupt the agent.
  }
}

export default function (pi) {
  if (!enabled()) {
    return;
  }

  let rootSession = false;
  let working = false;
  let blockedCount = 0;
  let blockedMessage: string | undefined;
  let last: string | undefined;

  function publish(force = false) {
    const state: State = blockedCount > 0 ? "blocked" : working ? "working" : "idle";
    const message = state === "blocked" ? blockedMessage : undefined;
    const key = `${state}\n${message ?? ""}`;
    if (!force && key === last) {
      return;
    }
    last = key;
    call("report-agent", ["--state", state, ...(message ? ["--message", message] : [])]);
  }

  pi.events.on("herdr:blocked", (data) => {
    if (!rootSession) {
      return;
    }
    if (data?.active) {
      blockedCount += 1;
      blockedMessage = data.label;
    } else {
      blockedCount = Math.max(0, blockedCount - 1);
      if (blockedCount === 0) {
        blockedMessage = undefined;
      }
    }
    publish();
  });

  pi.on("session_start", (_event, ctx) => {
    // Headless modes have no pane for Herdr to show.
    if (ctx?.mode !== "tui") {
      return;
    }
    rootSession = true;
    working = ctx?.isIdle?.() === false;
    publish(true);
  });

  pi.on("agent_start", () => {
    if (!rootSession) {
      return;
    }
    working = true;
    publish();
  });

  pi.on("agent_settled", (_event, ctx) => {
    if (!rootSession || ctx?.isIdle?.() !== true) {
      return;
    }
    working = false;
    publish();
  });

  pi.on("session_shutdown", (event) => {
    // A reload keeps the same process; only a quit frees the pane.
    if (!rootSession || event?.reason !== "quit") {
      return;
    }
    call("release-agent", []);
  });
}
