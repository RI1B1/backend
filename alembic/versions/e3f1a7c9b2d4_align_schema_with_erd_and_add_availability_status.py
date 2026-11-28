"""align schema with ERD v1.3 and add users.availability_status

Menyelaraskan database (hasil 9 migration awal) dengan model SQLAlchemy di
branch develop, sekaligus menambah users.availability_status.

Ringkasan perubahan:
- Semua kolom id dan FK: integer (SERIAL) -> bigint (IDENTITY ALWAYS).
- users: + availability_status (+ CHECK), email unik case-insensitive
  (uq_users_email_lower), index idx_users_role, CHECK diganti nama.
- driver_applications: + CHECK chk_driver_app_review, index diganti nama,
  + idx_driver_app_status.
- service_types: unique index ix_service_types_code -> constraint uq_service_types_code.
- locations: latitude/longitude double -> numeric(9,6) NULLABLE, + 3 CHECK, + index.
- orders: passenger_count smallint, service_request_type varchar(20),
  CHECK diganti nama, + chk_orders_driver_by_status, index diganti/ditambah
  (termasuk index parsial).
- order_status_logs dan chat_messages: FK ON DELETE CASCADE/RESTRICT,
  CHECK/Index diganti nama, chat_messages.message -> TEXT + CHECK panjang 1..2000.
- Semua FK: ON DELETE RESTRICT (CASCADE untuk order_status_logs.order_id dan
  chat_messages.order_id).

Data tidak dihapus. Perubahan tipe/constraint dapat GAGAL jika data lama
melanggar aturan baru (mis. dua email yang hanya beda huruf besar/kecil,
atau order ACCEPTED tanpa driver). Itu disengaja: gagal keras lebih aman
daripada mengubah data diam-diam.

Revision ID: e3f1a7c9b2d4
Revises: 5d158c3a338b
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e3f1a7c9b2d4"
down_revision: Union[str, None] = "5d158c3a338b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tabel dengan kolom id serial -> identity
ID_TABLES = [
    "users",
    "driver_applications",
    "service_types",
    "locations",
    "orders",
    "order_status_logs",
    "chat_messages",
]

# (tabel, kolom) FK yang tipenya ikut berubah
FK_COLUMNS = [
    ("driver_applications", "user_id"),
    ("driver_applications", "reviewed_by"),
    ("orders", "customer_id"),
    ("orders", "driver_id"),
    ("orders", "service_type_id"),
    ("orders", "pickup_location_id"),
    ("orders", "destination_location_id"),
    ("order_status_logs", "order_id"),
    ("order_status_logs", "changed_by"),
    ("chat_messages", "order_id"),
    ("chat_messages", "sender_id"),
]

# Nama FK bawaan PostgreSQL (dibuat oleh migration awal tanpa nama eksplisit)
FK_NAMES = [
    ("driver_applications", "driver_applications_user_id_fkey"),
    ("driver_applications", "driver_applications_reviewed_by_fkey"),
    ("orders", "orders_customer_id_fkey"),
    ("orders", "orders_driver_id_fkey"),
    ("orders", "orders_service_type_id_fkey"),
    ("orders", "orders_pickup_location_id_fkey"),
    ("orders", "orders_destination_location_id_fkey"),
    ("order_status_logs", "order_status_logs_order_id_fkey"),
    ("order_status_logs", "order_status_logs_changed_by_fkey"),
    ("chat_messages", "chat_messages_order_id_fkey"),
    ("chat_messages", "chat_messages_sender_id_fkey"),
]

# FK versi baru: (tabel, kolom, tabel_ref, on_delete)
NEW_FKS = [
    ("driver_applications", "user_id", "users", "RESTRICT"),
    ("driver_applications", "reviewed_by", "users", "RESTRICT"),
    ("orders", "customer_id", "users", "RESTRICT"),
    ("orders", "driver_id", "users", "RESTRICT"),
    ("orders", "service_type_id", "service_types", "RESTRICT"),
    ("orders", "pickup_location_id", "locations", "RESTRICT"),
    ("orders", "destination_location_id", "locations", "RESTRICT"),
    ("order_status_logs", "order_id", "orders", "CASCADE"),
    ("order_status_logs", "changed_by", "users", "RESTRICT"),
    ("chat_messages", "order_id", "orders", "CASCADE"),
    ("chat_messages", "sender_id", "users", "RESTRICT"),
]

# FK versi lama (tanpa ON DELETE eksplisit): (tabel, kolom, tabel_ref)
OLD_FKS = [(t, c, ref) for (t, c, ref, _od) in NEW_FKS]

STATUSES = "'OPEN', 'ACCEPTED', 'ON_THE_WAY', 'COMPLETED', 'CANCELLED'"


def _run(statements):
    for stmt in statements:
        op.execute(stmt)


def _serial_to_identity(table):
    return [
        f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT",
        f"DROP SEQUENCE {table}_id_seq",
        f"ALTER TABLE {table} ALTER COLUMN id SET DATA TYPE bigint",
        f"ALTER TABLE {table} ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY",
        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
        f"COALESCE((SELECT max(id) FROM {table}), 0) + 1, false)",
    ]


def _identity_to_serial(table):
    return [
        f"ALTER TABLE {table} ALTER COLUMN id DROP IDENTITY",
        f"ALTER TABLE {table} ALTER COLUMN id SET DATA TYPE integer",
        f"CREATE SEQUENCE {table}_id_seq AS integer OWNED BY {table}.id",
        f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{table}_id_seq')",
        f"SELECT setval('{table}_id_seq', "
        f"COALESCE((SELECT max(id) FROM {table}), 0) + 1, false)",
    ]


def upgrade() -> None:
    stmts = []

    # 1. Lepas semua FK dulu supaya perubahan tipe tidak terhalang
    for table, name in FK_NAMES:
        stmts.append(f"ALTER TABLE {table} DROP CONSTRAINT {name}")

    # 2. id: serial -> bigint identity; kolom FK -> bigint
    for table in ID_TABLES:
        stmts += _serial_to_identity(table)
    for table, col in FK_COLUMNS:
        stmts.append(f"ALTER TABLE {table} ALTER COLUMN {col} SET DATA TYPE bigint")

    # 3. users
    stmts += [
        "ALTER TABLE users DROP CONSTRAINT ck_users_role",
        "ALTER TABLE users ADD CONSTRAINT chk_users_role "
        "CHECK (role IN ('CUSTOMER', 'DRIVER', 'ADMIN'))",
        "DROP INDEX ix_users_email",
        "CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))",
        "CREATE INDEX idx_users_role ON users (role)",
        "ALTER TABLE users ADD COLUMN availability_status VARCHAR(10) "
        "NOT NULL DEFAULT 'INACTIVE'",
        "ALTER TABLE users ADD CONSTRAINT chk_users_availability "
        "CHECK (availability_status IN ('ACTIVE', 'INACTIVE'))",
    ]

    # 4. driver_applications
    stmts += [
        "ALTER TABLE driver_applications DROP CONSTRAINT ck_driver_applications_status",
        "ALTER TABLE driver_applications ADD CONSTRAINT chk_driver_app_status "
        "CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))",
        "ALTER TABLE driver_applications ADD CONSTRAINT chk_driver_app_review "
        "CHECK (status = 'PENDING' OR "
        "(reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))",
        "DROP INDEX ix_driver_applications_user_id",
        "CREATE INDEX idx_driver_app_user ON driver_applications (user_id)",
        "CREATE INDEX idx_driver_app_status ON driver_applications (status)",
    ]

    # 5. service_types
    stmts += [
        "DROP INDEX ix_service_types_code",
        "ALTER TABLE service_types ADD CONSTRAINT uq_service_types_code UNIQUE (code)",
    ]

    # 6. locations
    stmts += [
        "ALTER TABLE locations ALTER COLUMN latitude SET DATA TYPE numeric(9,6) "
        "USING latitude::numeric(9,6)",
        "ALTER TABLE locations ALTER COLUMN longitude SET DATA TYPE numeric(9,6) "
        "USING longitude::numeric(9,6)",
        "ALTER TABLE locations ALTER COLUMN latitude DROP NOT NULL",
        "ALTER TABLE locations ALTER COLUMN longitude DROP NOT NULL",
        "ALTER TABLE locations ADD CONSTRAINT chk_locations_lat "
        "CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90)",
        "ALTER TABLE locations ADD CONSTRAINT chk_locations_lng "
        "CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)",
        "ALTER TABLE locations ADD CONSTRAINT chk_locations_pair "
        "CHECK ((latitude IS NULL) = (longitude IS NULL))",
        "CREATE INDEX idx_locations_category_active ON locations (category, is_active)",
    ]

    # 7. orders
    stmts += [
        "ALTER TABLE orders ALTER COLUMN passenger_count SET DATA TYPE smallint",
        "ALTER TABLE orders ALTER COLUMN service_request_type SET DATA TYPE varchar(20)",
        "ALTER TABLE orders DROP CONSTRAINT ck_orders_status",
        "ALTER TABLE orders DROP CONSTRAINT ck_orders_optional_cost_expectation",
        "ALTER TABLE orders DROP CONSTRAINT ck_orders_passenger_count",
        "ALTER TABLE orders DROP CONSTRAINT ck_orders_service_request_type",
        f"ALTER TABLE orders ADD CONSTRAINT chk_orders_status "
        f"CHECK (status IN ({STATUSES}))",
        "ALTER TABLE orders ADD CONSTRAINT chk_orders_request_type "
        "CHECK (service_request_type IS NULL OR "
        "service_request_type IN ('AMBIL_BARANG', 'BELIKAN_BARANG'))",
        "ALTER TABLE orders ADD CONSTRAINT chk_orders_passenger "
        "CHECK (passenger_count IS NULL OR passenger_count > 0)",
        "ALTER TABLE orders ADD CONSTRAINT chk_orders_cost "
        "CHECK (optional_cost_expectation IS NULL OR optional_cost_expectation >= 0)",
        "ALTER TABLE orders ADD CONSTRAINT chk_orders_driver_by_status CHECK ("
        "(status IN ('OPEN', 'CANCELLED') AND driver_id IS NULL) OR "
        "(status IN ('ACCEPTED', 'ON_THE_WAY', 'COMPLETED') "
        "AND driver_id IS NOT NULL))",
        "DROP INDEX ix_orders_customer_id",
        "DROP INDEX ix_orders_driver_id",
        "DROP INDEX ix_orders_service_type_id",
        "DROP INDEX ix_orders_status",
        "CREATE INDEX idx_orders_customer ON orders (customer_id, created_at DESC)",
        "CREATE INDEX idx_orders_driver ON orders (driver_id, created_at DESC) "
        "WHERE driver_id IS NOT NULL",
        "CREATE INDEX idx_orders_status ON orders (status)",
        "CREATE INDEX idx_orders_service_type ON orders (service_type_id)",
        "CREATE INDEX idx_orders_open_created ON orders (created_at DESC) "
        "WHERE status = 'OPEN'",
        "CREATE INDEX idx_orders_pickup_loc ON orders (pickup_location_id) "
        "WHERE pickup_location_id IS NOT NULL",
        "CREATE INDEX idx_orders_dest_loc ON orders (destination_location_id) "
        "WHERE destination_location_id IS NOT NULL",
    ]

    # 8. order_status_logs
    stmts += [
        "ALTER TABLE order_status_logs DROP CONSTRAINT ck_order_status_logs_new_status",
        "ALTER TABLE order_status_logs DROP CONSTRAINT ck_order_status_logs_old_status",
        f"ALTER TABLE order_status_logs ADD CONSTRAINT chk_status_log_new "
        f"CHECK (new_status IN ({STATUSES}))",
        f"ALTER TABLE order_status_logs ADD CONSTRAINT chk_status_log_old "
        f"CHECK (old_status IS NULL OR old_status IN ({STATUSES}))",
        "DROP INDEX ix_order_status_logs_order_id",
        "DROP INDEX ix_order_status_logs_changed_by",
        "CREATE INDEX idx_status_logs_order ON order_status_logs (order_id, created_at)",
        "CREATE INDEX idx_status_logs_user ON order_status_logs (changed_by)",
    ]

    # 9. chat_messages
    stmts += [
        "ALTER TABLE chat_messages ALTER COLUMN message SET DATA TYPE text",
        "ALTER TABLE chat_messages ADD CONSTRAINT chk_chat_message_length "
        "CHECK (length(message) BETWEEN 1 AND 2000)",
        "DROP INDEX ix_chat_messages_order_id",
        "DROP INDEX ix_chat_messages_sender_id",
        "CREATE INDEX idx_chat_order_time ON chat_messages (order_id, created_at)",
        "CREATE INDEX idx_chat_sender ON chat_messages (sender_id)",
    ]

    # 10. Pasang kembali semua FK dengan aturan ON DELETE yang baru
    for table, col, ref, on_delete in NEW_FKS:
        stmts.append(
            f"ALTER TABLE {table} ADD FOREIGN KEY ({col}) "
            f"REFERENCES {ref} (id) ON DELETE {on_delete}"
        )

    _run(stmts)


def downgrade() -> None:
    stmts = []

    # 1. Lepas semua FK baru (nama bawaan PostgreSQL sama dengan yang lama)
    for table, name in FK_NAMES:
        stmts.append(f"ALTER TABLE {table} DROP CONSTRAINT {name}")

    # 2. chat_messages
    stmts += [
        "DROP INDEX idx_chat_order_time",
        "DROP INDEX idx_chat_sender",
        "ALTER TABLE chat_messages DROP CONSTRAINT chk_chat_message_length",
        "ALTER TABLE chat_messages ALTER COLUMN message SET DATA TYPE varchar(2000)",
        "CREATE INDEX ix_chat_messages_order_id ON chat_messages (order_id)",
        "CREATE INDEX ix_chat_messages_sender_id ON chat_messages (sender_id)",
    ]

    # 3. order_status_logs
    stmts += [
        "DROP INDEX idx_status_logs_order",
        "DROP INDEX idx_status_logs_user",
        "ALTER TABLE order_status_logs DROP CONSTRAINT chk_status_log_new",
        "ALTER TABLE order_status_logs DROP CONSTRAINT chk_status_log_old",
        f"ALTER TABLE order_status_logs ADD CONSTRAINT ck_order_status_logs_new_status "
        f"CHECK (new_status IN ({STATUSES}))",
        f"ALTER TABLE order_status_logs ADD CONSTRAINT ck_order_status_logs_old_status "
        f"CHECK (old_status IS NULL OR old_status IN ({STATUSES}))",
        "CREATE INDEX ix_order_status_logs_order_id ON order_status_logs (order_id)",
        "CREATE INDEX ix_order_status_logs_changed_by ON order_status_logs (changed_by)",
    ]

    # 4. orders
    stmts += [
        "DROP INDEX idx_orders_customer",
        "DROP INDEX idx_orders_driver",
        "DROP INDEX idx_orders_status",
        "DROP INDEX idx_orders_service_type",
        "DROP INDEX idx_orders_open_created",
        "DROP INDEX idx_orders_pickup_loc",
        "DROP INDEX idx_orders_dest_loc",
        "ALTER TABLE orders DROP CONSTRAINT chk_orders_driver_by_status",
        "ALTER TABLE orders DROP CONSTRAINT chk_orders_status",
        "ALTER TABLE orders DROP CONSTRAINT chk_orders_request_type",
        "ALTER TABLE orders DROP CONSTRAINT chk_orders_passenger",
        "ALTER TABLE orders DROP CONSTRAINT chk_orders_cost",
        f"ALTER TABLE orders ADD CONSTRAINT ck_orders_status "
        f"CHECK (status IN ({STATUSES}))",
        "ALTER TABLE orders ADD CONSTRAINT ck_orders_optional_cost_expectation "
        "CHECK (optional_cost_expectation IS NULL OR optional_cost_expectation >= 0)",
        "ALTER TABLE orders ADD CONSTRAINT ck_orders_passenger_count "
        "CHECK (passenger_count IS NULL OR passenger_count > 0)",
        "ALTER TABLE orders ADD CONSTRAINT ck_orders_service_request_type "
        "CHECK (service_request_type IS NULL OR "
        "service_request_type IN ('AMBIL_BARANG', 'BELIKAN_BARANG'))",
        "ALTER TABLE orders ALTER COLUMN passenger_count SET DATA TYPE integer",
        "ALTER TABLE orders ALTER COLUMN service_request_type SET DATA TYPE varchar(30)",
        "CREATE INDEX ix_orders_customer_id ON orders (customer_id)",
        "CREATE INDEX ix_orders_driver_id ON orders (driver_id)",
        "CREATE INDEX ix_orders_service_type_id ON orders (service_type_id)",
        "CREATE INDEX ix_orders_status ON orders (status)",
    ]

    # 5. locations (koordinat NULL tidak bisa kembali NOT NULL tanpa isi: gagal keras)
    stmts += [
        "DROP INDEX idx_locations_category_active",
        "ALTER TABLE locations DROP CONSTRAINT chk_locations_lat",
        "ALTER TABLE locations DROP CONSTRAINT chk_locations_lng",
        "ALTER TABLE locations DROP CONSTRAINT chk_locations_pair",
        "ALTER TABLE locations ALTER COLUMN latitude SET NOT NULL",
        "ALTER TABLE locations ALTER COLUMN longitude SET NOT NULL",
        "ALTER TABLE locations ALTER COLUMN latitude SET DATA TYPE double precision",
        "ALTER TABLE locations ALTER COLUMN longitude SET DATA TYPE double precision",
    ]

    # 6. service_types
    stmts += [
        "ALTER TABLE service_types DROP CONSTRAINT uq_service_types_code",
        "CREATE UNIQUE INDEX ix_service_types_code ON service_types (code)",
    ]

    # 7. driver_applications
    stmts += [
        "DROP INDEX idx_driver_app_user",
        "DROP INDEX idx_driver_app_status",
        "ALTER TABLE driver_applications DROP CONSTRAINT chk_driver_app_review",
        "ALTER TABLE driver_applications DROP CONSTRAINT chk_driver_app_status",
        "ALTER TABLE driver_applications ADD CONSTRAINT ck_driver_applications_status "
        "CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))",
        "CREATE INDEX ix_driver_applications_user_id ON driver_applications (user_id)",
    ]

    # 8. users
    stmts += [
        "ALTER TABLE users DROP CONSTRAINT chk_users_availability",
        "ALTER TABLE users DROP COLUMN availability_status",
        "DROP INDEX idx_users_role",
        "DROP INDEX uq_users_email_lower",
        "CREATE UNIQUE INDEX ix_users_email ON users (email)",
        "ALTER TABLE users DROP CONSTRAINT chk_users_role",
        "ALTER TABLE users ADD CONSTRAINT ck_users_role "
        "CHECK (role IN ('ADMIN', 'DRIVER', 'CUSTOMER'))",
    ]

    # 9. kolom FK dan id kembali ke integer / serial
    for table, col in FK_COLUMNS:
        stmts.append(f"ALTER TABLE {table} ALTER COLUMN {col} SET DATA TYPE integer")
    for table in ID_TABLES:
        stmts += _identity_to_serial(table)

    # 10. Pasang kembali FK lama (tanpa ON DELETE eksplisit)
    for table, col, ref in OLD_FKS:
        stmts.append(
            f"ALTER TABLE {table} ADD FOREIGN KEY ({col}) REFERENCES {ref} (id)"
        )

    _run(stmts)
