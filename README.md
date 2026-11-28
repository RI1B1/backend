# Anterin Dong API (Backend)

Backend FastAPI + PostgreSQL untuk proyek Prokom Anterin Dong.
Semua endpoint ada di bawah `/api/v1`, dokumentasi Swagger di `/docs`.

## Jalan lokal

Siapkan Python 3.11+, PostgreSQL, dan database `anterin_dong` secara lokal. Buat
virtual environment, pasang dependency, lalu salin `.env.example` menjadi `.env`.
Atur `DATABASE_URL` sesuai kredensial PostgreSQL yang dipakai (lokal atau Neon)
dan isi `JWT_SECRET` dengan string acak panjang.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

- Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health (`database: "up"` artinya terhubung)

## Skema database

Database Neon tim sudah dibuat dari `schema.sql`, jadi tabelnya sudah ada.
Model SQLAlchemy dipetakan agar sesuai dengan skema tersebut; `models.py` bukan
hasil scaffold otomatis dari database.

Jangan jalankan `alembic upgrade head` atau `revision --autogenerate` pada
database Neon ini dulu. Riwayat migration di `alembic/versions` masih
menggambarkan skema lama dan belum di-baseline terhadap database yang sudah ada.
`upgrade head` berusaha membuat tabel lagi, sedangkan autogenerate hanya
membandingkan model dengan database untuk menyusun migration—bukan mengambil
struktur database menjadi model.

## Tes dan lint

```bash
python -m pytest -q
python -m ruff check .
```

Tes memakai SQLite in-memory (lihat `tests/conftest.py`: fixture `client`,
`db_session`, `make_user`), jadi tidak butuh Postgres. Sebelum membuat atau
menerapkan migration baru, riwayat Alembic harus lebih dulu diselaraskan dengan
skema Neon dan disepakati tim.

## Struktur

```
app/
  main.py            instance FastAPI, middleware, handler error
  api.py             menggabungkan semua router modul
  core/
    config.py        setting dari .env
    response.py      format respons standar (ok, paginated, fail)
    errors.py        ErrorCode, exception, handler global
    security.py      Role, JWT, get_current_user, require_role, require_approved_driver
    constants.py     OrderStatus, DriverApplicationStatus, aturan transisi status
    pagination.py    PageParams (?page=&limit=)
  db/
    base.py          Base + TimestampMixin
    session.py       engine, get_db
    registry.py      daftar impor model untuk Alembic
  modules/<modul>/   router.py, service.py, schemas.py, models.py
alembic/             migrasi
tests/               pytest
```

Modul: `auth`, `users`, `services`, `orders`, `drivers`, `locations`, `chat`, `admin`.

## Konvensi wajib

1. **Router tipis, logika di `service.py`.** Router hanya menerima request, memanggil service, lalu mengembalikan bentuk respons sesuai API contract.
2. **Respons standar menggunakan helper `app/core/response.py`.**
   - Sukses: `{"success": true, "data": ..., "meta": {...}}` (meta hanya untuk daftar)
   - Gagal: `{"success": false, "error": {"code": "...", "message": "..."}}`
   - Pengecualian: endpoint `/orders` mengikuti bentuk respons sukses pada API Reference PDF v1.3.
3. **Error: `raise` exception dari `app/core/errors.py`**, jangan `return` manual.
   ```python
   raise NotFoundError(ErrorCode.ORDER_NOT_FOUND, "Pesanan tidak ditemukan.")
   ```
   Butuh error code baru? Tambah di `ErrorCode` lewat PR.
4. **Auth guard** (semua memeriksa ke database, role di token diabaikan):
   - `user: CurrentUser = Depends(get_current_user)` : login valid, user ada dan `is_active`.
   - `Depends(require_role(Role.ADMIN))` : role di DB harus sesuai. Customer boleh juga Driver: `require_role(Role.CUSTOMER, Role.DRIVER)`.
   - `Depends(require_approved_driver)` : wajib untuk menerima pesanan; cek `driver_applications.status == APPROVED`.
   - Cek kepemilikan data (misal order milik Customer itu) dilakukan di service, error `ORDER_ACCESS_DENIED`.
   - Gunakan enum di `app/core/constants.py` (`OrderStatus`, `DriverApplicationStatus`, `can_transition`), jangan menulis string status langsung.
5. **Daftar** memakai `params: PageParams = Depends()` dan `paginated(items, page, limit, total)`.
6. **Model baru:** buat di `modules/<modul>/models.py`, lalu pastikan sudah diimpor di `app/db/registry.py`.
7. Waktu disimpan UTC (ISO 8601). Teks untuk pengguna berbahasa Indonesia, kode dan nama variabel berbahasa Inggris.
8. Rahasia hanya di `.env`. Jangan commit `.env`.
9. Setiap endpoint: muncul di Swagger, input divalidasi (Pydantic), role dicek, ada tes happy path + 1 kasus gagal.

## Aturan Git

- `main` dilindungi. Semua kerja lewat `develop`.
- Branch: `feat/<squad>-<fitur>` atau `fix/<squad>-<masalah>`, contoh `feat/be-order-create`.
- Commit: `feat:`, `fix:`, `docs:`, `refactor:`.
- PR kecil, judul menyebut fitur/ID, minimal 1 reviewer, **jangan merge PR sendiri**.
- `develop` digabung ke `main` hanya oleh Tech Lead BE.
- Perubahan skema database setelah beku: PR berlabel `db-change`. Perubahan kontrak API: PR berlabel `api-change`. Umumkan di grup Integrasi.
