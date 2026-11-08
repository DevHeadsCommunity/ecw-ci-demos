"""Run only through Twister and ECW's RM pytest plugin, on the booked RA6E2."""

import re
import time
import uuid


def command(dut, text, pattern):
    dut.write(("\r\n" + text + "\r\n").encode("ascii"))
    return dut.readlines_until(regex=pattern, timeout=10)[-1]


def test_fpb_ra6e2_serial_smoke(ecw_dut, ecw_job_metadata):
    # One test keeps the function-scoped ecw_dut lease and flashes only once.
    assert ecw_job_metadata["bench"] == "ci_twister_test"
    assert ecw_job_metadata["board_id"] == 23
    assert ecw_job_metadata["platform"] == "fpb_ra6e2"

    # Commands avoid relying on boot output emitted before RM claims the UART.
    command(ecw_dut, "ecw_ci info", r"^ECW_CI_INFO fpb_ra6e2 Zephyr \S+$")
    for _ in range(5):
        nonce = uuid.uuid4().hex
        command(ecw_dut, f"ecw_ci ping {nonce}", rf"^ECW_CI_PONG {nonce}$")

    before = command(ecw_dut, "ecw_ci uptime", r"^ECW_CI_UPTIME \d+$")
    time.sleep(0.1)
    after = command(ecw_dut, "ecw_ci uptime", r"^ECW_CI_UPTIME \d+$")
    assert int(re.fullmatch(r"ECW_CI_UPTIME (\d+)", after).group(1)) > int(
        re.fullmatch(r"ECW_CI_UPTIME (\d+)", before).group(1)
    )
