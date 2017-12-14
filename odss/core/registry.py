import bisect

from odss.common import (OBJECTCLASS, SERVICE_BUNDLE_ID, SERVICE_ID,
                         SERVICE_RANKING)

from .errors import BundleException
from .query import create_query
from .utils import class_name, classes_name


class ServiceRegistry:
    def __init__(self, framework):
        self._framework = framework
        self._next_service_id = 1
        self._services = {}
        self._services_classes = {}
        self._services_bundles = {}

    def register(self, bundle, clazz, service, properties):
        service_id = self._next_service_id
        self._next_service_id += 1

        classes = classes_name(clazz)
        properties[OBJECTCLASS] = classes
        properties[SERVICE_ID] = service_id
        properties[SERVICE_BUNDLE_ID] = bundle.id

        if SERVICE_RANKING not in properties:
            properties[SERVICE_RANKING] = 0

        ref = ServiceReference(bundle, properties)
        self._services[ref] = service
        for spec in classes:
            refs = self._services_classes.setdefault(spec, [])
            bisect.insort_left(refs, ref)
        self._services_bundles.setdefault(bundle, []).append(ref)
        return ServiceRegistration(self._framework, ref)

    def unregister(self, reference):
        if reference not in self._services:
            raise BundleException('Unknown service: {}'.format(reference))

        service = self._services.pop(reference)
        for spec in reference.get_property(OBJECTCLASS):
            spec_services = self._services_classes[spec]
            idx = bisect.bisect_left(spec_services, reference)
            del spec_services[idx]
            if not spec_services:
                del self._services_classes[spec]
        bundle = reference.get_bundle()
        if bundle in self._services_bundles:
            self._services_bundles[bundle].remove(reference)
        return service

    def find_service_references(self, clazz=None, query=None,
                                only_first=False):
        refs = []
        if clazz is None and query is None:
            refs = sorted(self._services.keys())
        elif clazz is not None:
            name = class_name(clazz)
            refs = self._services_classes.get(name, [])

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
            service = self._services[reference]
            reference.used_by(bundle)
            return service
        except KeyError:
            raise BundleException(
                "Service not found fo reference: {0}".format(reference))

    def unget_service(self, bundle, reference):
        if not isinstance(reference, ServiceReference):
            raise BundleException('Expected ServiceReference object')
        try:
            service = self._services[reference]
            reference.unused_by(bundle)
            return service
        except KeyError:
            pass

    def get_bundle_references(self, bundle):
        return self._services_bundles.get(bundle, [])


class ServiceReference:
    def __init__(self, bundle, properties):
        self._properties = properties
        self._bundle = bundle
        self._service_id = properties[SERVICE_ID]
        self._sort_key = self._compute_sort_key()
        self._using_bundles = {}

    def get_bundle(self):
        return self._bundle

    def get_property(self, name):
        return self._properties.get(name)

    def get_properties(self):
        return self._properties.copy()

    def unused_by(self, bundle):
        if bundle is None or bundle is self._bundle:
            return
        if bundle in self._using_bundles:
            self._using_bundles[bundle].dec()
            if not self._using_bundles[bundle].is_used():
                del self._using_bundles[bundle]

    def used_by(self, bundle):
        if bundle is None or bundle is self._bundle:
            return
        self._using_bundles.setdefault(bundle, _Counter()).inc()

    def _compute_sort_key(self):
        return (-int(self._properties.get(SERVICE_RANKING, 0)),
                self._service_id)

    def __str__(self):
        return "ServiceReference(id={0}, Bundle={1}, Classes={2})".format(
            self._service_id,
            self._bundle.id,
            self._properties[OBJECTCLASS]
        )

    def __hash__(self):
        return self._service_id

    def __lt__(self, other):
        return self._sort_key < other._sort_key

    def __le__(self, other):
        return self._sort_key <= other._sort_key

    def __eq__(self, other):
        return self._service_id == other._service_id

    def __ne__(self, other):
        return self._service_id != other._service_id

    def __gt__(self, other):
        return self._sort_key > other._sort_key

    def __ge__(self, other):
        return self._sort_key >= other._sort_key


class ServiceRegistration:
    def __init__(self, framework, reference):
        self._framework = framework
        self._reference = reference

    async def unregister(self):
        await self._framework.unregister_service(self)

    def get_reference(self):
        return self._reference


class _Counter:
    def __init__(self):
        self.counter = 0

    def inc(self):
        self.counter += 1

    def dec(self):
        self.counter -= 1

    def is_used(self):
        return self.counter > 0
