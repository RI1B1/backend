# API Contract AnterinDong — DRAFT v0.1

Status: **usulan Tech Lead BE untuk T-002**, perlu disetujui Tech Lead FE dan PIC fitur.
Acuan: PRD v1.2 bagian 10 dan 11. Perubahan setelah disetujui wajib lewat PR berlabel `api-change`.

Base URL: `/api/v1` · Swagger: `/docs` · Waktu: UTC, ISO 8601 · Teks pengguna: Bahasa Indonesia.

## 1. Konvensi

**Autentikasi.** Header `Authorization: Bearer <access_token>`. Tidak ada SSO/Google dan tidak ada
refresh token; token berlaku 8 jam. Saat 401 `TOKEN_EXPIRED`/`INVALID_TOKEN`, Frontend mengarahkan ke login.
Backend selalu memeriksa role dan status akun ke database, jadi `role` di token hanya untuk tampilan.

**Sukses**
```json
{ "success": true, "data": { } }
{ "success": true, "data": [ ], "meta": { "page": 1, "limit": 20, "total": 57 } }
```
**Gagal**
```json
{ "success": false, "error": { "code": "ORDER_NOT_FOUND", "message": "Pesanan tidak ditemukan.", "details": null } }
```
Untuk 422, `details` berisi `[{ "field": "email", "message": "..." }]`.

**Pagination:** `?page=1&limit=20` (limit maks. 100). **ID** bertipe integer.

**Tidak ada** field/endpoint tarif, pembayaran, jarak, atau estimasi waktu (D-031 s.d. D-045).

## 2. Objek bersama

```jsonc
// User (ringkas)       { "id": 1, "name": "Budi" }
// UserMe               { "id": 1, "name": "Budi", "email": "budi@mail.ugm.ac.id", "role": "CUSTOMER", "driver_application_status": null | "PENDING" | "APPROVED" | "REJECTED" }
// Location             { "id": 3, "name": "Perpustakaan Pusat UGM", "category": "KAMPUS", "latitude": -7.7712, "longitude": 110.3775, "description": null, "is_active": true }
// ServiceType          { "id": 1, "name": "Antar-Jemput", "code": "ANTAR_JEMPUT", "description": "..." }   // code: ANTAR_JEMPUT | JASA_TITIP
// Order
{
  "id": 10,
  "status": "OPEN",                       // OPEN | ACCEPTED | ON_THE_WAY | COMPLETED | CANCELLED
  "service_type": { "id": 1, "name": "Antar-Jemput", "code": "ANTAR_JEMPUT" },
  "customer": { "id": 1, "name": "Budi" },
  "driver": null,                         // { "id": 2, "name": "Sari" } setelah ACCEPTED
  "pickup_location": { "id": 3, "name": "...", "category": "...", "latitude": 0, "longitude": 0 },
  "destination_location": { "id": 5, "name": "...", "category": "...", "latitude": 0, "longitude": 0 },
  "service_request_type": null,           // AMBIL_BARANG | BELIKAN_BARANG (hanya Jasa Titip)
  "item_description": null,
  "passenger_count": 1,
  "optional_cost_expectation": 15000,     // opsional, bukan tarif resmi
  "notes": "Tunggu di lobi",
  "created_at": "2026-11-25T03:00:00Z",
  "updated_at": "2026-11-25T03:00:00Z"
}
```
Lokasi pada Order tetap ditampilkan walau lokasi kemudian dinonaktifkan (PRD 6.9).
Email Customer/Driver **tidak** ditampilkan pada Order; hanya `id` dan `name`.

## 3. Endpoint

Kolom **Akses**: `Publik` tanpa token · `Login` semua pengguna login · `CUSTOMER` · `DRIVER*` = wajib APPROVED · `ADMIN`.

### Auth
| Method & path | Akses | Request | Response |
|---|---|---|---|
| `POST /auth/login` | Publik | `{ "email", "password" }` | `{ "access_token", "token_type": "bearer", "user": UserMe }` |
| `GET /auth/me` | Login | – | `UserMe` |

