#include <inttypes.h>

#include <zephyr/kernel.h>
#include <zephyr/shell/shell.h>
#include <zephyr/version.h>

static int cmd_ping(const struct shell *shell, size_t argc, char **argv)
{
	ARG_UNUSED(argc);
	shell_print(shell, "ECW_CI_PONG %s", argv[1]);
	return 0;
}

static int cmd_info(const struct shell *shell, size_t argc, char **argv)
{
	ARG_UNUSED(argc);
	ARG_UNUSED(argv);
	shell_print(shell, "ECW_CI_INFO fpb_ra6e2 Zephyr %s", KERNEL_VERSION_STRING);
	return 0;
}

static int cmd_uptime(const struct shell *shell, size_t argc, char **argv)
{
	ARG_UNUSED(argc);
	ARG_UNUSED(argv);
	shell_print(shell, "ECW_CI_UPTIME %" PRId64, k_uptime_get());
	return 0;
}

SHELL_STATIC_SUBCMD_SET_CREATE(ecw_ci_commands,
	SHELL_CMD_ARG(ping, NULL, "Echo a unique test nonce", cmd_ping, 2, 0),
	SHELL_CMD_ARG(info, NULL, "Identify the test image", cmd_info, 1, 0),
	SHELL_CMD_ARG(uptime, NULL, "Report kernel uptime in milliseconds", cmd_uptime, 1, 0),
	SHELL_SUBCMD_SET_END
);

SHELL_CMD_REGISTER(ecw_ci, &ecw_ci_commands, "ECW Twister CI testbench", NULL);

int main(void)
{
	return 0;
}
