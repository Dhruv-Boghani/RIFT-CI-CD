import React from "react";

interface TimelineProps {
  data: {
    logs?: string[];
  };
}

const Timeline: React.FC<TimelineProps> = ({ data }) => {
  return (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
      <h3 className="font-semibold text-lg mb-4">Execution Log</h3>
      <div className="space-y-2 max-h-60 overflow-y-auto font-mono text-sm">
        {data.logs &&
          data.logs.map((log, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-slate-500">[{i + 1}]</span>
              <span
                className={
                  log.includes("FAIL")
                    ? "text-red-400"
                    : log.includes("PASS") || log.includes("success")
                      ? "text-emerald-400"
                      : "text-slate-300"
                }
              >
                {log}
              </span>
            </div>
          ))}
        {(!data.logs || data.logs.length === 0) && (
          <div className="text-slate-500">Waiting for logs...</div>
        )}
      </div>
    </div>
  );
};

export default Timeline;