Error login: `EMAIL_DOMAIN_NOT_ALLOWED` (422, domain bukan `@mail.ugm.ac.id`), `INVALID_CREDENTIALS` (401), `USER_SUSPENDED` (403).
Pesan `INVALID_CREDENTIALS` sama untuk email tidak ada dan password salah.

### Services & Locations
| Method & path | Akses | Catatan |
|---|---|---|
| `GET /services` | Login | Daftar ServiceType aktif |
| `GET /locations` | Login | Hanya lokasi `is_active=true`. Query: `category`, `q` (cari nama). Tanpa pagination (katalog kecil) |
| `GET /locations/{id}` | Login | 404 `LOCATION_NOT_FOUND` |

### Orders
| Method & path | Akses | Request / Response |
|---|---|---|
| `POST /orders` | CUSTOMER, DRIVER | Lihat payload di bawah → `Order` (201), status `OPEN` |
| `GET /orders/my` | Login | Pesanan milik pengguna sebagai Customer. Query `status`, pagination → `Order[]` |
| `GET /orders/available` | DRIVER* | Hanya status `OPEN`, terbaru dulu, pagination → `Order[]` |
| `GET /orders/{id}` | Login | Hanya Customer pemilik, Driver penerima, Driver* untuk order `OPEN`, atau ADMIN. Selain itu 403 `ORDER_ACCESS_DENIED` |
| `POST /orders/{id}/accept` | DRIVER* | Tanpa body → `Order` (status `ACCEPTED`). Atomic. 409 `ORDER_ALREADY_TAKEN` jika sudah diambil/ bukan `OPEN` |
| `PATCH /orders/{id}/status` | DRIVER* (penerima) | `{ "status": "ON_THE_WAY" }` lalu `{ "status": "COMPLETED" }` → `Order`. 409 `INVALID_STATUS_TRANSITION` |
| `POST /orders/{id}/cancel` | CUSTOMER (pemilik) | Tanpa body → `Order` (`CANCELLED`). 409 `ORDER_NOT_CANCELLABLE` jika bukan `OPEN` |

Payload `POST /orders`:
```jsonc
// Antar-Jemput
{ "service_type_id": 1, "pickup_location_id": 3, "destination_location_id": 5,
  "passenger_count": 1, "notes": "…", "optional_cost_expectation": 15000 }

// Jasa Titip
{ "service_type_id": 2, "service_request_type": "BELIKAN_BARANG",
  "pickup_location_id": 7,        // lokasi asal / toko
  "destination_location_id": 5,
  "item_description": "Fotokopi 20 lembar", "notes": "…", "optional_cost_expectation": 10000 }
```
Validasi: lokasi harus ada dan aktif (`LOCATION_NOT_FOUND`/`LOCATION_INACTIVE`); `passenger_count` ≥ 1 (Antar-Jemput);
Jasa Titip wajib `service_request_type` dan `item_description`; `optional_cost_expectation` ≥ 0 dan opsional;
pickup dan destination tidak boleh sama. Setiap perubahan status dicatat di `order_status_logs`.

### Messages (chat)
| Method & path | Akses | Request / Response |
|---|---|---|
| `GET /orders/{id}/messages` | Customer & Driver terkait | Query `after_id` (opsional, untuk polling ~5 detik). Response `data`: `{ "read_only": false, "items": [Message] }` |
| `POST /orders/{id}/messages` | Customer & Driver terkait | `{ "message": "teks, 1–2000 karakter" }` → `Message` (201) |

`Message`: `{ "id", "order_id", "sender": { "id", "name" }, "message", "created_at" }`.
Chat baru tersedia setelah `ACCEPTED`. Saat `COMPLETED`/`CANCELLED`, `read_only=true` dan POST → 409 `CHAT_CLOSED`.
Pengguna tidak terkait → 403 `ORDER_ACCESS_DENIED`. Admin tidak ikut chat.

