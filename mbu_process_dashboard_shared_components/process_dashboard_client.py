""" The main class file, initialises a Process Dashboard class client """

import logging

import requests

logger = logging.getLogger(__name__)


PROCESS_DASHBOARD_BASE_URL = (
    "https://mbu-dashboard-api.adm.aarhuskommune.dk/api/v1"
)


class ProcessDashboardClient:
    """
    Reusable API client for the Process Dashboard.
    Handles:
      • Base URL management
      • Auth headers (X-API-Key)
      • GET / POST / PATCH requests

    The other modules depend on this class.
    """

    def __init__(self, api_admin_token: str, base_url: str = None):
        """
        Initialize the client with token-based authentication.

        Args:
            api_admin_token (str): The admin API key used for authorization.
        """

        if base_url:
            self.base_url = base_url

        else:
            self.base_url = PROCESS_DASHBOARD_BASE_URL

        self.headers = {
            "X-API-Key": api_admin_token,
            "Content-Type": "application/json",
        }

    #
    # Generic helpers -----------------------
    #

    def get(self, endpoint: str, timeout: int = 30):
        """
        Send a GET request.

        Args:
            endpoint (str): API path relative to base_url.
            timeout (int): Request timeout in seconds.

        Returns:
            Response: requests.Response object.
        """

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        logger.info("Printing the url for the requested GET API-call: %s", url)

        return requests.get(url, headers=self.headers, timeout=timeout)

    def post(self, endpoint: str, json: dict, timeout: int = 30):
        """
        Send a POST request with JSON payload.

        Args:
            endpoint (str): API path.
            json (dict): JSON payload.

        Returns:
            Response: requests.Response object.
        """

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        logger.info("Printing the url for the requested POST API-call: %s", url)

        return requests.post(url, headers=self.headers, json=json, timeout=timeout)

    def patch(self, endpoint: str, json: dict, timeout: int = 30):
        """
        Send a PATCH request with JSON payload.

        Args:
            endpoint (str): API path.
            json (dict): JSON payload.

        Returns:
            Response: requests.Response object.
        """

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        logger.info("Printing the url for the requested PATCH API-call: %s", url)

        return requests.patch(url, headers=self.headers, json=json, timeout=timeout)
