"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import WizardUpload from "@/components/WizardUpload";
import WizardBrand from "@/components/WizardBrand";
import WizardDuration from "@/components/WizardDuration";

interface WizardState {
  documentText: string;
  brandName: string;
  brandColor: string;
  duration: number;
}

function CreatePageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const defaultDuration = Number(searchParams.get("duration") || "30");

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [state, setState] = useState<WizardState>({
    documentText: "",
    brandName: "",
    brandColor: "#1A56DB",
    duration: defaultDuration,
  });

  const steps = ["Upload Content", "Brand Settings", "Duration & Pay"];

  async function handleCheckout() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          duration: state.duration,
          brand_name: state.brandName,
          brand_color: state.brandColor,
          document_text: state.documentText,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Checkout failed");
      window.location.href = data.checkout_url;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/10">
        <a href="/" className="text-xl font-bold text-white">
          <span className="text-brand-cyan">Video</span>Magic
        </a>
        <span className="text-slate-400 text-sm">Step {step} of 3</span>
      </nav>

      <div className="max-w-2xl mx-auto px-8 py-16">
        {/* Step indicator */}
        <div className="flex gap-2 mb-12">
          {steps.map((label, i) => (
            <div key={label} className="flex-1">
              <div
                className={`h-1 rounded-full mb-2 transition-colors ${
                  i + 1 <= step ? "bg-brand-cyan" : "bg-white/10"
                }`}
              />
              <div className={`text-xs ${i + 1 === step ? "text-brand-cyan" : "text-slate-500"}`}>
                {label}
              </div>
            </div>
          ))}
        </div>

        {/* Step content */}
        {step === 1 && (
          <WizardUpload
            value={state.documentText}
            onChange={(text) => setState((s) => ({ ...s, documentText: text }))}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <WizardBrand
            brandName={state.brandName}
            brandColor={state.brandColor}
            onChange={(name, color) =>
              setState((s) => ({ ...s, brandName: name, brandColor: color }))
            }
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <WizardDuration
            duration={state.duration}
            onChange={(d) => setState((s) => ({ ...s, duration: d }))}
            onBack={() => setStep(2)}
            onCheckout={handleCheckout}
            loading={loading}
            error={error}
          />
        )}
      </div>
    </main>
  );
}

export default function CreatePage() {
  return (
    <Suspense>
      <CreatePageInner />
    </Suspense>
  );
}
