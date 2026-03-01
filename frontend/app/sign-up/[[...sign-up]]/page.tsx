import { SignUp } from "@clerk/nextjs";

interface Props {
  searchParams: Promise<{ ref?: string }>;
}

export default async function SignUpPage({ searchParams }: Props) {
  const { ref } = await searchParams;

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="mb-8 text-center">
        <a href="/" className="text-2xl font-bold text-white">
          <span className="text-brand-cyan">Video</span>Magic
        </a>
        <p className="text-slate-400 text-sm mt-2">Create your account to get started</p>
        {ref && (
          <div className="mt-3 inline-block px-4 py-1.5 bg-brand-gold/20 border border-brand-gold/30 rounded-full text-brand-gold text-xs font-medium">
            🎁 You were referred — your friend earns $5 when you make your first video
          </div>
        )}
      </div>
      <SignUp
        forceRedirectUrl={ref ? `/api/referral-track?code=${ref}&next=/create` : "/create"}
        appearance={{
          elements: {
            card: "bg-white/5 border border-white/15 shadow-2xl",
            headerTitle: "text-white",
            headerSubtitle: "text-slate-400",
            socialButtonsBlockButton: "border-white/20 text-white hover:bg-white/10",
            dividerLine: "bg-white/10",
            dividerText: "text-slate-500",
            formFieldLabel: "text-slate-300",
            formFieldInput: "bg-white/5 border-white/15 text-white placeholder-slate-500",
            formButtonPrimary: "bg-brand-cyan hover:bg-cyan-400 text-brand-navy font-bold",
            footerActionLink: "text-brand-cyan hover:text-cyan-400",
          },
        }}
      />
    </main>
  );
}
