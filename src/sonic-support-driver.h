// Copyright (c) 2016 Arista Networks, Inc.  All rights reserved.
// Arista Networks, Inc. Confidential and Proprietary.

#ifndef DRIVER_SONICSUPPORTDRIVER_H
#define DRIVER_SONICSUPPORTDRIVER_H

#define SONICDBG 1

#ifdef SONICDBG
#define DPRINT(_text) printk(KERN_DEBUG _text);
#else
#define DPRINT(_text) do {} while (0);
#endif

s32 i2c_read_byte(int master_num, int bus, u16 addr, u8 reg, u8 *buf);
s32 i2c_write_byte(int master_num, int bus, u16 addr, u8 reg, u8 data);

#endif // DRIVER_SOINCSUPPORTDRIVER_H

