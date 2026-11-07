import React, { useState } from 'react';
import { ChevronDown, ArrowRight, Check, SlidersHorizontal, Camera } from 'lucide-react';
import PhotoDropzone from './PhotoDropzone';

const APPLIANCE_CATEGORIES = [
  { id: "Washing Machine", label: "Washing Machine" },
  { id: "Air Conditioner", label: "Air Conditioner" },
  { id: "Refrigerator", label: "Refrigerator" },
  { id: "Water Purifier", label: "Water Purifier (RO)" },
  { id: "Water Heater", label: "Water Heater (Geyser)" },
  { id: "Microwave Oven", label: "Microwave Oven" },
];

const POPULAR_BRANDS = ["IFB", "Voltas", "Godrej", "LG", "Samsung", "Blue Star", "Kent", "Havells", "Whirlpool", "Bosch"];

const SAMPLE_SYMPTOMS = [
  "Machine beeps with dE error code on spin cycle",
  "AC outdoor compressor cuts off after 10 mins with low cooling",
  "Freezer has mountain of ice but lower compartment is warm",
  "Geyser trips 32A MCB instantly when switched on",
  "RO purifier continuous beep alarm and water flow stopped"
];

const CATEGORY_DEFAULTS = {
  "Washing Machine": { newPrice: 28000, quote: 2400, expectedNewLife: 10, symptom: "Machine starts wash cycle, beeps continuously and stops with dE error code on the control display." },
  "Air Conditioner": { newPrice: 42000, quote: 3800, expectedNewLife: 8, symptom: "AC outdoor compressor cuts off after 10 mins with low cooling and error code on display." },
  "Refrigerator": { newPrice: 32000, quote: 2200, expectedNewLife: 12, symptom: "Freezer has heavy ice buildup but lower refrigerator compartment is warm and not cooling." },
  "Water Purifier": { newPrice: 16000, quote: 1800, expectedNewLife: 6, symptom: "Continuous beep buzzer alarm and pure water flow has completely stopped." },
  "Water Heater": { newPrice: 12000, quote: 1400, expectedNewLife: 7, symptom: "Geyser trips 32A MCB instantly when switched on, heating element suspected shorted." },
  "Microwave Oven": { newPrice: 14000, quote: 1600, expectedNewLife: 8, symptom: "Turntable rotates and timer runs, but food is completely cold with loud buzzing noise." },
};

