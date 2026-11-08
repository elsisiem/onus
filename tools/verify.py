"""Verify an ONUS certificate: python3 tools/verify.py evidence/last_certificate.json"""
import json, sys, hashlib
from cryptography.hazmat.primitives import serialization as ser
c = json.load(open(sys.argv[1]))
body = json.dumps(c["statement"], sort_keys=True).encode()
assert hashlib.sha256(body).hexdigest() == c["sha256"], "hash mismatch"
ser.load_pem_public_key(c["public_key"].encode()).verify(bytes.fromhex(c["signature_ed25519"]), body)
print("OK: sha256 matches and ed25519 signature verifies;", c["statement"]["predicate"]["result"]["route"])
