import bisect

from odss_common import (OBJECTCLASS, SERVICE_BUNDLE_ID, SERVICE_ID,
                         SERVICE_RANKING)

from .errors import BundleException
from .query import create_query
from .utils import class_name, classes_name


class ServiceRegistry:
    def __init__(self, framework):
        self.__framework = framework
        self.__next_service_id = 1
        self.__serivces = {}
        self.__services_classes = {}
        self.__serivces_bundles = {}

    def register(self, bundle, clazz, service, properties):
        service_id = self.__next_service_id
        self.__next_service_id += 1

        classes = classes_name(clazz)
        properties[OBJECTCLASS] = classes
        properties[SERVICE_ID] = service_id
        properties[SERVICE_BUNDLE_ID] = bundle.id

        if SERVICE_RANKING not in properties:
            properties[SERVICE_RANKING] = 0

        ref = ServiceReference(bundle, properties)
        self.__serivces[ref] = service
        for spec in classes:
            refs = self.__services_classes.setdefault(spec, [])
            bisect.insort_left(refs, ref)
        self.__serivces_bundles.setdefault(bundle, []).append(ref)
        return ServiceRegistration(self.__framework, ref)
    
    def unregister(self, reference):
        if reference not in self.__serivces:
            raise BundleException('Unknown service: {}'.format(reference))

        service = self.__serivces.pop(reference)
        for spec in reference.get_property(OBJECTCLASS):
            spec_services = self.__services_classes[spec]
            idx = bisect.bisect_left(spec_services, reference)
            del spec_services[idx]
            if not spec_services:
                del self.__services_classes[spec]
        bundle = reference.get_bundle()
        if bundle in self.__serivces_bundles:
            self.__serivces_bundles[bundle].remove(reference)
        return service

    def find_service_references(self, clazz=None, query=None,
                                only_first=False):
        refs = []
        if clazz is None and query is None:
            refs = sorted(self.__serivces.keys())
        elif clazz is not None:
            name = class_name(clazz)
            refs = self.__services_classes.get(name, [])

        if refs and query is not None:
            matcher = create_query(query)
            refs = tuple(ref for ref in refs if matcher.match(
                ref.get_properties()))
        if only_first:
            return refs[0] if refs else None
        return refs

    def find_service_reference(self, clazz, query=None):
        if clazz is None:
            raise BundleException('Expected class interface')
        return self.find_service_references(clazz, query, True)

    def get_service(self, bundle, reference):
        if not isinstance(reference, ServiceReference):
            raise BundleException('Expected ServiceReference object')

        try:
            service = self.__serivces[reference]
            reference.used_by(bundle)
            return service
        except KeyError:
            raise BundleException(
                "Service not found fo reference: {0}".format(reference))

    def unget_service(self, bundle, reference):
        if not isinstance(reference, ServiceReference):
            raise BundleException('Expected ServiceReference object')

        try:
            service = self.__serivces[reference]
            reference.unused_by(bundle)
            return service
        except KeyError:
            pass


class ServiceReference:
    def __init__(self, bundle, properties):
        self.__properties = properties
        self.__bundle = bundle
        self.__service_id = properties[SERVICE_ID]
        self.__sort_key = self.__compute_sort_key()
        self.__using_bundles = {}

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

    def __compute_sort_key(self):
        return (-int(self.__properties.get(SERVICE_RANKING, 0)),
                self.__service_id)

    def __str__(self):
        return "ServiceReference(id={0}, Bundle={1}, Classes={2})".format(
            self.__service_id,
            self.__bundle.id,
            self.__properties[OBJECTCLASS]
        )

    def __hash__(self):
        return self.__service_id

    def __lt__(self, other):
        return self.__sort_key < other.__sort_key

    def __le__(self, other):
        return self.__sort_key <= other.__sort_key

    def __eq__(self, other):
        return self.__service_id == other.__service_id

    def __ne__(self, other):
        return self.__service_id != other.__service_id

    def __gt__(self, other):
        return self.__sort_key > other.__sort_key

    def __ge__(self, other):
        return self.__sort_key >= other.__sort_key


class ServiceRegistration:
    def __init__(self, framework, reference):
        self.__framework = framework
        self.__reference = reference

    async def unregister(self):
        await self.__framework.unregister_service(self)

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
