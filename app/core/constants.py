"""Konstanta bersama (status, jenis permintaan) + aturan transisi status pesanan.

Semua service WAJIB memakai enum ini, jangan menulis string "OPEN", "APPROVED", dst. langsung.
Nilai enum sama persis dengan yang tersimpan di database (lihat CheckConstraint di models).
"""
from enum import Enum


class OrderStatus(str, Enum):
    OPEN = "OPEN"
    ACCEPTED = "ACCEPTED"
    ON_THE_WAY = "ON_THE_WAY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DriverApplicationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ServiceRequestType(str, Enum):
    AMBIL_BARANG = "AMBIL_BARANG"
    BELIKAN_BARANG = "BELIKAN_BARANG"


FINAL_STATUSES = frozenset({OrderStatus.COMPLETED, OrderStatus.CANCELLED})

# Transisi yang sah menurut PRD 6.6. Catatan siapa yang boleh memicunya:
#   OPEN -> ACCEPTED       : hanya lewat POST /orders/{id}/accept (atomic, Driver APPROVED)
#   OPEN -> CANCELLED      : hanya lewat POST /orders/{id}/cancel (Customer pemilik)
#   ACCEPTED -> ON_THE_WAY -> COMPLETED : PATCH /orders/{id}/status oleh Driver pemilik order
# Pembatalan setelah ACCEPTED tidak termasuk MVP (D-023).
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.OPEN: frozenset({OrderStatus.ACCEPTED, OrderStatus.CANCELLED}),
    OrderStatus.ACCEPTED: frozenset({OrderStatus.ON_THE_WAY}),
    OrderStatus.ON_THE_WAY: frozenset({OrderStatus.COMPLETED}),
    OrderStatus.COMPLETED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


def can_transition(old: OrderStatus | str, new: OrderStatus | str) -> bool:
    """True jika perpindahan status old -> new sah menurut alur MVP."""
    try:
        return OrderStatus(new) in ALLOWED_TRANSITIONS[OrderStatus(old)]
    except (ValueError, KeyError):
        return False


def is_final(status: OrderStatus | str) -> bool:
    """Status akhir -> order tidak bisa diproses lagi dan chat menjadi read-only."""
    try:
        return OrderStatus(status) in FINAL_STATUSES
    except ValueError:
        return False
