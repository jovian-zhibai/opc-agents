/**
 * OPC Session Start Hook — OpenCode 插件
 *
 * 订阅 session.created 事件，在会话启动时执行：
 *   1. 调用共享核心 scripts/opc_session_hook.py（五运行时通用）
 *   2. 获取注入上下文（中断恢复 + 会话引导 + 流程提醒）
 *   3. 将上下文写入 $OPC_WORK_PATH/session-start-context.md（默认=仓库根 work/）
 *   4. 通过 client.app.log() 记录日志
 *
 * 与其他运行时的区别：
 *   - Claude Code / Gemini / Codex 有原生 SessionStart hook，可直接注入 additionalContext
 *   - OpenCode 用插件系统间接实现（session.created 事件 + 写文件 + Director 读取）
 *   - 过渡方案：opencode director.md 保留"会话启动自动检查"节，Director 启动时读取
 *     session-start-context.md 文件（如果存在）
 *
 * 降级：任何一步失败都静默跳过，不影响正常流程。
 *
 * 安装：放在 .opencode/plugins/ 目录，OpenCode 启动时自动加载。
 * 官方文档：https://opencode.ai/docs/plugins/
 */
import type { Plugin } from "@opencode-ai/plugin"
import { writeFileSync, existsSync, mkdirSync } from "fs"
import { join } from "path"

export const OpcSessionHook: Plugin = async ({
  project,
  client,
  $,
  directory,
  worktree,
}) => {
  const projectDir = directory || worktree || process.cwd()
  // 统一产出物目录：$OPC_WORK_PATH（默认=仓库根 work/），与五运行时适配器一致
  const workDir = process.env.OPC_WORK_PATH || join(projectDir, "work")
  const contextFile = join(workDir, "session-start-context.md")

  // 确保目录存在
  if (!existsSync(workDir)) {
    try {
      mkdirSync(workDir, { recursive: true })
    } catch {
      // 静默失败
    }
  }

  return {
    event: async ({ event }) => {
      // 只处理 session.created 事件
      if (event.type !== "session.created") {
        return
      }

      try {
        // 调用共享核心（Python 脚本），获取 session_start 模式的注入上下文
        // 共享核心：scripts/opc_session_hook.py
        // 输入：{"mode": "session_start"}（无 prompt，因为会话刚启动）
        // 输出：{"context": "..."}
        const hookScript = join(projectDir, "scripts", "opc_session_hook.py")

        if (!existsSync(hookScript)) {
          // 共享核心不存在，静默跳过
          return
        }

        // 通过 Bun 的 $ API 执行 Python 脚本
        const result = await $`python3 ${hookScript}`.json({
          mode: "session_start",
        })

        const context = result?.context || ""

        if (!context) {
          // 无需注入（无未完成任务、无会话记录）
          return
        }

        // 将注入上下文写入文件，供 Director 读取
        // Director 在"会话启动自动检查"节中会读取这个文件
        try {
          writeFileSync(contextFile, context, "utf-8")
        } catch {
          // 写入失败，静默跳过
        }

        // 记录日志
        try {
          await client.app.log({
            body: {
              service: "opc-session-hook",
              level: "info",
              message: "Session start context generated",
              extra: {
                contextLength: context.length,
                contextFile,
              },
            },
          })
        } catch {
          // 日志失败，静默跳过
        }
      } catch {
        // 任何错误都静默跳过，不影响正常流程
      }
    },
  }
}

export default OpcSessionHook
