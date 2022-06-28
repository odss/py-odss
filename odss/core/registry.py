import bisect
import typing as t
import logging

from .consts import OBJECTCLASS, SERVICE_BUNDLE_ID, SERVICE_ID, SERVICE_PRIORITY
from .errors import BundleException
from .events import ServiceEvent
from .query import create_query
from .utils import class_name, classes_name


logger = logging.getLogger(__name__)


class ServiceReference:

    __slots__ = [
        "__properties",
        "__bundle",
        "__service_id",
        "__using_bundles",
        "__sort_value",
    ]

    def __init__(self, bundle, properties):
        self.__properties = properties
        self.__bundle = bundle
        self.__service_id = properties[SERVICE_ID]
        self.__using_bundles = {}
        self.__sort_value = self.__compute_sort_value()

    def get_bundle(self):
        return self.__bundle

    def get_property(self, name):
        return self.__properties.get(name)

    def get_properties(self):
        return self.__properties.copy()

    def unused_by(self, bundle):
        if bundle is None or bundle is self.__bundle:
            return
        if bundle in self.__using_bundles:
            self.__using_bundles[bundle].dec()
            if not self.__using_bundles[bundle].is_used():
                del self.__using_bundles[bundle]

    def used_by(self, bundle):
        if bundle is None or bundle is self.__bundle:
            return
        self.__using_bundles.setdefault(bundle, _Counter()).inc()

    def get_using_bundles(self):
        return list(self.__using_bundles.keys())

    def get_sort_value(self) -> t.Tuple[int]:
        return self.__sort_value

    def check_sort_update(self) -> bool:
        sort_value = self.__compute_sort_value()
        if self.__sort_value != sort_value:
            self.__sort_value = sort_value

    def update_sort_value(self) -> None:
        self.__sort_value = self.__compute_sort_value()

    def __compute_sort_value(self):
        return (int(self.__properties.get(SERVICE_PRIORITY, 0)), self.__service_id)

    def __str__(self):
        return "ServiceReference(id={0}, Bundle={1}, Classes={2})".format(
            self.__service_id, self.__bundle.id, self.__properties[OBJECTCLASS]
        )

    def __hash__(self):
        return self.__service_id

    def __lt__(self, other):
        return self.__sort_value < other.__sort_value

    def __le__(self, other):
        return self.__sort_value <= other.__sort_value

    def __eq__(self, other):
        return self.__service_id == other.__service_id

    def __ne__(self, other):
        return self.__service_id != other.__service_id

    def __gt__(self, other):
        return self.__sort_value > other.__sort_value

    def __ge__(self, other):
        return self.__sort_value >= other.__sort_value


class ServiceRegistry:
    def __init__(self, framework):
        self._next_service_id = 1
        self._services = {}
        self._services_classes = {}
        self.__bundle_services = {}
        self.__bundle_unsing = {}
        self.__framework = framework

    def register(self, bundle, clazz, service, properties):
        service_id = self._next_service_id
        self._next_service_id += 1

        classes = classes_name(clazz)
        properties[OBJECTCLASS] = classes
        properties[SERVICE_ID] = service_id
        properties[SERVICE_BUNDLE_ID] = bundle.id

        if SERVICE_PRIORITY not in properties:
            properties[SERVICE_PRIORITY] = 50

        ref = ServiceReference(bundle, properties)
        self._services[ref] = service
        for spec in classes:
            refs = self._services_classes.setdefault(spec, [])
            bisect.insort_left(refs, ref)
        self.__bundle_services.setdefault(bundle, []).append(ref)
        return ServiceRegistration(self.__framework, ref, properties)

    def unregister(self, reference: ServiceReference):
        """
        Unregister serivce

        Args:
            reference (ServiceReference): service reference

        Raises:
            BundleException: Unknow serice reference

        Returns:
            any: service
        """
        if reference not in self._services:
            raise BundleException(f"Unknown service: {reference}")

        logger.debug("Unregister service %s", reference)

        service = self._services.pop(reference)
        for spec in reference.get_property(OBJECTCLASS):
            spec_services = self._services_classes[spec]
            idx = bisect.bisect_left(spec_services, reference)
            del spec_services[idx]
            if not spec_services:
                del self._services_classes[spec]

        bundle = reference.get_bundle()
        if bundle in self.__bundle_services:
            self.__bundle_services[bundle].remove(reference)
        return service

    def find_service_references(self, clazz=None, query=None, only_first=False):
        refs = []
        if clazz is None:
            refs = sorted(self._services.keys())
        elif clazz is not None:
            name = class_name(clazz)
            refs = self._services_classes.get(name, [])

        if refs and query is not None:
            matcher = create_query(query)
            refs = tuple(ref for ref in refs if matcher.match(ref.get_properties()))
        if only_first:
            return refs[0] if refs else None
        return refs

    def find_service_reference(self, clazz, query=None):
        return self.find_service_references(clazz, query, True)

    def get_service(self, bundle, reference: ServiceReference):
        if not isinstance(reference, ServiceReference):
            raise BundleException("Expected ServiceReference object")

        try:
            using = self.__bundle_unsing.setdefault(bundle, {})
            using.setdefault(reference, _Counter()).inc()

            service = self._services[reference]
            reference.used_by(bundle)
            return service
        except KeyError:
            raise BundleException(f"Service not found fo reference: {reference}")

    def unget_service(self, bundle, reference):
        if not isinstance(reference, ServiceReference):
            raise BundleException("Expected ServiceReference object")
        try:
            reference.unused_by(bundle)
            using = self.__bundle_unsing[bundle]
            using[reference].dec()
            if not using[reference].is_used():
                del using[reference]
                if not using:
                    del self.__bundle_unsing[bundle]
        except KeyError:
            pass

    def get_bundle_references(self, bundle):
        return self.__bundle_services.get(bundle, [])[:]

    def get_bundle_using_services(self, bundle):
        return list(self.__bundle_unsing.get(bundle, {}).keys())[:]


class ServiceRegistration:

    __slots__ = ["__framework", "__reference", "__properties"]

    def __init__(self, framework, reference, properties):
        self.__framework = framework
        self.__reference = reference
        self.__properties = properties

    def unregister(self):
        self.__framework.unregister_service(self)

    def set_properties(self, properties):
        for forbidden_key in [OBJECTCLASS, SERVICE_ID, SERVICE_BUNDLE_ID]:
            try:
                del properties[forbidden_key]
            except KeyError:
                pass

        previous = self.__properties.copy()
        self.__properties.update(properties)
        self.__reference.check_sort_update()

        self.__framework._fire_service_event(
            ServiceEvent.MODIFIED, self.__reference, previous
        )

    def get_reference(self):
        return self.__reference


class _Counter:
    def __init__(self):
        self.counter = 0

    def inc(self):
        self.counter += 1

    def dec(self):
        self.counter -= 1

    def is_used(self):
        return self.counter > 0
