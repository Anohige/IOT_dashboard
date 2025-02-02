# daq.py

class daq:
    """
    A simple class for data acquisition (DAQ) operations,
    here focusing on retrieving the Raspberry Pi serial number.
    """

    def __init__(self):
        self.serial_number = self.get_rpi_serial()

    def get_rpi_serial(self):
        """
        Attempt to read the Raspberry Pi serial from /proc/cpuinfo.
        Returns a string. If not on a Pi or any error occurs, returns 'UNKNOWN'.
        """
        cpuserial = "UNKNOWN"
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Serial'):
                        # Typically line looks like: "Serial  : 00000000xxxxxxx"
                        parts = line.split(':')
                        if len(parts) == 2:
                            cpuserial = parts[1].strip()
                            break
        except Exception as e:
            print(f"[DAQ] Could not read /proc/cpuinfo: {e}")
        return cpuserial