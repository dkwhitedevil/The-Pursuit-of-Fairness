#!/usr/bin/env node
import { execSync } from "child_process";
import path from "path";

/**
 * Upload a file using the official Walrus CLI installed via suiup
 */
function upload(filePath) {
    const abs = path.resolve(filePath);
    console.log("Uploading to Walrus Testnet:", abs);

    const relay = process.env.WALRUS_UPLOAD_RELAY;

    let cmd = `walrus store ${abs} --epochs 2 --context testnet --json`;

    if (relay) {
        console.log(`Using WALRUS_UPLOAD_RELAY=${relay}`);
        cmd = `walrus store ${abs} --epochs 2 --context testnet --upload-relay ${relay} --json`;
    }

    try {
        const raw = execSync(cmd, { encoding: "utf8" });

        // CLI already returns valid JSON with --json
        const data = JSON.parse(raw);

        // Normalize output
        const blobId = data.blobId;
        const objectId = data.objectId;

        if (!blobId || !objectId) {
            throw new Error("Walrus output missing blobId or objectId: " + raw);
        }

        const result = {
            blobId,
            objectId,
            walrusURL: `https://walruscan.com/testnet/blob/${blobId}`,
            objectURL: `https://walruscan.com/testnet/object/${objectId}`
        };

        console.log(JSON.stringify(result));
    } catch (err) {
        console.error("Upload failed!", err.message);
        process.exit(1);
    }
}

if (process.argv[2]) {
    upload(process.argv[2]);
}
