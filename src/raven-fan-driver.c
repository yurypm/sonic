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

#include <linux/module.h>
#include <linux/hwmon.h>
#include <linux/hwmon-sysfs.h>
#include <linux/platform_device.h>

#define SB800_BASE 0xfed80000
#define SB800_PM2_BASE (SB800_BASE + 0x0400)
#define SB800_PM2_SIZE 0xff
#define SB800_IOSIZE 4
#define NUM_FANS 4
#define DRIVER_NAME "sb800-fans"

#define FAN_DEVICE_ATTR(_name)                                                      \
static ssize_t show_fan##_name##_input(struct device *dev,                          \
                                       struct device_attribute *attr, char *buf)    \
{                                                                                   \
    u32 tach = 0;                                                                   \
    u32 tach_lo;                                                                    \
    u32 tach_lo_1;                                                                  \
    u32 tach_hi;                                                                    \
    u32 tach_hi_1;                                                                  \
    u32 fan_id = (_name) - 1;                                                       \
    unsigned int *tach_lo_reg = ioremap(SB800_PM2_BASE + 0x66 + (fan_id * 0x05) + 3,\
                                        SB800_IOSIZE);                              \
    unsigned int *tach_hi_reg = ioremap(SB800_PM2_BASE + 0x66 + (fan_id * 0x05) + 4,\
                                        SB800_IOSIZE);                              \
    tach_lo = ioread8(tach_lo_reg);                                                 \
    tach_hi = ioread8(tach_hi_reg);                                                 \
    tach_lo_1 = ioread8(tach_lo_reg);                                               \
    tach_hi_1 = ioread8(tach_hi_reg);                                               \
    if (tach_lo_1 == tach_lo) {                                                     \
        tach = (tach_hi << 8) + tach_lo;                                            \
    } else {                                                                        \
        tach = (tach_hi_1 << 8) + tach_lo_1;                                        \
    }                                                                               \
    tach = (22700 * 60) / ((tach ?: 1) * 2);                                        \
    return scnprintf(buf, 12, "%u\n", tach);                                        \
}                                                                                   \
static ssize_t show_pwm##_name(struct device *dev, struct device_attribute *attr,   \
                               char *buf)                                           \
{                                                                                   \
    u32 fan_id = (_name) - 1;                                                       \
    u32 *reg = ioremap(SB800_PM2_BASE + (fan_id * 0x10) + 3, SB800_IOSIZE);         \
    u32 pwm = ioread8(reg);                                                         \
    return scnprintf(buf, 5, "%u\n", pwm);                                          \
}                                                                                   \
static ssize_t store_pwm##_name(struct device *dev, struct device_attribute *attr,  \
                                const char *buf, size_t count)                      \
{                                                                                   \
    u32 fan_id = (_name) - 1;                                                       \
    u32 *reg = ioremap(SB800_PM2_BASE + (fan_id * 0x10) + 3, SB800_IOSIZE);         \
    unsigned long pwm;                                                              \
    if (kstrtoul(buf, 10, &pwm)) {                                                  \
        return 0;                                                                   \
    }                                                                               \
    iowrite8(pwm & 0xff, reg);                                                      \
    return count;                                                                   \
}                                                                                   \
static SENSOR_DEVICE_ATTR(fan##_name##_input, S_IRUGO,                              \
                          show_fan##_name##_input, NULL, 0);                        \
static SENSOR_DEVICE_ATTR(pwm##_name, S_IRUGO|S_IWUSR|S_IWGRP,                      \
                          show_pwm##_name, store_pwm##_name, 0);

FAN_DEVICE_ATTR(1);
FAN_DEVICE_ATTR(2);
FAN_DEVICE_ATTR(3);
FAN_DEVICE_ATTR(4);

static struct attribute *fan_attrs[] = {
    &sensor_dev_attr_fan1_input.dev_attr.attr,
    &sensor_dev_attr_pwm1.dev_attr.attr,
    &sensor_dev_attr_fan2_input.dev_attr.attr,
    &sensor_dev_attr_pwm2.dev_attr.attr,
    &sensor_dev_attr_fan3_input.dev_attr.attr,
    &sensor_dev_attr_pwm3.dev_attr.attr,
    &sensor_dev_attr_fan4_input.dev_attr.attr,
    &sensor_dev_attr_pwm4.dev_attr.attr,
    NULL,
};

ATTRIBUTE_GROUPS(fan);

static s32 sb_fan_probe_init(struct platform_device *pdev)
{
    int i;
    u32 num_fans = NUM_FANS;
    unsigned int *reg;

    if (num_fans == 0) {
        return 0;
    }
    if (!request_mem_region(SB800_PM2_BASE, SB800_PM2_SIZE, "SB800_PM2")) {
        dev_err(&pdev->dev, "failed request_mem_region in SB fan initialization\n");
        return -EBUSY;
    }
    for (i = 0; i < num_fans; i++) {
        reg = ioremap(SB800_PM2_BASE + (0x10 * i), SB800_IOSIZE);
        iowrite8(0x06, reg); /* FanInputControl */
        reg = ioremap(SB800_PM2_BASE + (0x10 * i) + 1, SB800_IOSIZE);
        iowrite8(0x04, reg); /* FanControl */
        reg = ioremap(SB800_PM2_BASE + (0x10 * i) + 2, SB800_IOSIZE);
        iowrite8(0x01, reg); /* FanFreq */
        reg = ioremap(SB800_PM2_BASE + (0x10 * i) + 3, SB800_IOSIZE);
        iowrite8(0xff, reg); /* LowDuty */
        reg = ioremap(SB800_PM2_BASE + 0x66 + (0x05 * i), SB800_IOSIZE);
        iowrite8(0x01, reg); /* FanDetectorControl */
    }
    return 0;
}

static int sb_fan_remove(struct platform_device *pdev)
{
    int err = 0;
    struct device *hwmon_dev = platform_get_drvdata(pdev);

    release_mem_region(SB800_PM2_BASE, SB800_PM2_SIZE);

    hwmon_device_unregister(hwmon_dev);

    return err;
}

static int sb_fan_probe(struct platform_device *pdev)
{
    int err = 0;
    struct device *dev = &pdev->dev;
    struct device *hwmon_dev;

    dev_dbg(dev, "initializing raven fan driver\n");
    err = sb_fan_probe_init(pdev);
    if (err) {
        dev_err(dev, "failed to initialize fans\n");
        return err;
    }

    hwmon_dev = hwmon_device_register_with_groups(dev, "fans", NULL, fan_groups);
    if (IS_ERR(hwmon_dev)) {
       dev_err(dev, "failed to create hwmon sysfs entries\n");
       sb_fan_remove(pdev);
       return PTR_ERR(hwmon_dev);
    }

    platform_set_drvdata(pdev, hwmon_dev);

    return err;
}

static struct platform_device *sb800_pdev = 0;

static int __init sb_fan_init(void)
{
    int err;
    struct platform_device *pdev;

    pdev = platform_device_register_simple(DRIVER_NAME, -1, NULL, 0);
    if (IS_ERR(pdev)) {
        printk(KERN_ERR "failed to register " DRIVER_NAME);
        return PTR_ERR(pdev);
    }

    err = sb_fan_probe(pdev);
    if (err) {
        dev_err(&pdev->dev, "failed to init device ");
        platform_device_unregister(pdev);
        return err;
    }

    sb800_pdev = pdev;

    return err;
}

static void __exit sb_fan_exit(void)
{
    if (!sb800_pdev) {
        return;
    }

    sb_fan_remove(sb800_pdev);
    platform_device_unregister(sb800_pdev);

    sb800_pdev = 0;
}

module_init(sb_fan_init);
module_exit(sb_fan_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Arista Networks");
MODULE_DESCRIPTION("Raven Fan Driver");
