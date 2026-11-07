import SwiftUI

struct ContentView: View {
    @StateObject private var model = LocationModel()
    private let tick = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    @State private var now = Date()

    private func f(_ v: Double?, _ d: Int = 6) -> String { v.map { String(format: "%.\(d)f", $0) } ?? "—" }
    private func b(_ v: Bool?) -> String { v.map { $0 ? "YES" : "no" } ?? "unavailable" }

    var body: some View {
        NavigationStack {
            List {
                Section("Position") {
                    row("Latitude", f(model.latitude))
                    row("Longitude", f(model.longitude))
                    row("Horizontal accuracy (m)", f(model.horizontalAccuracy, 1))
                    row("Fix timestamp", model.timestamp.map { $0.formatted(date: .omitted, time: .standard) } ?? "—")
                    row("Speed (m/s)", f(model.speed, 1))
                    row("Course (°)", f(model.course, 0))
                }
                Section("Freshness") {
                    row("Fresh update arrived (<10s)", model.isFresh(now: now) ? "YES" : "no")
                    row("Updates received", "\(model.updateCount)")
                }
                Section("Source (CLLocationSourceInformation)") {
                    row("Source info available", model.sourceInfoAvailable ? "yes" : "no")
                    row("isSimulatedBySoftware", b(model.isSimulatedBySoftware))
                    row("isProducedByAccessory", b(model.isProducedByAccessory))
                }
                Section("Authorization") { row("Status", model.authorization) }
                Section {
                    Text("Observes what Core Location reports on this device. It cannot tell you whether any other app accepts or rejects a location.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Location Probe")
        }
        .onAppear { model.start() }
        .onReceive(tick) { now = $0 }
    }

    private func row(_ k: String, _ v: String) -> some View {
        HStack { Text(k); Spacer(); Text(v).monospacedDigit().foregroundStyle(.secondary) }
    }
}
