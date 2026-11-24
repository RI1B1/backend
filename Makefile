up:        ## jalankan app + database
	docker compose up --build
migrate:   ## terapkan migrasi
	docker compose exec api alembic upgrade head
revision:  ## buat migrasi baru: make revision m="tambah tabel users"
	docker compose exec api alembic revision --autogenerate -m "$(m)"
test:      ## jalankan tes
	docker compose exec api pytest -q
lint:
	docker compose exec api ruff check .
