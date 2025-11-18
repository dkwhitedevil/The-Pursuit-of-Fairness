"use client";
import { getProviders, signIn } from "next-auth/react";
import { useEffect, useState } from "react";

export default function LoginPage() {
  const [providers, setProviders] = useState<any>(null);

  useEffect(() => {
    getProviders().then(setProviders);
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <img src="/logo.png" alt="PF" width={120} height={120} />
        <h1 className="text-2xl font-semibold mt-4">The Pursuit of Fairness</h1>
        <div className="mt-6">
          {providers &&
            Object.values(providers).map((provider: any) => (
              <button
                key={provider.name}
                onClick={() => signIn(provider.id, { callbackUrl: "/dashboard" })}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg"
              >
                Sign in with {provider.name}
              </button>
            ))}
        </div>
      </div>
    </div>
  );
}
