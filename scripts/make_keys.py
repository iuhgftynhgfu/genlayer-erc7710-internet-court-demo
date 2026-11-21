"""Generate FRESH demo keypairs (delegator, delegate, seller) for DelegateCourt.

Writes ../.keys/keypairs.json (mode 600). These are throwaway testnet keys
for the Studio Next demo only — never a real wallet, never mainnet.
Requires: eth_account.
"""
import json
import os
from pathlib import Path

from eth_account import Account

out = Path(__file__).resolve().parent.parent / ".keys"
out.mkdir(mode=0o700, exist_ok=True)
keys = {}
for name in ("delegator", "delegate", "seller"):
    acct = Account.create()
    keys[name] = {"address": acct.address, "key": acct.key.hex()}
    print(name, acct.address)
path = out / "keypairs.json"
path.write_text(json.dumps(keys, indent=2))
os.chmod(path, 0o600)
print("wrote", path, "(mode 600 — never commit this file)")
