from .errors import BundleException


def class_name(clazz):
    if isinstance(clazz, str):
        return clazz
    module = getattr(clazz, '__module__', '')
    name = getattr(clazz, '__name__', '')
    if not module and not name:
        raise BundleException('Invalid class name {}'.format(clazz))
    return '{}.{}'.format(module, name)


def classes_name(classes):
    if isinstance(classes, (tuple, list)):
        return tuple((class_name(clazz) for clazz in classes))
    return (class_name(classes), )
