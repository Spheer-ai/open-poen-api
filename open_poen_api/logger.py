import logging

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s :: %(name)s :: %(message)s"
)
audit_logger = logging.getLogger("audit")
