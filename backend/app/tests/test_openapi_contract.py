#!/usr/bin/env python3
"""Fail loudly when a registered business operation disappears or changes."""

from __future__ import annotations

from collections.abc import Mapping

from app.main import app

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})
_EXPECTED_SUCCESS_STATUS: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/auth/signup"): "201",
    ("POST", "/api/v1/auth/login"): "200",
    ("GET", "/api/v1/users/me"): "200",
    ("GET", "/api/v1/users/me/profile"): "200",
    ("PATCH", "/api/v1/users/me/profile"): "200",
    ("POST", "/api/v1/users/me/verify-password"): "200",
    ("PATCH", "/api/v1/users/me/account"): "200",
    ("GET", "/api/v1/users/me/consents"): "200",
    ("PUT", "/api/v1/users/me/consents"): "200",
    ("DELETE", "/api/v1/users/me"): "200",
    ("GET", "/api/v1/categories"): "200",
    ("GET", "/api/v1/categories/{category_id}/questions"): "200",
    ("PUT", "/api/v1/categories/{category_id}/answers"): "200",
    ("GET", "/api/v1/policies"): "200",
    ("GET", "/api/v1/users/me/recommendations"): "200",
    ("GET", "/api/v1/users/me/dashboard-summary"): "200",
    ("GET", "/api/v1/policies/{policy_id}"): "200",
    ("GET", "/api/v1/policies/{policy_id}/match"): "200",
    ("POST", "/api/v1/policies/{policy_id}/bookmark"): "201",
    ("DELETE", "/api/v1/policies/{policy_id}/bookmark"): "204",
    ("POST", "/api/v1/policies/{policy_id}/questions"): "200",
    ("POST", "/api/v1/policies/{policy_id}/preparation"): "201",
    ("GET", "/api/v1/preparations/{state_id}"): "200",
    (
        "PATCH",
        "/api/v1/preparations/{state_id}/documents/{document_id}",
    ): "200",
    (
        "PATCH",
        "/api/v1/preparations/{state_id}/conditions/{condition_id}",
    ): "200",
    ("POST", "/api/v1/policies/{policy_id}/applications"): "200",
    ("GET", "/api/v1/users/me/policies"): "200",
    ("GET", "/api/v1/users/me/notification-settings"): "200",
    ("PATCH", "/api/v1/users/me/notification-settings"): "200",
    ("GET", "/api/v1/users/me/notifications"): "200",
    ("PATCH", "/api/v1/notifications/{notification_id}/read"): "200",
    ("POST", "/api/v1/simulator/housing"): "200",
    ("POST", "/api/v1/simulator/transport"): "200",
    ("POST", "/api/v1/simulator/finance"): "200",
    ("POST", "/api/v1/simulator/tax"): "200",
    ("POST", "/api/v1/simulator/employment"): "200",
    ("POST", "/api/v1/simulator/welfare"): "200",
    ("GET", "/health"): "200",
}
_PUBLIC_OPERATIONS = {
    ("POST", "/api/v1/auth/signup"),
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/categories"),
    ("GET", "/api/v1/categories/{category_id}/questions"),
    ("POST", "/api/v1/simulator/housing"),
    ("POST", "/api/v1/simulator/transport"),
    ("POST", "/api/v1/simulator/finance"),
    ("POST", "/api/v1/simulator/tax"),
    ("POST", "/api/v1/simulator/employment"),
    ("POST", "/api/v1/simulator/welfare"),
    ("GET", "/health"),
}


def _business_operations(
    schema: Mapping[str, object],
) -> dict[tuple[str, str], Mapping[str, object]]:
    paths = schema.get("paths")
    assert isinstance(paths, Mapping)
    operations: dict[tuple[str, str], Mapping[str, object]] = {}
    for raw_path, raw_path_item in paths.items():
        assert isinstance(raw_path, str)
        assert isinstance(raw_path_item, Mapping)
        for raw_method, raw_operation in raw_path_item.items():
            if not isinstance(raw_method, str) or raw_method not in _HTTP_METHODS:
                continue
            assert isinstance(raw_operation, Mapping)
            operations[(raw_method.upper(), raw_path)] = raw_operation
    return operations


def test_openapi_enumerates_every_business_operation() -> None:
    schema = app.openapi()
    operations = _business_operations(schema)

    assert len(operations) == 38
    assert set(operations) == set(_EXPECTED_SUCCESS_STATUS)
    operation_ids = [operation.get("operationId") for operation in operations.values()]
    assert all(isinstance(operation_id, str) for operation_id in operation_ids)
    assert len(operation_ids) == len(set(operation_ids))

    for key, expected_status in _EXPECTED_SUCCESS_STATUS.items():
        responses = operations[key].get("responses")
        assert isinstance(responses, Mapping)
        assert expected_status in responses, key


def test_openapi_auth_contract_matches_route_dependencies() -> None:
    schema = app.openapi()
    operations = _business_operations(schema)
    components = schema.get("components")
    assert isinstance(components, Mapping)
    security_schemes = components.get("securitySchemes")
    assert isinstance(security_schemes, Mapping)
    assert security_schemes["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
    }

    for key, operation in operations.items():
        security = operation.get("security")
        if key in _PUBLIC_OPERATIONS:
            assert security in (None, []), key
        else:
            assert security == [{"HTTPBearer": []}], key
