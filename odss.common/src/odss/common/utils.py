import inspect
from contextlib import contextmanager

from .core import IBundleContext, IServiceReference


def get_class_name(specification):
    if not specification:
        raise ValueError("No specifications given")
    if inspect.isclass(specification):
        return "{0}.{1}".format(specification.__module__, specification.__qualname__)
    if isinstance(specification, str):
        return specification
    raise ValueError("Unknow specifications type: {}".format(type(specification)))


def get_classes_name(specifications):
    if not isinstance(specifications, (tuple, list)):
        specifications = [specifications]
    return tuple(get_class_name(specification) for specification in specifications)


@contextmanager
def use_serivce(ctx: IBundleContext, reference: IServiceReference):
    if reference is None:
        raise TypeError("Invalid reference")

    try:
        yield ctx.get_service(reference)
    finally:
        ctx.unget_service(reference)