### Driver
| Method & path | Akses | Request / Response |
|---|---|---|
| `POST /driver/applications` | Login | `{ "application_note": "opsional" }` → `DriverApplication` (201). 409 `DRIVER_APPLICATION_EXISTS` jika masih `PENDING` atau sudah `APPROVED` (yang `REJECTED` boleh mengajukan ulang) |
| `GET /driver/application` | Login | Pengajuan terbaru milik sendiri. 404 `DRIVER_APPLICATION_NOT_FOUND` |
| `GET /driver/orders/history` | DRIVER* | Order yang pernah diterima, pagination → `Order[]` |

`DriverApplication`: `{ "id", "status", "application_note", "reviewed_at", "created_at", "user": { "id", "name" } }`.

### Admin (semua `ADMIN`)
| Method & path | Request / Response |
|---|---|
| `GET /admin/summary` | `{ "orders_by_status": { "OPEN": 0, "ACCEPTED": 0, "ON_THE_WAY": 0, "COMPLETED": 0, "CANCELLED": 0 }, "orders_total": 0, "pending_driver_applications": 0 }` |
| `GET /admin/orders` | Query `status`, pagination → `Order[]` |
| `GET /admin/driver-applications` | Query `status`, pagination → `DriverApplication[]` |
| `PATCH /admin/driver-applications/{id}` | `{ "status": "APPROVED" \| "REJECTED" }`. Hanya dari `PENDING`, selain itu 409 `CONFLICT`. Saat `APPROVED`, `users.role` menjadi `DRIVER` |
| `POST /admin/locations` | `{ "name", "category", "latitude", "longitude", "description?" }` → `Location` (201) |
| `PATCH /admin/locations/{id}` | Field di atas (parsial) + `is_active` → `Location` |
| `DELETE /admin/locations/{id}` | **Soft delete**: set `is_active=false` → `Location` (bukan menghapus baris, agar riwayat aman) |

## 4. Kode error

| Code | HTTP | Arti |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Input tidak valid (`details` per field) |
| `BAD_REQUEST` | 400 | Permintaan tidak valid |
| `UNAUTHORIZED` / `INVALID_TOKEN` / `TOKEN_EXPIRED` | 401 | Belum login / token salah / token kedaluwarsa |
| `INVALID_CREDENTIALS` | 401 | Email atau password salah |
| `FORBIDDEN` | 403 | Role tidak sesuai |
| `USER_SUSPENDED` | 403 | Akun dinonaktifkan |
| `DRIVER_NOT_APPROVED` | 403 | Belum berstatus Driver APPROVED |
| `ORDER_ACCESS_DENIED` | 403 | Bukan pihak terkait pesanan |
| `EMAIL_DOMAIN_NOT_ALLOWED` | 422 | Domain bukan `@mail.ugm.ac.id` |
| `NOT_FOUND`, `USER_NOT_FOUND`, `ORDER_NOT_FOUND`, `SERVICE_NOT_FOUND`, `LOCATION_NOT_FOUND`, `DRIVER_APPLICATION_NOT_FOUND` | 404 | Data tidak ditemukan |
| `ORDER_ALREADY_TAKEN`, `ORDER_NOT_CANCELLABLE`, `INVALID_STATUS_TRANSITION`, `CHAT_CLOSED`, `DRIVER_APPLICATION_EXISTS`, `CONFLICT` | 409 | Konflik keadaan data |
| `LOCATION_INACTIVE` | 422 | Lokasi tidak aktif untuk pesanan baru |
| `INTERNAL_ERROR` | 500 | Kesalahan server (tanpa detail internal) |

## 5. Keputusan yang perlu disetujui

1. Saat Admin meng-approve, `users.role` diubah menjadi `DRIVER`; Driver tetap bisa membuat pesanan sebagai Customer. Pengecekan akses Driver tetap memakai status `APPROVED`, bukan role.
2. Tidak ada refresh token; access token 8 jam.
3. `GET /orders/available` dan `POST /orders/{id}/accept` hanya untuk Driver APPROVED.
4. Chat memakai `after_id` untuk polling hemat; field ini opsional.
5. Kode kategori lokasi (`KAMPUS`, `KOS`, `PRINT`, `TOKO`, `USAHA`, `LAINNYA`) disepakati dengan Raihan/Fawwaz saat seed (T-001).
