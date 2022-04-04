#!/usr/bin/env python

import asyncio

from uhidgamepad import Gamepad

# Fake a Logitech F310 in DirectInput mode
VENDOR_ID   = 0x046D # Logitech
PRODUCT_ID  = 0xC216 # Direct Input Gamepad
DEVICE_NAME = 'Logitech Dual Action'

async def main():
    gp = Gamepad(VENDOR_ID, PRODUCT_ID, DEVICE_NAME)
    await gp.open()
    await asyncio.sleep(30)
 
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())  # create device
    #loop.run_forever()  # run queued dispatch tasks