// backend/services/seal_client.js
// --------------------------------------------------------------------
// FINAL WORKING VERSION — SUI SDK FIXED
// --------------------------------------------------------------------
import crypto from "crypto";

if (!globalThis.crypto) {
  globalThis.crypto = crypto.webcrypto;
}

import fs from "fs";
import { SuiClient } from "@mysten/sui/client";
import { fromHEX } from "@mysten/sui/utils";
import { SealClient } from "@mysten/seal";

// --------------------------------------------------------------------
// CONFIG
// --------------------------------------------------------------------

const SEAL_POLICY_PACKAGE =
  "0xf0ce36656cd421dce66aef95e972e901f21689c3a7ce6402a3b12d4b17eb7b61";

const SEAL_ALLOWLIST_OBJECT_ID =
  "0x85c9763f1fb62d8ff01f33ab681bebf4d7e5891ae18f52a09bb3f01d50b070e6";

const KEY_SERVERS = [
  {
    objectId: "0x73d05d62c18d9374e3ea529e8e0ed6161da1a141a94d3f76ae3fe4e99356db75",
    weight: 1,
  },
  {
    objectId: "0xf5d14a81a982144ae441cd7d64b09027f116a468bd36e7eca494f750591623c8",
    weight: 1,
  },
];

const SUI_RPC = "https://fullnode.testnet.sui.io";

// --------------------------------------------------------------------
// CLIENTS
// --------------------------------------------------------------------

const suiClient = new SuiClient({ url: SUI_RPC });

const sealClient = new SealClient({
  suiClient,
  serverConfigs: KEY_SERVERS,
  verifyKeyServers: false,
});

// --------------------------------------------------------------------
// MAIN FUNCTION — encryptFile()
// --------------------------------------------------------------------

async function encryptFile(inputPath, identity) {
  if (!fs.existsSync(inputPath)) {
    console.error("File not found:", inputPath);
    process.exit(1);
  }

  try {
    const raw = fs.readFileSync(inputPath);

    const encrypted = await sealClient.encrypt({
    threshold: 2,
    packageId: SEAL_POLICY_PACKAGE,          // <── FIXED
    policyObjectId: SEAL_ALLOWLIST_OBJECT_ID,
    id: Buffer.from(identity, "utf8").toString("hex"),
    data: raw,
  });

    const final = {
      encryptedObject: Buffer.from(encrypted.encryptedObject).toString("base64"),
      backupKey: Buffer.from(encrypted.key).toString("base64"),
      identity,
    };

    console.log(JSON.stringify(final));
  } catch (err) {
    console.error("Seal Encryption FAILED:", err);
    process.exit(1);
  }
}

// --------------------------------------------------------------------
// CLI ENTRYPOINT
// --------------------------------------------------------------------

const input = process.argv[2];
const identity = process.argv[3];

if (!input || !identity) {
  console.error("Usage: node seal_client.js <file_path> <identity>");
  process.exit(1);
}

encryptFile(input, identity);
