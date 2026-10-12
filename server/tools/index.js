import { fileTools } from "./fileTool.js";
import { erpTools } from "./erpTool.js";
import { browserTools } from "./browserTool.js";
import { databaseTools } from "./databaseTool.js";
import { verificationTools } from "./verificationTool.js";
import { notificationTools } from "./notificationTool.js";

export class ToolRegistry {
  constructor() {
    this.tools = new Map();
    this.registerCategory(fileTools);
    this.registerCategory(erpTools);
    this.registerCategory(browserTools);
    this.registerCategory(databaseTools);
    this.registerCategory(verificationTools);
    this.registerCategory(notificationTools);
  }

  registerCategory(toolMap) {
    for (const [name, tool] of Object.entries(toolMap)) {
      this.tools.set(name, tool);
    }
  }

  getTool(name) {
    return this.tools.get(name) || null;
  }

  listToolSchemas() {
    return Array.from(this.tools.values()).map(t => ({
      name: t.name,
      description: t.description,
      parameters: t.parameters
    }));
  }

  async execute(name, params = {}, context = {}) {
    const tool = this.tools.get(name);
    if (!tool) {
      return {
        success: false,
        error: `Unknown tool: "${name}". Available tools: ${Array.from(this.tools.keys()).join(", ")}`
      };
    }

    const startTime = Date.now();
    try {
      // Validate required parameters if specified
      if (tool.parameters?.required) {
        for (const req of tool.parameters.required) {
          if (params[req] === undefined || params[req] === null || params[req] === "") {
            return {
              success: false,
              error: `Missing required parameter '${req}' for tool '${name}'. Required: [${tool.parameters.required.join(", ")}]`
            };
          }
        }
      }

      const result = await tool.execute(params, context);
      const durationMs = Date.now() - startTime;
      return {
        ...result,
        _meta: {
          toolName: name,
          durationMs,
          timestamp: new Date().toISOString()
        }
      };
    } catch (err) {
      const durationMs = Date.now() - startTime;
      return {
        success: false,
        error: `Exception in tool '${name}': ${err.message}`,
        _meta: {
          toolName: name,
          durationMs,
          timestamp: new Date().toISOString()
        }
      };
    }
  }
}

export const globalToolRegistry = new ToolRegistry();
