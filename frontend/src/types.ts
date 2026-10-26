export type Provider = {
  id: string;
  name: string;
  kind: "demo" | "http";
  endpoint: string;
  api_key_env: string;
  supports_tools: boolean;
  timeout: number;
  retries: number;
  concurrency: number;
};
export type Agent = {
  id: string;
  name: string;
  role: string;
  provider_id: string;
  model: string;
  temperature: number;
  max_tokens: number;
  context_tokens: number;
  tools: string[];
  topics: string[];
  can_orchestrate: boolean;
  x: number;
  y: number;
  kind: "agent" | "human" | "tool" | "join";
  tool_id: string;
  tool_arguments: Record<string, unknown>;
  max_visits: number;
};
export type Link = {
  id: string;
  source: string;
  target: string;
  template: string;
  condition: "always" | "contains" | "not_contains" | "equals";
  value: string;
};
export type Network = {
  schema_version: 1;
  id: string;
  name: string;
  description: string;
  mode: "workflow" | "autonomous";
  initial_task?: string;
  agents: Agent[];
  links: Link[];
  entry_agents: string[];
  limits: {
    concurrency: number;
    tool_concurrency: number;
    max_agents: number;
    max_calls: number;
    max_steps: number;
    active_seconds: number;
  };
};
export type Tool = {
  id: string;
  name: string;
  description: string;
  kind: "cli" | "shell" | "compiler" | "analyzer" | "python";
  executable: string;
  args: string[];
  input_schema: Record<string, unknown>;
  stdin: string;
  cwd: string;
  env: Record<string, string>;
  timeout: number;
  accepted_exit_codes: number[];
  output_format: "text" | "json" | "artifact";
  artifacts: string[];
  max_output: number;
  version_args: string[];
  plugin: string;
};
export type Run = {
  id: string;
  status: string;
  created: number;
  updated: number;
  prompt: string;
  error: string;
  snapshot?: { network: Network };
  current_network?: Network;
  messages?: {
    seq: number;
    agent_id: string;
    role: string;
    content: string | null;
    tool_calls?: unknown[];
  }[];
  pending_human?: string[];
};
export type Event = {
  seq: number;
  run_id: string;
  kind: string;
  at: number;
  body: Record<string, any>;
};
export type Install = {
  manager: string;
  package: string;
  version: string;
  source: string;
  action: string;
  recipe_id: string;
};
// getRandomValues also works on remote HTTP origins; randomUUID requires HTTPS.
export const uid = () =>
  Array.from(crypto.getRandomValues(new Uint8Array(6)), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
export const newAgent = (kind: Agent["kind"] = "agent"): Agent => ({
  id: uid(),
  name:
    kind === "agent"
      ? "New agent"
      : kind === "human"
        ? "Human review"
        : kind === "join"
          ? "Join"
          : "Tool step",
  role: "You are a helpful collaborator.",
  provider_id: "demo",
  model: "demo",
  temperature: 0.5,
  max_tokens: 2048,
  context_tokens: 8192,
  tools: [],
  topics: [],
  can_orchestrate: false,
  x: 150,
  y: 150,
  kind,
  tool_id: kind === "tool" ? "compiler" : "",
  tool_arguments: kind === "tool" ? { code: "${message}" } : {},
  max_visits: 5,
});
export const newNetwork = (): Network => ({
  schema_version: 1,
  id: uid(),
  name: "Untitled network",
  description: "",
  mode: "workflow",
  initial_task: "",
  agents: [],
  links: [],
  entry_agents: [],
  limits: {
    concurrency: 4,
    tool_concurrency: 4,
    max_agents: 16,
    max_calls: 100,
    max_steps: 200,
    active_seconds: 1200,
  },
});
export const newTool = (): Tool => ({
  id: uid(),
  name: "New CLI tool",
  description: "",
  kind: "cli",
  executable: "",
  args: [],
  input_schema: { type: "object", properties: {} },
  stdin: "",
  cwd: "",
  env: {},
  timeout: 60,
  accepted_exit_codes: [0],
  output_format: "text",
  artifacts: [],
  max_output: 12000,
  version_args: ["--version"],
  plugin: "",
});
