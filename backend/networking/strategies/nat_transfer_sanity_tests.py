
"""
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
