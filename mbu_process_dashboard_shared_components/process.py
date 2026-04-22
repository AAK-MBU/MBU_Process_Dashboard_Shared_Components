""" Functions to interact with processes """

import logging
import time

from .process_dashboard_client import ProcessDashboardClient

logger = logging.getLogger(__name__)


def find_process_id_and_steps(client: ProcessDashboardClient, process_name: str):
    """
    Look up a process and return:
      • its ID
      • its list of process steps
    """

    logger.info(
        "Inside find_process_id_and_steps() - finding for process_name: %s",
        process_name,
    )

    retry_count = 3
    attempt = 1

    while attempt <= retry_count:
        try:
            res = client.get(
                "processes/?page=1&size=100",
                timeout=10,
            )

            if 200 <= res.status_code < 300:

                if not res.content:
                    raise ValueError("Empty response body")

                items = res.json().get("items", [])

                for row in items:
                    if row.get("name") == process_name:
                        return row.get("id"), row.get("steps", [])

                # Valid response, but process not found
                logger.warning(
                    "Process '%s' not found (attempt %s/%s)",
                    process_name,
                    attempt,
                    retry_count,
                )

                return None, []

            logger.warning(
                "GET processes failed (attempt %s/%s) | status=%s | body=%s",
                attempt,
                retry_count,
                res.status_code,
                res.text,
            )

        except ValueError as exc:
            logger.exception(
                "Invalid JSON or response when fetching processes (attempt %s): %s",
                attempt,
                exc,
            )

        except Exception:
            logger.exception(
                "GET processes request crashed (attempt %s)",
                attempt,
            )

        time.sleep(1)
        attempt += 1

    # Total failure
    raise RuntimeError(
        f"Could not fetch process list or find process '{process_name}' after retries"
    )


def get_dashboard_process_id(client: ProcessDashboardClient, process_name: str) -> str:
    """
    Fetch the ID of a process by its name.
    """

    logger.info("Retrieving process ID for name: %s", process_name)

    retry_count = 3
    attempt = 1

    while attempt <= retry_count:
        try:
            res = client.get(
                "processes/?include_deleted=false",
                timeout=10,
            )

            if 200 <= res.status_code < 300:

                if not res.content:
                    raise ValueError("Empty response body")

                items = res.json().get("items", [])

                for process in items:
                    if process.get("name") == process_name:
                        return process.get("id")

                # API worked, but process does not exist
                raise LookupError(
                    f"Process '{process_name}' not found in dashboard"
                )

            logger.warning(
                "GET processes failed (attempt %s/%s) | status=%s | body=%s",
                attempt,
                retry_count,
                res.status_code,
                res.text,
            )

        except (ValueError, LookupError) as exc:
            logger.exception(
                "Invalid response when fetching process ID (attempt %s): %s",
                attempt,
                exc,
            )

        except Exception:
            logger.exception(
                "GET process ID request crashed (attempt %s)",
                attempt,
            )

        time.sleep(1)
        attempt += 1

    raise RuntimeError(
        f"Could not retrieve process ID for '{process_name}' after retries"
    )
