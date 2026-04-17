import Foundation

// MARK: - WishlistService

final class WishlistService {

    private let storageKey = "fitfinder.wishlist.v1"
    private let defaults = UserDefaults.standard

    // MARK: - Read

    func loadAll() -> [WishlistItem] {
        guard let data = defaults.data(forKey: storageKey) else { return [] }
        do {
            return try JSONDecoder().decode([WishlistItem].self, from: data)
        } catch {
            return []
        }
    }

    func contains(productURL: String) -> Bool {
        loadAll().contains { $0.product.purchaseURL == productURL }
    }

    // MARK: - Write

    @discardableResult
    func save(_ item: WishlistItem) -> Bool {
        var items = loadAll()
        if items.contains(where: { $0.id == item.id }) { return false }
        items.insert(item, at: 0)
        return persist(items)
    }

    @discardableResult
    func remove(id: UUID) -> Bool {
        var items = loadAll()
        items.removeAll { $0.id == id }
        return persist(items)
    }

    @discardableResult
    func update(_ item: WishlistItem) -> Bool {
        var items = loadAll()
        guard let idx = items.firstIndex(where: { $0.id == item.id }) else { return false }
        items[idx] = item
        return persist(items)
    }

    func clearAll() {
        defaults.removeObject(forKey: storageKey)
    }

    // MARK: - Private

    @discardableResult
    private func persist(_ items: [WishlistItem]) -> Bool {
        do {
            let data = try JSONEncoder().encode(items)
            defaults.set(data, forKey: storageKey)
            return true
        } catch {
            return false
        }
    }
}
