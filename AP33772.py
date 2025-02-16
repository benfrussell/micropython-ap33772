"""
MicroPython port of AP33772-Cpp by CentyLab at https://github.com/CentyLab/AP33772-Cpp
AP33772-Cpp structs and register list ported from "AP33772 I2C Command Tester" by Joseph Liang
"""

import machine
from uctypes import BFUINT8, BFUINT32, BF_POS, BF_LEN, struct, addressof
import time


CMD_SRCPDO = const(0x00)
CMD_PDONUM = const(0x1C)
CMD_STATUS = const(0x1D)
CMD_MASK = const(0x1E)
CMD_VOLTAGE = const(0x20)
CMD_CURRENT = const(0x21)
CMD_TEMP = const(0x22)
CMD_OCPTHR = const(0x23)
CMD_OTPTHR = const(0x24)
CMD_DRTHR = const(0x25)
CMD_RDO = const(0x30)

AP33772_ADDRESS = const(0x51)
SRCPDO_LENGTH = const(28)

AP33772_STATUS = {
    "is_ready":      BFUINT8 | 0 << BF_POS | 1 << BF_LEN,
    "is_success":    BFUINT8 | 1 << BF_POS | 1 << BF_LEN,
    "is_new_pdo":     BFUINT8 | 2 << BF_POS | 1 << BF_LEN,
    "reserved":     BFUINT8 | 3 << BF_POS | 1 << BF_LEN,
    "is_ovp":        BFUINT8 | 4 << BF_POS | 1 << BF_LEN,
    "is_ocp":        BFUINT8 | 5 << BF_POS | 1 << BF_LEN,
    "is_otp":        BFUINT8 | 6 << BF_POS | 1 << BF_LEN,
    "is_dr":         BFUINT8 | 7 << BF_POS | 1 << BF_LEN,
}

PDO_FIXED_DATA = {
    "max_current":   BFUINT32 | 00 << BF_POS | 10 << BF_LEN,
    "voltage":      BFUINT32 | 10 << BF_POS | 10 << BF_LEN,
    "reserved_1":   BFUINT32 | 20 << BF_POS | 10 << BF_LEN,
    "type":         BFUINT32 | 30 << BF_POS | 2 << BF_LEN,
}

PDO_PPS_DATA = {
    "max_current":   BFUINT32 | 0 << BF_POS | 7 << BF_LEN,
    "reserved_1":   BFUINT32 | 7 << BF_POS | 1 << BF_LEN,
    "min_voltage":   BFUINT32 | 8 << BF_POS | 8 << BF_LEN,
    "reserved_2":   BFUINT32 | 16 << BF_POS | 1 << BF_LEN,
    "max_voltage":   BFUINT32 | 17 << BF_POS | 8 << BF_LEN,
    "reserved_3":   BFUINT32 | 25 << BF_POS | 3 << BF_LEN,
    "apdo":         BFUINT32 | 28 << BF_POS | 2 << BF_LEN,
    "type":         BFUINT32 | 30 << BF_POS | 2 << BF_LEN,
}

RDO_FIXED_DATA = {
    "max_current":   BFUINT32 | 00 << BF_POS | 10 << BF_LEN,
    "op_current":    BFUINT32 | 10 << BF_POS | 10 << BF_LEN,
    "reserved_1":   BFUINT32 | 20 << BF_POS | 8 << BF_LEN,
    "obj_position":  BFUINT32 | 28 << BF_POS | 3 << BF_LEN,
    "reserved_2":   BFUINT32 | 31 << BF_POS | 1 << BF_LEN,
}

RDO_PPS_DATA = {
    "op_current":    BFUINT32 | 0 << BF_POS | 7 << BF_LEN,
    "reserved_1":   BFUINT32 | 7 << BF_POS | 2 << BF_LEN,
    "voltage":      BFUINT32 | 9 << BF_POS | 11 << BF_LEN,
    "reserved_2":   BFUINT32 | 20 << BF_POS | 8 << BF_LEN,
    "obj_position":  BFUINT32 | 28 << BF_POS | 3 << BF_LEN,
    "reserved_3":   BFUINT32 | 31 << BF_POS | 1 << BF_LEN,
}

