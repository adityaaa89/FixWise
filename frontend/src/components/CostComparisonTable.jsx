import React from 'react';
import { Columns, Info } from 'lucide-react';

export default function CostComparisonTable({ verdictData, inputs }) {
  const bd = verdictData.breakdown || {};
  const rep = bd.repair || {};
  const repl = bd.replace || {};
  const isRepairWinner = verdictData.verdict === 'Repair';

  return (
    <div className="bg-white rounded-3xl p-6 sm:p-7 border border-brand-border shadow-xs space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-brand-border pb-4">
        <h3 className="text-base font-extrabold text-brand-dark flex items-center space-x-2">
          <Columns className="w-5 h-5 text-brand-dark" />
          <span>Deterministic Cost Breakdown</span>
        </h3>
        <span className="text-[11px] font-bold text-brand-muted uppercase bg-brand-canvas px-3 py-1 rounded-full border border-brand-border">
          Amortized Annual Comparison
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-brand-border text-brand-muted uppercase font-bold text-[11px]">
              <th className="py-3 px-3">Cost Component</th>
              <th className={`py-3 px-4 rounded-tl-xl ${isRepairWinner ? 'bg-slate-100/90 text-brand-dark font-extrabold' : 'bg-slate-50 text-slate-700'}`}>
                Repair Option ({inputs.L_r} yrs)
              </th>
              <th className={`py-3 px-4 rounded-tr-xl ${!isRepairWinner ? 'bg-slate-100/90 text-brand-dark font-extrabold' : 'bg-slate-50 text-slate-700'}`}>
                Replace Option ({inputs.L_n} yrs)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-medium">
            <tr>
              <td className="py-3.5 px-3 text-slate-700">1. Upfront Outlay (Quote vs Net Purchase)</td>
              <td className="py-3.5 px-4 text-brand-dark font-bold">₹{rep.quote_cost?.toLocaleString()}</td>
              <td className="py-3.5 px-4 text-brand-dark font-bold">
                ₹{repl.net_capital_outlay?.toLocaleString()}{' '}
                <span className="text-[11px] text-brand-muted font-normal">(P + D - S)</span>
              </td>
            </tr>
            <tr>
              <td className="py-3.5 px-3 text-slate-700">2. Owner's Hassle Time Cost (v = ₹{inputs.v}/hr)</td>
              <td className="py-3.5 px-4 text-slate-700">
                ₹{rep.time_hassle_cost?.toLocaleString()}{' '}
                <span className="text-[11px] text-brand-muted">({inputs.tr} hrs)</span>
              </td>
              <td className="py-3.5 px-4 text-slate-700">
                ₹{repl.time_hassle_cost?.toLocaleString()}{' '}
                <span className="text-[11px] text-brand-muted">({inputs.tn} hrs)</span>
              </td>
            </tr>
            <tr>
              <td className="py-3.5 px-3 text-slate-700">3. Repeat Breakdown Risk (p = {((inputs.p || 0.15) * 100).toFixed(0)}%)</td>
              <td className="py-3.5 px-4 text-slate-700">₹{rep.repeat_failure_risk_cost?.toLocaleString()}</td>
              <td className="py-3.5 px-4 text-brand-muted">
                ₹0 <span className="text-[10px] text-emerald-700 font-bold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">OEM Warranty</span>
              </td>
            </tr>
            <tr>
              <td className="py-3.5 px-3 text-slate-700">4. Running Energy / Water Costs (Cumulative)</td>
              <td className="py-3.5 px-4 text-slate-700">
                ₹{rep.energy_operating_cost?.toLocaleString()}{' '}
                <span className="text-[11px] text-brand-muted">(@ ₹{inputs.E_old}/yr)</span>
              </td>
              <td className="py-3.5 px-4 text-slate-700">
                ₹{repl.energy_operating_cost?.toLocaleString()}{' '}
                <span className="text-[11px] text-brand-muted">(@ ₹{inputs.E_new}/yr)</span>
              </td>
            </tr>
            <tr className="font-bold text-brand-dark bg-slate-50/70">
              <td className="py-3.5 px-3">Total Cumulative Cost (Full Lifespan)</td>
              <td className="py-3.5 px-4 font-black">₹{verdictData.total_repair_cost?.toLocaleString()}</td>
              <td className="py-3.5 px-4 font-black">₹{verdictData.total_replace_cost?.toLocaleString()}</td>
            </tr>
            <tr className="font-extrabold text-base border-t-2 border-slate-300">
              <td className="py-4 px-3 text-brand-dark">Annualized Cost Per Year</td>
              <td className={`py-4 px-4 ${isRepairWinner ? 'text-brand-dark bg-brand-limeSoft font-black' : 'text-slate-700'}`}>
                ₹{verdictData.annual_repair_cost?.toLocaleString()}
                <span className="text-xs font-semibold text-brand-muted">/yr</span>
              </td>
              <td className={`py-4 px-4 ${!isRepairWinner ? 'text-brand-dark bg-brand-limeSoft font-black' : 'text-slate-700'}`}>
                ₹{verdictData.annual_replace_cost?.toLocaleString()}
                <span className="text-xs font-semibold text-brand-muted">/yr</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Transparency & Methodology Footnote */}
      <div className="bg-brand-canvas rounded-2xl p-4 sm:p-5 border border-brand-border text-xs text-brand-muted space-y-3">
        <div className="flex items-center space-x-1.5 text-brand-dark font-bold text-[11px] uppercase tracking-wider">
          <Info className="w-3.5 h-3.5 text-brand-dark" />
          <span>Deterministic Cost Model Methodology</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-[11px] leading-relaxed">
          <div>
            <span className="font-bold text-brand-dark block mb-0.5">1. Repair Estimate (Q)</span>
            Computed from OEM replacement component price bands plus verified technician labor rates in India (or custom technician quote).
          </div>
          <div>
            <span className="font-bold text-brand-dark block mb-0.5">2. Replacement Capital Outlay (P)</span>
            Current retail median for modern 4/5-star inverter appliance, adjusted for ₹800 delivery/install (D) and ₹1,500 trade-in scrap credit (S).
          </div>
          <div>
            <span className="font-bold text-brand-dark block mb-0.5">3. Energy Running Cost (E)</span>
            Annual kWh electricity consumption based on Bureau of Energy Efficiency (BEE) star label standards at ₹8.50/unit utility tariff.
          </div>
          <div>
            <span className="font-bold text-brand-dark block mb-0.5">4. Repeat Failure Risk (p)</span>
            Stochastic probability penalty (15%) for post-repair recurrence based on appliance age and component degradation curves.
          </div>
        </div>
      </div>
    </div>
  );
}
