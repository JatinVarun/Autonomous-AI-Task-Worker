import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DOCS_DIR = path.resolve(__dirname, "../environment/mockFiles");

export const fileTools = {
  list_files: {
    name: "list_files",
    description: "List available files and documents in company storage directories (e.g. 'invoices', 'contracts', 'emails'). Returns file names, sizes, and modification dates to help locate latest documents.",
    parameters: {
      type: "object",
      properties: {
        directory: {
          type: "string",
          description: "Subdirectory to list (e.g. 'invoices', 'contracts', 'emails', or '' for all)",
          default: ""
        }
      }
    },
    async execute({ directory = "" }) {
      try {
        const targetDir = path.join(ROOT_DOCS_DIR, directory);
        // Security check: ensure path is within ROOT_DOCS_DIR
        if (!targetDir.startsWith(ROOT_DOCS_DIR)) {
          return { error: "Access denied: Path outside allowed documents directory" };
        }

        const entries = await fs.readdir(targetDir, { withFileTypes: true });
        const results = [];

        for (const entry of entries) {
          const fullPath = path.join(targetDir, entry.name);
          const relPath = path.relative(ROOT_DOCS_DIR, fullPath).replace(/\\/g, "/");

          if (entry.isDirectory()) {
            results.push({ name: entry.name, path: relPath, type: "directory" });
          } else {
            const stats = await fs.stat(fullPath);
            results.push({
              name: entry.name,
              path: relPath,
              type: "file",
              sizeBytes: stats.size,
              modifiedTime: stats.mtime.toISOString()
            });
          }
        }

        // Sort files by modifiedTime descending so newest are on top
        results.sort((a, b) => {
          if (a.modifiedTime && b.modifiedTime) {
            return new Date(b.modifiedTime) - new Date(a.modifiedTime);
          }
          return 0;
        });

        return {
          success: true,
          directory: directory || "/",
          count: results.length,
          files: results
        };
      } catch (err) {
        return { success: false, error: `Failed to list files: ${err.message}` };
      }
    }
  },

  read_file: {
    name: "read_file",
    description: "Read the complete contents of a specific document or file by its relative path (e.g. 'invoices/Acme_Invoice_INV-2024-889.txt' or 'invoices/Globex_Invoice_GL-2024-902.json').",
    parameters: {
      type: "object",
      required: ["filePath"],
      properties: {
        filePath: {
          type: "string",
          description: "Relative file path within documents storage"
        }
      }
    },
    async execute({ filePath }) {
      try {
        if (!filePath) return { success: false, error: "filePath is required" };
        const cleanPath = filePath.replace(/^[/\\]+/, "");
        const targetPath = path.join(ROOT_DOCS_DIR, cleanPath);

        if (!targetPath.startsWith(ROOT_DOCS_DIR)) {
          return { success: false, error: "Access denied: Path traversal not permitted" };
        }

        const content = await fs.readFile(targetPath, "utf-8");
        const stats = await fs.stat(targetPath);

        let parsedJson = null;
        if (cleanPath.endsWith(".json")) {
          try {
            parsedJson = JSON.parse(content);
          } catch {}
        }

        return {
          success: true,
          filePath: cleanPath,
          sizeBytes: stats.size,
          lastModified: stats.mtime.toISOString(),
          isJson: Boolean(parsedJson),
          content: parsedJson || content
        };
      } catch (err) {
        return {
          success: false,
          error: `File read error for '${filePath}': ${err.code === 'ENOENT' ? 'File not found. Please verify directory listing.' : err.message}`
        };
      }
    }
  },

  search_documents: {
    name: "search_documents",
    description: "Search across company files for specific keywords (e.g. 'Acme', 'INV-2024-889', 'refund', 'tax'). Returns matches and file paths.",
    parameters: {
      type: "object",
      required: ["query"],
      properties: {
        query: {
          type: "string",
          description: "Keyword or pattern to search for across company documents"
        }
      }
    },
    async execute({ query }) {
      try {
        const matches = [];
        const lowerQuery = query.toLowerCase();

        async function scanDir(dir) {
          const entries = await fs.readdir(dir, { withFileTypes: true });
          for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
              await scanDir(fullPath);
            } else {
              const relPath = path.relative(ROOT_DOCS_DIR, fullPath).replace(/\\/g, "/");
              // check filename
              const filenameMatches = entry.name.toLowerCase().includes(lowerQuery);
              let contentMatches = false;
              let snippet = "";

              try {
                const text = await fs.readFile(fullPath, "utf-8");
                const idx = text.toLowerCase().indexOf(lowerQuery);
                if (idx !== -1) {
                  contentMatches = true;
                  const start = Math.max(0, idx - 40);
                  const end = Math.min(text.length, idx + query.length + 40);
                  snippet = "..." + text.substring(start, end).replace(/\r?\n/g, " ") + "...";
                }
              } catch {}

              if (filenameMatches || contentMatches) {
                matches.push({
                  path: relPath,
                  filename: entry.name,
                  matchedIn: filenameMatches && contentMatches ? "both" : filenameMatches ? "filename" : "content",
                  snippet
                });
              }
            }
          }
        }

        await scanDir(ROOT_DOCS_DIR);
        return {
          success: true,
          query,
          matchCount: matches.length,
          matches
        };
      } catch (err) {
        return { success: false, error: `Search failed: ${err.message}` };
      }
    }
  }
};
