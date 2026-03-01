import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="mb-8 text-center">
        <a href="/" className="text-2xl font-bold text-white">
          <span className="text-brand-cyan">Video</span>Magic
        </a>
      </div>
      <SignIn
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
            identityPreviewText: "text-white",
            identityPreviewEditButtonIcon: "text-brand-cyan",
          },
        }}
      />
    </main>
  );
}
