"""Functions to interact with process step runs"""

import logging
import time
from datetime import datetime, timezone

from mbu_rpa_core.exceptions import BusinessError

from .process import find_process_id_and_steps
from .process_run import get_dashboard_run_id

logger = logging.getLogger(__name__)


def get_step_run_id_for_process_step_cpr(
    client,
    process_name: str,
    step_name: str,
    cpr: str,
) -> int:
    """
    Look up a step-run ID using:
        • process name
        • step name
        • CPR number
    """

    logger.info(
        "Finding step-run ID for process=%s | step=%s | cpr=%s",
        process_name,
        step_name,
        cpr,
    )

    # --- Resolve process + steps (already retry-safe upstream)
    process_id, process_steps = find_process_id_and_steps(
        client=client,
        process_name=process_name,
    )

    if not process_id:
        raise RuntimeError(f"Process '{process_name}' not found")

    # --- Resolve step ID
    step_id = None
    for step in process_steps:
        if step.get("name") == step_name:
            step_id = step.get("id")
            break

    if not step_id:
        raise RuntimeError(f"Step '{step_name}' not found for process '{process_name}'")

    # --- Resolve run ID (already retry-safe upstream)
    run_id = get_dashboard_run_id(
        client=client,
        process_id=process_id,
        cpr=cpr,
    )

    # --- Fetch step-run ID (needs retries)
    retry_count = 3
    attempt = 1

    while attempt <= retry_count:
        try:
            res = client.get(
                f"step-runs/run/{run_id}/step/{step_id}?include_deleted=false",
                timeout=10,
            )

            if 200 <= res.status_code < 300:
                if not res.content:
                    raise ValueError("Empty response body")

                step_run = res.json()
                step_run_id = step_run.get("id")

                if step_run_id:
                    return step_run_id

                raise LookupError("Step run exists but ID missing in response")

            logger.warning(
                "GET step-run failed (attempt %s/%s) | status=%s | body=%s",
                attempt,
                retry_count,
                res.status_code,
                res.text,
            )

        except (ValueError, LookupError) as exc:
            logger.exception(
                "Invalid response when fetching step-run ID (attempt %s): %s",
                attempt,
                exc,
            )

        except Exception:
            logger.exception(
                "GET step-run request crashed (attempt %s)",
                attempt,
            )

        time.sleep(1)
        attempt += 1

    raise RuntimeError(
        "Step run ID not found for "
        f"process='{process_name}', step='{step_name}', cpr='{cpr}'"
    )


def build_step_run_update(
    status: str, failure: Exception | None = None, rerun_config: dict | None = None
) -> dict:
    """
    Build the JSON body used for updating a step run.

    Args:
        status (str): New status ("success", "failed", etc.)
        failure (Exception|None): Error info to include.
        rerun_config (dict|None): Configuration for rerunning the step.

    Returns:
        dict: JSON payload for PATCH.
    """

    now = (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

    failure_data = None

    if failure:
        if isinstance(failure, BusinessError):
            failure_data = {
                "error_code": type(failure).__name__,
                "message": str(failure),
                "details": str(failure.__traceback__)
                if failure.__traceback__
                else None,
            }
        else:
            failure_data = {
                "error_code": "ApplicationException",
                "message": "Processen er fejlet",
                "details": (
                    "Digitalisering undersøger fejlen og genstarter processen.\n\n"
                    "Kontakt Digitalisering hvis det ikke er løst efter 2 arbejdsdage."
                ),
            }

    return {
        "status": status,
        "started_at": now,
        "finished_at": now,
        "failure": failure_data,
        "rerun_config": rerun_config or {},
    }


def update_dashboard_step_run_by_id(client, step_run_id: int, update_data: dict):
    """
    PATCH update a step-run entry in the dashboard.
    """

    retry_count = 3
    attempt = 1

    logger.info("Updating step run ID %s", step_run_id)

    while attempt <= retry_count:
        try:
            logger.info("before res")
            res = client.patch(f"step-runs/{step_run_id}", json=update_data)
            logger.info(f"after res: {res}")

            # Success responses (2xx)
            if 200 <= res.status_code < 300:
                # Only parse JSON if there actually is a body
                if res.content:
                    return res.json(), res.status_code

                return None, res.status_code

            logger.warning(
                "PATCH failed (attempt %s/%s) | status=%s | body=%s",
                attempt,
                retry_count,
                res.status_code,
                res.text,
            )

        except ValueError:
            # JSON decode error
            logger.exception(
                "Invalid JSON response for step run ID %s (attempt %s)",
                step_run_id,
                attempt,
            )

        except Exception:
            # Network errors, timeouts, etc.
            logger.exception(
                "PATCH request crashed for step run ID %s (attempt %s)",
                step_run_id,
                attempt,
            )

        time.sleep(1)
        attempt += 1

    return {
        "error": "Patch call failed after retries",
        "step_run_id": step_run_id,
    }, None
