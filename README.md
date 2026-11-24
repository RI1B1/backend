# Anterin Dong API (Backend)

Backend FastAPI + PostgreSQL untuk proyek Prokom Anterin Dong.
Semua endpoint ada di bawah `/api/v1`, dokumentasi Swagger di `/docs`.

## Jalan lokal (Docker)

```bash
cp .env.example .env        # lalu isi JWT_SECRET dengan string acak panjang
docker compose up --build
```

- Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health (`database: "up"` artinya terhubung)

Migrasi database:

```bash
docker compose exec api alembic revision --autogenerate -m "pesan singkat"
docker compose exec api alembic upgrade head
```

Tes dan lint:

```bash
docker compose exec api pip install -r requirements-dev.txt
docker compose exec api pytest -q
docker compose exec api ruff check .
```

## Struktur

```
app/
  main.py            instance FastAPI, middleware, handler error
  api.py             menggabungkan semua router modul
  core/
    config.py        setting dari .env
    response.py      format respons standar (ok, paginated, fail)
    errors.py        ErrorCode, exception, handler global
    security.py      Role, JWT, get_current_user, require_role
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

1. **Router tipis, logika di `service.py`.** Router hanya menerima request, memanggil service, lalu mengembalikan `ok(...)`.
2. **Respons selalu lewat helper `app/core/response.py`.**
   - Sukses: `{"success": true, "data": ..., "meta": {...}}` (meta hanya untuk daftar)
   - Gagal: `{"success": false, "error": {"code": "...", "message": "..."}}`
3. **Error: `raise` exception dari `app/core/errors.py`**, jangan `return` manual.
   ```python
   raise NotFoundError(ErrorCode.ORDER_NOT_FOUND, "Pesanan tidak ditemukan.")
   ```
   Butuh error code baru? Tambah di `ErrorCode` lewat PR.
4. **Role guard:** `user: CurrentUser = Depends(require_role(Role.DRIVER))`.
   Cek kepemilikan data (misal order milik Customer itu) di service.
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
