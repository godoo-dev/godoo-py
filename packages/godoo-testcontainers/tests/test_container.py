from __future__ import annotations

from godoo_testcontainers.container import OdooTestContainer


class TestOdooTestContainerDefaults:
    def test_default_options(self) -> None:
        c = OdooTestContainer()
        assert c._modules == []
        assert c._database == "test_odoo"
        assert c._admin_password == "admin"
        assert c._startup_timeout == 300

    def test_default_env_is_empty(self) -> None:
        c = OdooTestContainer()
        assert c._env == {}

    def test_custom_options(self) -> None:
        c = OdooTestContainer(
            modules=["crm", "sale"],
            database="mydb",
            admin_password="secret",
            startup_timeout=120,
        )
        assert c._modules == ["crm", "sale"]
        assert c._database == "mydb"
        assert c._admin_password == "secret"
        assert c._startup_timeout == 120

    def test_custom_env(self) -> None:
        c = OdooTestContainer(env={"LOG_LEVEL": "debug"})
        assert c._env == {"LOG_LEVEL": "debug"}

    def test_modules_default_is_independent(self) -> None:
        c1 = OdooTestContainer()
        c2 = OdooTestContainer()
        c1._modules.append("crm")
        assert c2._modules == []
