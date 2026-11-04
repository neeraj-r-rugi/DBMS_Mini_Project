"""Small CouchDB REST adapter for unstructured car and service documents."""

from dataclasses import dataclass
from typing import Any

import requests

from .config import COUCHDB_CAR_DATABASE, COUCHDB_PASSWORD, COUCHDB_URL, COUCHDB_USER


@dataclass
class CouchDBClient:
    url: str
    user: str = ""
    password: str = ""

    @property
    def auth(self) -> tuple[str, str] | None:
        return (self.user, self.password) if self.user else None

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return requests.request(
            method,
            f"{self.url.rstrip('/')}/{path.lstrip('/')}",
            auth=self.auth,
            timeout=3,
            **kwargs,
        )

    def ensure_database(self, name: str) -> None:
        response = self.request("PUT", name)
        if response.status_code not in (201, 202, 412):
            response.raise_for_status()

    def ensure_indexes(self, database: str) -> None:
        indexes = [
            {
                "index": {"fields": ["car_id"]},
                "name": "car-id",
                "type": "json",
            },
            {
                "index": {"fields": ["service_id"]},
                "name": "service-id",
                "type": "json",
            },
            {
                "index": {"fields": ["car_id", "service_date"]},
                "name": "service-car-date",
                "type": "json",
            },
        ]
        for index in indexes:
            response = self.request("POST", f"{database}/_index", json=index)
            response.raise_for_status()

    def put_document(self, database: str, document_id: str, document: dict[str, Any]) -> dict[str, Any]:
        response = self.request("PUT", f"{database}/{document_id}", json=document)
        response.raise_for_status()
        return response.json()

    def get_document(self, database: str, document_id: str) -> dict[str, Any] | None:
        response = self.request("GET", f"{database}/{document_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def find(self, database: str, selector: dict[str, Any], limit: int = 100) -> list[dict[str, Any]]:
        response = self.request(
            "POST",
            f"{database}/_find",
            json={"selector": selector, "limit": limit},
        )
        response.raise_for_status()
        return response.json().get("docs", [])

    def delete_document(self, database: str, document_id: str, revision: str) -> None:
        response = self.request("DELETE", f"{database}/{document_id}?rev={revision}")
        response.raise_for_status()

    def ping_and_initialize(self) -> None:
        response = self.request("GET", "_up")
        response.raise_for_status()
        self.ensure_database(COUCHDB_CAR_DATABASE)
        self.ensure_database(f"{COUCHDB_CAR_DATABASE}_service_history")
        self.ensure_indexes(COUCHDB_CAR_DATABASE)
        self.ensure_indexes(f"{COUCHDB_CAR_DATABASE}_service_history")

    @property
    def service_database(self) -> str:
        return f"{COUCHDB_CAR_DATABASE}_service_history"


def get_couchdb_client() -> CouchDBClient | None:
    if not COUCHDB_URL:
        return None
    return CouchDBClient(COUCHDB_URL, COUCHDB_USER, COUCHDB_PASSWORD)


def initialize_couchdb() -> bool:
    client = get_couchdb_client()
    if client is None:
        return False
    client.ping_and_initialize()
    return True
