import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Import a bank CSV into the ledger database. Returns a one-line summary " +
    "(counts and date range). Raw merchant strings are never returned.",
  args: {
    csvPath: tool.schema
      .string()
      .describe("Path to the CSV bank export, relative to the project root"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, "ledger_cli.py")
    // Use the project's venv interpreter so fastmcp is importable.
    const venvPython = path.join(context.worktree, ".venv", "bin", "python")
    const result =
      await Bun.$`${venvPython} ${script} import ${args.csvPath}`.text()
    return result.trim() // single short line: imported=N dupes=M range=YYYY-MM-DD..YYYY-MM-DD
  },
})