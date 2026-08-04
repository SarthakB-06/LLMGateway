import { useEffect, useState } from 'react';
import { Activity, Zap, Database, Coins, Hash, LayoutDashboard, Scale, MessageSquare } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { EvaluationDashboard } from './components/EvaluationDashboard';
import { ComparisonView } from './components/ComparisonView';
import { Playground } from './components/Playground';

export default function App() {
  const [activeTab, setActiveTab] = useState('telemetry');
  const [stats, setStats] = useState({
    total_requests: 0,
    average_latency_ms: 0,
    cache_hit_rate_percent: 0,
    total_tokens: 0,
    total_cost: 0,
    models: []
  });

  const fetchAnalytics = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/summary');
      const data = await response.json();
      if (!data.error) setStats(data);
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-50 p-8 font-sans">
      <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-linear-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            AI Gateway Control Plane
          </h1>
          <p className="text-slate-400 mt-2">Real-time infrastructure telemetry & cost optimization</p>
        </div>
        
        {/* Navigation Tabs */}
        <div className="flex space-x-2 bg-slate-900/50 p-1 rounded-lg border border-slate-800 overflow-x-auto max-w-full">
          <button 
            onClick={() => setActiveTab('telemetry')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors whitespace-nowrap ${activeTab === 'telemetry' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Telemetry</span>
          </button>
          <button 
            onClick={() => setActiveTab('playground')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors whitespace-nowrap ${activeTab === 'playground' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Playground</span>
          </button>
          <button 
            onClick={() => setActiveTab('evaluation')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors whitespace-nowrap ${activeTab === 'evaluation' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
          >
            <Scale className="w-4 h-4" />
            <span>Evaluation</span>
          </button>
        </div>
      </header>

      {activeTab === 'telemetry' && (
        <>
          {/* Top Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            {[
              { title: "Total Requests", value: stats.total_requests, icon: Activity, color: "text-blue-400" },
              { title: "Avg Latency", value: `${stats.average_latency_ms} ms`, icon: Zap, color: "text-amber-400" },
              { title: "Cache Hit Rate", value: `${stats.cache_hit_rate_percent} %`, icon: Database, color: "text-emerald-400" },
              { title: "Tokens Processed", value: stats.total_tokens.toLocaleString(), icon: Hash, color: "text-purple-400" },
              { title: "API Cost", value: `$${stats.total_cost.toFixed(6)}`, icon: Coins, color: "text-rose-400" },
            ].map((stat, i) => (
              <div key={i} className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-sm">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-slate-400 font-medium text-sm">{stat.title}</h2>
                  <stat.icon className={`${stat.color} w-5 h-5`} />
                </div>
                <p className="text-2xl font-bold">{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 shadow-lg">
              <h3 className="text-lg font-semibold mb-6 text-slate-200">Model Traffic Distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.models} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                    <XAxis dataKey="name" stroke="#64748B" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748B" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip 
                      cursor={{ fill: '#1E293B' }}
                      contentStyle={{ backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '8px' }}
                    />
                    <Bar dataKey="requests" fill="#3B82F6" radius={[4, 4, 0, 0]} barSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 shadow-lg flex flex-col justify-center items-center text-center">
                <Database className="w-16 h-16 text-emerald-500/20 mb-4" />
                <h3 className="text-lg font-semibold text-slate-200 mb-2">Semantic Cache Status</h3>
                <p className="text-slate-400 max-w-sm">
                  Your vector-based routing engine is currently active. Identical semantic requests are successfully bypassing external APIs, driving API costs down to $0.00 while reducing latency to sub-millisecond speeds.
                </p>
            </div>
          </div>
        </>
      )}

      {activeTab === 'playground' && (
        <Playground />
      )}

      {activeTab === 'evaluation' && (
        <div className="space-y-8">
           <ComparisonView prompt="What are the key benefits of using a semantic cache in an LLM Gateway?" />
           <EvaluationDashboard />
        </div>
      )}
    </div>
  );
}
