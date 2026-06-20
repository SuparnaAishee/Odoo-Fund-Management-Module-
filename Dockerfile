# Production image for Render (and any Docker host).
# Bundles the custom addon into the official Odoo 17 image and boots through a
# small entrypoint that renders odoo.conf from environment variables and binds
# Render's injected $PORT. No secrets are baked into the image.
FROM odoo:17.0

# Our module(s).
COPY ./addons /mnt/extra-addons

# Entrypoint renders the config from env and starts Odoo.
COPY ./deploy/render-entrypoint.sh /render-entrypoint.sh

USER root
RUN chmod +x /render-entrypoint.sh
USER odoo

ENTRYPOINT ["/render-entrypoint.sh"]
