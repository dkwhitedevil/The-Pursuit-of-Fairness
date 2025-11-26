#!/usr/bin/env node
import { WalrusClient } from "@mysten/walrus";
import fs from "fs";
import path from "path";

async function upload(filePath) {
    const abs = path.resolve(filePath);
    console.log("Uploading to Walrus Testnet using SDK:", abs);

    const client = new WalrusClient({
        network: "testnet", // Official testnet
    });

    const data = fs.readFileSync(abs);

    try {
        // CORRECT usage
        const result = await client.storeBlob(data, {
            epochs: 2,
        });

        const output = {
            blobId: result.blobId,
            objectId: result.objectId,
            walrusURL: `https://walruscan.com/testnet/blob/${result.blobId}`,
            objectURL: `https://walruscan.com/testnet/object/${result.objectId}`,
        };

        console.log(JSON.stringify(output));
    } catch (err) {
        console.error("Walrus SDK upload failed:", err);
        process.exit(1);
    }
}

if (process.argv[2]) upload(process.argv[2]);
