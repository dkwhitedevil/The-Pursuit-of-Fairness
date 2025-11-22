// frontend/components/UploadSection.tsx
"use client";
import { useEffect, useState } from "react";

export default function UploadSection() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [computedProofHash, setComputedProofHash] = useState<string | null>(null);

  // compute proof hash when result contains walrus blob id and sui tx digest but no proof_hash
  // runs asynchronously using Web Crypto
  useEffect(() => {
    let mounted = true;
    async function compute() {
      setComputedProofHash(null);
      if (!result) return;
      try {
        const blob = result.walrus?.blobId || result.walrus?.blob_id || (result.walrus && (result.walrus.blob || result.walrus.id)) || null;
        let txDigest = null;
        const s = result.sui || {};
        const manifest = result.sui_manifest || {};
        const pick = (obj: any, ...keys: string[]) => {
          for (const k of keys) {
            if (!obj) continue;
            const v = obj[k];
            if (v !== undefined && v !== null && v !== "") return v;
          }
          return null;
        };
        txDigest = pick(s, 'tx_digest', 'tx', 'txDigest', 'digest') || pick(manifest, 'tx_digest', 'tx', 'txDigest', 'digest') || (s.proof && (s.proof.tx_digest || s.proof.tx)) || null;
        if (!txDigest && s.sui_raw && typeof s.sui_raw.stdout === 'string') {
          const out = s.sui_raw.stdout;
          const m = out.match(/Transaction Digest:\s*([A-Za-z0-9]+)/);
          if (m) txDigest = m[1];
          else {
            const m2 = out.match(/\nDigest:\s*([A-Za-z0-9]+)/);
            if (m2) txDigest = m2[1];
          }
        }

        if (!blob || !txDigest) return;

        // compute sha256(blob + txDigest)
        const txt = String(blob) + String(txDigest);
        const enc = new TextEncoder();
        const data = enc.encode(txt);
        const hashBuf = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuf));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        if (mounted) setComputedProofHash(hashHex);
      } catch (e) {
        // ignore
      }
    }
    compute();
    return () => { mounted = false; };
  }, [result]);

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
      const res = await fetch("http://localhost:8000/upload-dataset", {
        method: "POST",
        body: formData,
      });
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

  return (
    <div className="bg-white p-6 rounded-xl shadow-md w-full max-w-3xl">
      <h2 className="text-xl font-semibold mb-4">Upload Dataset (CSV)</h2>

      <input
        type="file"
        accept=".csv"
        onChange={(e) => {
          setFile(e.target.files?.[0] || null);
          setResult(null);
          setError(null);
        }}
        className="mb-4 block"
      />

      <div className="flex gap-3">
        <button
          onClick={handleUpload}
          disabled={uploading || !file}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {uploading ? "Uploading..." : "Upload & Analyze"}
        </button>
        <button
          onClick={() => { setFile(null); setResult(null); setError(null); }}
          className="px-4 py-2 border rounded"
        >
          Reset
        </button>
      </div>

      {error && (
        <div className="mt-4 text-red-600">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-semibold mb-2">Audit Results</h3>

          <div className="mb-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {result?.walrus && (() => {
              const w = result.walrus || {};
              // normalize a variety of possible keys returned by different uploader versions
              const blobId = w.blob_id || w.blobId || (w.raw_response && (w.raw_response.blobId || w.raw_response.blob_id)) || w.blob || w.id || null;
              const objectId = w.sui_object_id || w.object_id || w.objectId || (w.raw_response && (w.raw_response.objectId || w.raw_response.object_id)) || w.blob_object_id || null;
              const explorer = w.explorer_link || w.explorer_url || w.walrusURL || w.objectURL || (w.raw_response && (w.raw_response.walrusURL || w.raw_response.objectURL || w.raw_response.explorer_url)) || null;

              return (
                <div className="p-3 bg-white rounded border">
                  <h4 className="font-medium">Walrus</h4>
                  <div className="text-sm mt-2">
                    <div><strong>Blob ID:</strong> {blobId || "—"}</div>
                    <div><strong>Sui Object ID:</strong> {objectId || "—"}</div>
                    <div>
                      <strong>Explorer:</strong>{' '}
                      {explorer ? (
                        <a href={explorer} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                          View on Walrus Explorer
                        </a>
                      ) : (
                        <span>—</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })()}

            {result?.sui && (() => {
              const s = result.sui || {};
              const manifest = result.sui_manifest || {};

              const pick = (obj: any, ...keys: string[]) => {
                for (const k of keys) {
                  if (!obj) continue;
                  const v = obj[k];
                  if (v !== undefined && v !== null && v !== "") return v;
                }
                return null;
              };

              // try to find tx digest from common fields
              let txDigest = pick(s, 'tx_digest', 'tx', 'txDigest', 'digest') || pick(manifest, 'tx_digest', 'tx', 'txDigest', 'digest') || (s.proof && (s.proof.tx_digest || s.proof.tx)) || null;

              // if not found, try parsing raw stdout from sui_raw
              if (!txDigest && s.sui_raw && typeof s.sui_raw.stdout === 'string') {
                const out = s.sui_raw.stdout;
                const m = out.match(/Transaction Digest:\s*([A-Za-z0-9]+)/);
                if (m) txDigest = m[1];
                else {
                  const m2 = out.match(/\nDigest:\s*([A-Za-z0-9]+)/);
                  if (m2) txDigest = m2[1];
                }
              }

              const proofHash = pick(s, 'proof_hash', 'proofHash') || pick(manifest, 'proof_hash', 'proofHash') || (s.proof && (s.proof.proof_hash || s.proof.hash)) || pick(result, 'proof_hash') || computedProofHash || null;
              const explorer = pick(s, 'explorer_url', 'explorer', 'explorerUrl') || pick(manifest, 'explorer_url', 'explorer') || null;

              // prefer provided explorer, otherwise use suiscan testnet viewer
              const explorerLink = explorer || (txDigest ? `https://suiscan.xyz/testnet/tx/${txDigest}` : null);

              return (
                <div className="p-3 bg-white rounded border">
                  <h4 className="font-medium">Sui Proof</h4>
                  <div className="text-sm mt-2">
                    <div><strong>Tx Digest:</strong> {txDigest || '—'}</div>
                    <div><strong>Proof Hash:</strong> {proofHash || '—'}</div>
                    {explorerLink && (
                      <div>
                        <a href={explorerLink} target="_blank" rel="noreferrer" className="text-blue-600 underline">
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
            <summary className="cursor-pointer">Raw JSON response</summary>
            <pre className="text-sm overflow-auto max-h-96 bg-white p-3 rounded mt-2">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

// compute proof hash when result contains walrus blob id and sui tx digest but no proof_hash
// this runs in the browser using Web Crypto and sets `computedProofHash` in the component state
// NOTE: we attach a global side-effect hook above; since this file is a simple component module
// we re-run the computation when `result` changes via useEffect. Add the hook now.
