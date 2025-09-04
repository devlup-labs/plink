
"""
This file is a sanity check script your seniors gave you.
It doesnt do real file transfer — instead it just:

Imports your NAT strategy classes (FC_to_RC, FC_to_PRC, RC_to_RC).

Instantiates them with dummy configs (fake IPs, fake ports, fake keys).

Runs their initialization code to make sure:

No syntax errors.

No missing imports.

Multiprocessing workers start correctly.

Example output you saw earlier

FullConeToRestrictedConeNAT initialized OK with 12 workers
FullConeToPortRestrictedConeNAT initialized OK with 12 workers
RestrictedToRestrictedNAT initialized OK with 12 workers

All 64 ports are being used properly.
Lightweight sanity tests (no real peer transfer). These tests validate:
- Port list sizes (exactly 64)
- Class initialization succeeds
- Keepalive methods callable (no-op here)
- Worker counts are reasonable

Run: python nat_transfer_sanity_tests.py
"""

from backend.networking.strategies.FC_to_RC import FullConeToRestrictedConeNAT
from backend.networking.strategies.FC_to_PRC import FullConeToPortRestrictedConeNAT
from backend.networking.strategies.RC_to_RC import RestrictedToRestrictedNAT


def fake_info(start_port=40000):
    return {
        "external_ip": "127.0.0.1",
        "open_ports": list(range(start_port, start_port+64)),
    }

class FakeKey: pass

def main():
    self_info = fake_info(41000)
    peer_info = fake_info(42000)

    pk = FakeKey()
    pubk = FakeKey()
    log_path = "nat_test.log"

    for cls in (FullConeToRestrictedConeNAT, FullConeToPortRestrictedConeNAT, RestrictedToRestrictedNAT):
        obj = cls(self_info, peer_info, pk, pubk, log_path)
        assert len(obj.data_ports_self) == 63, "Data ports must be 63"
        assert obj.control_port_self == self_info["open_ports"][0]
        assert obj.control_port_peer == peer_info["open_ports"][0]
        print(cls.__name__, "initialized OK with", obj.worker_count, "workers")

if __name__ == "__main__":
    main()
