""" Functions to interact with process runs """

import logging
import time

from urllib.parse import urlencode

from .process_dashboard_client import ProcessDashboardClient
from .process import find_process_id_and_steps

logger = logging.getLogger(__name__)


def get_all_process_runs(client: ProcessDashboardClient, process_id: int = None, entity_id: str = None, entity_name: str = None, run_status: str = None, started_after: str = None, started_before: str = None, meta_filter: str = None):
    """
    Fetch all process runs

    Additional params can filter the search
    """

    all_process_runs = []

    page = 1

    params = {
        "order_by": "created_at",
        "sort_direction": "desc",
        "size": 100,
    }

    if process_id:
        params["process_id"] = process_id

    if entity_id:
        params["entity_id"] = entity_id

    if entity_name:
        params["entity_name"] = entity_name

    if run_status:
        params["run_status"] = run_status

    if started_after:
        params["started_after"] = started_after

    if started_before:
        params["started_before"] = started_before

    if meta_filter:
        params["meta_filter"] = meta_filter

    while True:

        params["page"] = page
        endpoint = f"/runs/?{urlencode(params)}"

        response = client.get(endpoint=endpoint, timeout=30)

        if response.status_code != 200:
            logger.info(f"Request failed with status {response.status_code}")

            break

        data = response.json()
        results = data.get("items", [])
        total_pages = data.get("pages", 1)

        all_process_runs.extend(results)

        if page >= total_pages:
            logger.info("Finished scanning all pages for process runs.")

            break

        page += 1

    return all_process_runs


def get_dashboard_run_id(client, process_id: int, cpr: str) -> int:
    """
    Get the latest run ID for a process + CPR combination.
    """

    logger.info(
        "Fetching run ID for process %s and CPR %s",
        process_id,
        cpr,
    )

    retry_count = 3
    attempt = 1

    while attempt <= retry_count:
        try:
            res = client.get(f"runs/?process_id={process_id}&meta_filter=cpr:{cpr}", timeout=10)

            if 200 <= res.status_code < 300:

                if not res.content:
                    raise ValueError("Empty response body")

                data = res.json()
                items = data.get("items", [])

                if not items:
                    raise ValueError("No run items found")

                return items[0]["id"]

            logger.warning(
                "GET run ID failed (attempt %s/%s) | status=%s | body=%s",
                attempt,
                retry_count,
                res.status_code,
                res.text,
            )

        except ValueError as exc:
            logger.exception(
                "Invalid response when fetching run ID (attempt %s): %s",
                attempt,
                exc,
            )

        except Exception:
            logger.exception(
                "GET run ID request crashed (attempt %s)",
                attempt,
            )

        time.sleep(1)
        attempt += 1

    raise RuntimeError(
        f"Could not fetch dashboard run ID for process_id={process_id}, cpr={cpr}"
    )


def get_process_run_by_cpr(client, process_name: str, cpr: str) -> bool:
    """
    Check if a process run exists for a given CPR.
    """

    process_id, _ = find_process_id_and_steps(client=client, process_name=process_name)

    retry_count = 3
    attempt = 1

    while attempt <= retry_count:
        try:
            res = client.get(
                f"runs/?process_id={process_id}"
                f"&meta_filter=cpr%3A{cpr}"
                f"&order_by=created_at"
                f"&sort_direction=desc"
                f"&page=1&size=100", timeout=10,
            )

            if 200 <= res.status_code < 300:

                if not res.content:
                    return False

                items = res.json().get("items", [])

                return len(items) > 0

            logger.warning(
                "GET runs failed (attempt %s/%s) | status=%s | body=%s",
                attempt,
                retry_count,
                res.status_code,
                res.text,
            )

        except ValueError:
            # JSON decode error
            logger.exception(
                "Invalid JSON response when fetching runs (attempt %s)",
                attempt,
            )

        except Exception:
            # Network / timeout / request crash
            logger.exception(
                "GET runs request crashed (attempt %s)",
                attempt,
            )

        time.sleep(1)
        attempt += 1

    # If we exhausted retries, assume no valid run found
    return False


def create_dashboard_run(client, process_name: str, meta: dict):
    """
    Create a new process run.

    Requires meta containing at least:
      • 'cpr'
      • 'name'

    Args:
        client (ProcessDashboardClient)
        process_name (str)
        meta (dict)
    """

    logger.info("Creating process run for %s", process_name)
    logger.info("Metadata: %s", meta)

    process_id, _ = find_process_id_and_steps(client, process_name)

    payload = {
        "entity_id": meta.get("cpr"),
        "entity_name": meta.get("name"),
        "meta": meta,
        "process_id": process_id,
    }

    client.post("runs/", json=payload)
