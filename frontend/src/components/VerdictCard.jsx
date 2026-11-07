import React from 'react';
import { Wrench, ShoppingCart, ShieldCheck, AlertCircle, ArrowUpRight } from 'lucide-react';

export default function VerdictCard({ verdictData }) {
  const isRepair = verdictData.verdict === "Repair";
  const isFirm = verdictData.confidence === "firm";

  return (
    <div className="bg-white rounded-3xl p-6 sm:p-8 border border-brand-border shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-brand-border">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {/* Visual Verdict Badge */}
            <span
              className={`text-xs font-black uppercase px-3.5 py-1.5 rounded-full tracking-wider flex items-center space-x-1.5 ${
                isRepair
                  ? "bg-brand-lime text-brand-dark"
                  : "bg-brand-dark text-white"
              }`}
            >
              {isRepair ? <Wrench className="w-3.5 h-3.5" /> : <ShoppingCart className="w-3.5 h-3.5" />}
              <span>DECISION: {verdictData.verdict?.toUpperCase()}</span>
            </span>

            {/* Uncertainty Sensitivity Badge */}
            <span
              className={`text-xs font-semibold px-3 py-1 rounded-full border flex items-center space-x-1.5 ${
                isFirm
                  ? "bg-slate-50 text-slate-700 border-slate-200"
                  : "bg-amber-50 text-amber-900 border-amber-200"
              }`}
            >
              {isFirm ? (
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
              )}
              <span>
                {isFirm ? "Firm Recommendation" : `Close Call (Verify ${verdictData.volatile_parameter || 'Lifespan L_r'})`}
              </span>
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black text-brand-dark tracking-tight">
            {isRepair
              ? "Repairing is the smarter financial choice."
              : "Time to replace with a modern efficient model."}
          </h2>

          <p className="text-sm text-brand-muted max-w-2xl leading-relaxed">
            {verdictData.recommendation_summary}
          </p>
        </div>

        {/* Financial Metric Callouts */}
        <div className="flex sm:flex-row lg:flex-col gap-3 shrink-0">
          <div className="bg-brand-canvas p-4 rounded-2xl border border-brand-border min-w-[200px]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-brand-muted block mb-1">
              Net Estimated Savings
            </span>
            <div className="flex items-baseline space-x-1">
              <span className="text-2xl sm:text-3xl font-black text-brand-dark">
                ₹{(verdictData.annual_savings ?? 0).toLocaleString()}
              </span>
              <span className="text-xs font-semibold text-brand-muted">/year</span>
            </div>
            <div className="flex items-center space-x-1 text-[11px] font-semibold text-emerald-700 mt-1">
              <ArrowUpRight className="w-3 h-3" />
              <span>Lower annualized total outlay</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stat Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-5">
        <div>
          <span className="text-[11px] text-brand-muted font-medium block">Repair Annualized</span>
          <span className="text-base sm:text-lg font-bold text-brand-dark">
            ₹{(verdictData.annual_repair_cost ?? 0).toLocaleString()}
            <span className="text-xs text-brand-muted font-normal">/yr</span>
          </span>
        </div>
        <div>
          <span className="text-[11px] text-brand-muted font-medium block">Replace Annualized</span>
          <span className="text-base sm:text-lg font-bold text-brand-dark">
            ₹{(verdictData.annual_replace_cost ?? 0).toLocaleString()}
            <span className="text-xs text-brand-muted font-normal">/yr</span>
          </span>
        </div>
        <div>
          <span className="text-[11px] text-brand-muted font-medium block">Total Repair Outlay</span>
          <span className="text-base sm:text-lg font-bold text-brand-dark">
            ₹{(verdictData.total_repair_cost ?? 0).toLocaleString()}
          </span>
        </div>
        <div>
          <span className="text-[11px] text-brand-muted font-medium block">Total Replace Outlay</span>
          <span className="text-base sm:text-lg font-bold text-brand-dark">
            ₹{(verdictData.total_replace_cost ?? 0).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}
