from __future__ import annotations

from typing import Any

import httpx

from config.settings import settings
from integrations.diadoc.exceptions import DiadocApiError, DiadocConfigError


class DiadocClient:
    def __init__(
        self,
        *,
        api_url: str | None = None,
        access_token: str | None = None,
        client_id: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_url = (api_url or settings.diadoc_api_url).rstrip("/")
        self.access_token = access_token or settings.diadoc_access_token
        self.client_id = client_id or settings.diadoc_client_id
        self.timeout = timeout

        if not self.access_token:
            raise DiadocConfigError(
                "Не задан DIADOC_ACCESS_TOKEN. Укажите токен в файле .env "
                "(см. INTEGRATION_DIADOC.md)."
            )

    def _headers(self, *, json_response: bool = True) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if json_response:
            headers["Accept"] = "application/json; charset=utf-8"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_response: bool = True,
    ) -> Any:
        url = f"{self.api_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method,
                    url,
                    params=params,
                    headers=self._headers(json_response=json_response),
                )
        except httpx.HTTPError as exc:
            raise DiadocApiError(f"Сеть недоступна или Diadoc API не отвечает: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text.strip()[:500]
            raise DiadocApiError(
                f"Diadoc API {response.status_code}: {detail or response.reason_phrase}",
                status_code=response.status_code,
            )

        if not json_response:
            return response.content

        if not response.content:
            return {}
        return response.json()

    def get_my_organizations(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/GetMyOrganizations")
        if isinstance(data, list):
            return data
        return data.get("Organizations", [])

    def list_box_ids(self) -> list[str]:
        configured = settings.diadoc_box_ids
        if configured:
            return configured

        box_ids: list[str] = []
        for org in self.get_my_organizations():
            for box in org.get("Boxes", []):
                box_id = box.get("BoxId") or box.get("BoxIdGuid")
                if box_id:
                    box_ids.append(str(box_id))
        return box_ids

    def get_new_events(
        self,
        box_id: str,
        *,
        after_index_key: str | None = None,
        document_direction: str = "Inbound",
        limit: int = 100,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "boxId": box_id,
            "documentDirection": document_direction,
            "limit": limit,
        }
        if after_index_key:
            params["afterIndexKey"] = after_index_key
        return self._request("GET", "/V8/GetNewEvents", params=params)

    def get_document(self, box_id: str, message_id: str, entity_id: str) -> dict[str, Any]:
        params = {
            "boxId": box_id,
            "messageId": message_id,
            "entityId": entity_id,
            "injectEntityContent": "false",
        }
        data = self._request("GET", "/V3/GetDocument", params=params)
        return data if isinstance(data, dict) else {}

    def get_entity_content(self, box_id: str, message_id: str, entity_id: str) -> bytes:
        params = {
            "boxId": box_id,
            "messageId": message_id,
            "entityId": entity_id,
        }
        content = self._request(
            "GET",
            "/V4/GetEntityContent",
            params=params,
            json_response=False,
        )
        return bytes(content)

    def generate_print_form(self, box_id: str, message_id: str, entity_id: str) -> bytes:
        import time

        params = {
            "boxId": box_id,
            "messageId": message_id,
            "documentId": entity_id,
        }
        url = f"{self.api_url}/GeneratePrintForm"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                for _ in range(5):
                    response = client.get(
                        url,
                        params=params,
                        headers=self._headers(json_response=False),
                    )
                    if response.status_code >= 400:
                        detail = response.text.strip()[:500]
                        raise DiadocApiError(
                            f"Diadoc API {response.status_code}: {detail or response.reason_phrase}",
                            status_code=response.status_code,
                        )
                    if response.content and not response.headers.get("Retry-After"):
                        return response.content
                    time.sleep(float(response.headers.get("Retry-After", "2")))
        except httpx.HTTPError as exc:
            raise DiadocApiError(f"Не удалось получить печатную форму: {exc}") from exc
        raise DiadocApiError("Diadoc не вернул печатную форму документа.")
