/**
 * Herdr Agent Status Extension for Pi
 *
 * Features:
 * 1. Footer status bar — real-time agent readiness (🟢 idle / 🟡 working / 🔴 offline)
 * 2. `herdr_send` tool — send messages to Herdr agents with auto-retry & readiness wait
 * 3. `/agent-status` command — manual status check
 *
 * Install: pi install /path/to/herdr-agent-status.ts
 */

import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

interface AgentInfo {
  agent: string;
  agent_status: string;
  pane_id: string;
  terminal_title_stripped: string;
}

const STATUS_ICONS: Record<string, string> = {
  idle: "🟢",
  working: "🟡",
  blocked: "🟠",
  done: "🔵",
  unknown: "🔴",
};

function statusIcon(status: string): string {
  return STATUS_ICONS[status] ?? "🔴";
}

async function getAgents(pi: ExtensionAPI): Promise<AgentInfo[]> {
  try {
    const { stdout, code } = await pi.exec("herdr", ["agent", "list"]);
    if (code !== 0) return [];

    const data = JSON.parse(stdout);
    return data.result?.agents || data.agents || [];
  } catch {
    return [];
  }
}

async function waitForAgentReady(
  pi: ExtensionAPI,
  agentNameOrPane: string,
  maxWaitMs: number,
  intervalMs: number,
  signal?: AbortSignal,
): Promise<string | null> {
  const start = Date.now();

  while (Date.now() - start < maxWaitMs) {
    if (signal?.aborted) return null;

    const agents = await getAgents(pi);
    for (const a of agents) {
      if (a.pane_id === agentNameOrPane || a.agent === agentNameOrPane) {
        return a.pane_id;
      }
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }

  return null;
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

function startPolling(ctx: ExtensionContext, pi: ExtensionAPI) {
  if (pollTimer) return;

  const updateFooter = async () => {
    const agents = await getAgents(pi);
    const theme = ctx.ui.theme;

    if (agents.length === 0) {
      ctx.ui.setStatus(
        "herdr-agents",
        theme.fg("muted", "🟣 herdr: no agents"),
      );
      return;
    }

    const parts: string[] = [];
    for (const a of agents) {
      const icon = statusIcon(a.agent_status);
      const title = (a.terminal_title_stripped || a.agent || "?").slice(0, 25);
      parts.push(`${icon} ${a.agent}:${title}`);
    }

    ctx.ui.setStatus("herdr-agents", parts.join("  "));
  };

  updateFooter().catch(() => {});
  pollTimer = setInterval(() => updateFooter().catch(() => {}), 5000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

export default function (pi: ExtensionAPI) {
  // ─── herdr_send tool (with retry) ────────────────────────────────────────

  pi.registerTool({
    name: "herdr_send",
    label: "Herdr Send",
    description:
      "Send a message to a Herdr agent pane. Automatically waits for the agent to be detected and retries on failure. Target can be a pane ID (e.g. w1:p3) or agent name (e.g. opencode).",
    promptSnippet: "Send messages to other agents in Herdr with retry",
    promptGuidelines: [
      "Use herdr_send to communicate with other agents running in Herdr. It includes built-in retry logic so you don't need to worry about timing.",
    ],
    parameters: Type.Object({
      target: Type.String({
        description: "Agent pane ID (e.g. w1:p3) or agent name (e.g. opencode)",
      }),
      message: Type.String({ description: "The message to send" }),
      retries: Type.Optional(
        Type.Integer({
          minimum: 0,
          maximum: 10,
          description: "Max retries (default: 5)",
        }),
      ),
      timeout: Type.Optional(
        Type.Integer({
          minimum: 1000,
          maximum: 300000,
          description: "Timeout per attempt in ms (default: 15000)",
        }),
      ),
    }),

    async execute(_toolCallId, params, signal, onUpdate, ctx) {
      const target = params.target;
      const message = params.message;
      const maxRetries = params.retries ?? 5;
      const timeoutMs = params.timeout ?? 15000;

      let targetPane: string | null = null;

      // Try to find existing pane immediately
      const agents = await getAgents(pi);
      for (const a of agents) {
        if (a.pane_id === target || a.agent === target) {
          targetPane = a.pane_id;
          break;
        }
      }

      // If not found, wait for it with retries
      if (!targetPane) {
        onUpdate?.({
          content: [{ type: "text", text: `Waiting for agent "${target}" to be ready...` }],
        });

        targetPane = await waitForAgentReady(pi, target, timeoutMs, 2000, signal);

        if (!targetPane) {
          return {
            content: [{ type: "text", text: `Agent "${target}" not found or not ready after ${timeoutMs}ms` }],
            details: { target, found: false },
          };
        }
      }

      // Send with retry (exponential backoff)
      let backoffMs = 2000;
      for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
        if (signal?.aborted) {
          return { content: [{ type: "text", text: "Cancelled" }] };
        }

        onUpdate?.({
          content: [{ type: "text", text: `Sending to ${targetPane} (attempt ${attempt}/${maxRetries + 1})...` }],
        });

        try {
          const { stdout, code } = await pi.exec("herdr", ["agent", "prompt", targetPane, message]);

          if (code !== 0) {
            throw new Error(`herdr agent prompt failed: ${stdout.trim()}`);
          }

          // Try to wait for the agent to finish processing
          try {
            await pi.exec("herdr", ["agent", "wait", targetPane, "--timeout", String(timeoutMs)]);
            return {
              content: [{ type: "text", text: `✓ Message sent to ${targetPane} (${target}) on attempt ${attempt}` }],
              details: { targetPane, attempt },
            };
          } catch (waitErr: any) {
            // Agent might already be idle; treat as non-critical
            onUpdate?.({
              content: [{ type: "text", text: `✓ Sent to ${targetPane}, but could not confirm receipt (${waitErr.message})` }],
            });
            return {
              content: [{ type: "text", text: `✓ Sent to ${targetPane} (could not confirm receipt)` }],
              details: { targetPane, attempt, confirmed: false },
            };
          }
        } catch (err: any) {
          onUpdate?.({
            content: [{ type: "text", text: `Attempt ${attempt} failed: ${err.message}` }],
          });

          if (attempt <= maxRetries) {
            const delay = Math.min(backoffMs, 10000);
            onUpdate?.({
              content: [{ type: "text", text: `Retrying in ${delay}ms...` }],
            });
            await new Promise((r) => setTimeout(r, delay));
            backoffMs = Math.min(backoffMs * 2, 10000);
          }
        }
      }

      return {
        content: [{ type: "text", text: `Failed to send to "${target}" after ${maxRetries} retries` }],
        details: { target, attempts: maxRetries + 1 },
      };
    },
  });

  // ─── /agent-status command ───────────────────────────────────────────────

  pi.registerCommand("agent-status", {
    description: "Show Herdr agent status",
    handler: async (_args, ctx) => {
      const agents = await getAgents(pi);

      if (agents.length === 0) {
        return {
          content: [{ type: "text", text: "No Herdr agents detected." }],
        };
      }

      const lines = agents.map(
        (a) =>
          `${statusIcon(a.agent_status)} ${a.agent} [${a.agent_status}] pane=${a.pane_id}  ${a.terminal_title_stripped || "(no title)"}`,
      );

      return {
        content: [{ type: "text", text: "Herdr Agents:\n" + lines.join("\n") }],
      };
    },
  });

  // ─── Lifecycle ───────────────────────────────────────────────────────────

  pi.on("session_start", (_event, ctx) => {
    startPolling(ctx, pi);
  });

  pi.on("session_shutdown", () => {
    stopPolling();
  });
}
