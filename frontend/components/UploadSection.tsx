// frontend/components/UploadSection.tsx
"use client";
import { useState } from "react";

export default function UploadSection() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

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

            {result?.sui && (
              <div className="p-3 bg-white rounded border">
                <h4 className="font-medium">Sui Proof</h4>
                <div className="text-sm mt-2">
                  <div><strong>Tx Digest:</strong> {result.sui.tx_digest || result.sui_manifest?.tx_digest || "—"}</div>
                  <div><strong>Proof Hash:</strong> {result.sui.proof_hash || result.sui_manifest?.proof_hash || "—"}</div>
                  {result.sui.explorer_url && (
                    <div>
                      <a href={result.sui.explorer_url} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                        View on Sui Explorer
                      </a>
                    </div>
                  )}
                </div>
              </div>
            )}
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
