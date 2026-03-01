"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";

interface ReferralData {
  code: string;
  referral_url: string;
  credit_per_referral_display: string;
}

interface CreditsData {
  balance_cents: number;
  balance_display: string;
}

export default function ReferralWidget() {
  const { user } = useUser();
  const [referral, setReferral] = useState<ReferralData | null>(null);
  const [credits, setCredits] = useState<CreditsData | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!user?.id) return;
    const uid = user.id;

    fetch(`/api/backend/users/${uid}/referral-code`, {
      headers: { "X-User-Id": uid },
    })
      .then((r) => r.json())
      .then(setReferral)
      .catch(() => {});

    fetch(`/api/backend/users/${uid}/credits`, {
      headers: { "X-User-Id": uid },
    })
      .then((r) => r.json())
      .then(setCredits)
      .catch(() => {});
  }, [user?.id]);

  function copyLink() {
    if (!referral) return;
    navigator.clipboard.writeText(referral.referral_url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (!referral) return null;

  return (
    <div className="border border-brand-gold/30 bg-brand-gold/5 rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-sm font-semibold text-brand-gold mb-0.5">Refer a Friend</div>
          <div className="text-xs text-slate-400">
            Earn {referral.credit_per_referral_display} credit when they make their first video.
          </div>
        </div>
        {credits && credits.balance_cents > 0 && (
          <div className="text-right">
            <div className="text-brand-gold font-bold text-lg">{credits.balance_display}</div>
            <div className="text-xs text-slate-500">available credit</div>
          </div>
        )}
      </div>

      <div className="flex gap-2 mt-3">
        <input
          readOnly
          value={referral.referral_url}
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-slate-300 text-xs font-mono min-w-0 truncate outline-none"
        />
        <button
          onClick={copyLink}
          className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors shrink-0 ${
            copied
              ? "bg-green-700 text-white"
              : "bg-brand-gold/20 hover:bg-brand-gold/30 text-brand-gold"
          }`}
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      {credits && credits.balance_cents > 0 && (
        <div className="mt-3 text-xs text-brand-gold/80 bg-brand-gold/10 rounded-lg px-3 py-2">
          {credits.balance_display} credit will be automatically applied at checkout.
        </div>
      )}
    </div>
  );
}
