import 'dotenv/config';
import { SuiClient } from "@mysten/sui/client";
import { Transaction } from "@mysten/sui/transactions";
import { Ed25519Keypair } from "@mysten/sui/keypairs/ed25519";
import { fromHex } from "@mysten/bcs";
import { bcs } from "@mysten/sui/bcs";

// -----------------------------------------------------
// Load ENV
// -----------------------------------------------------
const SUI_RPC = process.env.SUI_RPC;
const PACKAGE_ID = process.env.SUI_PACKAGE_ID;
const MODULE = process.env.SUI_MODULE;
const FUNCTION = process.env.SUI_FUNCTION;
const TABLE_ID = process.env.SUI_TABLE_ID;

// This is HEX private key from your .env
const PRIVATE_KEY_HEX = process.env.SUI_PRIVATE_KEY;

// Optional gas coin (you provided it)
const GAS_OBJECT_ID = process.env.SUI_GAS_OBJECT_ID;
const GAS_VERSION = Number(process.env.GAS_VERSION);
const GAS_DIGEST = process.env.GAS_DIGEST;

// -----------------------------------------------------
// Create Keypair (Ed25519) from HEX secret key
// -----------------------------------------------------
const secretBytes = fromHex(PRIVATE_KEY_HEX);   // 32-byte secret key
const keypair = Ed25519Keypair.fromSecretKey(secretBytes);

// Sui client
const client = new SuiClient({ url: SUI_RPC });

// -----------------------------------------------------
// ANCHOR AUDIT FUNCTION
// -----------------------------------------------------
export async function anchorAudit(bundleHashHex, fairnessScore, timestamp) {

    // Convert bundle hash (hex) → vector<u8>
    const hashBytes = Array.from(Buffer.from(bundleHashHex.replace("0x", ""), "hex"));

    // -------------------------------------------------
    // Build PTB (Programmable Transaction Block)
    // -------------------------------------------------
    const txb = new Transaction();

    txb.setSender(keypair.toSuiAddress());
    txb.setGasBudget(20_000_000);

    // If you want to *force* using your specific gas coin
    

    // Call your Move function
    txb.moveCall({
    target: `${PACKAGE_ID}::${MODULE}::${FUNCTION}`,
    arguments: [
        txb.object(TABLE_ID),

        // vector<u8>
        txb.pure(
            bcs.vector(bcs.U8).serialize(hashBytes)
        ),

        // fairness_score: u64
        txb.pure(
            bcs.U64.serialize(fairnessScore)
        ),

        // timestamp: u64
        txb.pure(
            bcs.U64.serialize(timestamp)
        )
    ]
});

    // Build transaction bytes
    const txBytes = await txb.build({ client });
    

    // Sign using official intent-message signing
    const { signature } = await keypair.signTransaction(txBytes);

    // Execute
    const result = await client.executeTransactionBlock({
        transactionBlock: txBytes,
        signature,
        options: {
            showEffects: true,
            showEvents: true,
            showObjectChanges: true
        }
    });

    return result;
}

// -----------------------------------------------------
// TEST RUN
// -----------------------------------------------------
anchorAudit("ab12cd34ef56", 80, Math.floor(Date.now() / 1000))
    .then((res) => {
        console.log("🎉 Successfully Anchored!");
        console.log("Tx Digest:", res.digest);
        console.log(`Explorer: https://suiexplorer.com/txblock/${res.digest}?network=testnet`);
    })
    .catch((err) => {
        console.error("❌ ERROR:", err);
    });
