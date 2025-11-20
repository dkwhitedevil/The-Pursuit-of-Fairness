#!/usr/bin/env node
import { execSync } from "child_process";
import path from "path";
import fs from "fs";

function extractJson(output) {
    // remove color codes
    output = output.replace(/\x1b\[[0-9;]*m/g, "");

    // match JSON block
    const match = output.match(/\[\s*{[\s\S]*}\s*\]/);
    if (!match) throw new Error("No JSON returned by walrus\n" + output);

    return JSON.parse(match[0]);
}

function parseWalrus(jsonArray) {
    const entry = jsonArray[0];
    const result = entry.blobStoreResult;

    if (result.newlyCreated) {
        const x = result.newlyCreated.blobObject;
        return {
            blobId: x.blobId,
            objectId: x.id,
            walrusURL: `https://walruscan.com/testnet/blob/${x.blobId}`,
            objectURL: `https://walruscan.com/testnet/object/${x.id}`
        };
    }

    throw new Error("Unsupported Walrus JSON format: " + JSON.stringify(result));
}

function upload(filePath) {
    const abs = path.resolve(filePath);
    console.log("Uploading to Walrus Testnet:", abs);

    try {
        const cmd = `walrus store ${abs} --epochs 2 --json`;
        const raw = execSync(cmd, { encoding: "utf8" });

        const jsonArr = extractJson(raw);
        const parsed = parseWalrus(jsonArr);

        const final = {
            blobId: parsed.blobId,
            objectId: parsed.objectId,
            walrusURL: parsed.walrusURL,
            objectURL: parsed.objectURL
        };

        console.log(JSON.stringify(final));
    } catch (err) {
        console.error("Upload failed!", err);
        process.exit(1);
    }
}

if (process.argv[2]) {
    upload(process.argv[2]);
}
