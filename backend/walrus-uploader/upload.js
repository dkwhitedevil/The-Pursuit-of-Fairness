#!/usr/bin/env node
import { execSync } from "child_process";
import path from "path";

/**
 * Clean CLI output and extract JSON safely.
 * Walrus sometimes returns:
 *   { ... }
 * or:
 *   [ { ... } ]
 * or includes logs before JSON.
 */
function extractJson(output) {
    // remove ANSI color codes
    output = output.replace(/\x1b\[[0-9;]*m/g, "");

    // Try to match array JSON
    let match = output.match(/\[\s*{[\s\S]*}\s*\]/);
    if (match) return JSON.parse(match[0]);

    // Try to match single JSON object
    match = output.match(/\{\s*"[^]*?\}/);
    if (match) return JSON.parse(match[0]);

    throw new Error("Could not detect Walrus JSON output:\n" + output);
}

/**
 * Normalize Walrus store output to our backend format
 */
function parseWalrus(json) {
    // Walrus may return array; take first object
    const data = Array.isArray(json) ? json[0] : json;

    const res = data.blobStoreResult || data;

    if (!res)
        throw new Error("Walrus JSON missing blobStoreResult");

    const obj = res.newlyCreated?.blobObject || res.blobObject;

    if (!obj)
        throw new Error("Walrus JSON missing blobObject: " + JSON.stringify(res));

    return {
        blobId: obj.blobId || res.blobId,
        objectId: obj.id,
        walrusURL: `https://walruscan.com/testnet/blob/${obj.blobId}`,
        objectURL: `https://walruscan.com/testnet/object/${obj.id}`
    };
}

/**
 * Uploads a file via Walrus CLI
 */
function upload(filePath) {
    const abs = path.resolve(filePath);
    console.log("Uploading to Walrus Testnet:", abs);

    const relay = process.env.WALRUS_UPLOAD_RELAY;
    let cmd;

    if (relay) {
        console.log(`Using WALRUS_UPLOAD_RELAY=${relay}`);
        cmd = `walrus store ${abs} --upload-relay ${relay} --epochs 2 --json`;
    } else {
        console.log(`No WALRUS_UPLOAD_RELAY set. Using default Walrus endpoint.`);
        cmd = `walrus store ${abs} --epochs 2 --json`;
    }

    try {
        const raw = execSync(cmd, { encoding: "utf8" });
        const extracted = extractJson(raw);
        const parsed = parseWalrus(extracted);

        console.log(JSON.stringify(parsed));
    } catch (err) {
        console.error("Upload failed!", err.message);
        process.exit(1);
    }
}

if (process.argv[2]) {
    upload(process.argv[2]);
}
