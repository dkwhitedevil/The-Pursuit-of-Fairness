// frontend/components/UploadSection.tsx
"use client";

import { useEffect, useState } from "react";
import NeobrutalCard from "./NeobrutalCard";

export default function UploadSection() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [computedProofHash, setComputedProofHash] = useState<string | null>(null);

  const pick = (obj: any, ...keys: string[]) => {
    for (const k of keys) {
      if (!obj) continue;
      const v = obj[k];
      if (v !== undefined && v !== null && v !== "") return v;
    }
    return null;
  };

  // -------------------------------------------------------------------
  // AUTO-COMPUTE proof hash: SHA256(blobId + txDigest)
  // -------------------------------------------------------------------
  useEffect(() => {
    let mounted = true;

    async function computeHash() {
      setComputedProofHash(null);
      if (!result) return;

      try {
        const wal = result.walrus || {};
        const sui = result.sui || {};

        const blobId =
          wal.blobId ||
          wal.blob_id ||
          wal.id ||
          (wal.raw && (wal.raw.blobId || wal.raw.blob_id)) ||
          null;

        let tx =
          pick(sui, "digest", "txDigest", "tx", "tx_digest") ||
          (sui.raw && pick(sui.raw, "digest", "txDigest")) ||
          null;

        if (!tx && sui.raw && typeof sui.raw.stdout === "string") {
          const m = sui.raw.stdout.match(/Digest:\s*([A-Za-z0-9]+)/);
          if (m) tx = m[1];
        }

        if (!blobId || !tx) return;

        const enc = new TextEncoder();
        const buf = enc.encode(String(blobId) + String(tx));
        const hash = await crypto.subtle.digest("SHA-256", buf);
        const arr = Array.from(new Uint8Array(hash));
        const hex = arr.map(b => b.toString(16).padStart(2, "0")).join("");

        if (mounted) setComputedProofHash(hex);
      } catch (_) {}
    }

    computeHash();
    return () => { mounted = false };
  }, [result]);

  // -------------------------------------------------------------------
  // UPLOAD HANDLER
  // -------------------------------------------------------------------
  const handleUpload = async () => {
    setError(null);

    if (!file) {
      setError("Please choose a CSV file first.");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(
        "https://the-pursuit-of-fairness-ebxs.onrender.com/upload-dataset",
        { method: "POST", body: formData }
      );

      if (!res.ok) {
        const t = await res.text();
        throw new Error(`Upload failed: ${res.status} ${t}`);
      }

      setResult(await res.json());
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setUploading(false);
    }
  };

  // -------------------------------------------------------------------
  // FRONTEND UI
  // -------------------------------------------------------------------
  return (
    <div className="w-full">
      {/* HERO */}
      <div className="neo-hero p-8 rounded-lg mb-8">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start gap-8">
          <div className="flex-1">
            <h1 className="neo-hero-title text-6xl font-extrabold leading-tight">
              The Pursuit of Fairness
            </h1>
            <p className="neo-hero-sub mt-4 text-xl opacity-90">
              Upload datasets, run fairness audits, and anchor immutable proofs on Sui.
            </p>
            <div className="mt-6">
              <button
                onClick={() => {
                  document.getElementById("upload-card")?.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                  });
                }}
                className="neo-cta"
              >
                Upload & Analyze Now
              </button>
            </div>
          </div>

          {/* Upload Box */}
          <div className="w-full md:w-96">
            <NeobrutalCard
              title="Quick Upload"
              subtitle="CSV files only — less than 10MB"
              className="shadow-lg"
            >
              <div id="upload-card">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setError(null);
                    setResult(null);
                  }}
                  className="mb-4 block w-full"
                />

                <div className="flex gap-3">
                  <button
                    onClick={handleUpload}
                    disabled={uploading || !file}
                    className="neo-btn flex-1"
                  >
                    {uploading ? "Uploading..." : "Upload & Analyze"}
                  </button>
                  <button
                    className="neo-reset px-4 py-2 border rounded"
                    onClick={() => {
                      setFile(null);
                      setResult(null);
                      setError(null);
                    }}
                  >
                    Reset
                  </button>
                </div>

                {error && (
                  <div className="mt-4 text-red-600 font-semibold">
                    {error}
                  </div>
                )}
              </div>
            </NeobrutalCard>
          </div>
        </div>
      </div>

      {/* RESULTS */}
      {result && (
        <div className="max-w-6xl mx-auto">
          <NeobrutalCard title="Audit Results" accent="#00b4d8">
            <div className="mb-3 grid grid-cols-1 sm:grid-cols-2 gap-3">

              {/* WALRUS SECTION */}
              {(() => {
                const w = result.walrus || {};
                const blobId =
                  w.blobId || w.blob_id || w.id ||
                  (w.raw && (w.raw.blobId || w.raw.blob_id));

                const objectId =
                  w.objectId || w.object_id ||
                  (w.raw && (w.raw.objectId || w.raw.object_id));

                const explorer =
                  w.explorer ||
                  w.walrusURL ||
                  w.objectURL ||
                  (w.raw && (w.raw.walrusURL || w.raw.objectURL));

                return (
                  <div className="p-3 bg-white rounded border">
                    <h4 className="font-medium">Walrus Upload</h4>
                    <div className="text-sm mt-2">
                      <div><strong>Blob ID:</strong> {blobId || "—"}</div>
                      <div><strong>Object ID:</strong> {objectId || "—"}</div>

                      {explorer && (
                        <div>
                          <a
                            href={explorer}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-600 underline"
                          >
                            View on Walrus Explorer
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* SUI SECTION */}
              {(() => {
                const s = result.sui || {};

                const tx =
                  pick(s, "digest", "txDigest", "tx", "tx_digest") ||
                  (s.raw && pick(s.raw, "digest", "txDigest"));

                const proofHash =
                  computedProofHash ||
                  pick(s, "proof_hash", "proofHash");

                const explorer =
                  s.explorer ||
                  (tx ? `https://suiexplorer.com/txblock/${tx}?network=testnet` : null);

                return (
                  <div className="p-3 bg-white rounded border">
                    <h4 className="font-medium">Sui Proof</h4>
                    <div className="text-sm mt-2">
                      <div><strong>Tx Digest:</strong> {tx || "—"}</div>
                      <div><strong>Proof Hash:</strong> {proofHash || "—"}</div>

                      {explorer && (
                        <div>
                          <a
                            href={explorer}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-600 underline"
                          >
                            View on Sui Explorer
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>

            <details className="mt-3">
              <summary className="cursor-pointer">Raw JSON</summary>
              <pre className="text-sm overflow-auto max-h-96 bg-white mt-2 p-3 rounded">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </NeobrutalCard>
        </div>
      )}
    </div>
  );
}
