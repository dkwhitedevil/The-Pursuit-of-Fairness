#!/usr/bin/env node
import fs from "fs";
import path from "path";

const fetchFn = global.fetch ?? (await import("node-fetch")).default;

async function upload(filePath) {
    const abs = path.resolve(filePath);
    console.log("Uploading to Walrus Publisher:", abs);

    const publisher =
        process.env.WALRUS_PUBLISHER ||
        "https://publisher.walrus-testnet.walrus.space";

    const fileBuffer = fs.readFileSync(abs);

    const url = `${publisher}/v1/blobs?epochs=2`;

    const res = await fetchFn(url, {
        method: "PUT",
        body: fileBuffer,
        headers: {
            "Content-Type": "application/octet-stream"
        }
    });

    const text = await res.text();

    if (!res.ok) {
        console.error("HTTP Error:", res.status, res.statusText);
        console.error("Response:", text);
        process.exit(1);
    }

    const json = JSON.parse(text);

    if (json.newlyCreated) {
        const x = json.newlyCreated.blobObject;
        const output = {
            blobId: x.blobId,
            objectId: x.id,
            walrusURL: `https://aggregator.walrus-testnet.walrus.space/v1/blobs/${x.blobId}`,
            objectURL: `https://walruscan.com/testnet/object/${x.id}`
        };
        console.log(JSON.stringify(output));
    } else {
        console.log(JSON.stringify(json));  
    }
}

upload(process.argv[2]);
