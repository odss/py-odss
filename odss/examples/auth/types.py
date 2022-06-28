import collections
import json
import secrets
import typing

import redis as redis_client

# from rialto.application.ports import auth as interfaces


class UserInfo(IUserInfo):
    def __init__(self, identity: str, verified: bool = True) -> None:
        self._identity = identity
        self._verified = verified

    def get_identity(self) -> str:
        return self._identity

    def is_verified(self) -> bool:
        return self._verified

    def is_authenticated(self) -> bool:
        return True

    def is_anonymous(self) -> bool:
        return False


class AnonymousUserInfo(IUserInfo):
    def get_identity(self) -> str:
        pass

    def is_authenticated(self) -> bool:
        return False

    def is_anonymous(self) -> bool:
        return True

    def is_verified(self) -> bool:
        return False


class AuthRequestContext(IAuthRequestContext):
    def __init__(self, auth_policy: IAuthenticationPolicy) -> None:
        self.auth_policy = auth_policy
        self.action: IAction = NullAction()

    def remember(self, identity: str) -> None:
        pass

    def forget(self) -> None:
        pass

    def finalize(self, request: IAuthRequest, response: IAuthResponse) -> None:
        pass


class NullAction(IAction):
    def dispatch(
        self,
        policy: IAuthenticationPolicy,
        request: IAuthRequest,
        response: IAuthResponse,
    ) -> None:
        pass


class BaseAuthenticationPolicy(IAuthenticationPolicy):
    def identify(self, request: IAuthRequest) -> str:
        pass

    def authenticate(self, request: IAuthRequest) -> str:
        pass

    def remember(
        self, request: IAuthRequest, response: IAuthResponse, identity: str
    ) -> None:
        pass

    def forget(
        self,
        request: IAuthRequest,
        response: IAuthResponse,
    ) -> None:
        pass


class Auth(IAuth):
    def __init__(self) -> None:
        self.auth_policy = AuthenticationStackPolicy()

    def add_auth_policy(self, name: str, policy: IAuthenticationPolicy) -> None:
        self.auth_policy.add_policy(name, policy)

    def current_user(self, request: IAuthRequest) -> IUserInfo:
        identity = self.auth_policy.authenticate(request)
        if identity:
            return UserInfo(identity)
        return AnonymousUserInfo()

    def create_request_context(self) -> IAuthRequestContext:
        return AuthRequestContext(self.auth_policy)


class AuthenticationStackPolicy(IAuthenticationPolicy):
    def __init__(self) -> None:
        self._policies: typing.Dict[
            str, IAuthenticationPolicy
        ] = collections.OrderedDict()

    def add_policy(self, name: str, policy: IAuthenticationPolicy) -> None:
        self._policies[name] = policy

    def authenticate(self, request: IAuthRequest) -> str:
        for policy in self._policies.values():
            identity = policy.authenticate(request)
            if identity:
                return identity
        return ""

    def remember(
        self, request: IAuthRequest, response: IAuthResponse, identity: str
    ) -> None:
        for policy in self._policies.values():
            policy.remember(request, response, identity)

    def forget(
        self,
        request: IAuthRequest,
        response: IAuthResponse,
    ) -> None:
        for policy in self._policies.values():
            policy.forget(request, response)


class CookieStorage(ICookieStorage):
    def __init__(self, settings: ICookieSettings) -> None:
        self.settings = settings

    def load(self, request: IAuthRequest) -> typing.Optional[str]:
        return request.cookies.get(self.settings["name"])

    def create_token(self) -> str:
        return secrets.token_urlsafe(self.settings["size"])

    def save(self, request: IAuthRequest, response: IAuthResponse, sid: str) -> None:
        response.set_cookie(
            key=self.settings["name"],
            value=sid,
            max_age=self.settings["max_age"],
            httponly=self.settings["http_only"],
            secure=self.settings["secure"],
            path=self.settings["path"],
            domain=self.settings["domain"],
            samesite=self.settings["samesite"],
        )

    def remove(
        self,
        request: IAuthRequest,
        response: IAuthResponse,
    ) -> None:
        response.set_cookie(self.settings["name"], max_age=0)


class RedisIdentityStorage(IIdentityStorage):
    def __init__(self, redis: redis_client.Redis, time: int) -> None:
        self.redis = redis
        self.time = time

    def load(self, sid: str) -> str:
        key = self.key(sid)
        self.redis.expire(key, self.time)  # increase ttl time
        session = self.redis.get(
            key
        )  # session data obtained from redis might be NoneType
        return typing.cast(
            str,
            self._decode(session)
            if isinstance(session, (str, bytes, bytearray)) and session
            else "",
        )

    def save(self, sid: str, identity: str) -> bool:
        value = self._encode(identity)
        if value:
            self.redis.setex(name=self.key(sid), value=value, time=self.time)
            return True
        return False

    def remove(self, sid: str) -> None:
        self.redis.delete(self.key(sid))

    def key(self, sid: str) -> str:
        return "user:session:{}".format(sid)

    def _decode(
        self, data: typing.Union[str, bytes, bytearray]
    ) -> typing.Union[dict, list, str]:
        try:
            return json.loads(data)
        except (TypeError, ValueError):
            return ""

    def _encode(self, data: typing.Any) -> str:  # type: ignore  # (because typing.Any)
        try:
            return json.dumps(data)
        except (TypeError, ValueError):
            return ""
