# ECW CI demos

Examples of GitHub Actions workflows that build firmware, program a booked board, run hardware tests through ECW, and publish the results.

Choose a demo branch below. Each demo runs manually from GitHub Actions and includes its firmware, client scripts, documentation and flow diagram.

## Choose a demo

| Demo branch | What it does | Evidence |
| --- | --- | --- |
| [demo/ra6-blinky-camera](https://github.com/DevHeadsCommunity/ecw-ci-demos/tree/demo/ra6-blinky-camera) | Toggle the LED every **50 ms** and save screenshots every **30 ms** during a **2-second** window. | 67 JPEG files, an HTML gallery, actual capture timestamps and source frame counts. |
| [demo/ra6-hello-serial](https://github.com/DevHeadsCommunity/ecw-ci-demos/tree/demo/ra6-hello-serial) | Capture **5 seconds** of serial output and check consecutive numbered greetings. | Serial log, CI job results and verification report. |
| [demo/ra6-hil-50-samples](https://github.com/DevHeadsCommunity/ecw-ci-demos/tree/demo/ra6-hil-50-samples) | Configure BME280 HIL using **50 frontend-format CSV samples**, then compare the board's SPI readings with those values. | Configuration report, 150 verified encoded words and 50 DUT readings. |
| [demo/ra6-zephyr-twister](https://github.com/DevHeadsCommunity/ecw-ci-demos/tree/demo/ra6-zephyr-twister) | Run the trusted Zephyr Twister suite: firmware identification, five nonce echoes and increasing uptime. | Job metadata, Twister JSON, JUnit XML and diagnostic logs. |

The branch names identify the current hardware target. Check the selected branch's README for its board identity and wiring before running it.

## Run a demo manually

1. Open **Settings → Secrets and variables → Actions** and add the repository secret **`ECW_API_KEY`** for your ECW account.
2. Open **Actions → ECW CI Job Smoke → Run workflow**. Select a demo branch from the table, rather than `main`. The workflow file is `.github/workflows/ci-job-smoke.yml`; its name on the demo branches is **RA6 manual demo**.
3. Leave **`booking_id`** blank to create a CI booking, or enter your active booking for the configured board. A supplied booking must have more than six minutes remaining. Close other terminals using its serial console.
4. Start the workflow, then download its artifact. The blinky artifact includes `artifacts/camera.html` for browsing the screenshots locally.

Demo branches use **`workflow_dispatch` only**: pushing a commit or opening a pull request does not start a hardware test. They share one hardware concurrency group; run them one at a time.

| Repository setting | Type | Purpose |
| --- | --- | --- |
| `ECW_API_KEY` | Required secret | Authenticate as the booking owner. |
| `ECW_BACKEND_URL` | Optional variable | Override the default API base, `https://plovdiv.edgebench.io/api`. |
| `ECW_CONSOLE_URL` | Optional variable | Override the default console base, `wss://plovdiv.edgebench.io`. |

The demos set their board configuration themselves. No `BOARD_NAME`, `HIL_SENSOR_NAME` or `HIL_CSV_FILE` variable is required. The HIL branch includes its 50-row CSV under `.github/user/hil/`.

## Execution lifecycle

```text
Manual run → Build and offline checks → Active booking → Demo execution → Evidence → Cleanup
```

For the blinky, hello and CSV HIL demos, firmware upload and programming are separate operations:

1. **Upload:** `/upload` stores the built HEX on NFS; the client verifies the stored filename.
2. **Flash:** a separate request to `/v1/artifacts/my-uploads` programs that exact stored file.
3. **Test:** start only after programming succeeds. The CSV HIL demo completes sensor preparation and value configuration before uploading or flashing the MCU firmware.

The Twister demo submits the trusted `ci_twister_test` backend profile. Twister and its pytest/RM integration own the runtime build, flash and serial access. The GitHub build is a build-only check; the client does not request an additional hardware flash. The selected backend must already have that reviewed profile installed.

Cleanup closes the connections and releases bookings created by the workflow. Caller-supplied bookings are preserved. Available evidence is published after failures as well as successful runs.

## Read the results

A 30 ms screenshot save interval does not guarantee a new camera exposure every 30 ms. Slower camera delivery can repeat a source frame across several saved JPEGs. The blinky report records source frame numbers, ages and actual timestamps; inspect the gallery to confirm the LED is visible and blinking. Optical ON/OFF classification is manual.

All four firmware applications have been compiled, and each branch passes 49 offline client checks. Twister build-only discovery also passes. These checks do not establish a passing physical-board run; use the manual workflows to collect that evidence.

## Template and documentation

`main` retains the original template files and history and serves as the demo index. Its inherited workflow is separate from the manual demo workflows. Use a **demo branch** for these examples.

The general-purpose source template is [ECW CI GitHub Actions Templates](https://github.com/DevHeadsCommunity/ECW_CI_Github_Actions_Templates). The demos adapt the Zephyr application structure from [nxp-zephyr-projects](https://github.com/DevHeadsCommunity/nxp-zephyr-projects) and hardware examples from ECW_Lab.

Each demo branch has a focused README and SVG:

- [Blinky lifecycle and timing](https://github.com/DevHeadsCommunity/ecw-ci-demos/blob/demo/ra6-blinky-camera/docs/flow.svg)
- [Hello serial flow](https://github.com/DevHeadsCommunity/ecw-ci-demos/blob/demo/ra6-hello-serial/docs/flow.svg)
- [CSV HIL flow](https://github.com/DevHeadsCommunity/ecw-ci-demos/blob/demo/ra6-hil-50-samples/docs/flow.svg)
- [Twister flow](https://github.com/DevHeadsCommunity/ecw-ci-demos/blob/demo/ra6-zephyr-twister/docs/flow.svg)

The inherited template guides remain under [docs/](docs/).
