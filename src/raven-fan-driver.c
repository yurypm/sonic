/* Copyright (c) 2016 Arista Networks, Inc.  All rights reserved.
 * Arista Networks, Inc. Confidential and Proprietary.
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

static struct kobject *fan_kobject;
unsigned long num_sb_fans;

#define SB800_BASE 0xfed80000
#define SB800_PM2_BASE (SB800_BASE + 0x0400)
#define SB800_PM2_SIZE 0xff
#define SB800_IOSIZE 4
#define NUM_FANS 4

#define SONICDBG 1

#ifdef SONICDBG
#define DPRINT(_text) printk(KERN_DEBUG _text);
#else
#define DPRINT(_text) do {} while (0);
#endif

static ssize_t show_fan_num(struct device *dev, struct device_attribute *attr,
char *buf)
{
   int count = 0;
   count = sprintf(buf, "%lu\n", num_sb_fans);
   return count;
}
static ssize_t store_fan_num(struct device *dev, struct device_attribute *attr,
const char *buf, size_t count)
{
   unsigned long new_value = simple_strtoul(buf, NULL, 10);
   num_sb_fans = new_value;
   return count;
}
static DEVICE_ATTR(sb_fans, S_IRUGO|S_IWUSR|S_IWGRP, show_fan_num, store_fan_num);

#define FAN_DEVICE_ATTR(_name)                                                      \
static ssize_t show_fan##_name##_input(struct device *dev,                          \
struct device_attribute *attr, char *buf)                                           \
{                                                                                   \
   u32 tach = 0;                                                                    \
   u32 tach_lo;                                                                     \
   u32 tach_lo_1;                                                                   \
   u32 tach_hi;                                                                     \
   u32 tach_hi_1;                                                                   \
   u32 fan_id = (_name) - 1;                                                        \
   unsigned int *tach_lo_reg = ioremap(SB800_PM2_BASE + 0x66 + (fan_id * 0x05) + 3, \
                                       SB800_IOSIZE);                               \
   unsigned int *tach_hi_reg = ioremap(SB800_PM2_BASE + 0x66 + (fan_id * 0x05) + 4, \
                                       SB800_IOSIZE);                               \
   tach_lo = ioread8(tach_lo_reg);                                                  \
   tach_hi = ioread8(tach_hi_reg);                                                  \
   tach_lo_1 = ioread8(tach_lo_reg);                                                \
   tach_hi_1 = ioread8(tach_hi_reg);                                                \
   if (tach_lo_1 == tach_lo) {                                                      \
      tach = (tach_hi << 8) + tach_lo;                                              \
   } else {                                                                         \
      tach = (tach_hi_1 << 8) + tach_lo_1;                                          \
   }                                                                                \
   tach = (22700 * 60) / ((tach ?: 1) * 2);                                         \
   return scnprintf(buf, 12, "%u\n", tach);                                         \
}                                                                                   \
static ssize_t show_pwm##_name(struct device *dev, struct device_attribute *attr,   \
char *buf)                                                                          \
{                                                                                   \
   u32 fan_id = (_name) - 1;                                                        \
   u32 *reg = ioremap(SB800_PM2_BASE + (fan_id * 0x10) + 3, SB800_IOSIZE);          \
   u32 pwm = ioread8(reg);                                                          \
   return scnprintf(buf, 5, "%u\n", pwm);                                           \
}                                                                                   \
static ssize_t store_pwm##_name(struct device *dev, struct device_attribute *attr,  \
const char *buf, size_t count)                                                      \
{                                                                                   \
   u32 fan_id = (_name) - 1;                                                        \
   u32 *reg = ioremap(SB800_PM2_BASE + (fan_id * 0x10) + 3, SB800_IOSIZE);          \
   unsigned long pwm;                                                               \
   if (kstrtoul(buf, 10, &pwm)) {                                                   \
      return 0;                                                                     \
   }                                                                                \
   iowrite8(pwm & 0xff, reg);                                                       \
   return count;                                                                    \
}                                                                                   \
static DEVICE_ATTR(fan##_name##_input, S_IRUGO, show_fan##_name##_input, NULL);     \
static DEVICE_ATTR(pwm##_name, S_IRUGO|S_IWUSR|S_IWGRP, show_pwm##_name,            \
                   store_pwm##_name);

FAN_DEVICE_ATTR(1);
FAN_DEVICE_ATTR(2);
FAN_DEVICE_ATTR(3);
FAN_DEVICE_ATTR(4);

static struct attribute *fan_attrs[] = {
      &dev_attr_fan1_input.attr,
      &dev_attr_pwm1.attr,
      &dev_attr_fan2_input.attr,
      &dev_attr_pwm2.attr,
      &dev_attr_fan3_input.attr,
      &dev_attr_pwm3.attr,
      &dev_attr_fan4_input.attr,
      &dev_attr_pwm4.attr,
      &dev_attr_sb_fans.attr,
      NULL,
};

static struct attribute_group fan_attr_group = {
         .attrs = fan_attrs,
};

static void sb_fan_remove(void)
{
   release_mem_region(SB800_PM2_BASE, SB800_PM2_SIZE);
}

static s32 __init sb_fan_init(void)
{
   int i;
   u32 num_fans = NUM_FANS;
   unsigned int *reg;
   if (num_fans == 0) {
      return 0;
   }
   if (!request_mem_region(SB800_PM2_BASE, SB800_PM2_SIZE, "SB800_PM2")) {
      printk(KERN_ERR "Failed request_mem_region in SB fan initialization");
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
   num_sb_fans = NUM_FANS;
   return 0;
}

static int __init fan_init(void)
{
   int err = 0;
   DPRINT("Module Raven Fan Driver init\n");

   err = sb_fan_init();
   if (err) {
      return 1;
   }

   fan_kobject = kobject_create_and_add("fan_driver", kernel_kobj);

   if (!fan_kobject) {
      return -ENOMEM;
   }

   err = sysfs_create_group(fan_kobject, &fan_attr_group);

   if (err) {
      DPRINT("Failed to create the fan file in /sys/kernel\n");
   }

   return err;
}

static void __exit fan_exit(void)
{
      DPRINT("Module Raven Fan Driver removed\n");
      sysfs_remove_group(fan_kobject, &fan_attr_group);
      kobject_put(fan_kobject);
      sb_fan_remove();
}

module_init(fan_init);
module_exit(fan_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Arista Networks");
MODULE_DESCRIPTION("Raven Fan Driver");
