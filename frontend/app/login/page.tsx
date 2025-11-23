"use client";
import { getProviders, signIn } from "next-auth/react";
import { useEffect, useState } from "react";
import NeobrutalCard from "@/components/NeobrutalCard";

export default function LoginPage() {
  const [providers, setProviders] = useState<any>(null);

  useEffect(() => {
    getProviders().then(setProviders);
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-6">
      <div className="max-w-4xl w-full">
        <div className="flex flex-col md:flex-row gap-8 items-stretch">
          <NeobrutalCard title="The Pursuit of Fairness" subtitle="Analyze datasets. Surface fairness issues. Get mitigations." accent="#ff7a18" className="flex-1">
            <div className="flex flex-col items-center">
              <img src="/logo.png" alt="PF" width={140} height={140} className="mb-4" />
              <p className="text-center text-lg opacity-90">Sign in to upload datasets, run audits, and anchor results on Sui.</p>
            </div>
          </NeobrutalCard>

          <NeobrutalCard title="Sign In" subtitle="Choose a provider to continue" accent="#00b4d8" className="w-full md:w-96">
            <div className="flex flex-col gap-4">
              {providers ? (
                Object.values(providers).map((provider: any) => (
                  <button
                    key={provider.name}
                    onClick={() => signIn(provider.id, { callbackUrl: "/dashboard" })}
                    className="neo-btn w-full text-center"
                  >
                    Sign in with {provider.name}
                  </button>
                ))
              ) : (
                <div className="text-sm opacity-80">Loading providers...</div>
              )}

              <div className="pt-2 text-center text-xs opacity-80">By signing in you agree to the terms and data usage policies.</div>
            </div>
          </NeobrutalCard>
        </div>
      </div>
    </div>
  );
}
