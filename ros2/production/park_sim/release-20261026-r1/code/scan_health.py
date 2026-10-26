"""Wall-time freshness and schema checks for the fixed simulated lidar profile."""
import math

class ScanHealth:
    def __init__(self,started,startup_limit=120.,freshness_limit=1.):
        self.started=started;self.startup_limit=startup_limit;self.freshness_limit=freshness_limit
        self.last_advance=None;self.last_stamp=None

    def observe(self,message,now):
        values=[message.angle_min,message.angle_max,message.angle_increment,message.range_min,message.range_max]
        if not all(math.isfinite(v) for v in values) or len(message.ranges)!=720 or message.angle_increment<=0 or not 0<message.range_min<message.range_max:
            return 'invalid_scan_schema'
        expected=message.angle_min+(len(message.ranges)-1)*message.angle_increment
        if abs(expected-message.angle_max)>2*message.angle_increment:return 'invalid_scan_angles'
        if abs(message.range_min-.12)>.001 or abs(message.range_max-12.)>.001:return 'unexpected_sensor_ranges'
        stamp=message.header.stamp.sec+message.header.stamp.nanosec/1e9
        if self.last_stamp is not None and stamp<self.last_stamp:return 'scan_clock_regressed'
        if self.last_stamp is None or stamp>self.last_stamp:self.last_stamp=stamp;self.last_advance=now
        return self.fault(now)

    def fault(self,now):
        if self.last_advance is None:return 'scan_startup_missing' if now-self.started>self.startup_limit else None
        return 'scan_stale' if now-self.last_advance>self.freshness_limit else None
