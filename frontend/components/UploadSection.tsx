"use client";
import { useEffect, useState } from "react";
import NeobrutalCard from "./NeobrutalCard";

export default function UploadSection() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [computedProofHash, setComputedProofHash] = useState<string | null>(null);

  // ---------------------------------------------------------------
  // Compute Proof Hash from (blobId + txDigest) if backend didn't send one
  // ---------------------------------------------------------------
  useEffect(() => {
    let mounted = true;

    async function compute() {
      setComputedProofHash(null);
      if (!result) return;

      try {
        // 1. Get Walrus Blob ID
        const w = result.walrus || {};
        const blob =
          w.blobId ||
          w.blob_id ||
          w.id ||
          w.blob ||
          (w.raw_response && (w.raw_response.blobId || w.raw_response.blob_id)) ||
          null;

        // 2. Get Tx Digest
        const s = result.sui || {};
        const manifest = result.sui_manifest || {};

        const pick = (obj: any, ...keys: string[]) => {
          for (const k of keys) {
            if (obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== "") {
              return obj[k];
            }
          }
          return null;
        };

        let txDigest =
          pick(s, "tx_digest", "txDigest", "digest", "tx") ||
          pick(manifest, "tx_digest", "txDigest", "digest", "tx") ||
          (s.proof && (s.proof.tx_digest || s.proof.tx)) ||
          null;

        // NEW → Parse from "raw" string if no structured key found
        if (!txDigest && typeof s.raw === "string") {
          const m = s.raw.match(/Tx Digest:\s*([A-Za-z0-9]+)/i);
          if (m) txDigest = m[1];
        }

        // NEW → Parse from stdout if backend sends it differently
        if (!txDigest && s.sui_raw && typeof s.sui_raw.stdout === "string") {
          const out = s.sui_raw.stdout;
          const m = out.match(/Transaction Digest:\s*([A-Za-z0-9]+)/i);
          if (m) txDigest = m[1];
        }

        if (!blob || !txDigest) return;

        // 3. Compute SHA256(blobId + txDigest)
        const txt = String(blob) + String(txDigest);
        const enc = new TextEncoder();
        const data = enc.encode(txt);
        const hashBuf = await crypto.subtle.digest("SHA-256", data);
        const hashHex = Array.from(new Uint8Array(hashBuf))
          .map((b) => b.toString(16).padStart(2, "0"))
          .join("");

        if (mounted) setComputedProofHash(hashHex);
      } catch (e) {
        console.error("Proof hash compute failed:", e);
      }
    }

    compute();
    return () => {
      mounted = false;
    };
  }, [result]);

  // ---------------------------------------------------------------
  // Handle Upload
  // ---------------------------------------------------------------
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
        {
          method: "POST",
          body: formData,
        }
      );

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed: ${res.status} ${text}`);
      }

      const json = await res.json();
      setResult(json);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setUploading(false);
    }
  };

  // ---------------------------------------------------------------
  // UI
  // ---------------------------------------------------------------
  return (
    <div className="w-full">
      {/* HERO SECTION */}
      <div className="neo-hero p-8 rounded-lg mb-8">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start gap-8">
          <div className="flex-1">
            <h1 className="neo-hero-title text-6xl font-extrabold leading-tight">
              The Pursuit of Fairness
            </h1>
            <p className="neo-hero-sub mt-4 text-xl opacity-90">
              Upload datasets, run fairness audits, and verify Sui-anchored proofs.
            </p>

            <div className="mt-6">
              <button
                onClick={() => {
                  const el = document.getElementById("upload-card");
                  if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
                }}
                className="neo-cta"
              >
                Upload & Analyze Now
              </button>
            </div>
          </div>

          {/* UPLOAD CARD */}
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
                    setResult(null);
                    setError(null);
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
                    onClick={() => {
                      setFile(null);
                      setResult(null);
                      setError(null);
                    }}
                    className="neo-reset px-4 py-2 border rounded"
                  >
                    Reset
                  </button>
                </div>

                {error && (
                  <div className="mt-4 text-red-600">
                    <strong>Error:</strong> {error}
                  </div>
                )}
              </div>
            </NeobrutalCard>
          </div>
        </div>
      </div>

      {/* ================================================
         RESULTS SECTION 
      ================================================= */}
      {result && (
        <div className="max-w-6xl mx-auto">
          <NeobrutalCard
            title="Audit Results"
            subtitle="Detailed backend output"
            accent="#00b4d8"
          >
            <div className="mb-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* WALRUS CARD */}
              {(() => {
                const w = result.walrus || {};
                const blobId =
                  w.blobId ||
                  w.blob_id ||
                  w.id ||
                  w.blob ||
                  (w.raw_response &&
                    (w.raw_response.blobId || w.raw_response.blob_id)) ||
                  null;

                const objectId =
                  w.objectId ||
                  w.object_id ||
                  (w.raw_response &&
                    (w.raw_response.objectId || w.raw_response.object_id)) ||
                  null;

                const explorer =
                  w.explorer ||
                  w.explorer_url ||
                  w.walrusURL ||
                  w.objectURL ||
                  (w.raw_response &&
                    (w.raw_response.walrusURL || w.raw_response.objectURL)) ||
                  null;

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

              {/* SUI PROOF CARD */}
              {(() => {
                const s = result.sui || {};
                const manifest = result.sui_manifest || {};

                const pick = (obj: any, ...keys: string[]) => {
                  for (const k of keys) {
                    if (obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== "") {
                      return obj[k];
                    }
                  }
                  return null;
                };

                // ------------ TX DIGEST EXTRACTION ------------
                let txDigest =
                  pick(s, "tx_digest", "txDigest", "digest", "tx") ||
                  pick(manifest, "tx_digest", "txDigest", "digest", "tx") ||
                  (s.proof && (s.proof.tx_digest || s.proof.tx)) ||
                  null;

                // NEW: parse the raw string
                if (!txDigest && typeof s.raw === "string") {
                  const m = s.raw.match(/Tx Digest:\s*([A-Za-z0-9]+)/i);
                  if (m) txDigest = m[1];
                }

                // NEW: parse from stdout
                if (!txDigest && s.sui_raw && typeof s.sui_raw.stdout === "string") {
                  const out = s.sui_raw.stdout;
                  const m = out.match(/Transaction Digest:\s*([A-Za-z0-9]+)/i);
                  if (m) txDigest = m[1];
                }

                // ------------ PROOF HASH EXTRACTION ------------
                let proofHash =
                  pick(s, "proof_hash", "proofHash") ||
                  pick(manifest, "proof_hash", "proofHash") ||
                  (s.proof && (s.proof.proof_hash || s.proof.hash)) ||
                  computedProofHash ||
                  null;

                const explorerLink =
                  pick(s, "explorer_url", "explorer", "explorerUrl") ||
                  (txDigest ? `https://suiscan.xyz/testnet/tx/${txDigest}` : null);

                return (
                  <div className="p-3 bg-white rounded border">
                    <h4 className="font-medium">Sui Proof</h4>
                    <div className="text-sm mt-2">
                      <div><strong>Tx Digest:</strong> {txDigest || "—"}</div>
                      <div><strong>Proof Hash:</strong> {proofHash || "—"}</div>
                      {explorerLink && (
                        <div>
                          <a
                            href={explorerLink}
                            target="_blank"
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

            {/* RAW JSON */}
            <details className="mt-3">
              <summary className="cursor-pointer">Raw JSON</summary>
              <pre className="text-sm overflow-auto max-h-96 bg-white p-3 rounded mt-2">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </NeobrutalCard>
        </div>
      )}
    </div>
  );
}
