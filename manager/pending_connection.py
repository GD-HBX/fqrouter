import socket
import time
# used to track syn ack we are holding before we know a proper TTL to inject
SYN_ACK_TIMEOUT = 2
pending = {}


class PendingConnection(object):
    def __init__(self):
        self.started_at = time.time()
        self.syn_ack_packets = {} # (dst, dport, sport) => packet
        self.routers = {} # ttl => is_china_router


def is_ip_pending(ip):
    return ip in pending


def record_syn_ack(syn_ack):
    src = socket.inet_ntoa(syn_ack.src)
    dst = socket.inet_ntoa(syn_ack.dst)
    key = (dst, syn_ack.tcp.dport, syn_ack.tcp.sport)
    pending.setdefault(src, PendingConnection()).syn_ack_packets[key] = syn_ack


def record_router(ip, ttl, is_china_router):
    connection = pending.get(ip)
    if not connection:
        return
    connection.routers[ttl] = is_china_router


def is_ip_timeouted(ip):
    connection = pending.get(ip)
    if not connection:
        return False
    return time.time() - connection.started_at > SYN_ACK_TIMEOUT


def pop_syn_ack_packets(ip):
    connection = pending.get(ip)
    if connection is None:
        return ()
    packets = connection.syn_ack_packets.values()
    pending.pop(ip)
    return packets


def get_ttl_to_gfw(ip):
    connection = pending.get(ip)
    if connection is None:
        return None
    routers = connection.routers
    for ttl in sorted(routers.keys()):
        next = routers.get(ttl + 1)
        if next is None:
            continue
        # ttl 8 is china, ttl 9 is not
        # then we think 8 is the ttl to gfw
        if routers[ttl] and not next:
            return ttl
    return None