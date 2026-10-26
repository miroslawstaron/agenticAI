import React, {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import { createRoot } from "react-dom/client";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  applyNodeChanges,
  applyEdgeChanges,
  MarkerType,
  BaseEdge,
  getSmoothStepPath,
  type EdgeProps,
  type Connection,
  type NodeChange,
  type EdgeChange,
  type Node,
  type Edge,
} from "@xyflow/react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  Bot,
  Box,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Copy,
  Download,
  ExternalLink,
  FileJson,
  GitBranch,
  Layers,
  Loader2,
  MessageSquare,
  MoreHorizontal,
  Network as NetworkIcon,
  Pause,
  Play,
  Plus,
  Radio,
  Save,
  Search,
  Settings2,
  ShieldCheck,
  Square,
  Terminal,
  Trash2,
  User,
  Workflow,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, session, download } from "./api";
import {
  type Agent,
  type Network,
  type Provider,
  type Tool,
  type Run,
  type Event,
  type Install,
  newAgent,
  newNetwork,
  newTool,
  uid,
} from "./types";
import "@xyflow/react/dist/style.css";
import "./style.css";

type Screen = "workspace" | "tools" | "providers" | "runs" | "docs";
const terminal = new Set([
  "completed",
  "failed",
  "cancelled",
  "limited",
  "interrupted",
]);
const icons = { agent: Bot, human: User, tool: Terminal, join: GitBranch };
const START = "__workflow_start__";
const startEdge = (id: string) => `${START}:${id}`;
const withStart = (n: Network): Network => ({
  ...n,
  initial_task: n.initial_task || "",
  entry_agents:
    n.initial_task !== undefined || n.entry_agents.length
      ? n.entry_agents
      : n.agents
          .filter((a) => !n.links.some((l) => l.target === a.id))
          .map((a) => a.id),
});
const formatTime = (stamp: number) => new Date(stamp * 1000).toLocaleString();

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
function JsonField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: unknown;
  onChange: (v: any) => void;
}) {
  const [text, setText] = useState(JSON.stringify(value, null, 2));
  const [error, setError] = useState("");
  useEffect(
    () => setText(JSON.stringify(value, null, 2)),
    [JSON.stringify(value)],
  );
  return (
    <Field label={label}>
      <textarea
        className={"code " + (error ? "invalid" : "")}
        rows={5}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          try {
            const v = JSON.parse(e.target.value);
            setError("");
            onChange(v);
          } catch {
            setError("Enter valid JSON");
          }
        }}
      />
      {error && <small className="error-text">{error}</small>}
    </Field>
  );
}
function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        role="dialog"
        aria-label={title}
        className={"modal " + (wide ? "wide" : "")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-heading">
          <h2>{title}</h2>
          <button aria-label="Close" className="icon-button" onClick={onClose}>
            <X size={19} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
function Status({ status }: { status: string }) {
  return (
    <span className={"status " + status}>
      <span />
      {status}
    </span>
  );
}
function AgentNode({ data, selected }: any) {
  const agent: Agent = data.agent;
  const Icon = icons[agent.kind];
  return (
    <div className={"agent-node " + (selected ? "selected " : "") + agent.kind}>
      <Handle type="target" position={Position.Left} />
      <div className="node-top">
        <span className={"node-icon " + agent.kind}>
          <Icon size={20} />
        </span>
        <span className="node-kind">
          {agent.kind === "agent"
            ? "AI AGENT"
            : agent.kind === "human"
              ? "HUMAN INPUT"
              : agent.kind === "join"
                ? "JOIN"
                : "TOOL STEP"}
        </span>
        <MoreHorizontal size={16} />
      </div>
      <strong>{agent.name}</strong>
      <p>
        {agent.kind === "agent"
          ? agent.role
          : agent.kind === "human"
            ? "Wait for your response"
            : agent.kind === "join"
              ? "Wait for every incoming branch"
              : data.toolName || "Select a tool"}
      </p>
      <div className="node-footer">
        <span>
          <Circle size={8} fill="currentColor" />
          {agent.kind === "agent" ? agent.model : agent.kind}
        </span>
        <span>
          {agent.tools.length > 0 && (
            <>
              <Wrench size={11} />
              {agent.tools.length}
            </>
          )}
          {data.entry && <b>ENTRY</b>}
        </span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
function StartNode({ data, selected }: any) {
  return (
    <div className={"agent-node start-node " + (selected ? "selected" : "")}>
      <div className="node-top">
        <span className="node-icon">
          <Play size={19} />
        </span>
        <span className="node-kind">WORKFLOW START</span>
      </div>
      <strong>Start</strong>
      <p>{data.task || "Enter the initial task for your agents."}</p>
      <button className="text-button nodrag" onClick={data.onEdit}>
        Edit initial task <ArrowRight size={13} />
      </button>
      <div className="node-footer">
        <span>
          {data.recipients} first recipient{data.recipients === 1 ? "" : "s"}
        </span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { agentNode: AgentNode, startNode: StartNode };

function RoutedEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY } = props;
  const top = Math.min(sourceY, targetY) - 145;
  const path =
    sourceX >= targetX
      ? `M ${sourceX} ${sourceY} C ${sourceX + 55} ${sourceY} ${sourceX + 55} ${top} ${sourceX} ${top} L ${targetX} ${top} C ${targetX - 55} ${top} ${targetX - 55} ${targetY} ${targetX} ${targetY}`
      : getSmoothStepPath(props)[0];
  return <BaseEdge {...props} path={path} />;
}
const edgeTypes = { routed: RoutedEdge };

function App() {
  const [ready, setReady] = useState(false),
    [sessionInfo, setSessionInfo] = useState<any>({}),
    [screen, setScreen] = useState<Screen>("workspace");
  const [networks, setNetworks] = useState<Network[]>([]),
    [network, setNetwork] = useState<Network>(newNetwork),
    [providers, setProviders] = useState<Provider[]>([]),
    [tools, setTools] = useState<Tool[]>([]),
    [library, setLibrary] = useState<Agent[]>([]),
    [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<string>(START),
    [edgeId, setEdgeId] = useState(""),
    [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [error, setError] = useState("");
  const [runId, setRunId] = useState(""),
    [run, setRun] = useState<Run | null>(null),
    [events, setEvents] = useState<Event[]>([]),
    [tab, setTab] = useState("design"),
    [modal, setModal] = useState("");
  const importRef = useRef<HTMLInputElement>(null),
    eventRef = useRef<HTMLDivElement>(null);
  const notify = (message: string) => {
    setNotice(message);
    setTimeout(() => setNotice(""), 4000);
  };
  const report = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  const refresh = async () => {
    const [ns, ps, ts, rs, ls] = await Promise.all([
      api<Network[]>("/networks"),
      api<Provider[]>("/providers"),
      api<Tool[]>("/tools"),
      api<Run[]>("/runs"),
      api<Agent[]>("/agents"),
    ]);
    setNetworks(ns);
    setProviders(ps);
    setTools(ts);
    setRuns(rs);
    setLibrary(ls);
    return ns;
  };
  useEffect(() => {
    session()
      .then(async (info) => {
        setSessionInfo(info);
        const ns = await refresh();
        const last = localStorage.getItem("agenticai.network.v2");
        setNetwork(
          withStart(
            ns.find((n) => n.id === last) ||
              ns.find((n) => n.id === "designer-programmer") ||
              ns[0] ||
              newNetwork(),
          ),
        );
        setReady(true);
      })
      .catch(report);
  }, []);
  useEffect(() => {
    if (ready && network.id)
      localStorage.setItem("agenticai.network.v2", network.id);
  }, [network.id, ready]);
  useEffect(() => {
    if (!runId) return;
    setEvents([]);
    const source = new EventSource(`/api/v1/runs/${runId}/events`);
    source.onmessage = (e) => {
      const event: Event = JSON.parse(e.data);
      setEvents((previous) =>
        previous.some((p) => p.seq === event.seq)
          ? previous
          : [...previous, event],
      );
      if (
        event.kind === "status" ||
        event.kind === "human_input" ||
        event.kind === "network_changed"
      )
        api<Run>("/runs/" + runId)
          .then(setRun)
          .catch(report);
    };
    source.addEventListener("end", () => {
      source.close();
      api<Run>("/runs/" + runId).then(setRun);
      refresh().catch(report);
    });
    source.onerror = () => {};
    api<Run>("/runs/" + runId)
      .then(setRun)
      .catch(report);
    return () => source.close();
  }, [runId]);
  useEffect(() => {
    if (eventRef.current)
      eventRef.current.scrollTop = eventRef.current.scrollHeight;
  }, [events.length]);
  const change = (fn: (n: Network) => Network) => {
    setNetwork((n) => fn(n));
    setDirty(true);
  };
  const updateAgent = (patch: Partial<Agent>) =>
    change((n) => ({
      ...n,
      agents: n.agents.map((a) => (a.id === selected ? { ...a, ...patch } : a)),
    }));
  const save = async () => {
    setBusy(true);
    try {
      await api("/networks/" + network.id, "PUT", network);
      await refresh();
      setDirty(false);
      notify("Network saved");
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  };
  const pick = (n: Network) => {
    if (dirty && !window.confirm("Discard unsaved network changes?")) return;
    setNetwork(withStart(structuredClone(n)));
    setSelected(START);
    setEdgeId("");
    setDirty(false);
    setTab("design");
    setScreen("workspace");
  };
  const add = (kind: Agent["kind"] = "agent", preset?: Agent) => {
    const a = preset
      ? { ...structuredClone(preset), id: uid() }
      : newAgent(kind);
    a.x = 100 + (network.agents.length % 3) * 320;
    a.y = 90 + Math.floor(network.agents.length / 3) * 260;
    change((n) => ({
      ...n,
      agents: [...n.agents, a],
      entry_agents: n.agents.length ? n.entry_agents : [a.id],
    }));
    setSelected(a.id);
    setEdgeId("");
  };
  const start = async () => {
    if (!network.initial_task?.trim() || !network.entry_agents.length) {
      setSelected(START);
      setTab("design");
      setError(
        "Enter an initial task and connect Start to at least one first recipient.",
      );
      return;
    }
    setBusy(true);
    try {
      await api("/networks/" + network.id, "PUT", network);
      const r = await api("/runs", "POST", { network });
      setError("");
      setRunId(r.id);
      setTab("activity");
      setDirty(false);
      await refresh();
      notify("Run started");
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  };
  const selectedAgent = network.agents.find((a) => a.id === selected),
    selectedEdge = network.links.find((l) => l.id === edgeId);
  const nodes = useMemo<Node[]>(
    () => [
      {
        id: START,
        type: "startNode",
        position: {
          x: Math.min(100, ...network.agents.map((a) => a.x)) - 330,
          y: Math.min(130, ...network.agents.map((a) => a.y)),
        },
        selected: selected === START,
        deletable: false,
        draggable: false,
        data: {
          task: network.initial_task,
          recipients: network.entry_agents.length,
          onEdit: () => {
            setSelected(START);
            setEdgeId("");
          },
        },
      },
      ...network.agents.map((a) => ({
        id: a.id,
        type: "agentNode",
        position: { x: a.x, y: a.y },
        selected: a.id === selected,
        data: {
          agent: a,
          entry: network.entry_agents.includes(a.id),
          toolName: tools.find((t) => t.id === a.tool_id)?.name,
        },
      })),
    ],
    [
      network.agents,
      network.entry_agents,
      network.initial_task,
      selected,
      tools,
    ],
  );
  const edges = useMemo<Edge[]>(
    () => [
      ...network.entry_agents.map((id) => ({
        id: startEdge(id),
        source: START,
        target: id,
        type: "routed",
        label: "Initial task",
        selected: edgeId === startEdge(id),
        markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
        style: { stroke: "#399b7d", strokeWidth: 1.8 },
        labelStyle: { fontSize: 11, fill: "#347660" },
      })),
      ...network.links.map((l) => ({
        id: l.id,
        source: l.source,
        target: l.target,
        selected: l.id === edgeId,
        label: l.condition === "always" ? "" : `${l.condition}: ${l.value}`,
        type: "routed",
        markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
        style: { stroke: "#8ba5a7", strokeWidth: 1.6 },
        labelStyle: { fontSize: 11, fill: "#50676c" },
      })),
    ],
    [network.links, network.entry_agents, edgeId],
  );
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const updated = applyNodeChanges(changes, nodes);
      if (changes.some((c) => c.type === "position" || c.type === "remove"))
        change((n) => ({
          ...n,
          agents: n.agents
            .filter((a) => updated.some((node) => node.id === a.id))
            .map((a) => ({
              ...a,
              x: updated.find((node) => node.id === a.id)!.position.x,
              y: updated.find((node) => node.id === a.id)!.position.y,
            })),
          links: n.links.filter(
            (l) =>
              updated.some((a) => a.id === l.source) &&
              updated.some((a) => a.id === l.target),
          ),
          entry_agents: n.entry_agents.filter((id) =>
            updated.some((a) => a.id === id),
          ),
        }));
    },
    [nodes],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const updated = applyEdgeChanges(changes, edges);
      if (changes.some((c) => c.type === "remove"))
        change((n) => ({
          ...n,
          links: n.links.filter((l) => updated.some((e) => e.id === l.id)),
          entry_agents: n.entry_agents.filter((id) =>
            updated.some((e) => e.id === startEdge(id)),
          ),
        }));
    },
    [edges],
  );
  const onConnect = (c: Connection) => {
    if (c.target === START) return;
    if (c.source === START) {
      change((n) => ({
        ...n,
        entry_agents: [...new Set([...n.entry_agents, c.target!])],
      }));
      return;
    }
    change((n) => ({
      ...n,
      links: [
        ...n.links,
        {
          id: uid(),
          source: c.source!,
          target: c.target!,
          template: "{message}",
          condition: "always",
          value: "",
        },
      ],
    }));
  };
  const duplicate = () => {
    const copy = {
      ...structuredClone(network),
      id: uid(),
      name: network.name + " copy",
    };
    setNetwork(copy);
    setDirty(true);
    setSelected("");
    notify("Copy created. Save to keep it.");
  };
  const active = run && !terminal.has(run.status);
  const nav = [
    { id: "workspace", label: "Workspace", icon: Workflow },
    { id: "tools", label: "Tools & CLI", icon: Terminal },
    { id: "providers", label: "Model providers", icon: Box },
    { id: "runs", label: "Run history", icon: Activity },
    { id: "docs", label: "Documentation", icon: BookOpen },
  ];
  if (!ready)
    return (
      <div className="loading">
        <span className="brand-symbol">A</span>
        <h2>AgenticAI Studio</h2>
        {error ? (
          <p className="error-text">{error}</p>
        ) : (
          <Loader2 className="spin" />
        )}
      </div>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" onClick={() => setScreen("workspace")}>
          <span className="brand-symbol">A</span>
          <span>
            Agentic<span>AI</span>
            <small>STUDIO</small>
          </span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">M</span>
          <span>
            Personal workspace<small>Local environment</small>
          </span>
          <ChevronDown size={14} />
        </div>
        <nav>
          {nav.map((item) => (
            <button
              key={item.id}
              className={screen === item.id ? "active" : ""}
              onClick={() => setScreen(item.id as Screen)}
            >
              <item.icon size={18} />
              {item.label}
              {item.id === "tools" && (
                <span className="nav-count">{tools.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-section">
          <span>YOUR NETWORKS</span>
          <button
            aria-label="New network"
            className="icon-button"
            onClick={() => {
              setNetwork(newNetwork());
              setDirty(true);
              setScreen("workspace");
              setSelected("");
            }}
          >
            <Plus size={15} />
          </button>
        </div>
        <div className="network-list">
          {[...networks]
            .sort(
              (a, b) =>
                Number(b.id === "designer-programmer") -
                Number(a.id === "designer-programmer"),
            )
            .map((n) => (
              <button
                key={n.id}
                className={
                  network.id === n.id && screen === "workspace" ? "current" : ""
                }
                onClick={() => pick(n)}
              >
                <GitBranch size={15} />
                <span>{n.name}</span>
                {n.mode === "autonomous" && <Zap size={12} />}
              </button>
            ))}
        </div>
        <div className="sidebar-bottom">
          <a href="/tutorial/" target="_blank">
            <BookOpen size={17} />
            <span>
              Getting started<small>An 18-slide walkthrough</small>
            </span>
            <ExternalLink size={13} />
          </a>
          <div className="connection">
            <span className="live-dot" />
            Running locally<span>v1.0</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Personal workspace
            <ChevronRight size={13} />
            <strong>{nav.find((n) => n.id === screen)?.label}</strong>
          </div>
          <div className="top-meta">
            <span className="local-badge">
              <ShieldCheck size={13} />
              {sessionInfo.external_access
                ? "Remote access"
                : sessionInfo.environment === "container"
                  ? "Container"
                  : "Local only"}
            </span>
            <span className="avatar">M</span>
          </div>
        </header>
        {screen === "workspace" ? (
          <>
            <section className="workspace-heading">
              <div>
                <div className="eyebrow">AGENT WORKSPACE</div>
                <div className="title-row">
                  <input
                    aria-label="Network name"
                    className="title-input"
                    value={network.name}
                    onChange={(e) =>
                      change((n) => ({ ...n, name: e.target.value }))
                    }
                  />
                  <span className="saved-label">
                    {dirty ? (
                      <>
                        <span className="unsaved-dot" />
                        Unsaved changes
                      </>
                    ) : (
                      <>
                        <CheckCircle2 size={13} />
                        Saved
                      </>
                    )}
                  </span>
                </div>
                <input
                  aria-label="Network description"
                  className="description-input"
                  placeholder="Add a description for this network"
                  value={network.description}
                  onChange={(e) =>
                    change((n) => ({ ...n, description: e.target.value }))
                  }
                />
              </div>
              <div className="heading-actions">
                <button onClick={duplicate} title="Duplicate network">
                  <Copy size={15} />
                </button>
                <button
                  onClick={() => download(network.name + ".json", network)}
                  title="Export network"
                >
                  <Download size={15} />
                </button>
                <button
                  onClick={() => importRef.current?.click()}
                  title="Import network"
                >
                  <ArrowDownToLine size={15} />
                </button>
                <button className="save-button" onClick={save} disabled={busy}>
                  <Save size={15} />
                  Save
                </button>
                <button
                  className="primary"
                  onClick={start}
                  disabled={busy || !network.agents.length}
                >
                  <Play size={15} fill="currentColor" />
                  Run network
                </button>
              </div>
            </section>
            <div className="workspace-tabs">
              <div>
                <button
                  className={tab === "design" ? "active" : ""}
                  onClick={() => setTab("design")}
                >
                  <Workflow size={15} />
                  Design
                </button>
                <button
                  className={tab === "activity" ? "active" : ""}
                  onClick={() => setTab("activity")}
                >
                  <Activity size={15} />
                  Activity{runId && <span className="tiny-dot" />}
                </button>
              </div>
              <div className="network-meta">
                <span>{network.agents.length} agents</span>
                <span>
                  {network.links.length + network.entry_agents.length}{" "}
                  connections
                </span>
                <span className="divider" />
                <select
                  aria-label="Execution mode"
                  value={network.mode}
                  onChange={(e) =>
                    change((n) => ({
                      ...n,
                      mode: e.target.value as Network["mode"],
                    }))
                  }
                >
                  <option value="workflow">Workflow</option>
                  <option value="autonomous">Autonomous</option>
                </select>
                <button
                  className="icon-button"
                  title="Run limits"
                  onClick={() => setModal("limits")}
                >
                  <Settings2 size={16} />
                </button>
              </div>
            </div>
            {tab === "design" ? (
              <div className="design-area">
                <div className="canvas-wrap">
                  <div className="canvas-toolbar">
                    <div className="add-menu">
                      <button className="add-agent" onClick={() => add()}>
                        <Plus size={16} />
                        Add agent
                      </button>
                      <select
                        aria-label="Add node type"
                        value=""
                        onChange={(e) => {
                          if (e.target.value === "library") setModal("library");
                          else add(e.target.value as Agent["kind"]);
                        }}
                      >
                        <option value="" disabled>
                          More nodes
                        </option>
                        <option value="human">Human input</option>
                        <option value="tool">Tool step</option>
                        <option value="join">Join branches</option>
                        <option value="library">Agent library</option>
                      </select>
                    </div>
                    <button
                      onClick={async () => {
                        try {
                          const v = await api(
                            "/networks/validate",
                            "POST",
                            network,
                          );
                          v.valid
                            ? notify(
                                "Network is valid" +
                                  (v.warnings.length
                                    ? ": " + v.warnings.join("; ")
                                    : ""),
                              )
                            : setError(v.errors.join("\n"));
                        } catch (e) {
                          report(e);
                        }
                      }}
                    >
                      <CheckCircle2 size={14} />
                      Validate
                    </button>
                  </div>
                  <ReactFlow
                    key={network.id}
                    nodes={nodes}
                    edges={edges}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onNodeClick={(_, node) => {
                      setSelected(node.id);
                      setEdgeId("");
                    }}
                    onEdgeClick={(_, edge) => {
                      setEdgeId(edge.id);
                      setSelected(edge.source === START ? START : "");
                    }}
                    onPaneClick={() => {
                      setSelected("");
                      setEdgeId("");
                    }}
                    fitView
                    fitViewOptions={{ padding: 0.16, maxZoom: 1 }}
                    minZoom={0.3}
                    maxZoom={1.5}
                    deleteKeyCode={["Backspace", "Delete"]}
                    proOptions={{ hideAttribution: true }}
                  >
                    <Background gap={22} size={1} color="#d5dfe1" />
                    <Controls showInteractive={false} />
                    <MiniMap
                      nodeColor="#d7eae5"
                      maskColor="rgba(246,249,249,0.7)"
                      pannable
                      zoomable
                    />
                  </ReactFlow>
                  <div className="canvas-tip">
                    <span className="live-dot" />
                    Connect handles to define communication<kbd>⌫</kbd>to delete
                  </div>
                  {!network.agents.length && (
                    <div className="empty-canvas">
                      <NetworkIcon size={40} />
                      <h2>Your next team starts here</h2>
                      <p>
                        Add an agent, choose a model, and connect your workflow.
                      </p>
                      <button className="primary" onClick={() => add()}>
                        <Plus size={15} />
                        Add your first agent
                      </button>
                    </div>
                  )}
                </div>
                <aside className="inspector">
                  {selectedAgent ? (
                    <>
                      <div className="inspector-heading">
                        <span className="node-icon">
                          <Bot size={18} />
                        </span>
                        <div>
                          <strong>{selectedAgent.name}</strong>
                          <small>Agent configuration</small>
                        </div>
                        <button
                          className="icon-button"
                          title="Delete agent"
                          onClick={() => {
                            change((n) => ({
                              ...n,
                              agents: n.agents.filter((a) => a.id !== selected),
                              links: n.links.filter(
                                (l) =>
                                  l.source !== selected &&
                                  l.target !== selected,
                              ),
                              entry_agents: n.entry_agents.filter(
                                (id) => id !== selected,
                              ),
                            }));
                            setSelected("");
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                      <div className="inspector-body">
                        <div className="section-label">IDENTITY</div>
                        <Field label="Name">
                          <input
                            value={selectedAgent.name}
                            onChange={(e) =>
                              updateAgent({ name: e.target.value })
                            }
                          />
                        </Field>
                        <Field label="Node type">
                          <select
                            value={selectedAgent.kind}
                            onChange={(e) =>
                              updateAgent({
                                kind: e.target.value as Agent["kind"],
                              })
                            }
                          >
                            <option value="agent">AI agent</option>
                            <option value="human">Human input</option>
                            <option value="tool">Tool step</option>
                            <option value="join">Join branches</option>
                          </select>
                        </Field>
                        <label className="check-row">
                          <input
                            type="checkbox"
                            checked={network.entry_agents.includes(selected)}
                            onChange={(e) =>
                              change((n) => ({
                                ...n,
                                entry_agents: e.target.checked
                                  ? [...n.entry_agents, selected]
                                  : n.entry_agents.filter(
                                      (id) => id !== selected,
                                    ),
                              }))
                            }
                          />
                          Entry agent<span>Receives the initial prompt</span>
                        </label>
                        {selectedAgent.kind === "agent" ? (
                          <>
                            <Field label="System prompt">
                              <textarea
                                rows={4}
                                value={selectedAgent.role}
                                onChange={(e) =>
                                  updateAgent({ role: e.target.value })
                                }
                              />
                            </Field>
                            <div className="section-label">MODEL</div>
                            <Field label="Provider">
                              <select
                                value={selectedAgent.provider_id}
                                onChange={(e) =>
                                  updateAgent({ provider_id: e.target.value })
                                }
                              >
                                {providers.map((p) => (
                                  <option key={p.id} value={p.id}>
                                    {p.name}
                                  </option>
                                ))}
                              </select>
                            </Field>
                            <Field label="Model name">
                              <input
                                value={selectedAgent.model}
                                onChange={(e) =>
                                  updateAgent({ model: e.target.value })
                                }
                              />
                            </Field>
                            <button
                              className="text-button"
                              onClick={async () => {
                                try {
                                  const names = await api<string[]>(
                                    `/providers/${selectedAgent.provider_id}/models`,
                                  );
                                  notify(
                                    "Available models: " + names.join(", "),
                                  );
                                } catch (e) {
                                  report(e);
                                }
                              }}
                            >
                              Discover models
                              <ArrowRight size={12} />
                            </button>
                            <div className="two-columns">
                              <Field label="Temperature">
                                <input
                                  type="number"
                                  min="0"
                                  max="2"
                                  step="0.1"
                                  value={selectedAgent.temperature}
                                  onChange={(e) =>
                                    updateAgent({
                                      temperature: Number(e.target.value),
                                    })
                                  }
                                />
                              </Field>
                              <Field label="Output tokens">
                                <input
                                  type="number"
                                  min="1"
                                  value={selectedAgent.max_tokens}
                                  onChange={(e) =>
                                    updateAgent({
                                      max_tokens: Number(e.target.value),
                                    })
                                  }
                                />
                              </Field>
                            </div>
                            <Field
                              label="Context budget"
                              hint="Conservative UTF-8 byte estimate, including output reservation."
                            >
                              <input
                                type="number"
                                value={selectedAgent.context_tokens}
                                onChange={(e) =>
                                  updateAgent({
                                    context_tokens: Number(e.target.value),
                                  })
                                }
                              />
                            </Field>
                            <div className="section-label">CAPABILITIES</div>
                            <div className="tool-checks">
                              {tools.map((t) => (
                                <label key={t.id}>
                                  <input
                                    type="checkbox"
                                    checked={selectedAgent.tools.includes(t.id)}
                                    onChange={(e) =>
                                      updateAgent({
                                        tools: e.target.checked
                                          ? [...selectedAgent.tools, t.id]
                                          : selectedAgent.tools.filter(
                                              (id) => id !== t.id,
                                            ),
                                      })
                                    }
                                  />
                                  <Terminal size={14} />
                                  <span>{t.name}</span>
                                  {t.kind === "shell" && (
                                    <small>host access</small>
                                  )}
                                </label>
                              ))}
                            </div>
                            {network.mode === "autonomous" && (
                              <>
                                <label className="check-row">
                                  <input
                                    type="checkbox"
                                    checked={selectedAgent.can_orchestrate}
                                    onChange={(e) =>
                                      updateAgent({
                                        can_orchestrate: e.target.checked,
                                      })
                                    }
                                  />
                                  Allow orchestration
                                  <span>
                                    Create agents, delegate, and change links
                                  </span>
                                </label>
                                <Field
                                  label="Topic subscriptions"
                                  hint="Comma-separated topic names"
                                >
                                  <input
                                    value={selectedAgent.topics.join(", ")}
                                    onChange={(e) =>
                                      updateAgent({
                                        topics: e.target.value
                                          .split(",")
                                          .map((s) => s.trim())
                                          .filter(Boolean),
                                      })
                                    }
                                  />
                                </Field>
                              </>
                            )}
                          </>
                        ) : selectedAgent.kind === "tool" ? (
                          <>
                            <Field label="Tool">
                              <select
                                value={selectedAgent.tool_id}
                                onChange={(e) =>
                                  updateAgent({ tool_id: e.target.value })
                                }
                              >
                                <option value="">Select a tool</option>
                                {tools.map((t) => (
                                  <option key={t.id} value={t.id}>
                                    {t.name}
                                  </option>
                                ))}
                              </select>
                            </Field>
                            <JsonField
                              label="Arguments · use ${message} for incoming text"
                              value={selectedAgent.tool_arguments}
                              onChange={(v) =>
                                updateAgent({ tool_arguments: v })
                              }
                            />
                          </>
                        ) : (
                          <p className="muted">
                            {selectedAgent.kind === "join"
                              ? "Waits for a message from every incoming predecessor, then combines them. Conditional branches should rejoin only when every branch delivers."
                              : "Execution waits for a response in the Activity tab. Human waiting time is excluded from the active-time budget."}
                          </p>
                        )}
                        <div className="section-label">EXECUTION</div>
                        <Field
                          label="Maximum visits"
                          hint="Bounds feedback loops and repeated activations."
                        >
                          <input
                            type="number"
                            min="1"
                            value={selectedAgent.max_visits}
                            onChange={(e) =>
                              updateAgent({
                                max_visits: Number(e.target.value),
                              })
                            }
                          />
                        </Field>
                        <button
                          className="full-width"
                          onClick={async () => {
                            try {
                              await api(
                                "/agents/" + selectedAgent.id,
                                "PUT",
                                selectedAgent,
                              );
                              await refresh();
                              notify("Agent saved to library");
                            } catch (e) {
                              report(e);
                            }
                          }}
                        >
                          <Save size={14} />
                          Save to agent library
                        </button>
                      </div>
                    </>
                  ) : selectedEdge ? (
                    <>
                      <div className="inspector-heading">
                        <GitBranch size={20} />
                        <strong>Communication link</strong>
                        <button
                          className="icon-button"
                          onClick={() => {
                            change((n) => ({
                              ...n,
                              links: n.links.filter((l) => l.id !== edgeId),
                            }));
                            setEdgeId("");
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                      <div className="inspector-body">
                        <p className="muted">
                          {
                            network.agents.find(
                              (a) => a.id === selectedEdge.source,
                            )?.name
                          }{" "}
                          →{" "}
                          {
                            network.agents.find(
                              (a) => a.id === selectedEdge.target,
                            )?.name
                          }
                        </p>
                        <Field
                          label="Message template"
                          hint="{message} inserts the preceding agent's output; {task} inserts the initial task."
                        >
                          <textarea
                            rows={5}
                            value={selectedEdge.template}
                            onChange={(e) =>
                              change((n) => ({
                                ...n,
                                links: n.links.map((l) =>
                                  l.id === edgeId
                                    ? { ...l, template: e.target.value }
                                    : l,
                                ),
                              }))
                            }
                          />
                        </Field>
                        <Field label="Route condition">
                          <select
                            value={selectedEdge.condition}
                            onChange={(e) =>
                              change((n) => ({
                                ...n,
                                links: n.links.map((l) =>
                                  l.id === edgeId
                                    ? { ...l, condition: e.target.value as any }
                                    : l,
                                ),
                              }))
                            }
                          >
                            {[
                              "always",
                              "contains",
                              "not_contains",
                              "equals",
                            ].map((c) => (
                              <option key={c}>{c}</option>
                            ))}
                          </select>
                        </Field>
                        {selectedEdge.condition !== "always" && (
                          <Field label="Match value">
                            <input
                              value={selectedEdge.value}
                              onChange={(e) =>
                                change((n) => ({
                                  ...n,
                                  links: n.links.map((l) =>
                                    l.id === edgeId
                                      ? { ...l, value: e.target.value }
                                      : l,
                                  ),
                                }))
                              }
                            />
                          </Field>
                        )}
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="inspector-heading">
                        <span className="node-icon">
                          <Play size={18} />
                        </span>
                        <div>
                          <strong>Start</strong>
                          <small>Initial task & first recipients</small>
                        </div>
                      </div>
                      <div className="inspector-body">
                        <Field
                          label="Initial task"
                          hint="Saved with this network. Each run sends this task to the connected first recipients."
                        >
                          <textarea
                            rows={7}
                            value={network.initial_task || ""}
                            placeholder="What should the agents accomplish?"
                            onChange={(e) =>
                              change((n) => ({
                                ...n,
                                initial_task: e.target.value,
                              }))
                            }
                          />
                        </Field>
                        <div className="section-label">FIRST RECIPIENTS</div>
                        <p className="muted">
                          Connect Start to an agent, or select recipients below.
                          Other agents receive messages through your
                          communication links.
                        </p>
                        {network.agents.map((a) => (
                          <label className="check-row" key={a.id}>
                            <input
                              type="checkbox"
                              checked={network.entry_agents.includes(a.id)}
                              onChange={(e) =>
                                change((n) => ({
                                  ...n,
                                  entry_agents: e.target.checked
                                    ? [...new Set([...n.entry_agents, a.id])]
                                    : n.entry_agents.filter(
                                        (id) => id !== a.id,
                                      ),
                                }))
                              }
                            />
                            {a.name}
                          </label>
                        ))}
                        {!network.agents.length && (
                          <p className="muted">
                            Add an agent to connect your starting point.
                          </p>
                        )}
                        {!network.entry_agents.length &&
                          !!network.agents.length && (
                            <p className="error-text">
                              Choose at least one first recipient.
                            </p>
                          )}
                      </div>
                    </>
                  )}
                </aside>
              </div>
            ) : (
              <RunView
                run={run}
                events={events}
                eventRef={eventRef}
                onControl={async (action) => {
                  try {
                    await api(`/runs/${runId}/control/${action}`, "POST");
                    setRun(await api("/runs/" + runId));
                  } catch (e) {
                    report(e);
                  }
                }}
                onHuman={async (id, text) => {
                  try {
                    await api(`/runs/${runId}/human/${id}`, "POST", {
                      message: text,
                    });
                    setRun(await api("/runs/" + runId));
                  } catch (e) {
                    report(e);
                  }
                }}
                onUseNetwork={() => {
                  if (run?.current_network) {
                    setNetwork({
                      ...run.current_network,
                      id: uid(),
                      name: run.current_network.name + " · evolved",
                    });
                    setDirty(true);
                    setTab("design");
                    notify("Evolved network loaded. Save to keep it.");
                  }
                }}
              />
            )}
            <div className="prompt-bar">
              <span className="prompt-icon">
                <MessageSquare size={18} />
              </span>
              <div>
                <label htmlFor="run-prompt">INITIAL TASK FOR NEXT RUN</label>
                <textarea
                  id="run-prompt"
                  rows={2}
                  value={network.initial_task || ""}
                  onChange={(e) =>
                    change((n) => ({ ...n, initial_task: e.target.value }))
                  }
                  placeholder="What should this agent network accomplish?"
                />
              </div>
              <span className="prompt-info">
                {network.mode === "autonomous" ? (
                  <>
                    <Zap size={14} />
                    Autonomous collaboration
                  </>
                ) : (
                  <>
                    <Workflow size={14} />
                    Directed workflow
                  </>
                )}
              </span>
              <button
                className="run-circle"
                aria-label="Run task"
                onClick={start}
                disabled={busy || !network.agents.length}
              >
                <ArrowRight size={19} />
              </button>
            </div>
          </>
        ) : screen === "tools" ? (
          <ToolsPage
            tools={tools}
            refresh={refresh}
            notify={notify}
            report={report}
          />
        ) : screen === "providers" ? (
          <ProvidersPage
            providers={providers}
            refresh={refresh}
            notify={notify}
            report={report}
          />
        ) : screen === "runs" ? (
          <section className="page">
            <div className="page-title">
              <div className="eyebrow">EXECUTION LOG</div>
              <h1>Run history</h1>
              <p>
                Every conversation, tool call, and network change stays here.
              </p>
            </div>
            <div className="data-table">
              <div className="table-header">
                <span>Network / task</span>
                <span>Status</span>
                <span>Started</span>
                <span />
              </div>
              {runs.length ? (
                runs.map((r) => (
                  <button
                    className="table-row"
                    key={r.id}
                    onClick={() => {
                      setRunId(r.id);
                      setTab("activity");
                      setScreen("workspace");
                    }}
                  >
                    <span>
                      <strong>{r.prompt.slice(0, 85)}</strong>
                      <small>{r.id}</small>
                    </span>
                    <Status status={r.status} />
                    <span>{formatTime(r.created)}</span>
                    <ChevronRight size={16} />
                  </button>
                ))
              ) : (
                <div className="empty-state">
                  Run a network to see its history here.
                </div>
              )}
            </div>
          </section>
        ) : (
          <DocsPage report={report} />
        )}
      </main>
      {notice && (
        <div className="toast">
          <CheckCircle2 size={16} />
          {notice}
        </div>
      )}
      {error && (
        <div className="error-banner">
          <strong>Something needs attention</strong>
          <pre>{error}</pre>
          <button
            className="icon-button"
            onClick={() => setError("")}
            aria-label="Dismiss error"
          >
            <X size={17} />
          </button>
        </div>
      )}
      <input
        ref={importRef}
        type="file"
        accept=".json"
        hidden
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          try {
            const n = JSON.parse(await file.text());
            await api("/networks/" + n.id, "PUT", n);
            await refresh();
            pick(n);
            notify("Network imported");
          } catch (e) {
            report(e);
          }
          e.target.value = "";
        }}
      />
      {modal === "limits" && (
        <Modal title="Run limits" onClose={() => setModal("")}>
          <p className="muted">
            These limits apply to every agent created during the run.
          </p>
          {Object.entries(network.limits).map(([key, value]) => (
            <Field key={key} label={key.replaceAll("_", " ")}>
              <input
                type="number"
                min="1"
                value={value}
                onChange={(e) =>
                  change((n) => ({
                    ...n,
                    limits: { ...n.limits, [key]: Number(e.target.value) },
                  }))
                }
              />
            </Field>
          ))}
          <button className="primary full-width" onClick={() => setModal("")}>
            Done
          </button>
        </Modal>
      )}
      {modal === "library" && (
        <Modal title="Agent library" onClose={() => setModal("")}>
          {library.length ? (
            library.map((a) => (
              <button
                key={a.id}
                className="library-row"
                onClick={() => {
                  add(a.kind, a);
                  setModal("");
                }}
              >
                <Bot size={20} />
                <span>
                  <strong>{a.name}</strong>
                  <small>{a.model}</small>
                </span>
                <Plus size={17} />
              </button>
            ))
          ) : (
            <p className="muted">
              Select an agent and choose “Save to agent library” to reuse it
              here.
            </p>
          )}
        </Modal>
      )}
    </div>
  );
}

function RunView({
  run,
  events,
  eventRef,
  onControl,
  onHuman,
  onUseNetwork,
}: {
  run: Run | null;
  events: Event[];
  eventRef: React.RefObject<HTMLDivElement | null>;
  onControl: (action: string) => void;
  onHuman: (id: string, text: string) => void;
  onUseNetwork: () => void;
}) {
  const [responses, setResponses] = useState<Record<string, string>>({}),
    [filter, setFilter] = useState("all");
  if (!run)
    return (
      <div className="empty-state activity-empty">
        <Activity size={40} />
        <h2>Your network, in motion</h2>
        <p>Run a task to watch conversations, tools, and network changes.</p>
      </div>
    );
  const messages = events.filter(
    (e) => e.kind === "message" && e.body.message.role !== "system",
  );
  const calls = events.filter((e) => e.kind === "model_call");
  const toolCalls = events.filter((e) => e.kind === "tool_completed");
  return (
    <div className="activity-area">
      <div className="run-heading">
        <div>
          <Status status={run.status} />
          <span className="mono">Run {run.id}</span>
        </div>
        <div>
          {!terminal.has(run.status) && (
            <>
              <button
                onClick={() =>
                  onControl(run.status === "paused" ? "resume" : "pause")
                }
              >
                {run.status === "paused" ? (
                  <Play size={14} />
                ) : (
                  <Pause size={14} />
                )}{" "}
                {run.status === "paused" ? "Resume" : "Pause"}
              </button>
              <button onClick={() => onControl("cancel")}>
                <Square size={13} />
                Cancel
              </button>
            </>
          )}
          <button onClick={onUseNetwork}>
            <GitBranch size={14} />
            Use evolved network
          </button>
          <select
            aria-label="Export run"
            defaultValue=""
            onChange={(e) => {
              if (e.target.value)
                window.open(
                  `/api/v1/runs/${run.id}/export/${e.target.value}`,
                  "_blank",
                );
              e.target.value = "";
            }}
          >
            <option value="" disabled>
              Export run
            </option>
            {["json", "csv", "html", "xlsx"].map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="run-metrics">
        <div>
          <small>MODEL CALLS</small>
          <strong>{calls.length}</strong>
        </div>
        <div>
          <small>TOOL CALLS</small>
          <strong>{toolCalls.length}</strong>
        </div>
        <div>
          <small>MESSAGES</small>
          <strong>{messages.length}</strong>
        </div>
        <div>
          <small>MODEL TIME</small>
          <strong>
            {calls.reduce((s, e) => s + e.body.duration, 0).toFixed(2)}
            <em>s</em>
          </strong>
        </div>
        <div>
          <small>REPORTED TOKENS</small>
          <strong>
            {calls.reduce((s, e) => s + (e.body.usage?.total_tokens || 0), 0) ||
              "—"}
          </strong>
        </div>
      </div>
      {run.error && <div className="inline-error">{run.error}</div>}
      {run.pending_human?.map((id) => (
        <div className="human-response" key={id}>
          <User size={20} />
          <div>
            <strong>
              {run.current_network?.agents.find((a) => a.id === id)?.name || id}{" "}
              needs your input
            </strong>
            <textarea
              aria-label="Human response"
              placeholder="Enter your response…"
              value={responses[id] || ""}
              onChange={(e) =>
                setResponses({ ...responses, [id]: e.target.value })
              }
            />
          </div>
          <button
            className="primary"
            onClick={() => onHuman(id, responses[id] || "")}
          >
            Send response
          </button>
        </div>
      ))}
      <div className="log-toolbar">
        <h3>Run timeline</h3>
        <div>
          {["all", "message", "tool_completed", "network_changed"].map((f) => (
            <button
              key={f}
              className={filter === f ? "selected" : ""}
              onClick={() => setFilter(f)}
            >
              {f === "all"
                ? "All events"
                : f === "message"
                  ? "Messages"
                  : f === "tool_completed"
                    ? "Tools"
                    : "Network"}
            </button>
          ))}
        </div>
      </div>
      <div className="event-list" ref={eventRef}>
        {events
          .filter((e) => filter === "all" || e.kind === filter)
          .map((event) => (
            <div className={"event " + event.kind} key={event.seq}>
              <span className="event-marker">
                {event.kind === "message" ? (
                  <MessageSquare size={14} />
                ) : event.kind.startsWith("tool") ? (
                  <Terminal size={14} />
                ) : event.kind === "network_changed" ? (
                  <GitBranch size={14} />
                ) : (
                  <Circle size={9} />
                )}
              </span>
              <div className="event-content">
                <div className="event-meta">
                  <strong>{event.kind.replaceAll("_", " ")}</strong>
                  {event.body.agent_id && (
                    <span>
                      {run.current_network?.agents.find(
                        (a) => a.id === event.body.agent_id,
                      )?.name || event.body.agent_id}
                    </span>
                  )}
                  <time>{new Date(event.at * 1000).toLocaleTimeString()}</time>
                </div>
                {event.kind === "message" ? (
                  <div className="message-content">
                    <span className="role-label">
                      {event.body.message.role}
                    </span>
                    <pre>
                      {event.body.message.content ||
                        JSON.stringify(event.body.message.tool_calls, null, 2)}
                    </pre>
                  </div>
                ) : event.kind === "tool_completed" ? (
                  <>
                    <Status
                      status={event.body.result.ok ? "completed" : "failed"}
                    />
                    <pre>
                      {event.body.result.stdout ||
                        event.body.result.stderr ||
                        event.body.result.error ||
                        JSON.stringify(event.body.result.data)}
                    </pre>
                    <div className="artifact-links">
                      {event.body.result.artifacts.map((path: string) => (
                        <a
                          key={path}
                          href={"/api/v1/artifacts/" + path}
                          target="_blank"
                        >
                          <Download size={12} />
                          {path.split(/[\\/]/).pop()}
                        </a>
                      ))}
                    </div>
                  </>
                ) : event.kind === "network_changed" ? (
                  <p>
                    {event.body.network.agents.length} agents ·{" "}
                    {event.body.network.links.length} links ·{" "}
                    {event.body.action}
                  </p>
                ) : (
                  <pre>{JSON.stringify(event.body, null, 2)}</pre>
                )}
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}

function ToolsPage({ tools, refresh, notify, report }: any) {
  const [tool, setTool] = useState<Tool | null>(null),
    [testArgs, setTestArgs] = useState("{}"),
    [testResult, setTestResult] = useState<any>(null),
    [jobs, setJobs] = useState<any[]>([]),
    [plan, setPlan] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [tab, setTab] = useState("registry"),
    [recipes, setRecipes] = useState<any[]>([]),
    [recipe, setRecipe] = useState<any>(null),
    [restorePlans, setRestorePlans] = useState<any[] | null>(null);
  const manifestInput = useRef<HTMLInputElement>(null);
  const [install, setInstall] = useState<Install>({
    manager: "pip",
    package: "",
    version: "",
    source: "",
    action: "install",
    recipe_id: "",
  });
  useEffect(() => {
    api("/recipes").then(setRecipes).catch(report);
    const poll = () => api("/installations").then(setJobs).catch(report);
    poll();
    const timer = setInterval(poll, 1500);
    return () => clearInterval(timer);
  }, []);
  const edit = (patch: Partial<Tool>) =>
    setTool((t) => (t ? { ...t, ...patch } : t));
  const save = async () => {
    if (!tool) return;
    setBusy(true);
    try {
      await api("/tools/" + tool.id, "PUT", tool);
      await refresh();
      notify("Tool saved");
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="page tools-page">
      <div className="page-title with-action">
        <div>
          <div className="eyebrow">AGENT CAPABILITIES</div>
          <h1>Tools & CLI</h1>
          <p>Give your agents the tools you already use.</p>
        </div>
        <button
          className="primary"
          onClick={() => {
            setTool(newTool());
            setTestResult(null);
          }}
        >
          <Plus size={16} />
          Register tool
        </button>
      </div>
      <div className="page-tabs">
        <button
          className={tab === "registry" ? "active" : ""}
          onClick={() => setTab("registry")}
        >
          Tool registry <span>{tools.length}</span>
        </button>
        <button
          className={tab === "install" ? "active" : ""}
          onClick={() => setTab("install")}
        >
          Install & manage
        </button>
        <button
          className={tab === "recipes" ? "active" : ""}
          onClick={() => setTab("recipes")}
        >
          Installer recipes
        </button>
      </div>
      {tab === "registry" ? (
        <>
          <div className="info-strip">
            <Terminal size={20} />
            <div>
              <strong>Any CLI. Your configuration.</strong>
              <span>
                Register an executable, map its inputs, then enable it for
                individual agents.
              </span>
            </div>
            <span className="outline-label">CLI · Python · Shell</span>
          </div>
          <div className="tool-grid">
            {tools.map((t: Tool) => (
              <button
                key={t.id}
                className="tool-card"
                onClick={() => {
                  setTool(structuredClone(t));
                  setTestResult(null);
                }}
              >
                <div>
                  <span className={"tool-icon " + t.kind}>
                    {t.kind === "compiler" ? (
                      <Box size={21} />
                    ) : t.kind === "analyzer" ? (
                      <Search size={21} />
                    ) : (
                      <Terminal size={21} />
                    )}
                  </span>
                  <span className="outline-label">{t.kind}</span>
                  <MoreHorizontal size={17} />
                </div>
                <h3>{t.name}</h3>
                <p>{t.description || t.executable || "Configure this tool"}</p>
                <footer>
                  <span className="mono">{t.executable || t.kind}</span>
                  <span>
                    {t.timeout}s timeout
                    <ChevronRight size={13} />
                  </span>
                </footer>
              </button>
            ))}
            <button
              className="tool-card add-tool-card"
              onClick={() => setTool(newTool())}
            >
              <Plus size={26} />
              <strong>Connect a tool</strong>
              <span>Executable, script, or plugin</span>
            </button>
          </div>
        </>
      ) : tab === "install" ? (
        <div className="install-layout">
          <div className="panel">
            <h3>Install a CLI tool</h3>
            <p className="muted">
              Preview the exact command before installation. Installers run only
              when you confirm.
            </p>
            <Field label="Package manager">
              <select
                value={install.manager}
                onChange={(e) =>
                  setInstall({ ...install, manager: e.target.value })
                }
              >
                {["pip", "npm", "winget", "apt", "recipe"].map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </select>
            </Field>
            <Field label="Package identifier">
              <input
                value={install.package}
                placeholder="e.g. ruff, typescript, Git.Git"
                onChange={(e) =>
                  setInstall({ ...install, package: e.target.value })
                }
              />
            </Field>
            <div className="two-columns">
              <Field label="Version (optional)">
                <input
                  value={install.version}
                  onChange={(e) =>
                    setInstall({ ...install, version: e.target.value })
                  }
                />
              </Field>
              <Field label="Action">
                <select
                  value={install.action}
                  onChange={(e) =>
                    setInstall({ ...install, action: e.target.value })
                  }
                >
                  {["install", "update", "remove"].map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
              </Field>
            </div>
            <Field label="Source / registry (optional)">
              <input
                value={install.source}
                onChange={(e) =>
                  setInstall({ ...install, source: e.target.value })
                }
              />
            </Field>
            {install.manager === "recipe" && (
              <Field label="Recipe">
                <select
                  value={install.recipe_id}
                  onChange={(e) =>
                    setInstall({ ...install, recipe_id: e.target.value })
                  }
                >
                  <option value="">Choose a recipe</option>
                  {recipes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <button
              className="primary full-width"
              disabled={busy || !install.package}
              onClick={async () => {
                try {
                  setPlan(await api("/installations/preview", "POST", install));
                } catch (e) {
                  report(e);
                }
              }}
            >
              <Search size={15} />
              Preview installation
            </button>
            <div className="install-downloads">
              <button onClick={() => manifestInput.current?.click()}>
                <ArrowDownToLine size={13} />
                Restore
              </button>
              <button
                onClick={async () =>
                  download(
                    "tool-manifest.json",
                    await api("/installations/manifest"),
                  )
                }
              >
                <Download size={13} />
                Manifest
              </button>
              <a href="/api/v1/installations/dockerfile" target="_blank">
                Image recipe
                <ExternalLink size={12} />
              </a>
            </div>
            <input
              ref={manifestInput}
              type="file"
              accept=".json"
              hidden
              onChange={async (event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                try {
                  setRestorePlans(
                    await api(
                      "/installations/restore-preview",
                      "POST",
                      JSON.parse(await file.text()),
                    ),
                  );
                } catch (error) {
                  report(error);
                }
                event.target.value = "";
              }}
            />
          </div>
          <div>
            <h3>Installation history</h3>
            {jobs.length ? (
              jobs
                .slice()
                .reverse()
                .map((job) => (
                  <details className="job" key={job.id}>
                    <summary>
                      <span>
                        <Terminal size={16} />
                        <strong>{job.request.package}</strong>
                        <small>{job.request.manager}</small>
                      </span>
                      <Status status={job.status} />
                    </summary>
                    <small>{formatTime(job.created)}</small>
                    <pre>{job.argv.join(" ")}</pre>
                    <pre>
                      {job.result?.stdout ||
                        job.result?.stderr ||
                        job.error ||
                        "Waiting for installer…"}
                    </pre>
                    {job.result?.error && (
                      <p className="error-text">{job.result.error}</p>
                    )}
                    {job.resolved_version && (
                      <p>Installed version: {job.resolved_version}</p>
                    )}
                  </details>
                ))
            ) : (
              <div className="empty-state">
                <ArrowDownToLine size={30} />
                <p>Installation jobs and their logs appear here.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="panel recipe-panel">
          <div className="with-action">
            <h3>Custom package managers</h3>
            <button
              onClick={() =>
                setRecipe({
                  id: uid(),
                  name: "Custom installer",
                  executable: "",
                  install_args: ["install", "${package}"],
                  update_args: [],
                  remove_args: [],
                  timeout: 600,
                })
              }
            >
              <Plus size={14} />
              Add recipe
            </button>
          </div>
          <p className="muted">
            Recipes call executables directly. Use ${"{package}"}, $
            {"{version}"}, and ${"{source}"} as argument values.
          </p>
          {recipes.map((r) => (
            <button
              className="library-row"
              key={r.id}
              onClick={() => setRecipe(r)}
            >
              <Terminal size={18} />
              <span>
                <strong>{r.name}</strong>
                <small>{r.executable}</small>
              </span>
              <ChevronRight size={15} />
            </button>
          ))}
        </div>
      )}
      {tool && (
        <Modal
          title={tool.name || "Register CLI tool"}
          wide
          onClose={() => setTool(null)}
        >
          <div className="tool-form-columns">
            <div>
              <div className="two-columns">
                <Field label="Tool name">
                  <input
                    value={tool.name}
                    onChange={(e) => edit({ name: e.target.value })}
                  />
                </Field>
                <Field label="Type">
                  <select
                    value={tool.kind}
                    onChange={(e) =>
                      edit({ kind: e.target.value as Tool["kind"] })
                    }
                  >
                    {["cli", "shell", "compiler", "analyzer", "python"].map(
                      (k) => (
                        <option key={k}>{k}</option>
                      ),
                    )}
                  </select>
                </Field>
              </div>
              <Field label="Description for the model">
                <textarea
                  rows={2}
                  value={tool.description}
                  onChange={(e) => edit({ description: e.target.value })}
                />
              </Field>
              {tool.kind === "python" ? (
                <Field label="Installed plugin entry-point name">
                  <input
                    value={tool.plugin}
                    onChange={(e) => edit({ plugin: e.target.value })}
                  />
                </Field>
              ) : (
                <>
                  <Field
                    label="Executable or interpreter"
                    hint="Use @python for this app's Python. Scripts need an explicit interpreter."
                  >
                    <input
                      className="mono"
                      value={tool.executable}
                      placeholder={
                        tool.kind === "shell"
                          ? "Default platform shell"
                          : "e.g. git, python, C:\\tools\\mytool.exe"
                      }
                      onChange={(e) => edit({ executable: e.target.value })}
                    />
                  </Field>
                  <Field
                    label="Argument templates · one argument per line"
                    hint="${name} substitutes an input. Quotes, spaces, and shell characters remain literal."
                  >
                    <textarea
                      className="code"
                      rows={4}
                      value={tool.args.join("\n")}
                      onChange={(e) =>
                        edit({ args: e.target.value.split("\n") })
                      }
                    />
                  </Field>
                </>
              )}
              <JsonField
                label="Input schema"
                value={tool.input_schema}
                onChange={(v) => edit({ input_schema: v })}
              />
              <Field label="Standard input template">
                <textarea
                  className="code"
                  rows={2}
                  value={tool.stdin}
                  onChange={(e) => edit({ stdin: e.target.value })}
                />
              </Field>
              <Field
                label="Working directory (optional)"
                hint="Empty uses an isolated run workspace."
              >
                <input
                  value={tool.cwd}
                  onChange={(e) => edit({ cwd: e.target.value })}
                />
              </Field>
              <JsonField
                label="Environment references · variable → host variable"
                value={tool.env}
                onChange={(v) => edit({ env: v })}
              />
            </div>
            <div>
              <div className="section-label">EXECUTION SETTINGS</div>
              <div className="two-columns">
                <Field label="Timeout (seconds)">
                  <input
                    type="number"
                    value={tool.timeout}
                    onChange={(e) => edit({ timeout: Number(e.target.value) })}
                  />
                </Field>
                <Field label="Output character limit">
                  <input
                    type="number"
                    value={tool.max_output}
                    onChange={(e) =>
                      edit({ max_output: Number(e.target.value) })
                    }
                  />
                </Field>
              </div>
              <Field label="Accepted exit codes">
                <input
                  value={tool.accepted_exit_codes.join(", ")}
                  onChange={(e) =>
                    edit({
                      accepted_exit_codes: e.target.value
                        .split(",")
                        .map(Number),
                    })
                  }
                />
              </Field>
              <Field label="Output format">
                <select
                  value={tool.output_format}
                  onChange={(e) =>
                    edit({
                      output_format: e.target.value as Tool["output_format"],
                    })
                  }
                >
                  {["text", "json", "artifact"].map((f) => (
                    <option key={f}>{f}</option>
                  ))}
                </select>
              </Field>
              <Field label="Artifact patterns · one per line">
                <textarea
                  className="code"
                  rows={2}
                  placeholder="reports/*.json"
                  value={tool.artifacts.join("\n")}
                  onChange={(e) =>
                    edit({
                      artifacts: e.target.value.split("\n").filter(Boolean),
                    })
                  }
                />
              </Field>
              <Field label="Version arguments · one per line">
                <textarea
                  className="code"
                  rows={2}
                  value={tool.version_args.join("\n")}
                  onChange={(e) =>
                    edit({
                      version_args: e.target.value.split("\n").filter(Boolean),
                    })
                  }
                />
              </Field>
              <div className="section-label">TEST YOUR TOOL</div>
              <Field label="Test arguments (JSON)">
                <textarea
                  className="code"
                  rows={3}
                  value={testArgs}
                  onChange={(e) => setTestArgs(e.target.value)}
                />
              </Field>
              <div className="button-row">
                <button
                  disabled={busy}
                  onClick={async () => {
                    try {
                      await save();
                      setTestResult(
                        await api("/tools/" + tool.id + "/availability"),
                      );
                    } catch (e) {
                      report(e);
                    }
                  }}
                >
                  <CheckCircle2 size={14} />
                  Check
                </button>
                <button
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await api("/tools/" + tool.id, "PUT", tool);
                      await refresh();
                      setTestResult(
                        await api(
                          "/tools/" + tool.id + "/test",
                          "POST",
                          JSON.parse(testArgs),
                        ),
                      );
                    } catch (e) {
                      report(e);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <Play size={14} />
                  Test
                </button>
              </div>
              {testResult && (
                <div className="test-result">
                  <pre>{JSON.stringify(testResult, null, 2)}</pre>
                  {testResult.artifacts?.map((p: string) => (
                    <a key={p} href={"/api/v1/artifacts/" + p} target="_blank">
                      Download {p.split(/[\\/]/).pop()}
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="modal-footer">
            <button
              className="danger-text"
              onClick={async () => {
                if (window.confirm("Delete this tool registration?"))
                  try {
                    await api("/tools/" + tool.id, "DELETE");
                    await refresh();
                    setTool(null);
                  } catch (e) {
                    report(e);
                  }
              }}
            >
              <Trash2 size={14} />
              Delete
            </button>
            <button className="primary" disabled={busy} onClick={save}>
              <Save size={15} />
              Save tool
            </button>
          </div>
        </Modal>
      )}
      {plan && (
        <Modal title="Review installation" onClose={() => setPlan(null)}>
          <p>
            Run this command on the <strong>{plan.environment}</strong>?
          </p>
          <pre className="command-preview">
            {plan.argv
              .map((a: string) => (/\s/.test(a) ? JSON.stringify(a) : a))
              .join(" ")}
          </pre>
          <p className="muted">{plan.agreements}</p>
          <div className="modal-footer">
            <button onClick={() => setPlan(null)}>Cancel</button>
            <button
              className="primary"
              onClick={async () => {
                setBusy(true);
                try {
                  await api("/installations", "POST", {
                    request: plan.request,
                    confirmation: plan.confirmation,
                  });
                  setPlan(null);
                  notify("Installation queued");
                } catch (e) {
                  report(e);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Confirm {plan.request.action}
            </button>
          </div>
        </Modal>
      )}
      {restorePlans && (
        <Modal
          title="Review tool restoration"
          onClose={() => setRestorePlans(null)}
        >
          <p className="muted">
            Review each command. Restoring packages runs their installers in
            this environment.
          </p>
          {restorePlans.map((item, index) => (
            <pre key={index} className="command-preview">
              {item.argv
                .map((arg: string) =>
                  /\s/.test(arg) ? JSON.stringify(arg) : arg,
                )
                .join(" ")}
            </pre>
          ))}
          <div className="modal-footer">
            <button onClick={() => setRestorePlans(null)}>Cancel</button>
            <button
              className="primary"
              disabled={busy || !restorePlans.length}
              onClick={async () => {
                setBusy(true);
                try {
                  for (const item of restorePlans)
                    await api("/installations", "POST", {
                      request: item.request,
                      confirmation: item.confirmation,
                    });
                  setRestorePlans(null);
                  notify("Restoration jobs queued");
                } catch (error) {
                  report(error);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Restore {restorePlans.length} packages
            </button>
          </div>
        </Modal>
      )}
      {recipe && (
        <Modal title="Installer recipe" onClose={() => setRecipe(null)}>
          <Field label="Name">
            <input
              value={recipe.name}
              onChange={(e) => setRecipe({ ...recipe, name: e.target.value })}
            />
          </Field>
          <Field label="Executable">
            <input
              value={recipe.executable}
              onChange={(e) =>
                setRecipe({ ...recipe, executable: e.target.value })
              }
            />
          </Field>
          {["install_args", "update_args", "remove_args"].map((key) => (
            <JsonField
              key={key}
              label={key.replaceAll("_", " ")}
              value={recipe[key]}
              onChange={(value) => setRecipe({ ...recipe, [key]: value })}
            />
          ))}
          <button
            className="primary full-width"
            onClick={async () => {
              try {
                await api("/recipes/" + recipe.id, "PUT", recipe);
                setRecipes(await api("/recipes"));
                setRecipe(null);
              } catch (e) {
                report(e);
              }
            }}
          >
            Save recipe
          </button>
        </Modal>
      )}
    </section>
  );
}

function ProvidersPage({ providers, refresh, notify, report }: any) {
  const [edit, setEdit] = useState<Provider | null>(null),
    [model, setModel] = useState(""),
    [result, setResult] = useState<any>(null),
    [busy, setBusy] = useState(false);
  return (
    <section className="page">
      <div className="page-title with-action">
        <div>
          <div className="eyebrow">INFERENCE CONNECTIONS</div>
          <h1>Model providers</h1>
          <p>
            Connect local or remote chat-completion servers. Keep your keys in
            environment variables.
          </p>
        </div>
        <button
          className="primary"
          onClick={() => {
            setEdit({
              id: uid(),
              name: "New provider",
              kind: "http",
              endpoint: "http://localhost:11434/v1/chat/completions",
              api_key_env: "",
              supports_tools: false,
              timeout: 300,
              retries: 2,
              concurrency: 2,
            });
            setResult(null);
          }}
        >
          <Plus size={16} />
          Add provider
        </button>
      </div>
      <div className="tool-grid">
        {providers.map((p: Provider) => (
          <button
            className="tool-card"
            key={p.id}
            onClick={() => {
              setEdit(structuredClone(p));
              setResult(null);
            }}
          >
            <div>
              <span className="tool-icon">
                <Box size={22} />
              </span>
              <span className="outline-label">{p.kind}</span>
            </div>
            <h3>{p.name}</h3>
            <p>
              {p.kind === "demo"
                ? "Deterministic demo. No credentials or model server needed."
                : p.endpoint}
            </p>
            <footer>
              <span>
                {p.supports_tools ? "Tool calling enabled" : "Chat completions"}
              </span>
              <ChevronRight size={14} />
            </footer>
          </button>
        ))}
      </div>
      {edit && (
        <Modal title="Provider configuration" onClose={() => setEdit(null)}>
          <Field label="Name">
            <input
              value={edit.name}
              onChange={(e) => setEdit({ ...edit, name: e.target.value })}
            />
          </Field>
          <Field label="Type">
            <select
              value={edit.kind}
              onChange={(e) =>
                setEdit({ ...edit, kind: e.target.value as Provider["kind"] })
              }
            >
              <option value="http">Compatible HTTP server</option>
              <option value="demo">Deterministic demo</option>
            </select>
          </Field>
          <Field label="Chat-completion endpoint">
            <input
              value={edit.endpoint}
              onChange={(e) => setEdit({ ...edit, endpoint: e.target.value })}
            />
          </Field>
          <Field
            label="API key environment variable"
            hint="The key value is read by the backend and never exported."
          >
            <input
              value={edit.api_key_env}
              placeholder="OPENAI_API_KEY"
              onChange={(e) =>
                setEdit({ ...edit, api_key_env: e.target.value })
              }
            />
          </Field>
          <label className="check-row">
            <input
              type="checkbox"
              checked={edit.supports_tools}
              onChange={(e) =>
                setEdit({ ...edit, supports_tools: e.target.checked })
              }
            />
            Server/model supports tool calling
            <span>Required for autonomous orchestration</span>
          </label>
          <div className="three-columns">
            {(["timeout", "retries", "concurrency"] as const).map((key) => (
              <Field key={key} label={key}>
                <input
                  type="number"
                  value={edit[key]}
                  onChange={(e) =>
                    setEdit({ ...edit, [key]: Number(e.target.value) })
                  }
                />
              </Field>
            ))}
          </div>
          <Field label="Model for connection test">
            <input
              placeholder="Enter a model served by this endpoint"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </Field>
          {result && (
            <pre className="test-result">{JSON.stringify(result, null, 2)}</pre>
          )}
          <div className="modal-footer">
            <button
              className="danger-text"
              onClick={async () => {
                if (window.confirm("Remove this provider?"))
                  try {
                    await api("/providers/" + edit.id, "DELETE");
                    await refresh();
                    setEdit(null);
                  } catch (e) {
                    report(e);
                  }
              }}
            >
              <Trash2 size={14} />
              Remove
            </button>
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api("/providers/" + edit.id, "PUT", edit);
                  setResult(
                    await api("/providers/" + edit.id + "/test", "POST", {
                      model: model || "demo",
                    }),
                  );
                  await refresh();
                } catch (e) {
                  report(e);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <Zap size={14} />
              Test
            </button>
            <button
              disabled={busy}
              className="primary"
              onClick={async () => {
                try {
                  await api("/providers/" + edit.id, "PUT", edit);
                  await refresh();
                  notify("Provider saved");
                } catch (e) {
                  report(e);
                }
              }}
            >
              <Save size={14} />
              Save
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}

function DocsPage({ report }: any) {
  const [names, setNames] = useState<string[]>([]),
    [selected, setSelected] = useState("architecture.md"),
    [text, setText] = useState("");
  useEffect(() => {
    api<string[]>("/docs").then(setNames).catch(report);
  }, []);
  useEffect(() => {
    fetch("/api/v1/docs/" + selected)
      .then((r) => r.text())
      .then(setText)
      .catch(report);
  }, [selected]);
  return (
    <section className="page docs-page">
      <div className="page-title">
        <div className="eyebrow">REFERENCE LIBRARY</div>
        <h1>Documentation</h1>
        <p>
          Architecture, deployment, tool development, and the decisions behind
          the framework.
        </p>
      </div>
      <div className="docs-layout">
        <div>
          {names.map((name) => (
            <button
              key={name}
              className={selected === name ? "active" : ""}
              onClick={() => setSelected(name)}
            >
              <BookOpen size={15} />
              {name.replace(".md", "").replaceAll("-", " ")}
            </button>
          ))}
          <a href="/tutorial/" target="_blank">
            <Play size={15} />
            Usage presentation
            <ExternalLink size={12} />
          </a>
          <a href="/docs" target="_blank">
            <FileJson size={15} />
            OpenAPI reference
            <ExternalLink size={12} />
          </a>
        </div>
        <article className="markdown">
          <ReactMarkdown>{text}</ReactMarkdown>
        </article>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
