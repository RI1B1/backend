run:       ## jalankan API lokal
	python -m uvicorn app.main:app --reload
migrate:   ## terapkan migrasi
	python -m alembic upgrade head
revision:  ## buat migrasi baru: make revision m="tambah tabel users"
	python -m alembic revision --autogenerate -m "$(m)"
test:      ## jalankan tes
	python -m pytest -q
lint:
	python -m ruff check .
