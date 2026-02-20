import React from "react";
import { GitBranch, Bug } from "lucide-react";

interface SummaryCardProps {
  data: {
    status: string;
    branch?: string;
    fixes?: any[];
    attempt?: number;
  };
}

const SummaryCard: React.FC<SummaryCardProps> = ({ data }) => {
  const isSuccess = data.status === "COMPLETED";
  const isFail = data.status === "FAILED";

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div
        className={`p-4 rounded-xl border ${isSuccess ? "bg-emerald-500/10 border-emerald-500/30" : isFail ? "bg-red-500/10 border-red-500/30" : "bg-slate-800 border-slate-700"}`}
      >
        <div className="text-slate-400 text-sm mb-1">Status</div>
        <div
          className={`text-2xl font-bold ${isSuccess ? "text-emerald-400" : isFail ? "text-red-400" : "text-blue-400"}`}
        >
          {data.status}
        </div>
      </div>

      <div className="p-4 bg-slate-800 rounded-xl border border-slate-700">
        <div className="text-slate-400 text-sm mb-1 flex items-center gap-2">
          <GitBranch size={14} /> Branch Created
        </div>
        <div className="font-mono text-sm text-yellow-400 break-all">
          {data.branch || "waiting..."}
        </div>
      </div>

      <div className="p-4 bg-slate-800 rounded-xl border border-slate-700">
        <div className="text-slate-400 text-sm mb-1 flex items-center gap-2">
          <Bug size={14} /> Fixes / Attempts
        </div>
        <div className="text-2xl font-bold text-white">
          {data.fixes ? data.fixes.length : 0}{" "}
          <span className="text-slate-500 text-lg">/ {data.attempt}</span>
        </div>
      </div>
    </div>
  );
};

export default SummaryCard;
