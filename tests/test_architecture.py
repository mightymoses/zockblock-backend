from pytest_archon import archrule


def test_repository_does_not_depend_on_router_or_service():
    (
        archrule(
            "repository-independence",
            comment="repository must stay pure data access: no router, no service layer",
        )
        .match("app.*.repository")
        .should_not_import("app.*.router")
        .should_not_import("app.*.application*")
        .check("app")
    )


def test_service_does_not_depend_on_router():
    (
        archrule(
            "service-independence",
            comment="the service layer (application/command|query) must not depend on the router",
        )
        .match("app.*.application*")
        .should_not_import("app.*.router")
        .check("app")
    )
