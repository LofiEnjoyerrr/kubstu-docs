from rest_framework.throttling import ScopedRateThrottle


class ExtendedRateThrottle(ScopedRateThrottle):
    def parse_rate(self, rate):
        # Extends DRF's ``X/Yu`` rate syntax so the ``Y`` multiplier may be
        # more than one digit — e.g. ``5/15m`` for "5 per 15 minutes".
        # The base class only understands ``X/u`` (multiplier always 1).
        num, period = rate.split('/')
        num_requests = int(num)
        multiplier = int(period[:-1])
        duration = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[period[-1]]
        return num_requests, duration * multiplier
