import pytest

from odss.cdi import consts
from odss.cdi.contexts import get_factory_context
from odss.cdi.decorators import (
    Component,
    Instantiate,
    Invalidate,
    Provides,
    Requires,
    Validate,
)


def test_component():
    with pytest.raises(TypeError):
        Component()

    @Component
    class Dummy1:
        pass

    config = get_factory_context(Dummy1)
    assert config.name == "tests.cdi.test_decorators.Dummy1"
    assert config.completed

    @Component("dummy2")
    class Dummy2:
        pass

    config = get_factory_context(Dummy2)
    assert config.name == "dummy2"
    assert config.completed

    @Component("dummy3")
    class Dummy3:
        def __init__(self, d1: Dummy1, d2: Dummy2):
            pass

    config = get_factory_context(Dummy3)
    assert config.name == "dummy3"
    assert config.completed
    requires = config.get_handler(consts.HANDLER_REQUIRES)
    assert len(requires) == 2


def test_instantiate():

    with pytest.raises(TypeError):
        Instantiate()

    for invalid_name in (None, True, False, 1, [1, 2], (1, 2)):
        with pytest.raises(TypeError):
            Instantiate(invalid_name)()

    for invalid_props in (None, True, False, 1, [1, 2], (1, 2)):
        with pytest.raises(TypeError):
            Instantiate("name", invalid_props)()

    with pytest.raises(NameError):
        Instantiate(Dummy1)

    @Instantiate
    class Dummy1:
        pass

    instances = get_factory_context(Dummy1).get_instances()
    assert len(instances) == 1
    assert instances[Dummy1.__name__] == {}

    @Instantiate("dummy")
    @Instantiate("new-dummy", {"id": 1})
    class Dummy2:
        pass

    instances = get_factory_context(Dummy2).get_instances()
    assert len(instances) == 2
    assert instances["dummy"] == {}
    assert instances["new-dummy"] == {"id": 1}


def test_provide():
    @Provides("test1")
    class Dummy1:
        pass

    specs = get_factory_context(Dummy1).get_handler(consts.HANDLER_PROVIDES)
    assert len(specs) == 1
    assert specs[0] == "test1"

    @Provides(["test1", "test2"])
    class Dummy2:
        pass

    specs = get_factory_context(Dummy2).get_handler(consts.HANDLER_PROVIDES)
    assert len(specs) == 2
    assert specs[0] == "test1"
    assert specs[1] == "test2"


def test_requires():
    @Requires("test1")
    class Dummy1:
        pass

    specs = get_factory_context(Dummy1).get_handler(consts.HANDLER_REQUIRES)
    assert len(specs) == 1
    assert specs[0] == "test1"

    @Requires("test1", "test2")
    class Dummy2:
        pass

    specs = get_factory_context(Dummy2).get_handler(consts.HANDLER_REQUIRES)
    assert len(specs) == 2
    assert specs[0] == "test1"
    assert specs[1] == "test2"


def test_default_requires():
    class IService1:
        pass

    class IService2:
        pass

    @Component("test1")
    class Dummy1:
        def __init__(self, s1: IService1, s2: IService2):
            pass

    specs = get_factory_context(Dummy1).get_handler(consts.HANDLER_REQUIRES)
    assert len(specs) == 2
    assert isinstance(specs[0], str)
    assert isinstance(specs[1], str)
    assert IService1.__name__ in specs[0]
    assert IService2.__name__ in specs[1]


def test_validate():
    @Component
    class Dummy:
        @Validate
        def validate(self, ctx):
            pass

        @Invalidate
        def invalidate(self, ctx):
            pass

    context = get_factory_context(Dummy)
    assert Dummy.validate == context.get_callback(consts.CALLBACK_VALIDATE)[0]
    assert Dummy.invalidate == context.get_callback(consts.CALLBACK_INVALIDATE)[0]
