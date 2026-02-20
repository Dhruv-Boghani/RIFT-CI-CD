import React from "react";
import { CheckCircle } from "lucide-react";

interface Fix {
  type: string;
  file: string;
  line: number;
  message: string;
}

interface FixTableProps {
  fixes: Fix[];
}

const FixTable: React.FC<FixTableProps> = ({ fixes }) => {
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="p-4 border-b border-slate-700">
        <h3 className="font-semibold text-lg">Applied Fixes</h3>
      </div>
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-900/50 text-slate-400">
          <tr>
            <th className="p-4 font-medium">Bug Type</th>
            <th className="p-4 font-medium">Location</th>
            <th className="p-4 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {fixes &&
            fixes.map((fix, idx) => (
              <tr key={idx} className="hover:bg-slate-700/30">
                <td className="p-4">
                  <span className="px-2 py-1 bg-yellow-500/10 text-yellow-500 rounded text-xs font-bold border border-yellow-500/20">
                    {fix.type || "UNKNOWN"}
                  </span>
                </td>
                <td className="p-4 font-mono text-slate-300">
                  {fix.message} in {fix.file} line {fix.line} &rarr; Fixed
                </td>
                <td className="p-4">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle size={16} /> Applied
                  </div>
                </td>
              </tr>
            ))}
          {(!fixes || fixes.length === 0) && (
            <tr>
              <td colSpan={3} className="p-8 text-center text-slate-500">
                No fixes applied yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default FixTable;
