import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  Activity, Cpu, Database, Zap, Shield, RefreshCw,
  Trash2, Lock, Terminal, BarChart2, Layers, Search, CheckCircle2,
  AlertTriangle, Clock, Server, HardDrive, ArrowUpRight
} from "lucide-react";
import AdminGuard from "../components/AdminGuard";
import { fetchAdminMetrics, clearAdminLogs } from "../api/telemetry";

function AdminDashboardContent() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [activeLogFilter, setActiveLogFilter] = useState("ALL");
  const [logSearch, setLogSearch] = useState("");

  const passcode = sessionStorage.getItem("synapse_admin_passcode") || "";
  const timerRef = useRef(null);

  const loadMetrics = async () => {
    try {
      const data = await fetchAdminMetrics(passcode);
      setMetrics(data);
      setError("");
    } catch (err) {
      setError(err.message || "Failed to load telemetry metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();

    if (autoRefresh) {
      timerRef.current = setInterval(loadMetrics, 3000);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [autoRefresh]);

  const handleClearLogs = async () => {
    try {
      await clearAdminLogs(passcode);
      loadMetrics();
    } catch (err) {
      alert("Failed to clear logs: " + err.message);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem("synapse_admin_passcode");
    window.location.reload();
  };

  if (loading && !metrics) {
    return (
      <div className="grafana-loading-container">
        <RefreshCw size={32} className="spin-icon text-cyan" />
        <span>Initializing Grafana Telemetry Stream...</span>
      </div>
    );
  }

  const logs = metrics?.logs || [];
  const filteredLogs = logs.filter((log) => {
    const matchesCategory = activeLogFilter === "ALL" || log.category === activeLogFilter;
    const matchesSearch =
      !logSearch ||
      log.message.toLowerCase().includes(logSearch.toLowerCase()) ||
      log.category.toLowerCase().includes(logSearch.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const stageDurations = metrics?.avg_stage_latencies_s || {};
  const stageEntries = Object.entries(stageDurations);
  const maxStageDuration = Math.max(...Object.values(stageDurations), 1);

  const providerCalls = metrics?.provider_calls || {};

  return (
    <div className="grafana-dashboard">
      {/* HEADER BAR */}
      <header className="grafana-header">
        <div className="grafana-header-left">
          <div className="grafana-brand-logo">
            <Activity className="pulse-icon text-cyan" size={22} />
            <span className="brand-text">SynapseAI</span>
            <span className="dashboard-pill">GRAFANA TELEMETRY v2.4</span>
          </div>
          <div className="system-health-badge healthy">
            <span className="dot"></span>
            <span>SYSTEM OPERATIONAL</span>
          </div>
        </div>

        <div className="grafana-header-right">
          <button
            className={`grafana-toggle-btn ${autoRefresh ? "active" : ""}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
            title="Toggle Live 3-second auto refresh"
          >
            <RefreshCw size={13} className={autoRefresh ? "spin-icon" : ""} />
            <span>{autoRefresh ? "Live 3s Refresh ON" : "Paused"}</span>
          </button>

          <button className="grafana-action-btn" onClick={loadMetrics}>
            <RefreshCw size={13} />
            <span>Refresh Now</span>
          </button>

          <button className="grafana-action-btn danger" onClick={handleLogout}>
            <Lock size={13} />
            <span>Lock Dashboard</span>
          </button>
        </div>
      </header>

      {error && (
        <div className="grafana-error-alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* KPI METRIC CARDS ROW */}
      <div className="grafana-kpi-grid">
        <motion.div className="grafana-card kpi-card" whileHover={{ y: -2 }}>
          <div className="kpi-header">
            <span className="kpi-title">TOTAL RESEARCH RUNS</span>
            <Server size={16} className="text-muted" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-number">{metrics?.total_research_runs || 0}</span>
            <span className="kpi-unit">runs</span>
          </div>
          <div className="kpi-footer">
            <span>Cache Hits: {metrics?.cache_hits || 0} | Misses: {metrics?.cache_misses || 0}</span>
          </div>
        </motion.div>

        <motion.div className="grafana-card kpi-card" whileHover={{ y: -2 }}>
          <div className="kpi-header">
            <span className="kpi-title">LLM INFERENCE CALLS</span>
            <Cpu size={16} className="text-purple" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-number">{metrics?.llm_calls || 0}</span>
            <span className="kpi-unit">calls</span>
          </div>
          <div className="kpi-footer">
            <span>Total Tokens: {(metrics?.llm_total_tokens || 0).toLocaleString()}</span>
          </div>
        </motion.div>

        <motion.div className="grafana-card kpi-card" whileHover={{ y: -2 }}>
          <div className="kpi-header">
            <span className="kpi-title">ESTIMATED LLM TOKENS</span>
            <Zap size={16} className="text-amber" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-number">{(metrics?.llm_total_tokens || 0).toLocaleString()}</span>
            <span className="kpi-unit">tok</span>
          </div>
          <div className="kpi-footer">
            <span>Prompt: {(metrics?.llm_prompt_tokens || 0).toLocaleString()} | Compl: {(metrics?.llm_completion_tokens || 0).toLocaleString()}</span>
          </div>
        </motion.div>

        <motion.div className="grafana-card kpi-card" whileHover={{ y: -2 }}>
          <div className="kpi-header">
            <span className="kpi-title">CACHE HIT RATE</span>
            <Database size={16} className="text-emerald" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-number">{metrics?.cache_hit_rate_pct || 0}%</span>
            <span className="kpi-unit">hits</span>
          </div>
          <div className="kpi-footer">
            <span>Stored Topics: {metrics?.cached_topics_count || 0}</span>
          </div>
        </motion.div>

        <motion.div className="grafana-card kpi-card" whileHover={{ y: -2 }}>
          <div className="kpi-header">
            <span className="kpi-title">AVG PIPELINE LATENCY</span>
            <Clock size={16} className="text-cyan" />
          </div>
          <div className="kpi-value-row">
            <span className="kpi-number">{metrics?.avg_pipeline_duration_s || 0}s</span>
            <span className="kpi-unit">sec</span>
          </div>
          <div className="kpi-footer">
            <span>Cache File: {metrics?.cache_file_size_kb || 0} KB</span>
          </div>
        </motion.div>
      </div>

      {/* ROW 2: LLM & SEARCH TELEMETRY GRID */}
      <div className="grafana-two-col-grid">
        {/* PANEL: LLM USAGE BREAKDOWN */}
        <div className="grafana-card panel-card">
          <div className="panel-header">
            <div className="panel-title">
              <Cpu size={16} className="text-purple" />
              <span>LLM Usage & Token Analytics</span>
            </div>
            <span className="panel-badge">Groq / Gemini Multi-LLM</span>
          </div>

          <div className="llm-stats-container">
            <div className="token-progress-bar-wrapper">
              <div className="token-label-row">
                <span>Prompt Tokens: {(metrics?.llm_prompt_tokens || 0).toLocaleString()}</span>
                <span>Completion Tokens: {(metrics?.llm_completion_tokens || 0).toLocaleString()}</span>
              </div>
              <div className="token-progress-bar">
                <div
                  className="token-bar-fill prompt"
                  style={{
                    width: `${
                      metrics?.llm_total_tokens
                        ? ((metrics.llm_prompt_tokens / metrics.llm_total_tokens) * 100).toFixed(1)
                        : 50
                    }%`,
                  }}
                ></div>
                <div
                  className="token-bar-fill completion"
                  style={{
                    width: `${
                      metrics?.llm_total_tokens
                        ? ((metrics.llm_completion_tokens / metrics.llm_total_tokens) * 100).toFixed(1)
                        : 50
                    }%`,
                  }}
                ></div>
              </div>
            </div>

            <div className="llm-meta-table">
              <div className="meta-row">
                <span className="meta-key">Primary Provider</span>
                <span className="meta-val highlight">Groq (gpt-oss-120b)</span>
              </div>
              <div className="meta-row">
                <span className="meta-key">Fallback Providers</span>
                <span className="meta-val">Gemini 1.5 Flash / OpenRouter</span>
              </div>
              <div className="meta-row">
                <span className="meta-key">Total Invocations</span>
                <span className="meta-val">{metrics?.llm_calls || 0} calls</span>
              </div>
              <div className="meta-row">
                <span className="meta-key">Avg Tokens per Call</span>
                <span className="meta-val">
                  {metrics?.llm_calls ? Math.round(metrics.llm_total_tokens / metrics.llm_calls) : 0} tokens/call
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* PANEL: SEARCH PROVIDER FALLOVER MATRIX */}
        <div className="grafana-card panel-card">
          <div className="panel-header">
            <div className="panel-title">
              <BarChart2 size={16} className="text-amber" />
              <span>Multi-Provider Search Failover Matrix</span>
            </div>
            <span className="panel-badge">Tavily → Serper → DDG</span>
          </div>

          <div className="provider-matrix-list">
            {["tavily", "serper", "duckduckgo", "jina_reader"].map((provKey) => {
              const pData = providerCalls[provKey] || { success: 0, fail: 0 };
              const total = pData.success + pData.fail;
              const succPct = total > 0 ? ((pData.success / total) * 100).toFixed(0) : 0;
              const displayName =
                provKey === "tavily"
                  ? "Tavily AI Search (Primary)"
                  : provKey === "serper"
                  ? "Serper Google Search (Secondary)"
                  : provKey === "duckduckgo"
                  ? "DuckDuckGo HTML Scraper (Fallback)"
                  : "Jina Reader Cloud API (Bypass)";

              return (
                <div key={provKey} className="provider-matrix-item">
                  <div className="prov-info-top">
                    <span className="prov-name">{displayName}</span>
                    <span className="prov-score">
                      {pData.success} Success | {pData.fail} Fail
                    </span>
                  </div>
                  <div className="prov-bar-track">
                    <div
                      className="prov-bar-fill success"
                      style={{ width: `${succPct}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ROW 3: AGENTIC STAGE TIMING & LATENCY */}
      <div className="grafana-card panel-card full-width">
        <div className="panel-header">
          <div className="panel-title">
            <Layers size={16} className="text-cyan" />
            <span>8-Agent Pipeline Execution Latency Visualizer</span>
          </div>
          <span className="panel-badge">Average Seconds per Stage</span>
        </div>

        <div className="stage-visualizer-grid">
          {[
            { key: "smart_search", label: "1. SMART SEARCH", color: "#3b82f6" },
            { key: "scraping", label: "2. URL SCRAPING", color: "#06b6d4" },
            { key: "reasoning", label: "3. REASONING AGENT", color: "#8b5cf6" },
            { key: "evidence_extraction", label: "4. EVIDENCE EXTRACTION", color: "#ec4899" },
            { key: "grounding", label: "5. EVIDENCE GROUNDING", color: "#10b981" },
            { key: "insight_generation", label: "6. INSIGHT GENERATION", color: "#f59e0b" },
            { key: "report_writer", label: "7. REPORT WRITER", color: "#6366f1" },
            { key: "critic_improver", label: "8. CRITIC & IMPROVER", color: "#14b8a6" }
          ].map((agent) => {
            const dur = stageDurations[agent.key] || 0.0;
            const pct = maxStageDuration > 0 && dur > 0 ? Math.min(100, Math.max(8, ((dur / maxStageDuration) * 100))) : 0;
            return (
              <div key={agent.key} className="stage-bar-card">
                <div className="stage-bar-header">
                  <span className="stage-name">{agent.label}</span>
                  <span className="stage-dur" style={{ color: dur > 0 ? agent.color : "#71717a" }}>
                    {dur > 0 ? `${dur}s` : "0.0s"}
                  </span>
                </div>
                <div className="stage-track">
                  <div
                    className="stage-fill"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: agent.color
                    }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ROW 4: REAL-TIME LOG MONITOR & TERMINAL STREAM */}
      <div className="grafana-card panel-card full-width log-terminal-panel">
        <div className="panel-header">
          <div className="panel-title">
            <Terminal size={16} className="text-emerald" />
            <span>Real-Time System & Telemetry Log Stream</span>
            <span className="log-count-pill">{filteredLogs.length} events</span>
          </div>

          <div className="log-actions-bar">
            <div className="log-filter-pills">
              {["ALL", "LLM", "SEARCH", "PIPELINE", "CACHE", "WARN", "ERROR"].map((cat) => (
                <button
                  key={cat}
                  className={`log-pill ${activeLogFilter === cat ? "active" : ""}`}
                  onClick={() => setActiveLogFilter(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="log-search-input">
              <Search size={12} />
              <input
                placeholder="Search logs..."
                value={logSearch}
                onChange={(e) => setLogSearch(e.target.value)}
              />
            </div>

            <button className="clear-logs-btn" onClick={handleClearLogs} title="Clear telemetry logs">
              <Trash2 size={12} />
              <span>Clear</span>
            </button>
          </div>
        </div>

        <div className="terminal-window">
          {filteredLogs.length === 0 ? (
            <div className="terminal-empty">No telemetry events recorded yet.</div>
          ) : (
            filteredLogs.map((log) => {
              const levelClass =
                log.level === "ERROR"
                  ? "lvl-error"
                  : log.level === "WARN"
                  ? "lvl-warn"
                  : log.level === "SUCCESS"
                  ? "lvl-success"
                  : "lvl-info";

              return (
                <div key={log.id} className="terminal-row">
                  <span className="log-time">[{log.timestamp}]</span>
                  <span className={`log-badge ${levelClass}`}>{log.level}</span>
                  <span className="log-cat">[{log.category}]</span>
                  <span className="log-msg">{log.message}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

function AdminDashboard() {
  return (
    <AdminGuard>
      <AdminDashboardContent />
    </AdminGuard>
  );
}

export default AdminDashboard;
