import socket
import threading
import time

from .protonlv1 import *
from .protocmp import *
from .common import *

MAX_LEN_FRAME = 8192
INTERVAL_HEARTBEAT = 60
OFFLINE_TIME = 180


class Param:
    def __init__(self):
        self.local_ip = "0.0.0.0"
        self.local_port = 0
        self.local_ia = 0
        self.pwd = ""
        self.server_ip = None
        self.server_port = 0
        self.server_ia = 0


_param = Param()
_socket = 0
_callback_rx_func = None
_rx_ack_heartbeat_thread_time = 0


def init(param):
    global _param
    _param = param
    threading.Thread(target=_udp_listen).start()
    threading.Thread(target=_heartbeat_thread).start()


def _udp_listen():
    global _socket
    _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _socket.bind((_param.local_ip, _param.local_port))

    while True:
        data, addr = _socket.recvfrom(MAX_LEN_FRAME)
        if not _is_frame_valid(data, addr):
            continue
        next_head = data[PNLV1_NEXT_HEAD_POS]
        if next_head == PCMP_HEAD_VALUE:
            _deal_cmp_frame(data)
        else:
            _deal_rx(data)


def _is_frame_valid(data, addr):
    global _param
    if not data:
        return False
    if addr != (_param.server_ip, _param.server_port):
        return False
    if len(data) < PNLV1_HEAD_LEN:
        return False
    if data[PNLV1_VER_POS] != PNLV1_VER:
        return False

    playload_len = (data[PNLV1_PLAYLOAD_LEN_POS] << 8) + data[PNLV1_PLAYLOAD_LEN_POS + 1]
    if playload_len + PNLV1_HEAD_LEN > MAX_LEN_FRAME:
        return False
    if playload_len + PNLV1_HEAD_LEN != len(data):
        return False

    if get_ia(data, PNLV1_HOPS_DST_ADDR_POS) != _param.local_ia:
        return False
    return True


def _deal_cmp_frame(data):
    if len(data) < PNLV1_HEAD_LEN + 3:
        return
    msg_type = data[PNLV1_HEAD_LEN]
    if msg_type != PCMP_MSG_TYPE_ACK_CONNECT_PARENT_ROUTER:
        return
    result = data[PNLV1_HEAD_LEN + 1]
    if result != 0:
        return

    global _rx_ack_heartbeat_thread_time
    _rx_ack_heartbeat_thread_time = time.time()


def _deal_rx(data):
    global _callback_rx_func
    src_ia = get_ia(data, PNLV1_HOPS_SRC_ADDR_POS)
    if _callback_rx_func:
        _callback_rx_func(src_ia, data[PNLV1_HEAD_LEN + 1:])


def _heartbeat_thread():
    while True:
        if _socket != 0:
            _send_heartbeat()
        if is_online():
            time.sleep(INTERVAL_HEARTBEAT)
        else:
            time.sleep(1)


def _send_heartbeat():
    global _param, _socket

    frame = bytearray()
    frame.append(0x01)
    frame.append(0x00)

    # 载荷长度
    frame.append(0x00)
    frame.append(0x00)

    frame.append(0x1C)
    frame.append(0xFF)

    # 源地址
    for i in range(8):
        frame.append((_param.local_ia >> ((7 - i) << 3)) & 0xff)
    # 目的地址
    for i in range(8):
        frame.append((_param.server_ia >> ((7 - i) << 3)) & 0xff)

    frame.append(0x05)
    # 密码长度
    len_pwd = len(_param.pwd)
    frame.append(len_pwd)
    # 密码
    for i in range(len_pwd):
        frame.append(ord(_param.pwd[i]))

    frame.append(0x00)
    frame.append(0x8A)
    frame.append(0x00)
    frame.append(0x00)

    # 载荷长度
    playload_len = len(frame) - PNLV1_HEAD_LEN
    frame[PNLV1_PLAYLOAD_LEN_POS] = playload_len >> 8
    frame[PNLV1_PLAYLOAD_LEN_POS + 1] = playload_len

    _socket.sendto(frame, (_param.server_ip, _param.server_port))


def register_callback_rx(callback_func):
    global _callback_rx_func
    _callback_rx_func = callback_func


def is_online():
    return time.time() - _rx_ack_heartbeat_thread_time < OFFLINE_TIME


def send(dst_ia, data):
    global _param, _socket
    if _socket == 0:
        return

    frame = bytearray()
    frame.append(0x01)
    frame.append(0x00)

    # 载荷长度
    playload_len = len(data) + 1
    frame.append(playload_len >> 8)
    frame.append(playload_len)

    frame.append(0x04)
    frame.append(0xFF)

    # 源地址
    for i in range(8):
        frame.append((_param.local_ia >> ((7 - i) << 3)) & 0xff)
    # 目的地址
    for i in range(8):
        frame.append((dst_ia >> ((7 - i) << 3)) & 0xff)

    frame.append(0x00)
    for i in range(playload_len - 1):
        frame.append(data[i])

    _socket.sendto(frame, (_param.server_ip, _param.server_port))
