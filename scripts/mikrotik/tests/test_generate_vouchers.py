import sys
from pathlib import Path

# Add scripts/mikrotik to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_vouchers import (
    SAFE_CHARS,
    generate_single_voucher_code,
    generate_voucher_batch,
)


def test_generate_single_voucher_code_format():
    code = generate_single_voucher_code()
    assert len(code) == 9  # e.g., K7PM-4XQ9 (4 chars + hyphen + 4 chars)
    assert "-" in code
    parts = code.split("-")
    assert len(parts) == 2
    assert len(parts[0]) == 4
    assert len(parts[1]) == 4


def test_generate_voucher_code_safe_characters():
    for _ in range(100):
        code = generate_single_voucher_code()
        clean_code = code.replace("-", "")
        for char in clean_code:
            assert char in SAFE_CHARS
            assert char not in "0O1IL"


def test_generate_voucher_batch_uniqueness_and_structure():
    vouchers = generate_voucher_batch(count=50, profile="LAB-15MIN", batch_ref="TEST-BATCH-01")
    assert len(vouchers) == 50

    codes = [v["code"] for v in vouchers]
    assert len(set(codes)) == 50  # All 50 codes must be unique

    for v in vouchers:
        assert v["profile"] == "LAB-15MIN"
        assert v["batch_ref"] == "TEST-BATCH-01"
        assert v["username"] == v["code"]
        assert v["password"] == v["code"]
