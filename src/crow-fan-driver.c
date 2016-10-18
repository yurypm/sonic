/* Copyright (c) 2016 Arista Networks, Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <linux/kernel.h>
#include <linux/printk.h>
#include <linux/sysfs.h>
#include <linux/kobject.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/version.h>
#include <linux/device.h>
#include <linux/hwmon.h>
#include "sonic-support-driver.h"

#define CPLDBUS 3
#define CPLDADDR 0x60

#define TACH1LOWREG 0
#define TACH1HIGHREG 1
#define TACH2LOWREG 2
#define TACH2HIGHREG 3
#define TACH3LOWREG 4
#define TACH3HIGHREG 5
#define TACH4LOWREG 6
#define TACH4HIGHREG 7

#define FAN1PWMREG 0x10
#define FAN1IDREG 0x18
#define FAN2PWMREG 0x11
#define FAN2IDREG 0x19
#define FAN3PWMREG 0x12
#define FAN3IDREG 0x1A
#define FAN4PWMREG 0x13
#define FAN4IDREG 0x1B

#define FANPRESENTREG 0x21
#define FANGREENLEDREG 0x24
#define FANREDLEDREG 0x25
#define CROWCPLDREVREG 0x40
#define SCRATCHREG 0x41

static struct kobject *fan_kobject;

/*
 * This function reads a byte from the crow cpld
 */
static s32 read_cpld(u8 reg, u8 *result)
{
    s32 status = 0;
    int master = 0;
    int bus = 1;
    u16 addr = CPLDADDR;

    status = i2c_read_byte(master, bus, addr, reg, result);

    return status;
}

/*
 * This function write a byte to the crow cpld
 */
static s32 write_cpld(u8 reg, u8 data)
{
    s32 status = 0;
    int master = 0;
    int bus = 1;
    u16 addr = CPLDADDR;

    status = i2c_write_byte(master, bus, addr, reg, data);

    return status;
}

static s32 read_cpld_to_buffer(u8 reg, char *buf)
{
    s32 status;
    u8 data;
    status = read_cpld(reg, &data);
    if (status) {
        return status;
    }
    return sprintf(buf, "%02x\n", data);

}

static s32 write_buffer_to_cpld(u8 reg, const char *buf)
{
    u8 data;
    s32 status;
    sscanf(buf, "%hhu", &data);
    status = write_cpld(reg, data);
    return status;
}

static s32 read_led_color(u8 reg_green, u8 reg_red, char *buf, int index)
{
    s32 status;
    u8 data;
    int fanIndex = index - 1;
    char read_value= 0;

    status = read_cpld(reg_green, &data);
    if (status) {
        return status;
    }
    read_value = (data >> fanIndex) & 0x01;

    status = read_cpld(reg_red, &data);
    if (status) {
        return status;
    }
    read_value = ((data >> fanIndex) & 0x01) << 1;

    switch (read_value) {
    case 0:
        status = sprintf(buf, "0\n");
        break;
    case 1:
        status = sprintf(buf, "1\n");
        break;
    case 2:
        status = sprintf(buf, "2\n");
        break;
    case 3:
    default:
        status = sprintf(buf, "3\n");
        break;
    }

    return status;
}

static s32 write_led_color(u8 reg_green, u8 reg_red, const char *buf, int index)
{
    s32 status;
    u8 data;
    u8 red_value;
    u8 green_value;
    int fanIndex = index - 1;
    u8 green_led;
    u8 red_led;

    sscanf(buf, "%hhu", &data);

    switch (data) {
    case 1:
        green_led = 1;
        red_led = 0;
        break;
    case 2:
        green_led = 0;
        red_led = 1;
        break;
    case 3:
        green_led = 1;
        red_led = 1;
        break;
    case 0:
    default:
        green_led = 0;
        red_led = 0;
        break;
    }

    status = read_cpld(reg_green, &green_value);
    if (status) {
        return status;
    }
    status = read_cpld(reg_red, &red_value);
    if (status) {
        return status;
    }

    if (green_led) {
        green_value |= (1u << fanIndex);
    } else {
        green_value &= ~(1u << fanIndex);
    }

    if (red_led) {
        red_value |= (1u << fanIndex);
    } else {
        red_value &= ~(1u << fanIndex);
    }

    status = write_cpld(reg_green, green_value);
    status |= write_cpld(reg_red, red_value);

    return status;
}

static s32 read_tach(u8 tachHigh, u8 tachLow, char *buf)
{
    s32 status;
    u8 dataHigh;
    u8 dataLow;
    u32 tachData;
    u32 speed;

    status = read_cpld(tachHigh, &dataHigh);
    status |= read_cpld(tachLow, &dataLow);
    if (status) {
        return status;
    }
    tachData = (dataHigh << 8) + dataLow;
    if (!tachData) {
        tachData = 1;
    }
    speed = 6000000 / tachData;
    speed = speed / 2;
    return sprintf(buf, "%02x\n", speed);
}

static s32 read_fan_present(u8 reg, char *buf, int index)
{
    s32 status;
    u8 data;
    int fanIndex = index - 1;
    char present = 0;

    status = read_cpld(reg, &data);
    if (status) {
        return status;
    }
    present = ~(data >> fanIndex) & 0x01;
    return sprintf(buf, "%d\n", present);
}

