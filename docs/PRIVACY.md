# Privacy and credential boundaries

Anywhere GPS runs its Mac API on localhost. That does not make the entire
workflow offline: the frontend requests OpenStreetMap tiles, and search uses
Nominatim. The on-device StikDebug build uses MapKit, can request route speed
limits from Overpass, and includes developer-image download/personalization
paths. Signing communicates with Apple through Xcode.

The Overpass route request contains a bounding box derived from coordinates.
MapKit rendering/search/routing use Apple's services. DDI assets and Apple
personalization involve functional network requests. The local audit identified
these paths; it did not establish a complete network or native-library audit.

Apple Account credentials belong only in Xcode or Apple's system interfaces.
Neither this repository nor its pairing exporter needs an Apple Account password.
Do not enter account credentials into a third-party signing utility for this flow.

Pairing records are device credentials. Keep them only on your Mac and phone,
with file mode **600** and a private Mac parent directory (**700**). Never commit,
upload, paste, export for sharing, or include their contents in logs. The local
phone patch keeps one protected Application Support copy, excludes it from
backups and removes legacy/shared copies after import.

The published tree excludes pairing records, provisioning profiles, certificates,
signed apps, device identifiers and private local handoffs. The ignore rules are
a defense against accidents; they are not a substitute for reviewing staged files.

No recognizable automatic telemetry endpoint was identified in inspected Swift
or bundled JavaScript. This is not a guarantee for bundled native binaries or
the separate LocalDevVPN app. Native debug logs may expose protocol secrets;
do not publish them.
