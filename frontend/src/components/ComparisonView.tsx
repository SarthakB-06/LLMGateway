import React, { useState } from 'react';

interface ComparisonProps {
  prompt: string;
}

export const ComparisonView: React.FC<ComparisonProps> = ({ prompt }) => {
  const [modelA, setModelA] = useState('gemini-2.5-flash');
  const [modelB, setModelB] = useState('gemini-3.5-flash');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCompare = async () => {
    setLoading(true);
    setErrorMsg(null);
    setResult(null);
    try {
      // 1. Run comparison
      const compareRes = await fetch('http://localhost:8001/api/v1/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          models: [{ provider: 'google', model: modelA }, { provider: 'google', model: modelB }]
        })
      });
      const compareData = await compareRes.json();
      
      // Check if any model failed
      if (compareData.results[0].error || compareData.results[1].error) {
         setErrorMsg("One of the models failed to generate a response. Please check your backend logs.");
         setLoading(false);
         return;
      }

      const responses = {
        [modelA]: compareData.results[0].response,
        [modelB]: compareData.results[1].response
      };

      // 2. Run judge
      const judgeRes = await fetch('http://localhost:8001/api/v1/judge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, responses })
      });
      const judgeData = await judgeRes.json();
      
      setResult({ responses, judge: judgeData.evaluation });
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected error occurred");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 shadow-xl mb-8">
      <h3 className="text-xl font-semibold text-white mb-4">Model Arena</h3>
      <button 
        onClick={handleCompare}
        disabled={loading}
        className="mb-6 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50"
      >
        {loading ? 'Evaluating...' : 'Run Head-to-Head Comparison'}
      </button>

      {errorMsg && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg mb-6">
          {errorMsg}
        </div>
      )}

      {result && (
        <div className="grid grid-cols-2 gap-6 mt-6">
          {/* Output structure remains exactly the same */}
          <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
            <h4 className="text-blue-400 font-bold mb-2">{modelA}</h4>
            <div className="text-slate-300 text-sm mb-4 bg-slate-900/50 p-3 rounded">
              {result.responses[modelA]}
            </div>
            {result.judge.response_a && (
              <div className="text-xs text-slate-400 mt-4 border-t border-slate-700 pt-3">
                <p><strong>Rationale:</strong> {result.judge.response_a.rationale}</p>
                <div className="flex gap-4 mt-2 flex-wrap">
                  <span>Correctness: {result.judge.response_a.correctness}/5</span>
                  <span>Completeness: {result.judge.response_a.completeness}/5</span>
                  <span>Faithfulness: {result.judge.response_a.faithfulness}/5</span>
                  <span>Groundedness: {result.judge.response_a.groundedness}/5</span>
                  <span>Clarity: {result.judge.response_a.clarity}/5</span>
                </div>
              </div>
            )}
          </div>

          <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
            <h4 className="text-orange-400 font-bold mb-2">{modelB}</h4>
            <div className="text-slate-300 text-sm mb-4 bg-slate-900/50 p-3 rounded">
              {result.responses[modelB]}
            </div>
            {result.judge.response_b && (
              <div className="text-xs text-slate-400 mt-4 border-t border-slate-700 pt-3">
                <p><strong>Rationale:</strong> {result.judge.response_b.rationale}</p>
                <div className="flex gap-4 mt-2 flex-wrap">
                  <span>Correctness: {result.judge.response_b.correctness}/5</span>
                  <span>Completeness: {result.judge.response_b.completeness}/5</span>
                  <span>Faithfulness: {result.judge.response_b.faithfulness}/5</span>
                  <span>Groundedness: {result.judge.response_b.groundedness}/5</span>
                  <span>Clarity: {result.judge.response_b.clarity}/5</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="col-span-2 text-center bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-lg mt-4">
            <h4 className="text-lg font-bold text-emerald-400">
              Verdict: {result.judge.verdict === 'tie' ? 'It\'s a Tie!' : `Model ${result.judge.verdict} Wins!`}
            </h4>
          </div>
        </div>
      )}
    </div>
  );
};
