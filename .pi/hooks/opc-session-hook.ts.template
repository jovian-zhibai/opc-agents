/**
 * OPC Session Start Hook — Pi Extension（模板）
 *
 * 功能：会话启动时自动检查，注入上下文给 Director：
 *   1. 中断恢复：检查未完成任务（state.json）
 *   2. 会话引导：读 session-notes.md 最后 20 行
 *   3. 高危流程提醒：钱/用户可见变化/QA 3次失败
 *   4. 任务前查教训：lessons-index 检索（仅当有 prompt 时）
 *
 * 核心逻辑委托给 scripts/opc_session_hook.py（五运行时共享核心），
 * 本扩展只做 Pi extension API 适配（before_agent_start → message 注入）。
 *
 * 安装：
 *   1. 复制本文件到 ~/.pi/agent/extensions/opc-session-hook.ts
 *   2. 修改 PROJECT_DIR 为你的 opc-agents 项目路径（或设置 OPC_AGENTS_PATH 环境变量）
 *   3. 重启 Pi
 *
 * 降级：任何一步失败都静默跳过，不影响正常流程。
 *
 * 官方文档：https://pi.dev/docs/latest/extensions
 * before_agent_start hook：Agent 启动前触发，可返回 message 注入上下文。
 */
import { execSync } from "child_process"
import * as path from "path"

// 项目路径（优先用环境变量，否则用默认路径）
const PROJECT_DIR =
  process.env.OPC_AGENTS_PATH ||
  path.join(process.env.HOME || "~", "code", "opc", "opc-agents")

const HOOK_SCRIPT = path.join(PROJECT_DIR, "scripts", "opc_session_hook.py")

export default function (pi: any) {
  pi.on("before_agent_start", async (event: any, _ctx: any) => {
    try {
      // 检查共享核心脚本是否存在
      try {
        const fs = await import("fs")
        if (!fs.existsSync(HOOK_SCRIPT)) {
          return // 共享核心不存在，静默跳过
        }
      } catch {
        return
      }

      // 获取用户 prompt（可能为空，如新会话启动时）
      const prompt = event?.prompt || ""

      // 决定模式：有 prompt → user_prompt，无 → session_start
      const mode = prompt && prompt.trim().length >= 4 ? "user_prompt" : "session_start"

      // 调用共享核心（Python 脚本）
      // 输入：{"prompt": "...", "mode": "..."}
      // 输出：{"context": "..."}
      const input = JSON.stringify({ prompt, mode })
      const output = execSync(`python3 "${HOOK_SCRIPT}"`, {
        input,
        encoding: "utf-8",
        timeout: 15000,
      })

      const result = JSON.parse(output)
      const context = result?.context || ""

      if (!context) {
        return // 无需注入
      }

      // 返回 message 注入上下文
      // Pi 的 before_agent_start hook 支持返回 message 注入到会话
      return {
        message: {
          customType: "opc-session-hook",
          content: context,
          display: true, // 在 TUI 中可见
          details: {
            mode,
            source: "opc_session_hook.py",
            timestamp: new Date().toISOString(),
          },
        },
      }
    } catch {
      // 任何错误都静默跳过，不影响正常流程
      return
    }
  })
}
