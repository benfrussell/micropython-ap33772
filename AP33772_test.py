from AP33772 import AP33772
from time import sleep

def pps_tests(ap: AP33772, index):
    print("\nDoing PPS tests")
    sleep(1)

    min_voltage = ap.get_pps_min_voltage(index)
    print(f"Min voltage: {min_voltage}mV")
    max_voltage = ap.get_pps_max_voltage(index)
    print(f"Max voltage: {max_voltage}mV")
    max_current = ap.get_pps_max_current(index)
    print(f"Max current: {max_current}mA")

    print(f"Setting supply voltage to {min_voltage}mV and current to {max_current}mA")
    ap.set_supply_voltage_current(min_voltage, max_current)  
    sleep(1)

    half_current = int(max_current / 2)
    print(f"Setting max current to {half_current}mA")
    ap.set_max_current(half_current)
    sleep(1)

    print(f"Setting voltage to {max_voltage}mV")
    ap.set_voltage(max_voltage)
    sleep(1)

def fixed_tests(ap: AP33772, index):
    print("\nDoing fixed tests")
    sleep(1)

    print(f"Setting PDO to index {index}")
    ap.set_pdo(index)
    sleep(1)

    max_current  = ap.get_pdo_max_current(index)
    print(f"Min current: {max_current}mA")
    voltage = ap.get_pdo_voltage(index)
    print(f"Voltage: {voltage}mV")

    print(f"Setting max current to {max_current}mA")
    ap.set_max_current(max_current)
    sleep(1)

    print(f"Setting voltage to {voltage}mV")
    ap.set_voltage(voltage)
    sleep(1)

def run_tests(ap: AP33772):
    try:
        ap.begin()
    except Exception as e:
        print(f"Failed to begin connection with power supply: {e}")

    if ap.get_num_pdo() == 0:
        print("No PDOs exist - skipping PDO tests")
    else:
        ap.print_pdo()

        pps_index = ap.get_pps_index()
        if pps_index == 8:
            print("No PPS PDO found - skipping PPS tests")
        else:
            pps_tests(ap, pps_index)

        fixed_index = None
        for i in range(ap.get_num_pdo()):
            if i != pps_index:
                print(f"Using PDO {i} for fixed PDO tests")
                break
        if fixed_index is None:
            print("No fixed PDO found - skipping fixed tests")
        else:
            fixed_tests(ap, fixed_index)

        print("\nPDO tests finished")

    print("\nSetting and clearing mask")
    ap.set_mask(0)
    sleep(1)
    ap.clear_mask(0)
    sleep(1)

    print("Setting derating temp")
    ap.set_derating_temp(120)
    sleep(1)

    print("Setting NTC")
    ap.set_ntc(10000, 4161, 1928, 974)
    sleep(1)

    print(f"\nCurrent is {ap.read_current()}mA")
    print(f"Voltage is {ap.read_voltage()}mV")
    print(f"Temperature is {ap.read_temp()}C")

try:
    ap = AP33772()
except Exception as e:
    print(f"Failed to connect to AP33772: {e}")
    exit(1)

run_tests(ap)

print("\nTests complete, resetting")
ap.reset()