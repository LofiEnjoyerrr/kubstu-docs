from rest_framework.throttling import ScopedRateThrottle


class ExtendedRateThrottle(ScopedRateThrottle):
    def parse_rate(self, rate):
        num, period = rate.split('/')
        num_requests = int(num)
        multiplier = int(period[0])
        duration = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[period[1]]
        return num_requests, duration * multiplier
