module 0x0::oracle {

    use sui::object;
    use sui::tx_context::TxContext;
    use sui::transfer;
    use std::vector;

    /// One audit entry stored on-chain
    struct AuditProof has store {
        bundle_hash: vector<u8>,
        fairness_score: u64,
        timestamp: u64,
    }

    /// Shared table storing all proofs
    struct AuditTable has key, store {
        id: object::UID,
        proofs: vector<AuditProof>,
    }

    /// Deploy once — creates the shared object.
    public entry fun init_table(ctx: &mut TxContext) {
        let uid = object::new(ctx);

        let table = AuditTable {
            id: uid,
            proofs: vector::empty<AuditProof>(),
        };

        transfer::share_object(table);
    }

    /// Append a new proof to the shared table.
    public entry fun anchor_audit(
        table: &mut AuditTable,
        bundle_hash: vector<u8>,
        fairness_score: u64,
        timestamp: u64
    ) {
        let proof = AuditProof {
            bundle_hash,
            fairness_score,
            timestamp,
        };

        vector::push_back(&mut table.proofs, proof);
    }

    /// View helper: number of proofs
    public fun proof_count(table: &AuditTable): u64 {
        vector::length(&table.proofs)
    }
}
