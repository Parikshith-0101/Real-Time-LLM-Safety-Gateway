import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import AnimatedBackground from '../components/AnimatedBackground';

export default function Home() {
  const navigate = useNavigate();
  const mainContentRef = useRef(null);

  // state
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleLoginClick = () => navigate('/login');

  const handleRecentClick = () => {
    if (mainContentRef.current) {
      mainContentRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // correlation id
  function makeCorrelationId() {
    try {
      if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
    } catch (_) {}
    return 'cid-' + Math.random().toString(36).slice(2, 10);
  }

  // axios instance: uses env variable REACT_APP_API_URL or relative path ''
  const BACKEND = import.meta.env.VITE_REACT_APP_API_URL || 'http://localhost:5000';
  const api = axios.create({
    baseURL: BACKEND,            // '' means same origin, or e.g. 'http://localhost:3000'
    timeout: 10000,             // 10s timeout
    headers: { 'Content-Type': 'application/json' }
  });

  async function sendPrompt() {
    setError(null);
    setResult(null);

    const trimmed = (prompt || "").trim();
    if (!trimmed) {
      setError("Prompt cannot be empty.");
      return;
    }

    setLoading(true);
    const correlationId = makeCorrelationId();

    try {
      const resp = await api.post('/api/sanitize', { prompt: trimmed }, {
        headers: { 'X-Correlation-ID': correlationId }
      });

      // axios treats non-2xx as exceptions; here resp.data is the body.
      setResult(resp.data);
    } catch (err) {
      // unwrap axios error for a friendly message
      let message = 'Request failed';
      if (axios.isAxiosError(err)) {
        if (err.response) {
          // server responded with non-2xx
          const status = err.response.status;
          const body = typeof err.response.data === 'string' ? err.response.data : JSON.stringify(err.response.data);
          message = `Server returned ${status}: ${body}`;
        } else if (err.request) {
          // request was made but no response
          message = 'No response from server (network error or server down)';
        } else {
          message = err.message;
        }
      } else {
        message = String(err);
      }
      console.error("Sanitize request failed:", err);
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full min-h-screen relative text-white font-sans">
      <AnimatedBackground />

      <header className="relative z-10 w-full h-[10vh] flex items-center justify-between px-10 shadow-xl animate-fadeIn bg-gray-800/40 backdrop-blur-md">
        <h1 className="text-4xl font-extrabold tracking-wide text-blue-300 drop-shadow-lg animate-slideDown">
          <span className="bg-gradient-to-r from-blue-300 via-purple-400 to-pink-400 bg-clip-text text-transparent">LLM Safety Gateway</span>
        </h1>

        <div className="flex items-center space-x-6">
          <span className="text-sm font-medium text-gray-300 hover:text-blue-400 transition duration-200 cursor-pointer animate-slideDown" onClick={handleRecentClick}>Recent</span>
          <button className="p-3 rounded-xl bg-blue-700 hover:bg-blue-600 active:scale-95 transition-all duration-300 text-white text-lg font-semibold shadow-md animate-slideDown" onClick={handleLoginClick}>Login / Sign up</button>
        </div>
      </header>

      <main ref={mainContentRef} className="relative z-10 w-full min-h-[70vh] p-6 flex flex-col items-center">
        <div className="w-full max-w-2xl bg-gray-800/40 backdrop-blur-md p-6 rounded-2xl shadow-xl border border-gray-700 mt-10 animate-fadeIn">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Enter your prompt</h2>

          <textarea
            placeholder="Type your prompt here..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full h-40 p-4 rounded-xl bg-gray-900 border border-gray-700 focus:border-blue-500 focus:outline-none text-white resize-none shadow-inner"
          />

          <button
            className={`w-full mt-4 py-3 bg-blue-700 hover:bg-blue-600 active:scale-95 transition-all rounded-xl text-white text-lg font-semibold shadow-md ${loading ? 'opacity-70 cursor-not-allowed' : ''}`}
            onClick={sendPrompt}
            disabled={loading}
          >
            {loading ? 'Sanitizing...' : 'Sanitize Prompt'}
          </button>

          {error && (
            <div className="mt-4 p-3 rounded-md bg-red-700/40 text-red-200">
              <strong>Error:</strong> {error}
            </div>
          )}

          {result && (
            <div className="mt-4 p-4 rounded-md bg-gray-900 border border-gray-700 text-sm text-gray-200">
              <div className="mb-2">
                <strong>Decision:</strong> <span className="text-blue-300">{result.decision}</span>
              </div>
              {result.score !== undefined && <div className="mb-2"><strong>Score:</strong> {String(result.score)}</div>}
              {result.sanitizedPrompt && (
                <div className="mb-2">
                  <strong>Sanitized Prompt:</strong>
                  <pre className="whitespace-pre-wrap bg-black/40 p-2 rounded mt-1 text-xs">{result.sanitizedPrompt}</pre>
                </div>
              )}
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer">Show raw response (audit)</summary>
                <pre className="whitespace-pre-wrap text-xs mt-2 bg-black/20 p-2 rounded">{JSON.stringify(result.audit || result, null, 2)}</pre>
              </details>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
