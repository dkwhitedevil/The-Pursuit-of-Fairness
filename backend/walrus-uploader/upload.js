#!/usr/bin/env node
import fs from "fs";
import path from "path";
import dotenv from "dotenv";
dotenv.config();

import { getFullnodeUrl, SuiJsonRpcClient } from "@mysten/sui/jsonRpc";
import { Ed25519Keypair } from "@mysten/sui/keypairs/ed25519";
import { fromHEX } from "@mysten/sui/utils";
import { walrus } from "@mysten/walrus";

async function upload(filePath) {
    const abs = path.resolve(filePath);
    console.log("Uploading to Walrus Testnet:", abs);

    // --- Load signer ---
    const PRIVATE_KEY = process.env.SUI_PRIVATE_KEY;
    if (!PRIVATE_KEY) {
        console.error("Missing SUI_PRIVATE_KEY in environment!");
        process.exit(1);
    }

    const signer = Ed25519Keypair.fromSecretKey(fromHEX(PRIVATE_KEY));

    // --- Build client ---
    const client = new SuiJsonRpcClient({
        url: getFullnodeUrl("testnet"),
        network: "testnet",
    }).$extend(
        walrus({
            uploadRelay: {
                host: process.env.WALRUS_UPLOAD_RELAY,
            },
        })
    );

    const data = fs.readFileSync(abs);

    try {
        const result = await client.walrus.writeBlob({
            blob: data,
            epochs: 2,
            deletable: false,
            signer,
        });

        const out = {
            blobId: result.blobId,
            objectId: result.id,
            walrusURL: `https://walruscan.com/testnet/blob/${result.blobId}`,
            objectURL: `https://walruscan.com/testnet/object/${result.id}`,
        };

        console.log(JSON.stringify(out));
    } catch (err) {
        console.error("Walrus upload failed:", err);
        process.exit(1);
    }
}

if (process.argv[2]) upload(process.argv[2]);
else {
    console.error("Usage: node upload.js <file>");
    process.exit(1);
}
