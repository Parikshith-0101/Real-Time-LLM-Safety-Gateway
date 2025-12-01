import React, { useMemo, useState, forwardRef } from 'react';
import { computeDiff } from '../utils/diffUtils';

const DiffView = forwardRef(({ original, sanitized, className = "", onScroll }, ref) => {
  const [viewMode, setViewMode] = useState('inline'); // 'inline' or 'side-by-side'

  const diff = useMemo(() => computeDiff(original, sanitized), [original, sanitized]);

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="flex justify-between items-center mb-2 px-1 shrink-0">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Diff Viewer</h3>
        <div className="flex bg-gray-800/50 rounded p-0.5 border border-gray-700">
          <button
            onClick={() => setViewMode('inline')}
            className={`px-2 py-0.5 text-xs rounded transition-colors ${
              viewMode === 'inline' 
                ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/30' 
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Inline
          </button>
          <button
            onClick={() => setViewMode('side-by-side')}
            className={`px-2 py-0.5 text-xs rounded transition-colors ${
              viewMode === 'side-by-side' 
                ? 'bg-purple-600/30 text-purple-300 border border-purple-500/30' 
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      <div 
        ref={ref}
        onScroll={onScroll}
        className="flex-1 overflow-auto bg-gray-900/50 border border-gray-700/50 rounded-lg p-3 font-mono text-sm leading-relaxed custom-scrollbar"
      >
        {viewMode === 'inline' ? (
          <div className="whitespace-pre-wrap break-words">
            {diff.map((part, index) => {
              if (part.type === 'insert') {
                return (
                  <span key={index} className="bg-green-900/40 text-green-300 border-b border-green-700/50 px-0.5 rounded-sm">
                    {part.value}
                  </span>
                );
              }
              if (part.type === 'delete') {
                return (
                  <span key={index} className="bg-red-900/40 text-red-300 border-b border-red-700/50 px-0.5 rounded-sm decoration-red-500/50 line-through decoration-2 select-none opacity-70">
                    {part.value}
                  </span>
                );
              }
              return <span key={index} className="text-gray-400">{part.value}</span>;
            })}
          </div>
        ) : (
          <div className="flex gap-2 h-full">
            {/* Side by Side: Left (Removals/Original context), Right (Additions/New context) */}
            <div className="flex-1 border-r border-gray-700/50 pr-2 overflow-hidden">
               {/* Show original with removals highlighted */}
               <div className="whitespace-pre-wrap break-words">
                {diff.map((part, index) => {
                  if (part.type === 'delete') {
                    return (
                      <span key={index} className="bg-red-900/40 text-red-300 border-b border-red-700/50 px-0.5 rounded-sm">
                        {part.value}
                      </span>
                    );
                  }
                  if (part.type === 'insert') return null; // Hide additions in left pane
                  return <span key={index} className="text-gray-400">{part.value}</span>;
                })}
              </div>
            </div>
            <div className="flex-1 pl-2 overflow-hidden">
               {/* Show new with additions highlighted */}
               <div className="whitespace-pre-wrap break-words">
                {diff.map((part, index) => {
                  if (part.type === 'insert') {
                    return (
                      <span key={index} className="bg-green-900/40 text-green-300 border-b border-green-700/50 px-0.5 rounded-sm">
                        {part.value}
                      </span>
                    );
                  }
                  if (part.type === 'delete') return null; // Hide removals in right pane
                  return <span key={index} className="text-gray-400">{part.value}</span>;
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

DiffView.displayName = 'DiffView';

export default DiffView;