#define GENERIC_FAN_READ(_name, _dev, _reg)                                         \
static ssize_t fan_##_name##_##_dev##_show(struct device *dev,                      \
                                           struct device_attribute *attr,           \
                                           char *buf)                               \
{                                                                                   \
    return read_cpld_to_buffer(_reg, buf);                                          \
}                                                                                   \

#define GENERIC_FAN_WRITE(_name, _dev, _reg)                                        \
static ssize_t fan_##_name##_##_dev##_store(struct device *dev,                     \
                                            struct device_attribute *attr,          \
                                            const char *buf, size_t count)          \
{                                                                                   \
    write_buffer_to_cpld(_reg, buf);                                                \
    return count;                                                                   \
}                                                                                   \

#define GENERIC_LED(_name, _reg_green, _reg_red)                                    \
static ssize_t fan_##_name##_led_show(struct device *dev,                           \
                                      struct device_attribute *attr, char *buf)     \
{                                                                                   \
    return read_led_color(_reg_green, _reg_red, buf, _name);                        \
}                                                                                   \
static ssize_t fan_##_name##_led_store(struct device *dev,                          \
                                       struct device_attribute *attr,               \
                                       const char *buf, size_t count)               \
{                                                                                   \
    write_led_color(_reg_green, _reg_red, buf, _name);                              \
    return count;                                                                   \
}                                                                                   \
DEVICE_ATTR(fan##_name##_led, S_IRUGO|S_IWGRP|S_IWUSR,                              \
            fan_##_name##_led_show, fan_##_name##_led_store);                       \


#define FAN_DEVICE_ATTR(_name)                                                      \
static ssize_t tach_##_name##_show(struct device *dev,                              \
                                   struct device_attribute *attr, char *buf)        \
{                                                                                   \
    return read_tach(TACH##_name##HIGHREG, TACH##_name##LOWREG, buf);               \
}                                                                                   \
DEVICE_ATTR(fan##_name##_input, S_IRUGO, tach_##_name##_show, NULL);                \
                                                                                    \
GENERIC_FAN_READ(_name, ID, FAN##_name##IDREG);                                     \
DEVICE_ATTR(fan##_name##_ID, S_IRUGO, fan_##_name##_ID_show, NULL);                 \
                                                                                    \
GENERIC_FAN_READ(_name, pwm, FAN##_name##PWMREG);                                   \
GENERIC_FAN_WRITE(_name, pwm, FAN##_name##PWMREG);                                  \
DEVICE_ATTR(pwm##_name, S_IRUGO|S_IWGRP|S_IWUSR,                                    \
            fan_##_name##_pwm_show, fan_##_name##_pwm_store);                       \
                                                                                    \
static ssize_t fan_##_name##_present_show(struct device *dev,                       \
                                          struct device_attribute *attr, char *buf) \
{                                                                                   \
    return read_fan_present(FANPRESENTREG, buf, _name);                             \
}                                                                                   \
DEVICE_ATTR(fan##_name##_present, S_IRUGO, fan_##_name##_present_show, NULL);       \
                                                                                    \
GENERIC_LED(_name, FANGREENLEDREG, FANREDLEDREG)                                    \


static ssize_t crow_cpld_rev_show(struct device *dev,
                                  struct device_attribute *attr, char *buf)
{
    return read_cpld_to_buffer(CROWCPLDREVREG, buf);
}

DEVICE_ATTR(crow_cpld_rev, S_IRUGO, crow_cpld_rev_show, NULL);

FAN_DEVICE_ATTR(1);
FAN_DEVICE_ATTR(2);
FAN_DEVICE_ATTR(3);
FAN_DEVICE_ATTR(4);

#define FANATTR(_name)                   \
    &dev_attr_pwm##_name.attr,           \
    &dev_attr_fan##_name##_ID.attr,      \
    &dev_attr_fan##_name##_input.attr,   \
    &dev_attr_fan##_name##_present.attr, \
    &dev_attr_fan##_name##_led.attr,     \


static struct attribute *fan_attrs[] = {
    FANATTR(1)
    FANATTR(2)
    FANATTR(3)
    FANATTR(4)
    &dev_attr_crow_cpld_rev.attr,
    NULL,
};


static struct attribute_group fan_attr_group = {
    .attrs = fan_attrs,
};

static int __init fan_init(void)
{
    int error = 0;
    DPRINT("Module Crow Fan Driver init\n");

    fan_kobject = kobject_create_and_add("fan_driver", kernel_kobj);
    if (!fan_kobject) {
        return -ENOMEM;

    }

    error = sysfs_create_group(fan_kobject, &fan_attr_group);
    if (error) {
        DPRINT("Failed to create the fan file in /sys/kernel\n");
        kobject_put(fan_kobject);
    }

    return error;
}

static void __exit fan_exit(void)
{
    DPRINT("Module Crow Fan Driver removed");
    sysfs_remove_group(fan_kobject, &fan_attr_group);
    kobject_put(fan_kobject);
}

module_init(fan_init);
module_exit(fan_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Arista Networks");
MODULE_DESCRIPTION("Crow Fan driver");
