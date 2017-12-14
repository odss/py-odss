
class Node:
    def __init__(self, value=None, name=''):
        self.value = value
        self.name = name

    def match(self, params):
        raise NotImplementedError


class LogicNode(Node):
    def __init__(self):
        super().__init__([])


class AndNode(LogicNode):
    def match(self, params):
        for item in self.value:
            if not item.match(params):
                return False
        return True


class OrNode(LogicNode):
    def match(self, params):
        for item in self.value:
            if item.match(params):
                return True
        return False


class NotNode(LogicNode):
    def match(self, params):
        for item in self.value:
            if not item.match(params):
                return True
        return False


class EqNode(Node):
    def match(self, params):
        if self.name in params:
            item = params[self.name]
            if isinstance(item, (list, tuple)):
                return self.value in item
            else:
                return item == self.value
        return False


class LteNode(Node):
    def match(self, params):
        if self.name in params:
            item = params[self.name]
            return item <= self.value
        return False


class GteNode(Node):
    def match(self, params):
        if self.name in params:
            item = params[self.name]
            return item >= self.value
        return False


class ApproxNode(Node):
    def match(self, params):
        if self.name in params:
            item = params[self.name]
            if isinstance(item, (list, tuple)):
                for sub in item:
                    if self.value in sub:
                        return True
            else:
                return self.value in item
        return False


class PresentNode(Node):
    def match(self, params):
        return self.name in params


class SubstringNode(Node):
    def match(self, params):
        if self.name in params:
            item = params[self.name]

            if isinstance(item, (list, tuple)):
                for s in item:
                    if self.value.match(s):
                        return True
            else:
                return self.value.match(item)
        return False


class AllNode(Node):
    def match(self, params):
        return True


class NoneNode(Node):
    def match(self, params):
        return False
