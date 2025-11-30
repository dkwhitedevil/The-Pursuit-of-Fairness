#!/usr/bin/env node
import fs from "fs";
import path from "path";

const fetchFn = global.fetch ?? (await import("node-fetch")).default;

async function upload(filePath) {

    const abs = path.resolve(filePath);

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
        // error must also be JSON or exit(1) without printing extra logs
        console.error(JSON.stringify({
            status: "error",
            http_status: res.status,
            message: res.statusText,
            response: text
        }));
        process.exit(1);
    }

    const json = JSON.parse(text);

    if (json.newlyCreated) {
        const x = json.newlyCreated.blobObject;
        const output = {
            blobId: x.blobId,
            objectId: x.id,
            walrusURL: `https://walruscan.com/testnet/blob/${x.blobId}`,
            objectURL: `https://walruscan.com/testnet/object/${x.id}`
        };
        console.log(JSON.stringify(output));
    } else {
        console.log(JSON.stringify(json));
    }
}

upload(process.argv[2]);
