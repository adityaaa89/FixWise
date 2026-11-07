import React from 'react';
import { Stethoscope, ArrowRight } from 'lucide-react';

export default function RankedCausesList({ causes, onSelectQuote }) {
  if (!causes || causes.length === 0) return null;

  return (
    <div className="bg-white rounded-3xl p-6 sm:p-7 border border-brand-border shadow-xs space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-brand-border pb-4">
        <h3 className="text-base font-extrabold text-brand-dark flex items-center space-x-2">
          <Stethoscope className="w-5 h-5 text-brand-dark" />
          <span>Ranked Diagnostic Causes & Part Price Bands</span>
        </h3>
        <span className="text-[11px] font-medium text-brand-muted">
          Click any component to simulate quote impact
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {causes.map((c, idx) => {
          const low = c.cost_band?.low ?? 750;
          const high = c.cost_band?.high ?? 2200;
          const isExpensive = high > 3000;
          const diff = c.diy_difficulty || "Moderate DIY";
          const isDIY = diff.includes("Easy") || diff.includes("Moderate");

          return (
            <div
              key={idx}
              onClick={() => onSelectQuote && onSelectQuote(high)}
              className="p-4 sm:p-5 rounded-2xl border border-brand-border hover:border-brand-dark transition-colors bg-brand-canvas hover:bg-white text-xs space-y-2.5 cursor-pointer group shadow-2xs"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-bold text-brand-dark text-sm group-hover:text-black transition">
                  {c.rank || idx + 1}. {c.cause}
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider shrink-0 ${
                    isDIY
                      ? "bg-emerald-100 text-emerald-900 border border-emerald-200"
                      : "bg-slate-200 text-slate-800"
                  }`}
                >
                  {diff}
                </span>
              </div>

              <p className="text-brand-muted leading-relaxed text-[11px]">{c.technical_description}</p>

              <div className="flex items-center justify-between pt-2.5 border-t border-brand-border font-semibold text-brand-dark text-xs">
                <div className="flex items-center space-x-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isExpensive ? 'bg-amber-500' : 'bg-brand-lime'
                    }`}
                  ></span>
                  <span>Part: ₹{low.toLocaleString()} – ₹{high.toLocaleString()}</span>
                </div>
                <div className="flex items-center space-x-1 text-brand-muted group-hover:text-brand-dark transition text-[11px]">
                  <span>Labor: ~{c.estimated_labor_hours ?? 1.2} hrs</span>
                  <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition" />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
