import React from 'react';
import { CheckCircle2, Loader2, Circle, Cpu } from 'lucide-react';

export default function LoadingState({ stepIndex = 0, message }) {
  const steps = [
    "Analyzing appliance technical profile & rating plate...",
    "Querying diagnostic failure modes & component bands...",
    "Cross-referencing OEM parts catalog & labor standards...",
    "Executing deterministic lifecycle cost amortization...",
    "Solving sensitivity scenarios & tipping point..."
  ];

  return (
    <div className="max-w-xl mx-auto py-12 px-4 text-center space-y-6 animate-fadeIn">
      <div className="w-14 h-14 mx-auto rounded-2xl bg-brand-dark flex items-center justify-center text-brand-lime shadow-sm">
        <Cpu className="w-7 h-7" />
      </div>

      <div className="space-y-1.5">
        <h2 className="text-xl font-black text-brand-dark tracking-tight">Evaluating Assessment</h2>
        <p className="text-xs text-brand-muted">{message || "Executing deterministic lifecycle cost engine..."}</p>
      </div>

      <div className="bg-white p-6 rounded-3xl border border-brand-border text-left space-y-3.5 shadow-xs">
        {steps.map((st, idx) => {
          const isDone = idx < stepIndex;
          const isCurrent = idx === stepIndex;
          return (
            <div key={idx} className="flex items-center space-x-3 text-xs">
              {isDone ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : isCurrent ? (
                <Loader2 className="w-4 h-4 animate-spin text-brand-dark shrink-0" />
              ) : (
                <Circle className="w-4 h-4 text-slate-300 shrink-0" />
              )}
              <span
                className={
                  isCurrent
                    ? "font-bold text-brand-dark"
                    : isDone
                    ? "text-slate-500 line-through opacity-70"
                    : "text-slate-400"
                }
              >
                {st}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
