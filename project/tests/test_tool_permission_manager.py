"""Tests for Role-based Tool Permission Manager (Security Fix #4)."""

import pytest

from services.execution.tool_permission_manager import (
    PermissionDeniedError,
    ToolPermissionManager,
)


class TestSpecialistPermissions:
    def setup_method(self):
        self.pm = ToolPermissionManager()

    def test_write_src_allowed(self):
        assert self.pm.check_write_permission("specialist", "src/main.py") is True

    def test_write_services_allowed(self):
        assert self.pm.check_write_permission("specialist", "services/user_service.py") is True

    def test_write_tests_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("specialist", "tests/test_main.py")

    def test_write_env_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("specialist", ".env")

    def test_write_laws_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("specialist", "shared/config/laws.yaml")

    def test_read_src_allowed(self):
        assert self.pm.check_read_permission("specialist", "src/main.py") is True

    def test_read_tests_allowed(self):
        assert self.pm.check_read_permission("specialist", "tests/test_main.py") is True

    def test_edit_src_allowed(self):
        assert self.pm.check_edit_permission("specialist", "src/main.py") is True

    def test_edit_tests_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_edit_permission("specialist", "tests/test_main.py")


class TestTesterPermissions:
    def setup_method(self):
        self.pm = ToolPermissionManager()

    def test_write_tests_allowed(self):
        assert self.pm.check_write_permission("tester", "tests/test_main.py") is True

    def test_write_src_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("tester", "src/main.py")

    def test_write_services_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("tester", "services/user_service.py")

    def test_read_src_allowed(self):
        assert self.pm.check_read_permission("tester", "src/main.py") is True

    def test_edit_tests_allowed(self):
        assert self.pm.check_edit_permission("tester", "tests/test_main.py") is True

    def test_edit_src_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_edit_permission("tester", "src/main.py")


class TestAuditorPermissions:
    def setup_method(self):
        self.pm = ToolPermissionManager()

    def test_read_everywhere(self):
        assert self.pm.check_read_permission("auditor", "src/main.py") is True
        assert self.pm.check_read_permission("auditor", "tests/test_main.py") is True
        assert self.pm.check_read_permission("auditor", "governance/laws.yaml") is True

    def test_write_nowhere(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("auditor", "src/main.py")
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("auditor", "tests/test_main.py")

    def test_edit_nowhere(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_edit_permission("auditor", "src/main.py")


class TestGatekeeperPermissions:
    def setup_method(self):
        self.pm = ToolPermissionManager()

    def test_write_config_allowed(self):
        assert self.pm.check_write_permission("gatekeeper", "shared/config/settings.py") is True

    def test_write_src_denied(self):
        with pytest.raises(PermissionDeniedError):
            self.pm.check_write_permission("gatekeeper", "src/main.py")

    def test_read_everywhere(self):
        assert self.pm.check_read_permission("gatekeeper", "src/main.py") is True
        assert self.pm.check_read_permission("gatekeeper", "tests/test_main.py") is True


class TestUnknownRole:
    def setup_method(self):
        self.pm = ToolPermissionManager()

    def test_unknown_role_write(self):
        assert self.pm.check_write_permission("unknown_role", "src/main.py") is False

    def test_unknown_role_read(self):
        assert self.pm.check_read_permission("unknown_role", "src/main.py") is False


class TestGetRolePermissions:
    def setup_method(self):
        self.pm = ToolPermissionManager()

    def test_get_specialist_permissions(self):
        perms = self.pm.get_role_permissions("specialist")
        assert perms is not None
        assert "src" in perms["can_write"]
        assert "tests" in perms["can_read"]

    def test_get_unknown_role(self):
        perms = self.pm.get_role_permissions("nonexistent")
        assert perms is None
