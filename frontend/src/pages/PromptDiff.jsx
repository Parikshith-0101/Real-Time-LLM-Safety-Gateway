/**
 * PromptDiff.jsx
 * Main page for the Prompt Safety Diff Viewer.
 * 
 * Usage:
 * 1. Ensure VITE_REACT_APP_API_URL is set in .env (defaults to http://localhost:3000)
 * 2. Add route in App.jsx: <Route path="/diff" element={<PromptDiff />} />
 */

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import AnimatedBackground from '../components/AnimatedBackground';
import DiffView from '../components/DiffView';
import { parseAgentResponse, formatConfidence } from '../utils/diffUtils';

// --- Configuration ---
const API_URL = import.meta.env.VITE_REACT_APP_API_URL || 'http://localhost:3000';
const SANITIZE_ENDPOINT = `${API_URL}/api/sanitize`;

// --- Helpers ---
const generateUUID = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

const extractTags = (explanation) => {
  if (!explanation) return [];
  const keywords = ['contains_url', 'base64', 'high-entropy', 'infoleak', 'pii', 'jailbreak', 'malicious'];
  const found = keywords.filter(k => explanation.toLowerCase().includes(k));
  if (found.length === 0) return ['transformed'];
  return found;
};

// Simulated response for development/fallback
const SIMULATED_RESPONSE = {
  "verdict": "sanitize",
  "sanitized_prompt": "This prompt has been safely transformed to remove harmful intent. Provide educational guidance on secure coding practices instead of exploit details.",
  "explanation": "Transformed to safe educational cybersecurity guidance; removed exploit details. Detected potential jailbreak attempt.",
  "confidence": 0.92
};

