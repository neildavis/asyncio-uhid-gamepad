import struct
import uhid

from descriptor import uhid_desc

DEFAULT_VENDOR_ID = 0x9999
DEFAULT_PRODUCT_ID = 0x9999
DEFAULT_DEVICE_NAME = 'asyncio-hid-gamepad'

class Gamepad:
    """Gamepad represents a USB HID Gamepad device implemented via Linux UHID
    """

    def __init__(self, vendor_id=DEFAULT_VENDOR_ID, 
                    product_id=DEFAULT_PRODUCT_ID,
                    device_name=DEFAULT_DEVICE_NAME):
        """Create a Gamepad object to send USB Gamepad HID events via local UHID
        You must await an open() call before sending any input events
        """

        # Reuse this bytearray to send HID reports.
        # Typically controllers start numbering buttons at 1 rather than 0.
        # report[0] buttons   0-8: report[1] buttons  9-16
        # report[2] buttons 17-24: report[3] buttons 25-32
        # report[4] joystick 0 x LSB: report[5] joystick 0 x MSB: -32767 to 32767
        # report[6] joystick 0 y LSB: report[7] joystick 0 y MSB: -32767 to 32767
        # report[8] joystick 1 x LSB: report[9] joystick 1 x MSB: -32767 to 32767
        # report[10] joystick 1 y LSB: report[11] joystick 1 y MSB: -32767 to 32767
        self._report = bytearray(12)
       
        # Remember the last report as well, so we can avoid sending duplicate reports.
        self._last_report = bytearray(12)

        # Gamepad controls state
        self._buttons_state = 0 # 32-bit bitfield. LSB = 1, MSB = 32
        self._joy_x = 0 # 16-bit
        self._joy_y = 0 # 16-bit
        self._joy_z = 0 # 16-bit
        self._joy_r_z = 0 # 16-bit

        # UHID device
        self._device = uhid.UHIDDevice(vendor_id,
            product_id, 
            device_name, 
            uhid_desc,
            backend=uhid.AsyncioBlockingUHID,
        )
        # UHIDDevice __init__ includes an initialize() call
        self._intitialized = True
        # The device is not ready to send input until we receive a UHID_START event from uhid system
        self._started = False


    async def open(self):
        """Create the UHID device and wait for it to become ready for input (UHID_START received)
        """
        if not self._intitialized:
            self._device.initialize()
            self._intitialized = True
        if not self._started:
            await self._device.wait_for_start_asyncio()
            self._started = True

    def close(self):
        """Close the UHID device. It can be re-opened by calling open()
        """
        if self._intitialized:
            self._device.destroy()
            self._intitialized = False
            self._started = False

    def press_buttons(self, *buttons):
        """Press and hold the given buttons."""
        for button in buttons:
            self._buttons_state |= 1 << self._validate_button_number(button) - 1
        self._send_report()

    def release_buttons(self, *buttons):
        """Release the given buttons."""
        for button in buttons:
            self._buttons_state &= ~(1 << self._validate_button_number(button) - 1)
        self._send_report()

    def release_all_buttons(self):
        """Release all the buttons."""

        self._buttons_state = 0
        self._send_report()

    def click_buttons(self, *buttons):
        """Press and release the given buttons."""
        self.press_buttons(*buttons)
        self.release_buttons(*buttons)

    def move_joysticks(self, x=None, y=None, z=None, r_z=None):
        """Set and send the given joystick values.
        The joysticks will remain set with the given values until changed
        One joystick provides ``x`` and ``y`` values,
        and the other provides ``z`` and ``r_z`` (z rotation).
        Any values left as ``None`` will not be changed.
        All values must be in the range -127 to 127 inclusive.
        Examples::
            # Change x and y values only.
            gp.move_joysticks(x=100, y=-50)
            # Reset all joystick values to center position.
            gp.move_joysticks(0, 0, 0, 0)
        """
        if x is not None:
            self._joy_x = self._validate_joystick_value(x)
        if y is not None:
            self._joy_y = self._validate_joystick_value(y)
        if z is not None:
            self._joy_z = self._validate_joystick_value(z)
        if r_z is not None:
            self._joy_r_z = self._validate_joystick_value(r_z)
        self._send_report()

    def reset_all(self):
        """Release all buttons and set joysticks to zero."""
        self._buttons_state = 0
        self._joy_x = 0
        self._joy_y = 0
        self._joy_z = 0
        self._joy_r_z = 0
        self._send_report(always=True)

    def _send_report(self, always=False):
        """Send a report with all the existing settings.
        If ``always`` is ``False`` (the default), send only if there have been changes.
        """
        if not self._started:
            return
        struct.pack_into(
            "<Lhhhh",
            self._report,
            0,
            self._buttons_state,
            self._joy_x,
            self._joy_y,
            self._joy_z,
            self._joy_r_z,
        )

        if always or self._last_report != self._report:
            self._device.send_input(self._report)
            # Remember what we sent, without allocating new storage.
            self._last_report[:] = self._report

    @staticmethod
    def _validate_button_number(button):
        if not 1 <= button <= 32:
            raise ValueError("Button number must in range 1 to 32")
        return button

    @staticmethod
    def _validate_joystick_value(value):
        if not -32767 <= value <= 32767:
            raise ValueError("Joystick value must be in range -32767 to 32767")
        return value