class RDO:
    def __init__(self):
        self.data = bytes([0,] * 4)
        self.pps = struct(addressof(self.data), RDO_PPS_DATA)
        self.fixed = struct(addressof(self.data), RDO_FIXED_DATA)

class PDO:
    def __init__(self, fixed_bytes=None, pps_bytes=None):
        if fixed_bytes is not None:
            self.fixed = struct(addressof(fixed_bytes), PDO_FIXED_DATA)
        elif pps_bytes is not None:
            self.pps = struct(addressof(pps_bytes), PDO_PPS_DATA)

class AP33772:
    def __init__(self, id=0, scl=1, sda=0, freq=400000):
        """Construct and return an AP33772 object with the ID and GPIO pins of the peripheral"""
        self.i2c = machine.I2C(id, scl=machine.Pin(scl), sda=machine.Pin(sda), freq=freq)
        self.exist_pps = 0

        self._num_pdo = 0
        self._index_pdo = 0
        self._req_pps_volt = 0            
        self._pps_index = 8
        self._pdo_data = []
        self._rdo_data = RDO()

    def _i2c_read(self, cmd_addr, length):
        return self.i2c.readfrom_mem(AP33772_ADDRESS, cmd_addr, length)

    def _i2c_write(self, cmd_addr, data):
        self.i2c.writeto_mem(AP33772_ADDRESS, cmd_addr, data)

    def write_rdo(self):
        self._i2c_write(CMD_RDO, self._rdo_data.data)

    def begin(self):
        """Check if power supply is good and fetch the PDO profile."""
        data = self._i2c_read(CMD_STATUS, 1)
        status = struct(addressof(data), AP33772_STATUS)
        time.sleep_ms(10)

        # If negotiation is finished and successful
        if status.is_ready and status.is_success: # type: ignore
            data = self._i2c_read(CMD_PDONUM, 1)
            self._num_pdo = data[0]

            data = self._i2c_read(CMD_SRCPDO, SRCPDO_LENGTH)
            for i in range(self._num_pdo):
                pdo_data = data[i * 4:(i + 1) * 4]
                # Profile type is defined in the last four bits of every 4th byte
                # If profile == 1100, it's a PPS profile
                isPPS = pdo_data[3] & 0xF0 == 0xC0
                if isPPS:
                    self._pdo_data.append(PDO(pps_bytes=pdo_data))
                    self._pps_index = i
                    self.exist_pps = 1
                else:
                    self._pdo_data.append(PDO(fixed_bytes=pdo_data))

    def set_voltage(self, target_voltage: int):
        """
        Set VBUS voltage.

        Args:
            target_voltage: mV
        """
        pps_index = self._pps_index
        if self.exist_pps and self._pdo_data[pps_index].pps.max_voltage * 100 >= target_voltage and self._pdo_data[pps_index].pps.min_voltage * 100 <= target_voltage:
            self._req_pps_volt = target_voltage / 20
            self._rdo_data.pps.obj_position = pps_index + 1 # type: ignore
            self._rdo_data.pps.op_current = pps_pdo_data.max_current # type: ignore
            self._rdo_data.pps.voltage = self._req_pps_volt # type: ignore
            self.write_rdo()
        else:
            temp_index = 0
            # Find which fixed is closest to the target voltage without going over
            for i in range(self._num_pdo - self.exist_pps):
                if self._pdo_data[i].fixed.voltage * 50 <= target_voltage:
                    temp_index = i

            # Check if found the closest fixed voltage is higher than what PPS can reach
            # It looks like this line would fail if there's no PPS PDO
            if self._pdo_data[temp_index].fixed.voltage * 50 > self._pdo_data[pps_index].pps.max_voltage * 100:
                self._index_pdo = temp_index
                self._rdo_data.fixed.obj_position = temp_index + 1 # type: ignore
                self._rdo_data.fixed.max_current = self._pdo_data[temp_index].fixed.max_current # type: ignore
                self._rdo_data.fixed.op_current = self._pdo_data[temp_index].fixed.max_current # type: ignore
                self.write_rdo()
            else:
                self._index_pdo = pps_index
                self._req_pps_volt = self._pdo_data[pps_index].pps.max_voltage * 5
                self._rdo_data.pps.obj_position = pps_index + 1 # type: ignore
                self._rdo_data.pps.op_current = self._pdo_data[pps_index].pps.max_current # type: ignore
                self._rdo_data.pps.voltage = self._req_pps_volt # type: ignore
                self.write_rdo()

    def set_max_current(self, target_max_current: int):
        """
        Set max current before tripping at wall plug.

        Args:
            target_max_current: mA
        """
        index_pdo = self._index_pdo
        pps_index = self._pps_index
        if index_pdo == pps_index:
            if target_max_current <= self._pdo_data[pps_index].pps.max_current * 50:
                self._rdo_data.pps.obj_position = pps_index + 1 # type: ignore
                self._rdo_data.pps.op_current = target_max_current / 50 # type: ignore
                self._rdo_data.pps.voltage = self._req_pps_volt # type: ignore
                self.write_rdo()
        else:
            if target_max_current <= self._pdo_data[index_pdo].fixed.max_current * 10:
                self._rdo_data.fixed.obj_position = index_pdo + 1 # type: ignore
                self._rdo_data.fixed.max_current = target_max_current / 10 # type: ignore
                self._rdo_data.fixed.op_current = target_max_current / 10 # type: ignore
                self.write_rdo()

    def set_pdo(self, pdo_index: int):
        """
        Request PDO profile.

        Args:
            pdo_index: Integer in range 0-255. Start from index 0 to (PDONum - 1) if no PPS, (PDONum -2) if PPS found.
        """

        if self._pps_index == 1:
            guarding = self._num_pdo - 2
        else:
            guarding = self._num_pdo - 1 # Example array[4] only exist index 0,1,2,3

        # Does this work for PPS?
        if pdo_index <= guarding:
            self._rdo_data.fixed.obj_position = pdo_index - 1 # type: ignore
            self._rdo_data.fixed.max_current = self._pdo_data[pdo_index].fixed.max_current # type: ignore
            self._rdo_data.fixed.op_current = self._pdo_data[pdo_index].fixed.max_current # type: ignore
            self.write_rdo()

    def set_ntc(self, tr25: int, tr50: int, tr75: int, tr100: int):
        """
        Set resistance value of 10K NTC at 25C, 50C, 75C and 100C. Default is 10000, 4161, 1928, 974Ohm.
        Blocking function due to long I2C write, min blocking time 15ms
        
        Args:
            tr25, tr50, tr75, tr100: Ohms
        """
        self._i2c_write(0x28, bytes([(tr25 & 0xFF), (tr25 >> 8) & 0xFF]))
        time.sleep_ms(5)

        self._i2c_write(0x2A, bytes([(tr50 & 0xFF), (tr50 >> 8) & 0xFF]))
        time.sleep_ms(5)

        self._i2c_write(0x2C, bytes([(tr75 & 0xFF), (tr75 >> 8) & 0xFF]))
        time.sleep_ms(5)

        self._i2c_write(0x2E, bytes([(tr100 & 0xFF), (tr100 >> 8) & 0xFF]))

    def set_derating_temp(self, temperature: int):
        """
        Set target temperature (C) when output power through USB-C is reduced. Default is 120 C.
        
        Args:
            temperature: unit in Celcius
        """
        self._i2c_write(CMD_DRTHR, bytes([temperature]))

    def set_mask(self, flag):
        mask_read = self._i2c_read(CMD_MASK, 1)
        new_mask = mask_read[0] | flag
        time.sleep_ms(5)
        self._i2c_write(CMD_MASK, bytes([new_mask]))

    def clear_mask(self, flag):
        mask_read = self._i2c_read(CMD_MASK, 1)
        new_mask = mask_read[0] | ~flag
        time.sleep_ms(5)
        self._i2c_write(CMD_MASK, bytes([new_mask]))

    def read_voltage(self) -> int:
        """
        Read VBUS voltage.
        
        Returns:
            voltage in mV
        """
        data = self._i2c_read(CMD_VOLTAGE, 1)
        return data[0] * 80  # I2C read return 80mV/LSB

    def read_current(self) -> int:
        """
        Read maximum VBUS current.
        
        Returns:
            current in mA
        """
        data = self._i2c_read(CMD_CURRENT, 1)
        return data[0] * 24  # I2C read return 24mA/LSB

    def read_temp(self) -> int:
        """
        Read NTC temperature.
        
        Returns:
            temperature in mA
        """
        data = self._i2c_read(CMD_TEMP, 1)
        return data[0]  # I2C read return 1C/LSB
    
    def print_pdo(self):
        """Debug code to quickly check power supply profile PDOs."""
        print(f"Source PDO Number = {self._num_pdo}\n")

        for i, pdo in enumerate(self._pdo_data):
            if i == self._pps_index:
                print(f"PDO[{i + 1}] - PPS : {pdo.pps.min_voltage * 100 / 1000}V~{pdo.pps.max_voltage * 100 / 1000}V @ {pdo.pps.max_current * 50 / 1000}A")
            else:
                print(f"PDO[{i + 1}] - Fixed : {pdo.fixed.voltage * 50 / 1000}V @ {pdo.fixed.max_current * 10 / 1000}A")
        print("===============================================")


    def reset(self):
        """Hard reset the power supply. Will temporary cause power outage."""    
        self._i2c_write(CMD_RDO, bytes([0x0] * 4))

    def get_num_pdo(self) -> int:
        """Get the number of power profile, include PPS if exist."""
        return self._num_pdo
    
    def get_pps_index(self) -> int:
        """Get index of PPS profile."""
        return self._pps_index

    def get_pdo_max_current(self, pdo_index: int) -> int:
        """
        max_current for fixed voltage PDO.

        Args:
            pdo_index: Integer in range 0-255.

        Returns:
            Current in mAmp.
        """
        return self._pdo_data[pdo_index].max_current * 10

    def get_pdo_voltage(self, pdo_index: int):
        """
        Get fixed PDO voltage.

        Args:
            pdo_index: Integer in range 0-255.

        Returns:
            Voltage in mVolt.
        """
        return self._pdo_data[pdo_index].voltage * 50
    
    # Test with PPS
    def get_pps_min_voltage(self, pps_index: int) -> int:
        """
        Get PPS min voltage.

        Args:
            pps_index: Integer in range 0-255.

        Returns:
            Voltage in mVolt.
        """
        return self._pdo_data[self._pps_index].min_voltage * 100

    # Test with PPS
    def get_pps_max_voltage(self, pps_index: int) -> int:
        """
        Get PPS max voltage.

        Args:
            pps_index: Integer in range 0-255.

        Returns:
            Voltage in mVolt.
        """
        return self._pdo_data[self._pps_index].max_voltage * 100

    # Test with PPS
    def get_pps_max_current(self, pps_index: int) -> int:
        """
        Get PPS max current.

        Args:
            pps_index: Integer in range 0-255.

        Returns:
            Current in mAmp.
        """
        return self._pdo_data[self._pps_index].max_current * 50

    def set_supply_voltage_current(self, target_voltage: int, target_current: int):
        """     
        Set VBUS voltage and max current. Current will automatically be in limit mode.
        
        Args:
            target_voltage: mV 
            target_current: mA
        """
        pps_profile = self._pdo_data[self._pps_index]
        pps_index = self._pps_index
        if self.exist_pps and pps_profile.max_voltage * 100 >= target_voltage and pps_profile.min_voltage * 100 <= target_voltage:
            self._index_pdo = pps_index
            self._req_pps_volt = target_voltage / 20
            self._rdo_data.pps.obj_position = pps_index + 1 # type: ignore
            self._rdo_data.pps.op_current = target_current / 50 # type: ignore
            self._rdo_data.pps.voltage = self._req_pps_volt # type: ignore
            self.write_rdo()