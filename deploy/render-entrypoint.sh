#!/bin/bash
# Render entrypoint tuned for the 512 MB FREE tier. DB connection comes from the
# linked Render PostgreSQL (see render.yaml); no credentials live in the source.
#
# Why two phases? The install/upgrade of the module (24 modules, registry +
# asset prep) is the memory-heavy part. Doing it in the SAME process that then
# serves HTTP makes peak RAM spike past 512 MB and the free instance gets
# OOM-killed -> "Exited with status 255" crash loop. So we run the one-off
# install/upgrade in its own short-lived process (--stop-after-init); when it
# exits, the OS reclaims all that memory BEFORE the long-running web server
# starts lean.
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
; --- free-tier (512 MB) memory tuning ---
; Threaded mode: no worker subprocesses, so the whole app is a single process.
workers = 0
; No background cron threads — saves memory/CPU; this app has no critical jobs.
max_cron_threads = 0
limit_time_real = 600
limit_time_cpu = 300
EOF

# One-off install/upgrade in its OWN process so its memory is freed before the
# server starts. ODOO_MODULE_OP:
#   -i  install on a fresh DB; a no-op once installed (default, lightest boot).
#   -u  run for ONE deploy when you need to apply data changes (e.g. new seed
#       users in data/seed_users.xml), then switch back to -i.
MODULE_OP="${ODOO_MODULE_OP:--i}"
odoo -c "$CONF" "${MODULE_OP}" nn_fund_management --without-demo=all --stop-after-init

# Long-running web server, started lean (no install work competing for RAM).
exec odoo -c "$CONF"
