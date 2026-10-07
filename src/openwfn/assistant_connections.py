"""Bounded model discovery and atomic session-only connection replacement."""

import json

import httpx

from .assistant_model import LocalModel


def discover_models(model: LocalModel) -> list[str]:
    headers = {'Authorization': f'Bearer {model.api_key}'} if model.api_key else {}
    try:
        with httpx.Client(timeout=5, follow_redirects=False, trust_env=False,
                          transport=model.transport) as client:
            with client.stream('GET', model.endpoint + '/models', headers=headers) as response:
                if response.status_code != 200:
                    raise RuntimeError(f'Model discovery returned HTTP {response.status_code}.')
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 65536:
                        raise ValueError('Model list exceeds the response limit.')
        payload = json.loads(body)
        entries = payload.get('data') if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise ValueError('Model endpoint did not return a model list.')
        names = []
        for item in entries:
            name = item.get('id') if isinstance(item, dict) else None
            if not isinstance(name, str) or not name.strip() or len(name) > 120 or not name.isprintable():
                raise ValueError('Model endpoint returned an invalid model identifier.')
            if name not in names:
                names.append(name)
        return names
    except httpx.HTTPError as exc:
        raise RuntimeError('Could not discover models. Start the runner or check the endpoint.') from exc


class ModelConnection:
    """Do not replace an active connection until discovery verifies the candidate."""

    def __init__(self, active: LocalModel | None = None):
        self.active = active

    def connect(self, candidate: LocalModel) -> None:
        if candidate.model not in discover_models(candidate):
            raise ValueError('The selected model is not available at this endpoint.')
        self.active = candidate

    def disconnect(self) -> None:
        self.active = None
