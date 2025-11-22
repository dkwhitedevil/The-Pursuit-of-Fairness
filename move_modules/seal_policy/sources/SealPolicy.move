module 0xf0ce36656cd421dce66aef95e972e901f21689c3a7ce6402a3b12d4b17eb7b61::seal_policy {

    use sui::tx_context::TxContext;
    use sui::transfer;
    use sui::object;
    use std::vector;

    //
    // Shared allowlist storing approved addresses
    //
    struct AllowList has key, store {
        id: object::UID,
        addrs: vector<address>,
    }

    //
    // Initialize allowlist (publish once)
    //
    public entry fun init_allowlist(
        addrs: vector<address>,
        ctx: &mut TxContext
    ) {
        let uid = object::new(ctx);
        let al = AllowList { id: uid, addrs };
        transfer::share_object(al);
    }

    //
    // Seal APPROVAL FUNCTION
    // Called by Seal key servers via dry_run
    //
    entry fun seal_approve(
        _id: vector<u8>,
        requester: address,
        allow: &AllowList
    ) {
        let vec = &allow.addrs;
        let len = vector::length(vec);

        let idx = 0;
        let ok = false;

        // manual loop because Move has no "for"
        while (idx < len) {
            let a = *vector::borrow(vec, idx);
            if (a == requester) {
                ok = true;
                break;
            };
            idx = idx + 1;
        };

        // if not found → Seal rejects access
        assert!(ok, 1);
    }

    //
    // helper: check if addr allowed
    //
    public fun is_allowed(addr: address, allow: &AllowList): bool {
        let vec = &allow.addrs;
        let len = vector::length(vec);

        let i = 0;
        while (i < len) {
            if (*vector::borrow(vec, i) == addr) {
                return true;
            };
            i = i + 1;
        };
        false
    }
}
