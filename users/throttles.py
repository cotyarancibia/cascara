"""Límites por origen y por pareja origen/cuenta, nunca por cuenta global."""
import ipaddress

from django.conf import settings
from django.core.cache import caches
from django.utils.crypto import salted_hmac
from redis.exceptions import RedisError
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle, SimpleRateThrottle


class ThrottleUnavailable(APIException):
    status_code = 503
    default_detail = 'La protección de acceso no está disponible. Intentá más tarde.'
    default_code = 'throttle_unavailable'


def client_ip(request):
    try:
        peer = ipaddress.ip_address(request.META.get('REMOTE_ADDR', ''))
        if settings.IS_PRODUCTION:
            if not any(peer in network for network in settings.AUTH_TRUSTED_PROXIES):
                raise ValueError('Proxy no confiable')
            return str(ipaddress.ip_address(request.META.get('HTTP_X_REAL_IP', '')))
        return str(peer)
    except ValueError as exc:
        raise ThrottleUnavailable() from exc


class OriginThrottle(SimpleRateThrottle):
    cache = caches['auth_throttle']

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': salted_hmac('auth-origin', client_ip(request)).hexdigest()}


class LoginOriginThrottle(OriginThrottle):
    scope = 'login_origin'
    rate = '30/hour'


class LoginPairThrottle(OriginThrottle):
    scope = 'login_pair'
    rate = '8/min'

    def get_cache_key(self, request, view):
        username = request.data.get('username', '')
        username = username.strip().casefold()[:150] if isinstance(username, str) else ''
        ident = salted_hmac('auth-pair', client_ip(request) + '\0' + username).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class RegisterOriginThrottle(OriginThrottle):
    scope = 'register_origin'
    rate = '5/hour'


class SafeThrottle(BaseThrottle):
    throttle_types = ()

    def allow_request(self, request, view):
        self.blocked = None
        if not settings.AUTH_THROTTLE_ENABLED:
            return True
        try:
            for throttle_type in self.throttle_types:
                throttle = throttle_type()
                if not throttle.allow_request(request, view):
                    self.blocked = throttle
                    return False
        except (RedisError, OSError) as exc:
            raise ThrottleUnavailable() from exc
        return True

    def wait(self):
        return self.blocked.wait() if self.blocked else None


class LoginThrottle(SafeThrottle):
    throttle_types = (LoginOriginThrottle, LoginPairThrottle)


class RegisterThrottle(SafeThrottle):
    throttle_types = (RegisterOriginThrottle,)
