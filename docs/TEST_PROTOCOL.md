# Repeating the physical test

Use only your own phone and Apple Maps. Record observations without publishing
your real coordinates or any device credentials.

1. Establish a trusted installation, valid free signing and connected LocalDevVPN.
2. Request Apple Park at **37.3349, -122.0090** and explicitly tap Set Location.
3. Confirm the two session-readiness messages. Resolve blocked/inactive status
   before starting a persistence test.
4. In Maps, tap the current-location arrow. Confirm the blue dot at Apple Park;
   a selected place pin is not evidence of the current location.
5. Physically unplug USB and lock the **iPhone** with its side button. Record
   the UTC time after lock confirmation. Optionally check the Mac's USB registry.
6. Leave the phone untouched for at least ten minutes. Make no device, debugger,
   automation or wake-up calls during the interval.
7. Unlock and open **Maps first**, before StikDebug. Tap its current-location
   arrow and wait about 15 seconds. Record what the blue dot shows.
8. Keep USB unplugged, tap Restore Real GPS in StikDebug, and record its response.
9. Return to Maps and independently confirm the real-location blue dot.

Keep command acceptance, Maps observations, source-information readings and
long-term reliability separate. Do not infer an OS kill from loss of simulation.
Do not claim app compatibility from a single Maps test.
