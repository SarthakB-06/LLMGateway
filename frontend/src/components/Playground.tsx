import React, { useState } from 'react';
import { Send, Zap, Database, Hash, Clock, AlertTriangle } from 'lucide-react';

export const Playground: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [model, setModel] = useState('gemini-1.5-flash');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  const [result, setResult] = useState<{
    text: string;
    latency_ms: number;
    tokens: number;
    cache_hit: boolean;
    cache_type: string | null;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setErrorMsg(null);
    setResult(null);

    // Track round-trip latency manually on the frontend
    const startTime = performance.now();

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, model })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      const endTime = performance.now();
      const roundTripLatency = Math.round(endTime - startTime);

      const content = data.choices[0]?.message?.content || "No response received.";
      const usage = data.usage || {};

      setResult({
        text: content,
        latency_ms: roundTripLatency,
        tokens: usage.total_tokens || 0,
        cache_hit: usage.cache_hit || false,
        cache_type: usage.cache_type || null
      });

    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "An unexpected error occurred while communicating with the Gateway.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 max-w-7xl mx-auto">
      {/* Input Section */}
      <div className="flex-1 bg-slate-900/50 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col h-[70vh]">
        <h2 className="text-xl font-bold text-slate-100 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-emerald-400" />
          Interactive Playground
        </h2>
        
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-400">Target Model</label>
            <select 
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-3 focus:outline-none focus:border-blue-500 transition-colors"
            >
              <option value="gemini-1.5-flash">Google Gemini 1.5 Flash (Fast & Cheap)</option>
              <option value="gemini-1.5-pro">Google Gemini 1.5 Pro (Advanced Logic)</option>
            </select>
          </div>

          <div className="flex flex-col flex-1 gap-2 mt-2">
            <label className="text-sm font-medium text-slate-400">System Prompt / Input</label>
            <textarea 
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask a question, request a summary, or write code..."
              className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-4 resize-none focus:outline-none focus:border-blue-500 transition-colors font-mono text-sm leading-relaxed"
            />
          </div>

          <button 
            type="submit"
            disabled={loading || !prompt.trim()}
            className="mt-2 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium py-3 px-6 rounded-lg transition-colors"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/20 border-t-white"></div>
                Processing via Gateway...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Generate Response
              </>
            )}
          </button>
        </form>
      </div>

      {/* Output Section */}
      <div className="flex-1 bg-slate-900/50 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col h-[70vh]">
        <h2 className="text-xl font-bold text-slate-100 mb-4">Response Output</h2>
        
        {errorMsg && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" />
            <p className="text-red-400 text-sm">{errorMsg}</p>
          </div>
        )}

        <div className="flex-1 bg-slate-950 border border-slate-700 rounded-lg p-4 overflow-y-auto font-sans text-slate-300 leading-relaxed whitespace-pre-wrap">
          {result ? result.text : (
            <div className="h-full flex items-center justify-center text-slate-600 italic">
              Awaiting your prompt...
            </div>
          )}
        </div>

        {/* Metrics Bar */}
        {result && (
          <div className="mt-4 pt-4 border-t border-slate-800 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <div className="flex flex-col">
                <span className="text-xs text-slate-500 uppercase tracking-wider">Latency</span>
                <span className="text-sm font-semibold text-amber-400">{result.latency_ms} ms</span>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Hash className="w-4 h-4 text-slate-400" />
              <div className="flex flex-col">
                <span className="text-xs text-slate-500 uppercase tracking-wider">Tokens</span>
                <span className="text-sm font-semibold text-purple-400">{result.tokens.toLocaleString()}</span>
              </div>
            </div>

            <div className="flex items-center gap-2 col-span-2 md:col-span-2">
              <Database className="w-4 h-4 text-slate-400" />
              <div className="flex flex-col">
                <span className="text-xs text-slate-500 uppercase tracking-wider">Cache Status</span>
                {result.cache_hit ? (
                  <span className="text-sm font-semibold text-emerald-400">
                    Hit ({result.cache_type === 'semantic' ? 'Semantic Match' : 'Exact Match'})
                  </span>
                ) : (
                  <span className="text-sm font-semibold text-rose-400">Miss (Live API)</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