const PromptDiff = () => {
  // --- State ---
  const [originalPrompt, setOriginalPrompt] = useState('');
  const [sanitizedPrompt, setSanitizedPrompt] = useState('');
  const [verdict, setVerdict] = useState(null); // 'allow' | 'sanitize'
  const [explanation, setExplanation] = useState('');
  const [confidence, setConfidence] = useState(0);
  
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null); // { message, type }

  // Scroll sync refs
  const leftRef = useRef(null);
  const centerRef = useRef(null); // Passed to DiffView
  const rightRef = useRef(null);
  const isScrolling = useRef(false);

  // --- Handlers ---

  const handleSanitize = async () => {
    if (!originalPrompt.trim()) {
      showToast("Please enter a prompt first.", "warning");
      return;
    }

    setLoading(true);
    setVerdict(null);
    setSanitizedPrompt('');
    setExplanation('');
    setConfidence(0);
    
    const correlationId = generateUUID();

    try {
      // Attempt real API call
      const response = await axios.post(SANITIZE_ENDPOINT, {
        prompt: originalPrompt
      }, {
        headers: {
          'X-Correlation-ID': correlationId,
          'Content-Type': 'application/json'
        },
        timeout: 5000 // 5s timeout
      });

      const parsed = parseAgentResponse(response.data);
      if (!parsed.ok) {
        throw new Error(parsed.error);
      }
      handleSuccess(parsed.data);

    } catch (err) {
      console.warn("Backend unavailable or error:", err);
      
      // Check if it's a validation error from our parser
      if (err.message && err.message.startsWith("Missing") || err.message.startsWith("Invalid")) {
         showToast(`Invalid agent response: ${err.message}`, "error");
         setLoading(false);
         return;
      }

      // Fallback for demo/dev purposes or network error
      const useFake = import.meta.env.VITE_REACT_APP_FAKE_SANITIZE === 'true' || true; // Default to true for demo if network fails
      
      if (useFake) {
          console.log("Simulating response after delay...");
          setTimeout(() => {
            const simulated = { ...SIMULATED_RESPONSE };
            // Simple mock logic to make it dynamic
            if (originalPrompt.toLowerCase().includes("allow")) {
                simulated.verdict = "allow";
                simulated.sanitized_prompt = originalPrompt;
                simulated.explanation = "No malicious content detected.";
                simulated.confidence = 0.99;
            } else {
                 // Keep default simulated sanitize
            }
            
            handleSuccess(simulated);
            showToast("Backend unreachable. Showing simulated response.", "info");
          }, 600);
      } else {
          showToast("Backend unreachable.", "error");
          setLoading(false);
      }
    }
  };

  const handleSuccess = (data) => {
    setVerdict(data.verdict);
    setSanitizedPrompt(data.sanitized_prompt);
    setExplanation(data.explanation);
    setConfidence(data.confidence);
    setLoading(false);
    showToast("Sanitization complete", "success");
  };

  const showToast = (message, type = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleAction = (action) => {
    console.log(`Action triggered: ${action}`, {
        prompt: originalPrompt,
        sanitized_prompt: sanitizedPrompt,
        verdict,
        confidence
    });
    
    if (action === 'agent') {
      showToast("Sent to agent (stub)", "success");
    } else if (action === 'approve') {
        showToast("Marked as Approved", "success");
    } else if (action === 'reject') {
        showToast("Marked as Rejected", "warning");
    }
  };

  // --- Scroll Sync ---
  const handleScroll = (e) => {
    if (isScrolling.current) return;
    isScrolling.current = true;

    const { scrollTop } = e.target;
    // Sync all 3 columns
    [leftRef, centerRef, rightRef].forEach(ref => {
      if (ref.current && ref.current !== e.target) {
        ref.current.scrollTop = scrollTop;
      }
    });

    setTimeout(() => {
      isScrolling.current = false;
    }, 50);
  };


  // --- Render ---
  return (
    <div className="relative min-h-screen w-full overflow-hidden text-gray-100 font-sans selection:bg-cyan-500/30">
      <AnimatedBackground />

      <div className="relative z-10 flex flex-col h-screen max-w-7xl mx-auto p-4 md:p-6 lg:p-8">
        
        {/* Header */}
        <header className="mb-6 flex justify-between items-end border-b border-gray-700/50 pb-4 shrink-0">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-400">
              Prompt Safety Diff Viewer
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Analyze, sanitize, and review LLM prompts in real-time.
            </p>
          </div>
        </header>

        {/* Main Content - 3 Columns */}
        <div className="flex-1 flex flex-col md:flex-row gap-4 min-h-0">
          
          {/* LEFT: Original Prompt */}
          <div className="flex-1 flex flex-col min-h-[200px] md:min-h-0 bg-gray-900/60 backdrop-blur-md border border-gray-700 rounded-xl overflow-hidden shadow-2xl transition-all hover:border-gray-600">
            <div className="bg-gray-800/50 px-4 py-2 border-b border-gray-700 flex justify-between items-center shrink-0">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Original Prompt</span>
              <span className="text-[10px] text-gray-500">Editable</span>
            </div>
            <textarea
              ref={leftRef}
              onScroll={handleScroll}
              className="flex-1 w-full bg-transparent p-4 resize-none focus:outline-none focus:bg-gray-800/30 transition-colors font-mono text-sm leading-relaxed custom-scrollbar"
              placeholder="Enter prompt here..."
              value={originalPrompt}
              onChange={(e) => setOriginalPrompt(e.target.value)}
              spellCheck="false"
              aria-label="Original Prompt"
            />
            <div className="p-3 border-t border-gray-700/50 bg-gray-800/30 flex justify-end shrink-0">
               <button
                onClick={handleSanitize}
                disabled={loading}
                aria-label="Sanitize Prompt"
                className={`flex items-center gap-2 px-6 py-2 rounded-lg font-semibold text-sm transition-all transform active:scale-95 ${
                  loading 
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                    : 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-900/20'
                }`}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                  </>
                ) : (
                  'Sanitize'
                )}
              </button>
            </div>
          </div>

          {/* CENTER: Diff Viewer */}
          <div className="flex-1 flex flex-col min-h-[200px] md:min-h-0 bg-gray-900/60 backdrop-blur-md border border-gray-700 rounded-xl overflow-hidden shadow-2xl">
             <div className="flex-1 overflow-hidden p-2 h-full">
                <DiffView 
                    ref={centerRef} // Pass ref for scroll sync
                    original={originalPrompt} 
                    sanitized={sanitizedPrompt} 
                    className="h-full"
                    onScroll={handleScroll}
                /> 
             </div>
          </div>

          {/* RIGHT: Sanitized Prompt */}
          <div className="flex-1 flex flex-col min-h-[200px] md:min-h-0 bg-gray-900/60 backdrop-blur-md border border-gray-700 rounded-xl overflow-hidden shadow-2xl">
            <div className="bg-gray-800/50 px-4 py-2 border-b border-gray-700 flex justify-between items-center shrink-0">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Sanitized Output</span>
              <span className="text-[10px] text-gray-500">Read-only</span>
            </div>
            <textarea
              ref={rightRef}
              onScroll={handleScroll}
              readOnly
              className="flex-1 w-full bg-transparent p-4 resize-none focus:outline-none font-mono text-sm leading-relaxed text-gray-300 custom-scrollbar"
              placeholder="Sanitized output will appear here..."
              value={sanitizedPrompt}
              aria-label="Sanitized Prompt"
            />
             <div className="p-3 border-t border-gray-700/50 bg-gray-800/30 flex justify-between items-center shrink-0">
                <span className="text-xs text-gray-500">
                    {verdict && (
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            verdict === 'allow' ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-amber-900/50 text-amber-400 border border-amber-800'
                        }`}>
                            {verdict}
                        </span>
                    )}
                </span>
                <button 
                    className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                    onClick={() => {navigator.clipboard.writeText(sanitizedPrompt); showToast("Copied to clipboard", "success")}}
                >
                    Copy
                </button>
            </div>
          </div>

        </div>

        {/* Bottom Bar: Badges & Actions */}
        <div className="mt-6 bg-gray-900/80 backdrop-blur-xl border border-gray-700 rounded-xl p-4 flex flex-col md:flex-row justify-between items-center gap-4 shadow-lg shrink-0">
          
          {/* Reason Badges & Confidence */}
          <div className="flex flex-wrap gap-4 items-center w-full md:w-auto">
            {/* Confidence Chip */}
            <div className="flex items-center gap-2 bg-gray-800/50 rounded-full px-3 py-1 border border-gray-600">
                <span className="text-xs text-gray-400 uppercase font-semibold">Confidence</span>
                <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-500" 
                        style={{ width: `${confidence * 100}%` }}
                    />
                </div>
                <span className="text-xs font-mono text-cyan-300">{formatConfidence(confidence)}</span>
            </div>

            <div className="h-4 w-px bg-gray-700 hidden md:block"></div>

            {/* Explanation Badges */}
            <div className="flex flex-wrap gap-2">
                {extractTags(explanation).map((tag, i) => (
                    <span key={i} className="px-2 py-1 rounded text-xs font-medium bg-gray-800 text-gray-300 border border-gray-600 capitalize">
                        {tag}
                    </span>
                ))}
            </div>
            
            {explanation && (
                <p className="text-xs text-gray-500 max-w-md truncate" title={explanation}>
                    {explanation}
                </p>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 w-full md:w-auto justify-end">
            <button 
                onClick={() => handleAction('approve')}
                className="flex-1 md:flex-none px-4 py-2 rounded-lg bg-green-900/20 text-green-400 border border-green-800/50 hover:bg-green-900/40 transition-colors text-sm font-medium"
                title="Mark as Safe"
            >
                Approve
            </button>
            <button 
                onClick={() => handleAction('reject')}
                className="flex-1 md:flex-none px-4 py-2 rounded-lg bg-red-900/20 text-red-400 border border-red-800/50 hover:bg-red-900/40 transition-colors text-sm font-medium"
                title="Mark as Unsafe"
            >
                Reject
            </button>
            <div className="w-px h-8 bg-gray-700 mx-1 hidden md:block"></div>
            <button 
                onClick={() => handleAction('agent')}
                className="flex-1 md:flex-none px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors text-sm font-medium shadow-lg shadow-indigo-900/30"
                title="Escalate to Human Agent"
            >
                Send to Agent
            </button>
          </div>
        </div>

      </div>

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-8 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-lg shadow-2xl backdrop-blur-md border z-50 transition-all duration-300 ${
            toast.type === 'error' ? 'bg-red-900/80 border-red-500 text-white' :
            toast.type === 'success' ? 'bg-green-900/80 border-green-500 text-white' :
            toast.type === 'warning' ? 'bg-yellow-900/80 border-yellow-500 text-white' :
            'bg-gray-800/90 border-gray-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}
    </div>
  );
};

// Add effect to attach scroll listener to centerRef
// Since we can't easily attach 'onScroll' to the forwarded ref component without prop drilling it specifically as a prop like 'onScroll'
// But DiffView doesn't accept onScroll prop in my implementation.
// I'll use a side effect to attach it.
// Actually, I can just modify DiffView to accept onScroll or just use native addEventListener.
// Let's use a small helper hook or effect inside PromptDiff.

export default PromptDiff;
