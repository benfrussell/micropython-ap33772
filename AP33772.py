"""
MicroPython port of AP33772-Cpp by CentyLab at https://github.com/CentyLab/AP33772-Cpp
AP33772-Cpp structs and register list ported from "AP33772 I2C Command Tester" by Joseph Liang
"""

import machine

AP33772_ADDRESS = const(0x51)
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
READ_BUFF_LENGTH = const(30)
WRITE_BUFF_LENGTH = const(6)
SRCPDO_LENGTH = const(28)

class AP33772:
    def __init__(self, id=0, scl=1, sda=0, freq=400000):
        """Construct and return an AP33772 object with the ID and GPIO pins of the peripheral"""
        self.i2c = machine.I2C(id, scl=machine.Pin(scl), sda=machine.Pin(sda), freq=freq)
        self.read_buf = bytearray(READ_BUFF_LENGTH)
        self.write_buf = bytearray(WRITE_BUFF_LENGTH)
        self.exist_pps = 0

        self._num_pdo = 0
        self._index_pdo = 0
        self._req_pps_volt = 0
        self._pps_index = 8

    def _i2c_read(self, cmd_addr, length):
        try:
            self.read_buf = self.i2c.readfrom_mem(AP33772_ADDRESS, cmd_addr, length)
            return list(self.read_buf)
        except Exception as e:
            print(f"I2C Read Error: {e}")
            return None

    def _i2c_write(self, cmd_addr, data):
        try:
            self.i2c.writeto_mem(AP33772_ADDRESS, cmd_addr, bytes(data))
        except Exception as e:
            print(f"I2C Write Error: {e}")

    def begin(self):
        """Check if power supply is good and fetch the PDO profile."""
        raise NotImplementedError()

    def set_voltage(self, target_voltage: int):
        """
        Set VBUS voltage.

        Args:
            target_voltage: mV
        """
        voltage_val = target_voltage // 80  # Convert mV to LSB
        self._i2c_write(CMD_VOLTAGE, [voltage_val])

    def set_max_current(self, target_max_current: int):
        """
        Set max current before tripping at wall plug.

        Args:
            target_max_current: mA
        """
        current_val = target_max_current // 24  # Convert mA to LSB
        self._i2c_write(CMD_CURRENT, [current_val])

    def set_pdo(self, pdo_index: int):
        """
        Request PDO profile.

        Args:
            pdo_index: Integer in range 0-255. Start from index 0 to (PDONum - 1) if no PPS, (PDONum -2) if PPS found.
        """
        raise NotImplementedError()

    def set_ntc(self, tr25: int, tr50: int, tr75: int, tr100: int):
        """
        Set resistance value of 10K NTC at 25C, 50C, 75C and 100C. Default is 10000, 4161, 1928, 974Ohm.
        Blocking function due to long I2C write, min blocking time 15ms
        
        Args:
            tr25, tr50, tr75, tr100: Ohms
        """
        raise NotImplementedError()

    def set_derating_temp(self, temperature: int):
        """
        Set target temperature (C) when output power through USB-C is reduced. Default is 120 C.
        
        Args:
            temperature: unit in Celcius
        """
        raise NotImplementedError()

    def set_mask(self, flag):
        raise NotImplementedError()

    def clear_mask(self, flag):
        raise NotImplementedError()

    def write_rdo(self):
        """Write the desire power profile back to the power source."""
        raise NotImplementedError()

    def read_voltage(self) -> int | None:
        """
        Read VBUS voltage.
        
        Returns:
            voltage in mV
        """
        data = self._i2c_read(CMD_VOLTAGE, 1)
        if data:
            return data[0] * 80  # LSB: 80mV
        return None

    def read_current(self) -> int | None:
        """
        Read maximum VBUS current.
        
        Returns:
            current in mA
        """
        data = self._i2c_read(CMD_CURRENT, 1)
        if data:
            return data[0] * 24  # LSB: 24mA
        return None

    def read_temp(self) -> int | None:
        """
        Read NTC temperature.
        
        Returns:
            temperature in mA
        """
        data = self._i2c_read(CMD_TEMP, 1)
        if data:
            return data[0]  # Unit: 1°C
        return None
    
    def print_pdo(self):
        """Debug code to quickly check power supply profile PDOs."""
        raise NotImplementedError()

    def reset(self):
        """Hard reset the power supply. Will temporary cause power outage."""
        self._i2c_write(CMD_MASK, [0x00])

    def get_num_pdo(self) -> int | None:
        """Get the number of power profile, include PPS if exist."""
        data = self._i2c_read(CMD_PDONUM, 1)
        if data:
            return data[0]
        return None
    
    def get_pps_index(self) -> int:
        """Get index of PPS profile."""
        raise NotImplementedError()

    def get_pdo_max_current(self, pdo_index: int) -> int | None:
        """
        MaxCurrent for fixed voltage PDO.

        Args:
            pdo_index: Integer in range 0-255.

        Returns:
            Current in mAmp.
        """
        data = self._i2c_read(CMD_SRCPDO + (pdo_index * 4), 4)
        if data:
            max_current = (data[0] & 0x3F) << 4 | (data[1] >> 4)
            return max_current * 10  # Convert to mA
        return None

    def get_pdo_voltage(self, pdo_index: int):
        """
        Get fixed PDO voltage.

        Args:
            pdo_index: Integer in range 0-255.

        Returns:
            Voltage in mVolt.
        """
        data = self._i2c_read(CMD_SRCPDO + (pdo_index * 4), 4)
        if data:
            voltage = (data[1] << 2) | (data[0] >> 6)
            return voltage * 50  # Convert to mV
        return None
    
    def get_pps_min_voltage(self, pps_index: int) -> int:
        """
        Get PPS min voltage.

        Args:
            pps_index: Integer in range 0-255.

        Returns:
            Voltage in mVolt.
        """
        raise NotImplementedError()

    def get_pps_max_voltage(self, pps_index: int) -> int:
        """
        Get PPS max voltage.

        Args:
            pps_index: Integer in range 0-255.

        Returns:
            Voltage in mVolt.
        """
        raise NotImplementedError()

    def get_pps_max_current(self, pps_index: int) -> int:
        """
        Get PPS max current.

        Args:
            pps_index: Integer in range 0-255.

        Returns:
            Current in mAmp.
        """
        raise NotImplementedError()

    def set_supply_voltage_current(self, target_voltage: int, target_current: int):
        """     
        Set VBUS voltage and max current. Current will automatically be in limit mode.
        
        Args:
            target_voltage: mV 
            target_current: mA
        """
        raise NotImplementedError()