run:       ## jalankan API lokal
	python -m uvicorn app.main:app --reload
migrate:   ## ditahan sampai riwayat Alembic diselaraskan dengan schema.sql
	@echo "Alembic belum di-baseline dengan schema.sql; upgrade dibatalkan."
	@exit 1
revision:  ## ditahan sampai riwayat Alembic diselaraskan dengan schema.sql
	@echo "Jangan autogenerate migration sebelum baseline Alembic disepakati."
	@exit 1
test:      ## jalankan tes
	python -m pytest -q
lint:
	python -m ruff check .
