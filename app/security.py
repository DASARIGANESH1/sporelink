import logging

security_logger = logging.getLogger("sporelink.security")


def log_security_event(
    event: str,
    method: str,
    path: str,
    client: str,
):
    security_logger.warning(
        "SECURITY_EVENT=%s method=%s path=%s client=%s",
        event,
        method,
        path,
        client,
    )