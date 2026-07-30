import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface EvalRun {
  run_id: string;
  timestamp: string;
  prompt: string;
  model: string;
  correctness_score: number | null;
  completeness_score: number | null;
  faithfullness_score: number | null;
  groundedness_score: number | null;
  clarity_score: number | null;
  verdict: string | null;
}

export const EvaluationDashboard: React.FC = () => {
  const [history, setHistory] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Note: adjust the URL depending on your frontend proxy / vite config
    fetch('http://localhost:8001/api/v1/history')
      .then(res => res.json())
      .then(data => {
        setHistory(data.history || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="text-white p-4">Loading evaluation data...</div>;

  return (
    <div className="p-6 bg-[#0B1120] min-h-screen text-slate-300 font-sans">
      <h2 className="text-3xl font-bold text-white mb-6 tracking-tight">Evaluation & Observability</h2>
      
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 shadow-xl mb-8">
        <h3 className="text-xl font-semibold text-white mb-4">Recent Runs</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400">
                <th className="p-3">Time</th>
                <th className="p-3">Model</th>
                <th className="p-3">Prompt</th>
                <th className="p-3 text-center">Score (Correct/Complete/Clear)</th>
                <th className="p-3 text-center">Score (Faithfullness/Groundedness)</th>
                <th className="p-3">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {history.map(run => (
                <tr key={`${run.run_id}-${run.model}`} className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                  <td className="p-3">{new Date(run.timestamp).toLocaleTimeString()}</td>
                  <td className="p-3 font-medium text-blue-400">{run.model}</td>
                  <td className="p-3 truncate max-w-xs">{run.prompt}</td>
                  <td className="p-3 text-center">
                    {run.correctness_score}/{run.completeness_score}/{run.clarity_score}
                  </td>
                  <td className="p-3 text-center">
                    {run.faithfullness_score}/{run.groundedness_score}
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      run.verdict === 'A' || run.verdict === 'B' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-300'
                    }`}>
                      {run.verdict || 'N/A'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
