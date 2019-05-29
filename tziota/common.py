def get_ia(data, offset):
    ia = 0
    for i in range(8):
        ia += data[offset + i] << ((7 - i) << 3)
    return ia
