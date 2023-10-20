from odss.http.common import ODSS_HTTP_HANDLER, route


def test_route_simple():
    @route("GET", "/path")
    def simple1():
        pass

    settings = getattr(simple1, ODSS_HTTP_HANDLER)
    assert len(settings) == 3
    assert settings["method"] == "GET"
    assert settings["path"] == "/path"
    assert settings["name"] == "test_route_simple.locals.simple1"


def test_route_all_method():
    @route("*", "/path")
    def simple2():
        pass

    settings = getattr(simple2, ODSS_HTTP_HANDLER)
    assert len(settings) == 3
    assert settings["method"] == "*"
    assert settings["path"] == "/path"
    assert settings["name"] == "test_route_all_method.locals.simple2"


def test_route_lower_method():
    @route("get", "/path")
    def simple2():
        pass

    settings = getattr(simple2, ODSS_HTTP_HANDLER)
    assert len(settings) == 3
    assert settings["method"] == "GET"
    assert settings["path"] == "/path"
    assert settings["name"] == "test_route_lower_method.locals.simple2"


def test_route_name():
    @route("get", "/path", name="simple-name")
    def simple3():
        pass

    settings = getattr(simple3, ODSS_HTTP_HANDLER)
    assert len(settings) == 3
    assert settings["method"] == "GET"
    assert settings["path"] == "/path"
    assert settings["name"] == "simple-name"


def test_route_extra():
    @route("get", "/path", name="simple-name", access="public")
    def simple4():
        pass

    settings = getattr(simple4, ODSS_HTTP_HANDLER)
    assert len(settings) == 4
    assert settings["method"] == "GET"
    assert settings["path"] == "/path"
    assert settings["name"] == "simple-name"
    assert settings["access"] == "public"


def test_get_route():
    @route.get("/path", name="simple-name", access="public")
    def simple4():
        pass

    settings = getattr(simple4, ODSS_HTTP_HANDLER)
    assert len(settings) == 4
    assert settings["method"] == "GET"
    assert settings["path"] == "/path"
    assert settings["name"] == "simple-name"
    assert settings["access"] == "public"


def test_post_route():
    @route.post("/path", name="simple-name", access="public")
    def simple4():
        pass

    settings = getattr(simple4, ODSS_HTTP_HANDLER)
    assert len(settings) == 4
    assert settings["method"] == "POST"
    assert settings["path"] == "/path"
    assert settings["name"] == "simple-name"
    assert settings["access"] == "public"
