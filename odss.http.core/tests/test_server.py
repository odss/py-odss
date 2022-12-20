from odss.http.common import route, Request, Response, JsonResponse


async def test_get_text(http_client):
    @route.get("/test_text")
    def test_handler():
        return Response("text", content_type="text/html")

    http_client.server.bind_handler(test_handler)

    response = await http_client.get("/test_text")

    assert response.status == 200
    assert response.content_type == "text/html"
    text = await response.text()
    assert text == "text"


async def test_post_json(http_client):
    @route.post("/")
    def test_handler():
        return JsonResponse({"response": 321})

    http_client.server.bind_handler(test_handler)

    response = await http_client.post("/", data={"id": 123})

    assert response.status == 200
    assert response.content_type == "application/json"
    content = await response.json()
    assert content == {"response": 321}


async def test_post_json_auto(http_client):
    @route.post("/")
    async def test_handler(q: str):
        return {"query": q}

    http_client.server.bind_handler(test_handler)

    response = await http_client.post("/?q=name")

    assert response.status == 200
    assert response.content_type == "application/json"
    content = await response.json()
    assert content == {"query": "name"}


async def test_get_param(http_client):
    @route.post("/{name}")
    async def test_handler(name: str):
        return {"name": name}

    http_client.server.bind_handler(test_handler)

    response = await http_client.post("/name-test")

    assert response.status == 200
    assert response.content_type == "application/json"
    content = await response.json()
    assert content == {"name": "name-test"}


async def test_methods(http_client):
    for method in ("get", "post", "put", "delete", "patch", "options", "head"):

        @route(method, "/")
        async def handler(request: Request):
            return {"method": request.method}

        http_client.server.bind_handler(handler)

    for method in ("get", "post", "put", "delete", "patch", "options", "head"):
        coro = getattr(http_client.session, method)
        response = await coro(http_client.make_url("/"))

        assert response.status == 200
        if method == "head":
            content = await response.text()
            assert content == ""
        else:
            content = await response.json()
            assert content == {"method": method.upper()}
