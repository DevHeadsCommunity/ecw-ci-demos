/* SPDX-License-Identifier: MIT */
/* BME280 HIL SPI transport adapted from ECW_Lab's RA6 demo. */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/shell/shell.h>

static int init_rc;
static const struct spi_dt_spec bus = SPI_DT_SPEC_GET(DT_NODELABEL(ecw_sensor),
    SPI_OP_MODE_MASTER | SPI_WORD_SET(8) | SPI_TRANSFER_MSB | SPI_MODE_CPOL | SPI_MODE_CPHA, 2);

static int read_regs(uint8_t reg, uint8_t *data, size_t length)
{
    uint8_t tx[9] = {reg | 0x80}, rx[9] = {0};
    if (!spi_is_ready_dt(&bus) || length > 8) { return -ENODEV; }
    const struct spi_buf tb = {.buf = tx, .len = length + 1};
    const struct spi_buf rb = {.buf = rx, .len = length + 1};
    const struct spi_buf_set ts = {.buffers = &tb, .count = 1};
    const struct spi_buf_set rs = {.buffers = &rb, .count = 1};
    int rc = spi_transceive_dt(&bus, &ts, &rs);
    if (!rc) { memcpy(data, rx + 1, length); }
    return rc;
}

static int cmd_info(const struct shell *sh, size_t argc, char **argv)
{
    ARG_UNUSED(argc);
    if (init_rc) { return init_rc; }
    uint8_t id = 0;
    int rc = read_regs(0xD0, &id, 1);
    if (rc) { shell_error(sh, "ECW_HIL_ERROR SPI %d", rc); return rc; }
    shell_print(sh, "ECW_HIL_ID %02X %s", (unsigned)id, argv[1]);
    return 0;
}

static int cmd_read(const struct shell *sh, size_t argc, char **argv)
{
    ARG_UNUSED(argc);
    uint8_t d[8];
    int rc = read_regs(0xF7, d, sizeof(d));
    if (rc) { shell_error(sh, "ECW_HIL_ERROR SPI %d", rc); return rc; }
    unsigned int p = ((unsigned)d[0] << 8) | d[1];
    unsigned int t = ((unsigned)d[3] << 8) | d[4];
    unsigned int h = ((unsigned)d[6] << 8) | d[7];
    shell_print(sh, "ECW_HIL_SAMPLE %04X %04X %04X %s", t, h, p, argv[1]);
    return 0;
}

SHELL_STATIC_SUBCMD_SET_CREATE(hil_commands,
    SHELL_CMD_ARG(info, NULL, "Read BME280 chip ID", cmd_info, 2, 0),
    SHELL_CMD_ARG(read, NULL, "Read one T/H/P sample over SPI", cmd_read, 2, 0),
    SHELL_SUBCMD_SET_END);
SHELL_CMD_REGISTER(hil, &hil_commands, "RA6 BME280 HIL test", NULL);

static int write_reg(uint8_t reg, uint8_t value)
{
    uint8_t tx[2] = {reg & 0x7F, value};
    const struct spi_buf buffer = {.buf = tx, .len = sizeof(tx)};
    const struct spi_buf_set data = {.buffers = &buffer, .count = 1};
    return spi_write_dt(&bus, &data);
}

int main(void)
{
    if (!spi_is_ready_dt(&bus)) { init_rc = -ENODEV; return init_rc; }
    init_rc = write_reg(0xE0, 0xB6);
    k_msleep(50);
    if (!init_rc) { init_rc = write_reg(0xF2, 0x01); }
    if (!init_rc) { init_rc = write_reg(0xF5, 0xA0); }
    if (!init_rc) { init_rc = write_reg(0xF4, 0x57); }
    return init_rc;
}
