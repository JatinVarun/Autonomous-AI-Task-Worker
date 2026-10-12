import { cognitiveRuleEngine } from "./ruleEngine.js";
import { SYSTEM_PROMPT, formatToolsDocumentation } from "./prompts.js";

export class LlmProvider {
  constructor(config = {}) {
    this.provider = config.provider || process.env.LLM_PROVIDER || "BUILTIN_COGNITIVE_ENGINE";
    this.geminiApiKey = config.geminiApiKey || process.env.GEMINI_API_KEY;
    this.openaiApiKey = config.openaiApiKey || process.env.OPENAI_API_KEY;
    this.anthropicApiKey = config.anthropicApiKey || process.env.ANTHROPIC_API_KEY;
    this.ollamaUrl = config.ollamaUrl || process.env.OLLAMA_URL || "http://localhost:11434";
    this.modelName = config.modelName || process.env.MODEL_NAME || "builtin-cognitive-v1";
  }

  setProvider(provider, keys = {}) {
    this.provider = provider;
    if (keys.geminiApiKey) this.geminiApiKey = keys.geminiApiKey;
    if (keys.openaiApiKey) this.openaiApiKey = keys.openaiApiKey;
    if (keys.anthropicApiKey) this.anthropicApiKey = keys.anthropicApiKey;
    if (keys.modelName) this.modelName = keys.modelName;
  }

  getProviderInfo() {
    return {
      provider: this.provider,
      hasGeminiKey: Boolean(this.geminiApiKey),
      hasOpenaiKey: Boolean(this.openaiApiKey),
      hasAnthropicKey: Boolean(this.anthropicApiKey),
      modelName: this.modelName
    };
  }

  /**
   * Plan initial steps.
   */
  async generateInitialPlan(goal) {
    if (this.provider === "BUILTIN_COGNITIVE_ENGINE" || !this.hasValidApiKey()) {
      return cognitiveRuleEngine.generateInitialPlan(goal);
    }

    try {
      if (this.provider === "GEMINI" && this.geminiApiKey) {
        return await this.generatePlanViaGemini(goal);
      }
      if (this.provider === "OPENAI" && this.openaiApiKey) {
        return await this.generatePlanViaOpenAI(goal);
      }
    } catch (err) {
      console.warn(`[LlmProvider] External LLM plan error (${err.message}). Falling back to cognitive engine.`);
    }

    return cognitiveRuleEngine.generateInitialPlan(goal);
  }

  /**
   * Decide next ReAct step (thought + tool call).
   */
  async decideNextStep({ goal, memory, stepCount, tools }) {
    if (this.provider === "BUILTIN_COGNITIVE_ENGINE" || !this.hasValidApiKey()) {
      return await cognitiveRuleEngine.decideNextStep({ goal, memory, stepCount });
    }

    try {
      if (this.provider === "GEMINI" && this.geminiApiKey) {
        return await this.decideStepViaGemini({ goal, memory, tools });
      }
      if (this.provider === "OPENAI" && this.openaiApiKey) {
        return await this.decideStepViaOpenAI({ goal, memory, tools });
      }
    } catch (err) {
      console.warn(`[LlmProvider] External LLM step decision error (${err.message}). Falling back to cognitive engine.`);
    }

    return await cognitiveRuleEngine.decideNextStep({ goal, memory, stepCount });
  }

  hasValidApiKey() {
    if (this.provider === "GEMINI") return Boolean(this.geminiApiKey);
    if (this.provider === "OPENAI") return Boolean(this.openaiApiKey);
    if (this.provider === "ANTHROPIC") return Boolean(this.anthropicApiKey);
    return false;
  }

  // --- Gemini API Connector (Native fetch) ---
  async decideStepViaGemini({ goal, memory, tools }) {
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${this.geminiApiKey}`;
    const toolsPrompt = formatToolsDocumentation(tools);
    const historyText = memory.history.map(h => 
      `Step ${h.stepNumber}:\nThought: ${h.thought}\nAction: ${h.action?.name}(${JSON.stringify(h.action?.parameters)})\nObservation: ${JSON.stringify(h.observation)}`
    ).join("\n\n");

    const prompt = `
${SYSTEM_PROMPT}

AVAILABLE TOOLS:
${toolsPrompt}

USER GOAL: "${goal}"

CURRENT MEMORY SCRATCHPAD:
${JSON.stringify(memory.scratchpad, null, 2)}

PREVIOUS EXECUTION HISTORY:
${historyText || "No previous steps yet."}

Respond ONLY in raw JSON format (no markdown fences) matching:
{
  "thought": "Your reasoning here",
  "action": {
    "name": "tool_name",
    "parameters": { ... }
  },
  "completed": false
}
If the task is fully achieved and verified, set "completed": true.
`;

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.1, responseMimeType: "application/json" }
      })
    });

    if (!res.ok) throw new Error(`Gemini API HTTP ${res.status}`);
    const data = await res.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
    return JSON.parse(text);
  }

  // --- OpenAI API Connector (Native fetch) ---
  async decideStepViaOpenAI({ goal, memory, tools }) {
    const endpoint = "https://api.openai.com/v1/chat/completions";
    const toolsPrompt = formatToolsDocumentation(tools);
    const historyText = memory.history.map(h => 
      `Step ${h.stepNumber}:\nThought: ${h.thought}\nAction: ${h.action?.name}(${JSON.stringify(h.action?.parameters)})\nObservation: ${JSON.stringify(h.observation)}`
    ).join("\n\n");

    const prompt = `
${SYSTEM_PROMPT}

AVAILABLE TOOLS:
${toolsPrompt}

USER GOAL: "${goal}"

CURRENT MEMORY SCRATCHPAD:
${JSON.stringify(memory.scratchpad, null, 2)}

PREVIOUS EXECUTION HISTORY:
${historyText || "No previous steps yet."}

Respond ONLY in raw JSON matching:
{
  "thought": "Your reasoning here",
  "action": { "name": "tool_name", "parameters": { ... } },
  "completed": false
}
`;

    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.openaiApiKey}`
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [{ role: "user", content: prompt }],
        response_format: { type: "json_object" },
        temperature: 0.1
      })
    });

    if (!res.ok) throw new Error(`OpenAI API HTTP ${res.status}`);
    const data = await res.json();
    return JSON.parse(data.choices[0].message.content);
  }

  async generatePlanViaGemini(goal) {
    // Falls back gracefully
    return cognitiveRuleEngine.generateInitialPlan(goal);
  }

  async generatePlanViaOpenAI(goal) {
    // Falls back gracefully
    return cognitiveRuleEngine.generateInitialPlan(goal);
  }
}

export const globalLlmProvider = new LlmProvider();
