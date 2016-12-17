// Copyright (c) 2016 Arista Networks, Inc.  All rights reserved.
// Arista Networks, Inc. Confidential and Proprietary.

#include <linux/gpio.h>
#include <linux/version.h>
#include "sonic-support-driver.h"

/*
 * The following snippet of code is a workaround to support kernel prior to 3.18
 * These previous kernel doesn't benefit of the gpio subsystem refactor that exports
 * more functions.
 */
#if LINUX_VERSION_CODE < KERNEL_VERSION(3, 18, 0)
#include <linux/gpio/driver.h>
#include <linux/gpio/consumer.h>

#define gpiochip_free_own_desc gpiochip_free_desc_hack
void gpiochip_free_desc_hack(struct gpio_desc *desc)
{
   // this call decrease the refcount of the module which means that it is an issue
   // if called outside of the module_exit
   gpio_free(desc_to_gpio(desc));
   try_module_get(THIS_MODULE);
}

#define gpiochip_request_own_desc gpiochip_request_desc_hack
struct gpio_desc *gpiochip_request_desc_hack(struct gpio_chip *chip,
                                                    u16 hwnum, const char *label)
{
    struct gpio_desc *desc = gpiochip_get_desc(chip, hwnum);
    int err;

    if (IS_ERR(desc)) {
        sonic_err("failed to get GPIO descriptor\n");
        return desc;
    }

    err = gpio_request(desc_to_gpio(desc), label);
    if (err < 0) {
        sonic_err("failed to request GPIO");
        return ERR_PTR(err);
    }

    // gpio_request increase the refcount on the module
    // Since the module asking for its own gpio, the refcount shouldn't be
    // increased. Given that this is the only exported symbol available this is the
    // is the easiest way to handle this without adding a kernel patch
    module_put(chip->owner);

    return desc;
}
#endif
