"""Bandingkan endpoint yang terdaftar di aplikasi dengan docs/API_CONTRACT.md.

Jalankan dari root repo:   python -m scripts.check_contract

Melaporkan:
  MISSING      ada di contract tapi belum ada di aplikasi (belum dikerjakan / salah path)
  EXTRA        ada di aplikasi tapi tidak ada di contract (perlu masuk contract atau dihapus)
  FORBIDDEN    path berbau tarif/pembayaran/rute/GPS (di luar scope MVP)
  UNPROTECTED  endpoint non-publik tanpa autentikasi (kemungkinan lupa Depends guard)

Exit code 1 nnnn jika ada MISSING (kecuali --allow-missing), FORBIDDEN, atau UNPROTECTED.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

# (METHOD, path tanpa prefix). Parameter path dinormalkan menjadi {id}.
EXPECTED = {
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("GET", "/services"),
    ("GET", "/locations"),
    ("GET", "/locations/{id}"),
    ("POST", "/orders"),
    ("GET", "/orders/my"),
    ("GET", "/orders/available"),
    ("GET", "/orders/{id}"),
    ("POST", "/orders/{id}/accept"),
    ("PATCH", "/orders/{id}/status"),
    ("POST", "/orders/{id}/cancel"),
    ("GET", "/orders/{id}/messages"),
    ("POST", "/orders/{id}/messages"),
    ("POST", "/driver/applications"),
    ("GET", "/driver/application"),
    ("GET", "/driver/orders/history"),
    ("GET", "/admin/orders"),
    ("GET", "/admin/summary"),
    ("GET", "/admin/driver-applications"),
    ("PATCH", "/admin/driver-applications/{id}"),
    ("POST", "/admin/locations"),
    ("PATCH", "/admin/locations/{id}"),
    ("DELETE", "/admin/locations/{id}"),
}
PUBLIC = {("POST", "/auth/login"), ("GET", "/health")}
IGNORED = {("GET", "/admin/ping"), ("GET", "/health")}  # endpoint infrastruktur / contoh
FORBIDDEN = re.compile(
    r"tarif|tariff|fare|price|pay|wallet|qris|voucher|promo|route|routing|distance|"
    r"navigat|gps|track|estimat|rating|escrow",
    re.IGNORECASE,
)


def norm(path: str) -> str:
    path = path.removeprefix(settings.API_PREFIX) or "/"
    return re.sub(r"\{[^}]+\}", "{id}", path)


def collect() -> dict[tuple[str, str], dict]:
    found = {}
    for path, ops in app.openapi()["paths"].items():
        for method, op in ops.items():
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                found[(method.upper(), norm(path))] = op
    return found


def main() -> int:
    allow_missing = "--allow-missing" in sys.argv
    found = collect()
    actual = set(found) - IGNORED

    missing = sorted(EXPECTED - actual)
    extra = sorted(actual - EXPECTED)
    forbidden = sorted(k for k in actual if FORBIDDEN.search(k[1]))
    unprotected = sorted(k for k in actual if k not in PUBLIC and not found[k].get("security"))

    def show(title, items, note=""):
        print(f"\n{title} ({len(items)}) {note}")
        for method, path in items:
            print(f"  {method:<7}{path}")

    print(f"Terdaftar di aplikasi: {len(actual)} endpoint | Di contract: {len(EXPECTED)} endpoint")
    show("MISSING", missing, "- di contract, belum ada di aplikasi")
    show("EXTRA", extra, "- ada di aplikasi, tidak ada di contract")
    show("FORBIDDEN", forbidden, "- di luar scope MVP")
    show("UNPROTECTED", unprotected, "- tanpa autentikasi, cek Depends guard")

    failed = bool(forbidden or unprotected or (missing and not allow_missing))
    print("\nHASIL:", "GAGAL" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
