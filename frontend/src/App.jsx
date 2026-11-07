import React, { useState } from 'react';
import {
  Wrench,
  FolderOpen,
  ArrowLeft,
  LayoutDashboard,
  Cpu,
  Database,
  History,
  Settings,
  HelpCircle,
  Search,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  X,
  Menu,
} from 'lucide-react';
import StepWizard from './components/StepWizard';
import LoadingState from './components/LoadingState';
import VerdictCard from './components/VerdictCard';
import FlipBanner from './components/FlipBanner';
import CostComparisonTable from './components/CostComparisonTable';
import RankedCausesList from './components/RankedCausesList';
import { diagnoseAppliance, calculateVerdict, getCaseRecord } from './services/api';

export default function App() {
  const [formData, setFormData] = useState({
    applianceType: "Washing Machine",
    brand: "IFB",
    age: 3.5,
    symptom: "Machine starts wash cycle, beeps continuously and stops with dE error code on the control display.",
    model: "Senator Smart Touch",
    errorCode: "dE",
    quotedRepairCost: 2400,
    newAppliancePrice: 28000,
    expectedRepairLife: 3.0,
    expectedNewLife: 10.0,
  });

  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [activeCaseId, setActiveCaseId] = useState(null);
  const [diagnosisResult, setDiagnosisResult] = useState(null);
  const [verdictResult, setVerdictResult] = useState(null);

  // Case Lookup Modal State
  const [reopenModalOpen, setReopenModalOpen] = useState(false);
  const [lookupCaseId, setLookupCaseId] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleAssessment = async () => {
    setLoading(true);
    setLoadingStep(0);

    try {
      const energyMap = {
        "Air Conditioner": { old: 11500, new: 6500 },
        "Water Heater": { old: 5500, new: 3200 },
        "Refrigerator": { old: 4800, new: 2400 },
        "Washing Machine": { old: 3200, new: 1800 },
        "Microwave Oven": { old: 1800, new: 1200 },
        "Water Purifier": { old: 1200, new: 800 },
      };
      const energy = energyMap[formData.applianceType] || energyMap["Washing Machine"];

      setLoadingStep(1);
      const diagPayload = {
        appliance_type: formData.applianceType,
        brand: formData.brand,
        age: parseFloat(formData.age) || 3.0,
        symptom_text: formData.symptom,
        model: formData.model || null,
        error_code: formData.errorCode || null,
        case_id: activeCaseId,
      };

      const diagData = await diagnoseAppliance(diagPayload);
      setDiagnosisResult(diagData);
      setActiveCaseId(diagData.case_id);

      setLoadingStep(3);
      const topBand = diagData.ranked_causes?.[0]?.cost_band?.high || 2400;
      const Q_val = (formData.quotedRepairCost !== "" && formData.quotedRepairCost !== undefined && !isNaN(Number(formData.quotedRepairCost)))
        ? parseFloat(formData.quotedRepairCost)
        : topBand;

      const costPayload = {
        Q: Q_val,
        P: parseFloat(formData.newAppliancePrice) || 28000,
        L_r: parseFloat(formData.expectedRepairLife) || 3.0,
        L_n: parseFloat(formData.expectedNewLife) || 10.0,
        E_old: energy.old,
        E_new: energy.new,
        p: 0.15,
        v: 350,
        D: 800,
        S: 1500,
        tr: 4.0,
        tn: 5.0,
        case_id: diagData.case_id,
      };

      const verdData = await calculateVerdict(costPayload);
      setLoadingStep(4);
      setVerdictResult(verdData);
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLookupCase = async () => {
    if (!lookupCaseId.trim()) return;
    try {
      const caseData = await getCaseRecord(lookupCaseId.trim());
      setActiveCaseId(caseData.id);
      if (caseData.user_input_snapshot) {
        const s = caseData.user_input_snapshot;
        setFormData((prev) => ({
          ...prev,
          applianceType: s.appliance_type || prev.applianceType,
          brand: s.brand || prev.brand,
          age: s.age || prev.age,
          symptom: s.symptom_text || prev.symptom,
          model: s.model || prev.model,
          errorCode: s.error_code || prev.errorCode,
        }));
      }
      if (caseData.returned_diagnosis) setDiagnosisResult(caseData.returned_diagnosis);
      if (caseData.final_verdict) setVerdictResult(caseData.final_verdict);
      setReopenModalOpen(false);
    } catch (e) {
      alert("Failed to retrieve case: " + e.message);
    }
  };

  const resetToWizard = () => {
    setVerdictResult(null);
  };

  return (
    <div className="min-h-screen bg-brand-canvas flex flex-col md:flex-row text-brand-dark font-sans selection:bg-brand-lime selection:text-brand-dark">
      {/* Mobile Top Header */}
      <div className="md:hidden bg-brand-dark text-white px-4 py-3.5 flex items-center justify-between border-b border-brand-darkBorder sticky top-0 z-50">
        <div
          className="flex items-center space-x-2.5 cursor-pointer"
          onClick={() => { resetToWizard(); setDiagnosisResult(null); }}
        >
          <div className="w-8 h-8 rounded-xl bg-brand-lime text-brand-dark flex items-center justify-center font-black text-sm">
            F
          </div>
          <span className="font-bold text-sm tracking-tight">FixWise Advisor</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setReopenModalOpen(true)}
            className="p-2 rounded-xl bg-brand-darkSurface text-white hover:bg-slate-800 transition"
          >
            <FolderOpen className="w-4 h-4" />
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl bg-brand-darkSurface text-white hover:bg-slate-800 transition"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Left Sidebar (Desktop & Mobile Dropdown) */}
      <aside
        className={`w-full md:w-64 lg:w-72 bg-brand-dark text-white shrink-0 p-5 flex flex-col justify-between transition-all duration-200 z-40 ${
          mobileMenuOpen ? 'block' : 'hidden md:flex'
        }`}
      >
        <div className="space-y-6">
          {/* Logo Area */}
          <div
            className="flex items-center space-x-3 cursor-pointer py-2 px-1"
            onClick={() => { resetToWizard(); setDiagnosisResult(null); setMobileMenuOpen(false); }}
          >
            <div className="w-10 h-10 rounded-2xl bg-brand-lime text-brand-dark flex items-center justify-center font-black text-lg shadow-sm">
              <Wrench className="w-5 h-5 text-brand-dark" />
            </div>
            <div>
              <h1 className="font-black text-base tracking-tight leading-none text-white">
                FixWise
              </h1>
              <p className="text-[11px] text-brand-darkMuted mt-1 font-medium">Repair or Replace Engine</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5 pt-2">
            <button
              onClick={() => { resetToWizard(); setMobileMenuOpen(false); }}
              className="w-full flex items-center space-x-3 px-3.5 py-3 rounded-2xl bg-brand-lime text-brand-dark font-extrabold text-xs transition"
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Assessment Advisor</span>
            </button>

            <button
              onClick={() => { setReopenModalOpen(true); setMobileMenuOpen(false); }}
              className="w-full flex items-center space-x-3 px-3.5 py-3 rounded-2xl text-brand-darkMuted hover:text-white hover:bg-brand-darkSurface font-semibold text-xs transition text-left"
            >
              <History className="w-4 h-4" />
              <span>Lookup Case History</span>
            </button>

            <div className="pt-4 pb-1 px-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Engine & Data
              </span>
            </div>

            <div className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-brand-darkMuted font-medium text-xs">
              <div className="flex items-center space-x-3">
                <Cpu className="w-4 h-4" />
                <span>Deterministic Math</span>
              </div>
              <span className="w-2 h-2 rounded-full bg-brand-lime"></span>
            </div>

            <div className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-brand-darkMuted font-medium text-xs">
              <div className="flex items-center space-x-3">
                <Database className="w-4 h-4" />
                <span>OEM Part Bands</span>
              </div>
              <span className="text-[10px] text-brand-darkMuted font-mono">v2.4</span>
            </div>
          </nav>
        </div>

        {/* Sidebar Bottom Featured Box (Matching Reference Promo Card) */}
        <div className="pt-6">
          <div className="bg-brand-lime text-brand-dark p-4 rounded-3xl space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider bg-black/10 px-2 py-0.5 rounded-full">
                Mathematical Model
              </span>
              <ExternalLink className="w-3.5 h-3.5 opacity-70" />
            </div>
            <p className="text-xs font-black leading-snug">
              Deterministic Lifecycle Amortization
            </p>
            <p className="text-[11px] opacity-80 leading-tight">
              Eliminating bias with verified labor rates, energy tariffs & repeat failure penalty.
            </p>
          </div>

          <div className="pt-4 text-center">
            <span className="text-[10px] text-brand-darkMuted">
              FixWise Advisor &bull; 2026
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Desktop Top Header Bar */}
        <header className="hidden md:flex h-20 bg-white border-b border-brand-border px-8 items-center justify-between sticky top-0 z-30">
          <div>
            <h2 className="text-lg font-black text-brand-dark tracking-tight">
              Appliance Decision Dashboard
            </h2>
            <p className="text-xs text-brand-muted font-medium">
              Objective financial verdicts for household appliances in India
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {/* Quick Case ID Lookup Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-brand-muted absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Lookup Case ID..."
                value={lookupCaseId}
                onChange={(e) => setLookupCaseId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleLookupCase()}
                className="w-56 pl-10 pr-4 py-2 bg-brand-canvas border border-brand-border rounded-xl text-xs font-mono text-brand-dark focus:bg-white focus:outline-none focus:border-brand-dark transition-colors"
              />
            </div>

            <button
              onClick={() => setReopenModalOpen(true)}
              className="px-4 py-2 rounded-xl bg-brand-dark hover:bg-black text-white text-xs font-bold transition flex items-center space-x-1.5"
            >
              <FolderOpen className="w-3.5 h-3.5 text-brand-lime" />
              <span>Load Case</span>
            </button>
          </div>
        </header>

        {/* Workspace Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-6xl w-full mx-auto">
          {loading ? (
            <LoadingState stepIndex={loadingStep} />
          ) : verdictResult ? (
            /* RESULT DASHBOARD VIEW */
            <div className="space-y-6 animate-fadeIn">
              {/* Context Summary Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 sm:p-5 rounded-3xl border border-brand-border shadow-xs">
                <div className="flex items-center flex-wrap gap-2 text-xs text-brand-dark">
                  <span className="font-black text-sm">{formData.brand} {formData.applianceType}</span>
                  <span className="text-brand-muted">&bull;</span>
                  <span className="text-brand-muted font-medium">Age: {formData.age} yrs</span>
                  <span className="text-brand-muted">&bull;</span>
                  <span className="font-mono bg-brand-canvas border border-brand-border text-brand-dark px-2.5 py-1 rounded-lg font-semibold text-[11px]">
                    {activeCaseId || "Assessment Active"}
                  </span>
                </div>
                <button
                  onClick={resetToWizard}
                  className="px-4 py-2 bg-brand-dark hover:bg-black text-white text-xs font-bold rounded-xl transition flex items-center justify-center space-x-1.5 self-start sm:self-auto cursor-pointer"
                >
                  <ArrowLeft className="w-3.5 h-3.5 text-brand-lime" />
                  <span>Modify Parameters & Re-run</span>
                </button>
              </div>

              {/* 1. Prominent Header Verdict Card with Uncertainty Badge */}
              <VerdictCard verdictData={verdictResult} />

              {/* 2. Flip Assumption Tipping Point Banner */}
              <FlipBanner flipSentence={verdictResult.flip_assumption} />

              {/* 3. Side-by-Side Cost Comparison Table */}
              <CostComparisonTable
                verdictData={verdictResult}
                inputs={{
                  Q: formData.quotedRepairCost,
                  P: formData.newAppliancePrice,
                  L_r: formData.expectedRepairLife,
                  L_n: formData.expectedNewLife,
                  E_old: formData.applianceType === "Air Conditioner" ? 11500 : 3200,
                  E_new: formData.applianceType === "Air Conditioner" ? 6500 : 1800,
                  v: 350,
                  p: 0.15,
                  tr: 4.0,
                  tn: 5.0,
                }}
              />

              {/* 4. Ranked Diagnostic Causes & Component Cost Bands */}
              {diagnosisResult?.ranked_causes && (
                <RankedCausesList
                  causes={diagnosisResult.ranked_causes}
                  onSelectQuote={(quote) => {
                    setFormData((prev) => ({ ...prev, quotedRepairCost: quote }));
                    handleAssessment();
                  }}
                />
              )}
            </div>
          ) : (
            /* GUIDED STEP-BY-STEP FORM WIZARD */
            <StepWizard
              formData={formData}
              setFormData={setFormData}
              onSubmit={handleAssessment}
              isSubmitting={loading}
            />
          )}
        </main>
      </div>

      {/* Case Lookup Modal */}
      {reopenModalOpen && (
        <div className="fixed inset-0 bg-brand-dark/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-xl border border-brand-border space-y-5 animate-scaleUp">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-black text-brand-dark">Reopen Saved Assessment</h3>
              <button
                onClick={() => setReopenModalOpen(false)}
                className="p-1 rounded-lg text-brand-muted hover:text-brand-dark transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-brand-muted leading-relaxed">
              Enter a previously generated Case ID to load the diagnostic profile, part price bands, and financial verdict.
            </p>
            <input
              type="text"
              placeholder="e.g. case_3a7b9c1d"
              value={lookupCaseId}
              onChange={(e) => setLookupCaseId(e.target.value)}
              className="w-full text-sm bg-brand-canvas border border-brand-border rounded-2xl px-4 py-3 font-mono text-brand-dark focus:border-brand-dark focus:bg-white focus:outline-none transition-colors"
            />
            <div className="flex space-x-3 pt-1">
              <button
                onClick={() => setReopenModalOpen(false)}
                className="flex-1 py-3 rounded-2xl border border-brand-border text-brand-dark text-xs font-bold hover:bg-brand-canvas transition"
              >
                Cancel
              </button>
              <button
                onClick={handleLookupCase}
                className="flex-1 py-3 rounded-2xl bg-brand-dark hover:bg-black text-brand-lime text-xs font-bold shadow-sm transition"
              >
                Load Case
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
