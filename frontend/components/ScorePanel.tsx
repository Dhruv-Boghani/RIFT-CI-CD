import React from "react";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { Doughnut } from "react-chartjs-2";

ChartJS.register(ArcElement, Tooltip, Legend);

interface ScorePanelProps {
  data: {
    attempt?: number;
  };
}

const ScorePanel: React.FC<ScorePanelProps> = ({ data }) => {
  // Simple mock score calculation
  // Base 100
  // -5 per fix attempt
  const baseScore = 100;
  const penalty = (data.attempt || 0) * 5;
  const score = Math.max(0, baseScore - penalty);

  const chartData = {
    labels: ["Score", "Penalty"],
    datasets: [
      {
        data: [score, penalty],
        backgroundColor: ["#10b981", "#ef4444"],
        borderWidth: 0,
      },
    ],
  };

  return (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
      <h3 className="font-semibold text-lg mb-4 text-center">
        Efficiency Score
      </h3>
      <div className="w-40 h-40 mx-auto relative">
        <Doughnut data={chartData} options={{ cutout: "75%" }} />
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <span className="text-3xl font-bold text-white">{score}</span>
          <span className="text-xs text-slate-400">POINTS</span>
        </div>
      </div>
      <div className="mt-4 text-center text-sm text-slate-400">
        -5 pts per retry attempt
      </div>
    </div>
  );
};

export default ScorePanel;
