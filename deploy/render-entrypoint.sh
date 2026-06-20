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
# Run as a separate --stop-after-init pass so we can seed an admin login before
# the server begins serving.
MODULE_OP="${ODOO_MODULE_OP:--i}"

odoo -c "$CONF" "${MODULE_OP}" nn_fund_management --without-demo=all --stop-after-init

# Seed/refresh the administrator login. Production runs without demo data, so the
# documented demo users (demo/demo_users.xml) are not loaded; without this, the
# only account is Odoo's built-in admin with its insecure default password. The
# admin already holds every fund role via security/groups.xml, so this single
# account can drive the whole GM -> MD workflow. The password comes from the
# environment, never from source: ODOO_ADMIN_PASSWORD if set, else the generated
# Odoo master password. Login defaults to "admin". A seed failure is logged but
# does not block boot (the built-in admin still applies).
export SEED_ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
export SEED_ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-${ODOO_MASTER_PASSWORD:-please-change-me}}"
odoo shell -c "$CONF" <<'PY' || echo "[seed] WARNING: admin seed failed; built-in admin login still applies"
import os
admin = env.ref('base.user_admin')
admin.write({
    'login': os.environ['SEED_ADMIN_LOGIN'],
    'password': os.environ['SEED_ADMIN_PASSWORD'],
})
env.cr.commit()
print('[seed] admin login set to %s' % os.environ['SEED_ADMIN_LOGIN'])
PY

# Hand off to the long-running server bound to Render's $PORT.
exec odoo -c "$CONF"
