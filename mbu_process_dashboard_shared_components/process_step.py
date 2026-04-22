""" Functions to interact with process steps """

import logging
import time

from .process_dashboard_client import ProcessDashboardClient

logger = logging.getLogger(__name__)


def get_dashboard_step_id(client: ProcessDashboardClient, process_id: int, step_name: str) -> int:
    """
    Return a step ID based on process_id + step name.
    """

    logger.info(
        "Looking up step ID for '%s' in process %s",
        step_name,
        process_id,
    )

    retry_count = 3
    attempt = 1

    while attempt <= retry_count:
        try:
            res = client.get(
                f"steps/process/{process_id}?include_deleted=false",
                timeout=10,
            )

            if 200 <= res.status_code < 300:

                if not res.content:
                    raise ValueError("Empty response body")

                steps = res.json()

                for step in steps:
                    if step.get("name") == step_name:
                        return step.get("id")

                raise LookupError(
                    f"Step '{step_name}' not found for process_id={process_id}"
                )

            logger.warning(
                "GET steps failed (attempt %s/%s) | status=%s | body=%s",
                attempt,
                retry_count,
                res.status_code,
                res.text,
            )

        except (ValueError, LookupError) as exc:
            logger.exception(
                "Invalid response when fetching step ID (attempt %s): %s",
                attempt,
                exc,
            )

        except Exception:
            logger.exception(
                "GET step ID request crashed (attempt %s)",
                attempt,
            )

        time.sleep(1)
        attempt += 1

    raise RuntimeError(
        f"Could not retrieve step ID '{step_name}' "
        f"for process_id={process_id} after retries"
    )
