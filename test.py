import threading
import time

import tziota


def main():
    param = tziota.Param()
    param.local_ip = "10.58.4.52"
    param.local_port = 14130
    param.local_ia = 0x2140000000000100
    param.pwd = "123"
    param.server_ip = "115.28.86.171"
    param.server_port = 14129
    param.server_ia = 0x2140000000000002
    tziota.init(param)
    tziota.register_callback_rx(deal_rx)

    threading.Thread(target=cycle_task).start()


def deal_rx(ia, data):
    print('IA:0x%016x' % ia)
    for x in data:
        print('%02x' % x, end=' ')
    print()


def cycle_task():
    while True:
        if tziota.is_online():
            frame = bytearray()
            frame.append(1)
            frame.append(2)
            frame.append(3)
            frame.append(4)
            frame.append(5)
            tziota.send(0x2140000000000101, frame)
        else:
            print('当前掉线')

        time.sleep(1)


if __name__ == '__main__':
    main()