export default function StepWizard({
  formData,
  setFormData,
  onSubmit,
  isSubmitting,
}) {
  const [accordionOpen, setAccordionOpen] = useState(true);

  const handleCategorySelect = (catId) => {
    const defs = CATEGORY_DEFAULTS[catId] || {};
    setFormData((prev) => ({
      ...prev,
      applianceType: catId,
      newAppliancePrice: defs.newPrice ?? prev.newAppliancePrice,
      quotedRepairCost: defs.quote ?? prev.quotedRepairCost,
      expectedNewLife: defs.expectedNewLife ?? prev.expectedNewLife,
      symptom: defs.symptom ?? prev.symptom,
    }));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Intro Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black text-brand-dark tracking-tight">
            New Assessment
          </h2>
          <p className="text-xs sm:text-sm text-brand-muted mt-0.5">
            Deterministic lifecycle amortization comparing repair vs. modern replacement.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-bold uppercase tracking-wider bg-brand-canvas border border-brand-border text-brand-muted px-3 py-1.5 rounded-full">
            Model: Standard Cost Engine v2.4
          </span>
        </div>
      </div>

      {/* STEP 1: Appliance Profile & Symptom */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-brand-border shadow-xs space-y-6">
        <div className="flex items-center justify-between border-b border-brand-border pb-3">
          <div className="flex items-center space-x-2 text-brand-dark font-extrabold text-xs uppercase tracking-wider">
            <span className="w-5 h-5 rounded-full bg-brand-dark text-brand-lime flex items-center justify-center text-[10px] font-black">
              1
            </span>
            <span>Appliance Profile & Symptoms</span>
          </div>
          <span className="text-[11px] font-semibold text-brand-muted">Required Parameters</span>
        </div>

        {/* Appliance Category Selector */}
        <div>
          <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider mb-2.5">
            Appliance Category
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {APPLIANCE_CATEGORIES.map((cat) => {
              const isSelected = formData.applianceType === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => handleCategorySelect(cat.id)}
                  className={`p-3.5 rounded-2xl border text-left transition-all ${
                    isSelected
                      ? "bg-brand-dark text-white border-brand-dark shadow-sm"
                      : "bg-brand-canvas hover:bg-slate-100/80 text-brand-dark border-brand-border"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold truncate">{cat.label}</span>
                    {isSelected && <span className="w-2 h-2 rounded-full bg-brand-lime"></span>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Brand & Quick-Select Pills */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
              Brand / Manufacturer
            </label>
            <span className="text-[11px] text-brand-muted">Select or type custom brand</span>
          </div>
          <input
            type="text"
            value={formData.brand}
            onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
            placeholder="e.g. IFB, Voltas, Godrej, LG, Samsung"
            className="w-full text-sm bg-brand-canvas border border-brand-border rounded-2xl px-4 py-3 focus:border-brand-dark focus:bg-white focus:outline-none font-medium text-brand-dark transition-colors"
          />
          <div className="flex flex-wrap gap-1.5 pt-1">
            {POPULAR_BRANDS.map((b) => {
              const isSelected = formData.brand?.toLowerCase() === b.toLowerCase();
              return (
                <button
                  key={b}
                  type="button"
                  onClick={() => setFormData({ ...formData, brand: b })}
                  className={`text-[11px] px-2.5 py-1 rounded-lg border transition ${
                    isSelected
                      ? "bg-brand-dark text-brand-lime border-brand-dark font-bold"
                      : "bg-white text-brand-muted border-brand-border hover:border-slate-300"
                  }`}
                >
                  {b}
                </button>
              );
            })}
          </div>
        </div>

        {/* Model Number & Error Code */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
                Model / Series Number
              </label>
              {formData.model && (
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Model Captured
                </span>
              )}
            </div>
            <input
              type="text"
              value={formData.model || ''}
              onChange={(e) => setFormData({ ...formData, model: e.target.value })}
              placeholder="e.g. Senator Smart Touch, 183V Vectra"
              className="w-full text-sm bg-brand-canvas border border-brand-border rounded-2xl px-4 py-3 focus:border-brand-dark focus:bg-white focus:outline-none font-medium text-brand-dark transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
                Error Code (Optional)
              </label>
              <span className="text-[11px] text-brand-muted">Display code</span>
            </div>
            <input
              type="text"
              value={formData.errorCode || ''}
              onChange={(e) => setFormData({ ...formData, errorCode: e.target.value })}
              placeholder="e.g. dE, EC, E03, IE, 4E"
              className="w-full text-sm bg-brand-canvas border border-brand-border rounded-2xl px-4 py-3 focus:border-brand-dark focus:bg-white focus:outline-none font-mono font-medium text-brand-dark transition-colors"
            />
          </div>
        </div>

        {/* Age Selector */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
              Appliance Age: <span className="text-brand-dark font-black text-sm">{formData.age} years</span>
            </label>
            <span className="text-[11px] text-brand-muted font-medium">
              {formData.age < 3 ? "Early Lifecycle" : formData.age <= 7 ? "Mid Lifecycle" : "Late Lifecycle"}
            </span>
          </div>
          <input
            type="range"
            min="0.5"
            max="15"
            step="0.5"
            value={formData.age}
            onChange={(e) => setFormData({ ...formData, age: parseFloat(e.target.value) })}
            className="w-full accent-brand-dark cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-brand-muted font-bold">
            <span>New (0.5 yr)</span>
            <span>5 Years</span>
            <span>10 Years</span>
            <span>15+ Years</span>
          </div>
        </div>

        {/* Plain-Language Symptom Description */}
        <div className="space-y-2">
          <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
            Symptom / Fault Description
          </label>
          <textarea
            rows="3"
            value={formData.symptom}
            onChange={(e) => setFormData({ ...formData, symptom: e.target.value })}
            placeholder="Describe the issue in everyday terms (e.g. 'AC not cooling', 'tripping MCB', 'water leaking from bottom')..."
            className="w-full text-sm bg-brand-canvas border border-brand-border rounded-2xl p-4 focus:border-brand-dark focus:bg-white focus:outline-none text-brand-dark transition-colors"
          ></textarea>

          <div className="space-y-1">
            <span className="text-[10px] text-brand-muted font-bold uppercase tracking-wider">Sample Symptoms:</span>
            <div className="flex flex-wrap gap-1.5">
              {SAMPLE_SYMPTOMS.map((samp, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setFormData({ ...formData, symptom: samp })}
                  className="text-[10px] bg-brand-canvas hover:bg-slate-200/80 text-brand-muted hover:text-brand-dark px-2.5 py-1 rounded-md transition text-left truncate max-w-xs border border-brand-border"
                >
                  {samp}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* STEP 2: Cost & Budget Parameters */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-brand-border shadow-xs space-y-6">
        <div className="flex items-center justify-between border-b border-brand-border pb-3">
          <div className="flex items-center space-x-2 text-brand-dark font-extrabold text-xs uppercase tracking-wider">
            <span className="w-5 h-5 rounded-full bg-brand-dark text-brand-lime flex items-center justify-center text-[10px] font-black">
              2
            </span>
            <span>Financial Baseline & Quotes</span>
          </div>
          <span className="text-[11px] font-semibold text-brand-muted bg-brand-canvas border border-brand-border px-2.5 py-1 rounded-full">
            Standard India Retail & Service Benchmarks
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Repair Quote Input Field */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
                Technician Repair Quote (Q)
              </label>
              <span className="text-[10px] font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                OEM Part Band
              </span>
            </div>
            <div className="relative">
              <span className="absolute left-4 top-3 text-brand-muted font-bold">₹</span>
              <input
                type="number"
                min="0"
                value={formData.quotedRepairCost}
                onChange={(e) => setFormData({ ...formData, quotedRepairCost: e.target.value === '' ? '' : parseFloat(e.target.value) })}
                placeholder="e.g. 2400"
                className="w-full pl-8 pr-4 py-3 bg-brand-canvas border border-brand-border rounded-2xl text-sm font-bold text-brand-dark focus:border-brand-dark focus:bg-white focus:outline-none transition-colors"
              />
            </div>
            <p className="text-[11px] text-brand-muted leading-tight">
              Pre-filled with typical OEM part range for {formData.applianceType}. You can replace this with your technician's exact quote.
            </p>
          </div>

          {/* New Replacement Price Estimate */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
                New Replacement Price (P)
              </label>
              <span className="text-[10px] font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                Retail Median
              </span>
            </div>
            <div className="relative">
              <span className="absolute left-4 top-3 text-brand-muted font-bold">₹</span>
              <input
                type="number"
                min="0"
                value={formData.newAppliancePrice}
                onChange={(e) => setFormData({ ...formData, newAppliancePrice: e.target.value === '' ? '' : parseFloat(e.target.value) })}
                className="w-full pl-8 pr-4 py-3 bg-brand-canvas border border-brand-border rounded-2xl text-sm font-bold text-brand-dark focus:border-brand-dark focus:bg-white focus:outline-none transition-colors"
              />
            </div>
            <p className="text-[11px] text-brand-muted leading-tight">
              Average retail price for modern 4/5-star {formData.applianceType}. Adjust if you are looking at a specific model.
            </p>
          </div>
        </div>

        {/* Expected Lifespans */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-3 border-t border-brand-border">
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
              Expected Repair Life: <span className="text-brand-dark font-black">{formData.expectedRepairLife || 3.0} Years</span>
            </label>
            <input
              type="range"
              min="1"
              max="6"
              step="0.5"
              value={formData.expectedRepairLife || 3.0}
              onChange={(e) => setFormData({ ...formData, expectedRepairLife: parseFloat(e.target.value) })}
              className="w-full accent-brand-dark cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-brand-muted font-medium">
              <span>Short (1 yr)</span>
              <span>Moderate (3 yrs)</span>
              <span>Extended (6 yrs)</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-brand-dark uppercase tracking-wider">
              New Unit Lifespan: <span className="text-brand-dark font-black">{formData.expectedNewLife || 10.0} Years</span>
            </label>
            <input
              type="range"
              min="5"
              max="15"
              step="1"
              value={formData.expectedNewLife || 10.0}
              onChange={(e) => setFormData({ ...formData, expectedNewLife: parseFloat(e.target.value) })}
              className="w-full accent-brand-dark cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-brand-muted font-medium">
              <span>5 Years</span>
              <span>10 Years (Industry Standard)</span>
              <span>15 Years</span>
            </div>
          </div>
        </div>
      </div>

      {/* STEP 3: Optional Photo Upload (Rating Plate OCR) */}
      <div className="bg-white rounded-3xl border border-brand-border shadow-xs overflow-hidden">
        <button
          type="button"
          onClick={() => setAccordionOpen(!accordionOpen)}
          className="w-full p-5 text-left flex items-center justify-between bg-brand-canvas hover:bg-slate-100/70 transition"
        >
          <div className="flex items-center space-x-2 text-brand-dark font-extrabold text-xs uppercase tracking-wider">
            <span className="w-5 h-5 rounded-full bg-slate-200 text-brand-dark flex items-center justify-center text-[10px] font-black">
              3
            </span>
            <span>Optional: Upload Rating Plate / Model Sticker</span>
          </div>
          <div className="flex items-center space-x-2 text-brand-muted">
            <span className="text-xs font-medium">{accordionOpen ? "Collapse" : "Add Photo"}</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${accordionOpen ? 'rotate-180' : ''}`} />
          </div>
        </button>

        {accordionOpen && (
          <div className="p-6 border-t border-brand-border space-y-4 animate-fadeIn">
            <p className="text-xs text-brand-muted">
              Upload a clear photo of the appliance model sticker or rating plate. Optical character recognition extracts the model number, serial, and electrical wattage automatically.
            </p>
            <PhotoDropzone
              brandHint={formData.brand}
              typeHint={formData.applianceType}
              onExtraction={(data) => {
                setFormData((prev) => ({
                  ...prev,
                  brand: data.brand || prev.brand,
                  model: data.model_number || prev.model,
                  errorCode: (data.detected_error_codes && data.detected_error_codes[0]) || prev.errorCode,
                  applianceType: data.appliance_type || prev.applianceType,
                }));
              }}
            />
          </div>
        )}
      </div>

      {/* Submit Action Button - High Contrast Lime + Charcoal Button */}
      <button
        type="button"
        disabled={isSubmitting}
        onClick={onSubmit}
        className="w-full py-4 bg-brand-lime hover:bg-brand-limeHover text-brand-dark font-black tracking-wide rounded-2xl shadow-sm transition-all duration-200 text-base flex items-center justify-center space-x-2 cursor-pointer active:scale-[0.99]"
      >
        <span>Calculate Repair vs Replace Decision</span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
