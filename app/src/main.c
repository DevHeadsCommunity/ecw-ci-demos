/* SPDX-License-Identifier: MIT */
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

int main(void)
{
    unsigned int count = 0;
    while (1) {
        printk("Hello from FPB-RA6E2! #%u\n", ++count);
        k_msleep(1000);
    }
    return 0;
}
