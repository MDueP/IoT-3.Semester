import machine
from time import sleep

class MPU6050():
    def __init__(self, i2c, addr=0x68):
        self.iic = i2c
        self.addr = addr
        try:
            self.iic.writeto(self.addr, bytearray([107,0]))
        except:
            print("I2C Fejl, Tjek GPIO pins er korrekt forbundet")
    def get_raw_values(self):
        raw_values = self.iic.readfrom_mem(self.addr, 0x3B, 14)
        return raw_values

    def bytes_toint(self, firstbyte, secondbyte):
        if not firstbyte & 0x80:
            return firstbyte << 8 | secondbyte
        return - (((firstbyte ^ 255) << 8) | (secondbyte ^ 255) + 1)

    def get_values(self):
        raw_ints = self.get_raw_values()
        vals = {}
        vals["GyroX"] = self.bytes_toint(raw_ints[8], raw_ints[9])
        vals["GyroY"] = self.bytes_toint(raw_ints[10], raw_ints[11])
        vals["GyroZ"] = self.bytes_toint(raw_ints[12], raw_ints[13])
        return vals 

    def val_test(self):  # ONLY FOR TESTING! Also, fast reading sometimes crashes IIC
        while 1:
            print(self.get_values())
            sleep(0.05)
