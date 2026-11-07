import Foundation
import CoreLocation

/// Observes documented Core Location behaviour only. It does not hide or alter any location.
final class LocationModel: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var latitude: Double?
    @Published var longitude: Double?
    @Published var horizontalAccuracy: Double?
    @Published var timestamp: Date?
    @Published var speed: Double?
    @Published var course: Double?
    @Published var authorization: String = "unknown"
    @Published var sourceInfoAvailable = false
    @Published var isSimulatedBySoftware: Bool?
    @Published var isProducedByAccessory: Bool?
    @Published var updateCount = 0
    @Published var lastUpdateReceivedAt: Date?

    private let manager = CLLocationManager()

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
        refreshAuthorization()
    }

    func start() {
        if manager.authorizationStatus == .notDetermined { manager.requestWhenInUseAuthorization() }
        manager.startUpdatingLocation()
    }

    func stop() { manager.stopUpdatingLocation() }

    /// A fix is "fresh" only if a delegate callback arrived recently AND the fix's own timestamp is recent.
    func isFresh(now: Date = Date(), maxAge: TimeInterval = 10) -> Bool {
        guard let rx = lastUpdateReceivedAt, let ts = timestamp else { return false }
        return now.timeIntervalSince(rx) < maxAge && now.timeIntervalSince(ts) < maxAge
    }

    private func refreshAuthorization() {
        switch manager.authorizationStatus {
        case .notDetermined: authorization = "not determined"
        case .restricted: authorization = "restricted"
        case .denied: authorization = "denied"
        case .authorizedAlways: authorization = "always"
        case .authorizedWhenInUse: authorization = "when in use"
        @unknown default: authorization = "unknown"
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        refreshAuthorization()
        if manager.authorizationStatus == .authorizedWhenInUse || manager.authorizationStatus == .authorizedAlways {
            manager.startUpdatingLocation()
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        latitude = loc.coordinate.latitude
        longitude = loc.coordinate.longitude
        horizontalAccuracy = loc.horizontalAccuracy
        timestamp = loc.timestamp
        speed = loc.speed >= 0 ? loc.speed : nil
        course = loc.course >= 0 ? loc.course : nil
        lastUpdateReceivedAt = Date()
        updateCount += 1
        if #available(iOS 15.0, macOS 12.0, *), let info = loc.sourceInformation {
            sourceInfoAvailable = true
            isSimulatedBySoftware = info.isSimulatedBySoftware
            isProducedByAccessory = info.isProducedByAccessory
        } else {
            sourceInfoAvailable = false
            isSimulatedBySoftware = nil
            isProducedByAccessory = nil
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        authorization += " (error: \(error.localizedDescription))"
    }
}
