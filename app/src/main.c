/* SPDX-License-Identifier: MIT */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/shell/shell.h>

static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);
static bool ready;
static volatile bool blinking;
static struct k_mutex led_mutex;

static int cmd_led(const struct shell *sh, size_t argc, char **argv)
{
    ARG_UNUSED(argc);
    if (!ready || (strcmp(argv[1], "on") && strcmp(argv[1], "off") && strcmp(argv[1], "blink"))) {
        shell_error(sh, "ECW_LED_ERROR not ready or invalid state");
        return -EINVAL;
    }
    k_mutex_lock(&led_mutex, K_FOREVER);
    blinking = !strcmp(argv[1], "blink");
    bool on = !strcmp(argv[1], "on") || blinking;
    int rc = gpio_pin_set_dt(&led, on);
    k_mutex_unlock(&led_mutex);
    if (rc) { return rc; }
    if (blinking) { shell_print(sh, "ECW_LED BLINK 50 %s", argv[2]); }
    else { shell_print(sh, "ECW_LED %s %s", on ? "ON" : "OFF", argv[2]); }
    return 0;
}

SHELL_CMD_ARG_REGISTER(led, NULL, "led on|off|blink nonce; blink toggles every 50 ms", cmd_led, 3, 0);

int main(void)
{
    k_mutex_init(&led_mutex);
    ready = gpio_is_ready_dt(&led) && gpio_pin_configure_dt(&led, GPIO_OUTPUT_INACTIVE) == 0;
    while (1) {
        k_msleep(50);
        k_mutex_lock(&led_mutex, K_FOREVER);
        if (blinking && ready) { gpio_pin_toggle_dt(&led); }
        k_mutex_unlock(&led_mutex);
    }
    return 0;
}
