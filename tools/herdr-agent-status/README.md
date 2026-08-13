# Herdr Agent Status & Reliable Messaging

Solves the problem: Herdr agent-to-agent communication works intermittently because agents exit and restart, and Pi has no built-in retry.

## Components

### 1. Pi Extension — `herdr-agent-status.ts`

Already installed: `pi install ./herdr-agent-status.ts`

**Features:**

| Feature | Description |
|---------|-------------|
| **Status Footer** | Auto-refreshes every 5s showing 🟢 idle / 🟡 working / 🔴 offline per agent |
| **`herdr_send` tool** | Send messages with auto-retry (5 retries, 15s timeout each) |
| **`/agent-status`** | Manual status check command |

**Usage in Pi:**

```
# Send message with retry (handles agent not ready)
herdr_send(target="opencode", message="Hey, are you there?")

# Custom retry count
herdr_send(target="w1:p3", message="test", retries=3, timeout=10000)

# Check status manually
/agent-status
```

### 2. CLI Tool — `herdr-send`

```bash
# Basic usage
herdr-send opencode "Hey there!"

# With options
herdr-send w1:p3 "message" -r 5 -t 15000 -v

# It auto-waits for the agent to appear, then retries on failure
```

## How it works

1. **Before sending**: polls `herdr agent list` to find the target pane
2. **If not found**: waits up to `timeout` ms, re-polling every 2s
3. **On send failure**: retries up to `retries` times with 2s backoff
4. **After send**: optionally calls `herdr agent wait` to confirm receipt

## Installation

```bash
# Extension (already done)
pi install /Users/souljian/code/opc/opc-agents/tools/herdr-agent-status/herdr-agent-status.ts

# CLI tool (add to PATH)
ln -s /Users/souljian/code/opc/opc-agents/tools/herdr-agent-status/herdr-send /usr/local/bin/herdr-send
```

## Restart Pi

The extension needs a Pi restart to activate (status footer, `herdr_send` tool, `/agent-status` command).
