#!/bin/bash
# Render entrypoint: write a production odoo.conf from environment variables,
# then start Odoo bound to Render's $PORT. DB connection comes from the linked
# Render PostgreSQL (see render.yaml); no credentials live in the source.
set -e

CONF=/var/lib/odoo/odoo.conf

cat > "$CONF" <<EOF
[options]
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
db_host = ${DB_HOST}
db_port = ${DB_PORT:-5432}
db_user = ${DB_USER}
db_password = ${DB_PASSWORD}
db_name = ${DB_NAME}
dbfilter = ^${DB_NAME}$
http_interface = 0.0.0.0
http_port = ${PORT:-8069}
proxy_mode = True
list_db = False
admin_passwd = ${ODOO_MASTER_PASSWORD:-please-change-me}
; Threaded mode keeps the memory footprint small enough for Render's free tier.
workers = 0
limit_time_real = 600
limit_time_cpu = 300
EOF

# -i installs+initialises the module on the first boot (empty DB) and is a no-op
# once installed, so the same command is safe on every restart. Switch to
# ODOO_MODULE_OP=-u to force an upgrade after pushing code changes.
MODULE_OP="${ODOO_MODULE_OP:--i}"

exec odoo -c "$CONF" "${MODULE_OP}" nn_fund_management --without-demo=all
