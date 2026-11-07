import React from 'react';
import { Scale } from 'lucide-react';

export default function FlipBanner({ flipSentence }) {
  if (!flipSentence) return null;

  return (
    <div className="bg-white rounded-2xl p-5 border border-brand-border flex items-start space-x-3.5 shadow-xs">
      <div className="w-9 h-9 rounded-xl bg-brand-dark flex items-center justify-center text-brand-lime shrink-0 mt-0.5">
        <Scale className="w-4 h-4" />
      </div>
      <div className="space-y-1">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-black uppercase tracking-wider text-brand-dark">
            Tipping Point Analysis
          </span>
          <span className="text-[10px] bg-slate-100 text-brand-muted px-2 py-0.5 rounded-full font-medium">
            Sensitivity Solver
          </span>
        </div>
        <p className="text-xs sm:text-sm text-brand-text leading-relaxed font-medium">
          {flipSentence}
        </p>
      </div>
    </div>
  );
}
