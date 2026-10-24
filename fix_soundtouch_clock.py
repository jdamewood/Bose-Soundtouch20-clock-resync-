import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


SPEAKER_IP = "192.168.1.208"
BASE_URL = f"http://{SPEAKER_IP}:8090"
TARGET_TIMEZONE = "America/Phoenix"
TIMEOUT = 10

OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({})
)


def api_request(endpoint, payload=None):
    method = "GET" if payload is None else "POST"
    url = BASE_URL + endpoint

    request = urllib.request.Request(
        url,
        data=payload,
        headers=(
            {"Content-Type": "application/xml"}
            if payload is not None
            else {}
        ),
        method=method,
    )

    print(f"\n>>> {method} {url}", flush=True)

    try:
        with OPENER.open(request, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8")
            print(f"<<< HTTP {response.status}", flush=True)
            return body

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"{method} {endpoint}: HTTP {exc.code}\n{body}"
        ) from exc

    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(
            f"{method} {endpoint} failed: {exc}"
        ) from exc


def show_clock():
    clock_xml = api_request("/clockTime")
    print("\n--- SPEAKER CLOCK ---")
    print(clock_xml)

    clock = ET.fromstring(clock_xml)
    utc_value = clock.get("utcTime")

    if utc_value is not None:
        speaker_epoch = int(utc_value)
        print(
            "\nSpeaker UTC:",
            datetime.fromtimestamp(
                speaker_epoch, timezone.utc
            ).isoformat(),
        )
        print(
            "Speaker minus computer:",
            f"{speaker_epoch - time.time():+.1f} seconds",
        )

    config_xml = api_request("/clockDisplay")
    print("\n--- CLOCK CONFIGURATION ---")
    print(config_xml)

    root = ET.fromstring(config_xml)
    config = root.find("clockConfig")

    if config is None:
        raise RuntimeError("No clockConfig element returned.")

    print("\nConfigured timezone:", config.get("timezoneInfo"))
    return root


def main():
    update_attempted = False

    try:
        print("SoundTouch:", BASE_URL)
        print(
            "Computer local time:",
            datetime.now().astimezone().isoformat(),
        )
        print(
            "Computer UTC:",
            datetime.now(timezone.utc).isoformat(),
        )

        root = show_clock()
        config = root.find("clockConfig")

        print("\n--- PROPOSED UPDATE ---")
        print(
            f"Timezone: {config.get('timezoneInfo')} "
            f"-> {TARGET_TIMEZONE}"
        )
        print("Time: synchronize with the computer's current UTC time")
        print("Manual clock setting: enabled")
        print("Manual offset: 0 minutes")
        print("Time format and brightness: preserved")
        print("\nVerify that the computer's date and time are correct.")

        answer = input(
            "\nApply the clock correction? Type yes: "
        ).strip().lower()

        if answer != "yes":
            print("Cancelled. No changes made.")
            return 0

        config.set("timezoneInfo", TARGET_TIMEZONE)
        config.set("userEnable", "true")
        config.set("userOffsetMinute", "0")
        config.set("userUtcTime", str(int(time.time())))

        payload = ET.tostring(root, encoding="utf-8")

        print("\n--- SENDING CLOCK UPDATE ---")
        print(payload.decode("utf-8"))

        update_attempted = True
        response = api_request("/clockDisplay", payload)

        print("\n--- UPDATE RESPONSE ---")
        print(response)

        time.sleep(1)

        print("\n--- READ-BACK VERIFICATION ---")
        show_clock()

        print("\nCompare the speaker display with your computer's time.")
        return 0

    except (
        RuntimeError,
        ET.ParseError,
        ValueError,
        OverflowError,
        OSError,
    ) as exc:
        print(f"\nERROR: {exc}")

        if update_attempted:
            print(
                "An update request was attempted, but the final "
                "clock state has not been verified."
            )
        else:
            print("No clock-update request was sent.")

        return 1

    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
        if update_attempted:
            print("An update was attempted; verify the speaker clock.")
        else:
            print("No clock-update request was sent.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())