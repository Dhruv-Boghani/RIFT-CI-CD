"use client";

import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  Activity,
  Shield,
  Zap,
  GitBranch,
  Terminal,
  CheckCircle,
  XCircle,
  Clock,
  Award,
  Hammer,
  AlertTriangle,
  Loader2,
  Lock,
  Key,
} from "lucide-react";

const API_URL = "https://rift-ci-cd.onrender.com";
// const API_URL = "http://localhost:8000";
// const API_URL = "https://dhruvboghani-rift.hf.space";
// --- Components ---

const StatusBadge = ({ status }: { status: string }) => {
  const styles = {
    PASSED: "bg-green-900/50 text-green-400 border-green-700",
    FAILED: "bg-red-900/50 text-red-400 border-red-700",
    PENDING: "bg-yellow-900/50 text-yellow-400 border-yellow-700",
    RUNNING: "bg-blue-900/50 text-blue-400 border-blue-700 animate-pulse",
    ERROR: "bg-red-900/50 text-red-400 border-red-700",
  };
  const s = status as keyof typeof styles;
  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-bold border ${styles[s] || styles.PENDING}`}
    >
      {status}
    </span>
  );
};

export default function Dashboard() {
  const [authMode, setAuthMode] = useState<"https" | "ssh">("https");

  const [formData, setFormData] = useState({
    repo_url: "",
    team_name: "",
    leader_name: "",
    github_token: "",
    private_key: "",
  });

  const [status, setStatus] = useState<any>({
    status: "IDLE",
    logs: [],
    final_status: "PENDING",
    score: 100,
    time_taken: "0s",
    iteration: 0,
    max_iterations: 5,
    fixes_applied: [],
    total_failures: 0,
    branch_name: "---",
    auth_mode: "https",
  });

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await axios.get(`${API_URL}/status`);
        setStatus(res.data);
      } catch (e) {
        console.error("Polling error", e);
      }
    };

    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);



  const [vercelToken, setVercelToken] = useState("");
  const [vercelLogs, setVercelLogs] = useState<{
    status: string;
    deployment: any;
    logs: string[];
    loading: boolean;
  } | null>(null);

  const checkVercelDeployment = async (repoUrl: string) => {
    if (!vercelToken && !repoUrl) return;

    setVercelLogs({
      status: "loading",
      deployment: null,
      logs: [],
      loading: true,
    });

    try {
      const res = await axios.get(`${API_URL}/vercel-logs`, {
        params: { repo_url: repoUrl, vercel_token: vercelToken },
      });

      if (res.data.status === "not_found") {
        setVercelLogs(null); // No deployment, don't show anything
      } else {
        setVercelLogs({
          status: "found",
          deployment: res.data.deployment,
          logs: res.data.logs || [],
          loading: false,
        });
      }
    } catch (e) {
      console.error("Vercel check failed", e);
      setVercelLogs(null);
    }
  };

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (authMode === "https" && !formData.github_token) {
      alert("Please enter a GitHub Token for HTTPS mode.");
      return;
    }
    if (authMode === "ssh" && !formData.private_key) {
      alert("Please enter a Private Key for SSH mode.");
      return;
    }

    // Check Vercel Deployment in background
    checkVercelDeployment(formData.repo_url);

    try {
      await axios.post(`${API_URL}/start-autonomous-run`, {
        ...formData,
        auth_mode: authMode,
      });
    } catch (err: any) {
      alert(
        "Failed to start agent: " + (err.response?.data?.detail || err.message),
      );
    }
  };

  const isRunning = status.status === "RUNNING";

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-200 font-sans selection:bg-blue-500/30">
      {/* Navbar */}
      <nav className="border-b border-slate-800 bg-[#1e293b]/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-emerald-400" />
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
              RIFT 2026: Autonomous Healing Agent
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span className="flex items-center gap-1">
              <Terminal size={14} /> v2.2.0 (Vercel Integration)
            </span>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Inputs & Score - Span 4 */}
        <div className="lg:col-span-4 space-y-6">
          {/* Input Panel */}
          <div className="bg-[#1e293b] rounded-xl border border-slate-700 shadow-xl overflow-hidden">
            <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex items-center gap-2 justify-between">
              <div className="flex items-center gap-2">
                <Activity className="text-blue-400" size={18} />
                <h2 className="font-semibold text-slate-100">Configuration</h2>
              </div>

              {/* Auth Mode Toggle */}
              <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-700">
                <button
                  type="button"
                  onClick={() => setAuthMode("https")}
                  disabled={isRunning}
                  className={`px-3 py-1 rounded text-xs font-bold flex items-center gap-1 transition-all ${authMode === "https" ? "bg-blue-600 text-white shadow" : "text-slate-400 hover:text-slate-200"}`}
                >
                  <Lock size={10} /> HTTPS
                </button>
                <button
                  type="button"
                  onClick={() => setAuthMode("ssh")}
                  disabled={isRunning}
                  className={`px-3 py-1 rounded text-xs font-bold flex items-center gap-1 transition-all ${authMode === "ssh" ? "bg-purple-600 text-white shadow" : "text-slate-400 hover:text-slate-200"}`}
                >
                  <Key size={10} /> SSH
                </button>
              </div>
            </div>

            <div className="p-6">
              <form onSubmit={handleRun} className="space-y-4">
                <div>
                  <label className="text-xs font-mono text-slate-400 uppercase">
                    Repository URL {authMode === "ssh" ? "(SSH)" : "(HTTPS)"}
                  </label>
                  <input
                    className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm focus:border-blue-500 outline-none transition-colors font-mono"
                    placeholder={
                      authMode === "ssh"
                        ? "git@github.com:user/repo.git"
                        : "https://github.com/user/repo"
                    }
                    value={formData.repo_url}
                    onChange={(e) =>
                      setFormData({ ...formData, repo_url: e.target.value })
                    }
                    disabled={isRunning}
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-mono text-slate-400 uppercase">
                      Team Name
                    </label>
                    <input
                      className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm focus:border-blue-500 outline-none"
                      placeholder="Team Alpha"
                      value={formData.team_name}
                      onChange={(e) =>
                        setFormData({ ...formData, team_name: e.target.value })
                      }
                      disabled={isRunning}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-xs font-mono text-slate-400 uppercase">
                      Leader Name
                    </label>
                    <input
                      className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm focus:border-blue-500 outline-none"
                      placeholder="John Doe"
                      value={formData.leader_name}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          leader_name: e.target.value,
                        })
                      }
                      disabled={isRunning}
                      required
                    />
                  </div>
                </div>

                {/* Dynamic Auth Fields */}
                {authMode === "https" ? (
                  <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                    <label className="text-xs font-mono text-slate-400 uppercase flex items-center gap-1">
                      <Lock size={10} /> GitHub Token
                    </label>
                    <input
                      type="password"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm focus:border-blue-500 outline-none"
                      placeholder="github_pat_..."
                      value={formData.github_token}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          github_token: e.target.value,
                        })
                      }
                      disabled={isRunning}
                    />
                  </div>
                ) : (
                  <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
                    <div>
                      <label className="text-xs font-mono text-slate-400 uppercase flex items-center gap-1">
                        <Key size={10} /> Private Key (PEM/OpenSSH)
                      </label>
                      <textarea
                        className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-xs font-mono focus:border-purple-500 outline-none h-24 resize-none"
                        placeholder="-----BEGIN OPENSSH PRIVATE KEY-----..."
                        value={formData.private_key}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            private_key: e.target.value,
                          })
                        }
                        disabled={isRunning}
                      />
                    </div>
                    <div className="p-2 bg-yellow-900/20 border border-yellow-800/50 rounded flex gap-2 items-start">
                      <AlertTriangle
                        size={14}
                        className="text-yellow-500 mt-0.5 shrink-0"
                      />
                      <p className="text-[10px] text-yellow-400/80">
                        SSH Mode Note: PR creation still requires a GitHub
                        Token. Automatic PRs might be skipped if token is not
                        provided separately.
                      </p>
                    </div>
                    <div>
                      <label className="text-xs font-mono text-slate-400 uppercase flex items-center gap-1">
                        <Lock size={10} /> GitHub Token (Optional for PRs)
                      </label>
                      <input
                        type="password"
                        className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm focus:border-purple-500 outline-none"
                        placeholder="github_pat_..."
                        value={formData.github_token}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            github_token: e.target.value,
                          })
                        }
                        disabled={isRunning}
                      />
                    </div>
                  </div>
                )}

                {/* Vercel Token Input (Optional) */}
                <div>
                  <label className="text-xs font-mono text-slate-400 uppercase flex items-center gap-1">
                    <Zap size={10} /> Vercel Token (Optional)
                  </label>
                  <input
                    type="password"
                    className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm focus:border-orange-500 outline-none"
                    placeholder="Access Token for Logs..."
                    value={vercelToken}
                    onChange={(e) => setVercelToken(e.target.value)}
                    disabled={isRunning}
                  />
                </div>

                <button
                  type="submit"
                  disabled={isRunning}
                  className={`w-full font-bold py-3 rounded-lg shadow-lg flex justify-center items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4 text-white
                    ${
                      authMode === "https"
                        ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500"
                        : "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500"
                    }`}
                >
                  {isRunning ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <Zap size={18} fill="currentColor" />
                  )}
                  {isRunning ? "AGENT RUNNING..." : "RUN AGENT"}
                </button>
              </form>
            </div>
          </div>

          {/* Score Panel */}
          <div className="bg-[#1e293b] rounded-xl border border-slate-700 shadow-xl overflow-hidden relative">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Award size={100} />
            </div>
            <div className="p-6">
              <h3 className="text-slate-400 text-xs font-mono uppercase mb-1">
                Final Score
              </h3>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-black text-white">
                  {status.score}
                </span>
                <span className="text-slate-500">/ 100</span>
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Base Score</span>
                  <span className="font-mono">100</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Time Bonus ({"<"} 5m)</span>
                  <span className="font-mono text-emerald-400">
                    {parseInt(status.time_taken) < 5 ? "+10" : "0"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Summaries & Logs - Span 8 */}
        <div className="lg:col-span-8 space-y-6">
          {/* Run Summary Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[#1e293b] p-4 rounded-xl border border-slate-700 flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <GitBranch size={16} />{" "}
                <span className="text-xs uppercase">Branch</span>
              </div>
              <div
                className="font-mono text-xs text-blue-300 break-all"
                title={status.branch_name}
              >
                {status.branch_name.length > 20
                  ? status.branch_name.substring(0, 18) + "..."
                  : status.branch_name}
              </div>
            </div>

            <div className="bg-[#1e293b] p-4 rounded-xl border border-slate-700 flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                {status.auth_mode === "ssh" ? (
                  <Key size={16} />
                ) : (
                  <Lock size={16} />
                )}
                <span className="text-xs uppercase">Auth Mode</span>
              </div>
              <div className="text-xl font-bold text-white uppercase">
                {status.auth_mode || "HTTPS"}
              </div>
            </div>

            <div className="bg-[#1e293b] p-4 rounded-xl border border-slate-700 flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <Hammer size={16} />{" "}
                <span className="text-xs uppercase">Fixes</span>
              </div>
              <div className="text-2xl font-bold text-white">
                {status.fixes_applied.length}
              </div>
            </div>

            <div className="bg-[#1e293b] p-4 rounded-xl border border-slate-700 flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <Clock size={16} />{" "}
                <span className="text-xs uppercase">Time</span>
              </div>
              <div className="text-2xl font-bold text-white">
                {status.time_taken}
              </div>
            </div>
          </div>

          {/* Timeline & Status */}
          <div className="bg-[#1e293b] rounded-xl border border-slate-700 shadow-xl overflow-hidden p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-semibold text-slate-100 flex items-center gap-2">
                <Activity className="text-emerald-400" size={20} /> Executing
                Workflow
              </h3>
              <StatusBadge status={status.final_status} />
            </div>

            <div className="relative pt-2 pb-6">
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ease-out ${status.auth_mode === "ssh" ? "bg-purple-500" : "bg-blue-500"}`}
                  style={{
                    width: `${(status.iteration / status.max_iterations) * 100}%`,
                  }}
                />
              </div>
              <div className="flex justify-between mt-2 text-xs text-slate-500 font-mono">
                <span>START</span>
                <span>
                  ITERATION {status.iteration} / {status.max_iterations}
                </span>
                <span>FINISH</span>
              </div>
            </div>
          </div>

          {/* Vercel Logs (Conditional) */}
          {vercelLogs &&
            (vercelLogs.loading || vercelLogs.status === "found") && (
              <div className="bg-black rounded-xl border border-orange-900/50 shadow-xl overflow-hidden font-mono text-xs mb-6">
                <div className="p-2 bg-orange-950/20 border-b border-orange-900/50 text-orange-200 flex justify-between items-center px-4">
                  <div className="flex items-center gap-2">
                    <Zap size={14} className="text-orange-500" />
                    <span>VERCEL DEPLOYMENT LOGS</span>
                    {vercelLogs.loading && (
                      <Loader2 size={12} className="animate-spin opacity-50" />
                    )}
                    {!vercelLogs.loading && vercelLogs.deployment && (
                      <span className="text-xs px-2 py-0.5 rounded bg-orange-500/20 text-orange-300">
                        {vercelLogs.deployment.project_name} (
                        {vercelLogs.deployment.state})
                      </span>
                    )}
                  </div>
                </div>
                <div className="h-48 overflow-y-auto p-4 space-y-1 text-slate-300 bg-black/80">
                  {vercelLogs.loading ? (
                    <span className="text-slate-500 italic">
                      Fetching latest deployment logs...
                    </span>
                  ) : vercelLogs.logs.length === 0 ? (
                    <span className="text-slate-500 italic">
                      No build logs available for this deployment.
                    </span>
                  ) : (
                    vercelLogs.logs.map((log, i) => (
                      <div
                        key={i}
                        className="break-words border-l-2 border-slate-800 pl-2"
                      >
                        <span className="text-orange-500/50 mr-2">{">"}</span>
                        {log}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

          {/* Fixes Table */}
          <div className="bg-[#1e293b] rounded-xl border border-slate-700 shadow-xl overflow-hidden">
            <div className="p-4 border-b border-slate-700 bg-slate-800/50">
              <h3 className="font-semibold text-slate-100">Fixes Applied</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-[#1e293b] text-slate-500 uppercase text-xs border-b border-slate-700">
                  <tr>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium">File</th>
                    <th className="px-4 py-3 font-medium">Line</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {status.fixes_applied.length === 0 ? (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-4 py-8 text-center text-slate-500"
                      >
                        No fixes applied yet.
                      </td>
                    </tr>
                  ) : (
                    status.fixes_applied.map((fix: any, i: number) => (
                      <tr
                        key={i}
                        className="hover:bg-slate-800/50 transition-colors"
                      >
                        <td className="px-4 py-3 font-mono text-xs">
                          <span className="px-2 py-0.5 rounded bg-purple-900/40 text-purple-400 border border-purple-800/50">
                            {fix.bug_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono">{fix.file}</td>
                        <td className="px-4 py-3 font-mono text-slate-500">
                          {fix.line_number}
                        </td>
                        <td className="px-4 py-3">
                          {fix.status.includes("Fixed") ? (
                            <span className="flex items-center gap-1 text-emerald-400 text-xs font-bold">
                              <CheckCircle size={12} /> FIXED
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-yellow-400 text-xs font-bold">
                              <Activity size={12} /> APPLIED
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Logs Console */}
          <div className="bg-[#0f172a] rounded-xl border border-slate-700 shadow-xl overflow-hidden font-mono text-xs">
            <div className="p-2 bg-slate-800 border-b border-slate-700 text-slate-400 flex justify-between items-center px-4">
              <span>TERMINAL OUTPUT</span>
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/50"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-green-500/50"></div>
              </div>
            </div>
            <div className="h-64 overflow-y-auto p-4 space-y-1 text-slate-300">
              {status.logs.map((log: string, i: number) => (
                <div key={i} className="break-words">
                  <span className="text-slate-600 select-none mr-3 opacity-50">
                    $
                  </span>
                  {log}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
