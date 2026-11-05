#!/usr/bin/env python3
"""Export a RemotePairing credential locally; never print its contents or upload it.

Run with this project's .venv/bin/python after the personal StikDebug build is installed.
Uses the existing USB trust relationship. This does not require an Apple Account login.
"""

import argparse
import asyncio
import logging
import os
import plistlib
import traceback
from pathlib import Path

from pymobiledevice3.exceptions import RemotePairingCompletedError
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.remote.tunnel_service import RemotePairingLockdownService
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.usbmux import list_devices

BUNDLE_ID = "com.shreyanshsharma.stikdebug.personal"
PRIVATE_DIRECTORY = Path.home() / ".local" / "share" / "stikdebug-private"
RECORD_PATH = PRIVATE_DIRECTORY / "pairingFile.mobiledevicepairing"


class HexProofSession:
    """Adapt pymobiledevice3's hex-encoded bytes to srptools' explicit hex-string API.

    New srptools treats bytes as raw proof bytes. Verification is still performed by
    srptools with its timing-resistant comparison; a failed proof is never accepted.
    """

    def __init__(self, session):
        self.session = session

    def __getattr__(self, name):
        return getattr(self.session, name)

    def verify_proof(self, proof):
        if isinstance(proof, bytes) and isinstance(self.session.key_proof_hash, str):
            proof = proof.decode("ascii")
        return self.session.verify_proof(proof)


class LocalRemotePairing(RemotePairingLockdownService):
    @property
    def pair_record_path(self) -> Path:
        return RECORD_PATH

    def _init_srp_context(self, consent):
        super()._init_srp_context(consent)
        self.srp_context = HexProofSession(self.srp_context)


async def export(udid: str | None) -> None:
    devices = [device for device in await list_devices() if device.connection_type == "USB"]
    if udid:
        devices = [device for device in devices if device.serial == udid]
    if len(devices) != 1:
        raise RuntimeError("Connect exactly one trusted iPhone by USB, or specify --udid.")

    async with await create_using_usbmux(serial=devices[0].serial, autopair=False, connection_type="USB") as lockdown:
        async with InstallationProxyService(lockdown) as apps:
            installed = await apps.get_apps(bundle_identifiers=[BUNDLE_ID])
        if BUNDLE_ID not in installed:
            raise RuntimeError("Install the prepared StikDebug app with your Personal Team in Xcode first.")

        if PRIVATE_DIRECTORY.is_symlink() or RECORD_PATH.is_symlink():
            raise RuntimeError("Private credential paths must not be symbolic links.")
        PRIVATE_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
        PRIVATE_DIRECTORY.chmod(0o700)
        if RECORD_PATH.exists():
            RECORD_PATH.chmod(0o600)

        service = await LocalRemotePairing.create(lockdown)
        try:
            try:
                await service.connect(autopair=True)
            except RemotePairingCompletedError:
                # pymobiledevice3 saves the record before the phone closes the pairing channel.
                pass
        finally:
            await service.close()

    RECORD_PATH.chmod(0o600)
    with RECORD_PATH.open("rb") as file:
        record = plistlib.load(file)
    # idevice's RpPairingFile requires the host identifier used in pair setup.
    # pymobiledevice3 omits it from its older saved-record shape. Preserve it for
    # both libraries so a later Mac rename cannot silently change the identity.
    record["identifier"] = service.identifier
    record["host_identifier"] = service.identifier
    if not all(isinstance(record.get(key), bytes) and len(record[key]) == 32
               for key in ("public_key", "private_key")):
        raise RuntimeError("The generated record is not a supported RemotePairing credential.")
    with RECORD_PATH.open("wb") as file:
        plistlib.dump(record, file)
    RECORD_PATH.chmod(0o600)
    if RECORD_PATH.stat().st_mode & 0o777 != 0o600:
        raise RuntimeError("Credential permissions are not 600.")
    print(f"Pairing credential ready locally: {RECORD_PATH}")
    print("Permissions: 600. Contents were not printed. Transfer only to your iPhone over USB.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--udid", help="Choose one USB device if more than one is connected")
    args = parser.parse_args()
    os.umask(0o077)
    # Protocol debugging can contain credentials. Keep library logging disabled.
    logging.disable(logging.CRITICAL)
    try:
        asyncio.run(asyncio.wait_for(export(args.udid), timeout=60))
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    except Exception as error:
        for frame in traceback.extract_tb(error.__traceback__):
            print(f"Diagnostic: {Path(frame.filename).name}:{frame.lineno} in {frame.name}")
        raise SystemExit(f"Pairing export did not finish ({type(error).__name__}). No credential contents were printed.") from None


if __name__ == "__main__":
    main()
