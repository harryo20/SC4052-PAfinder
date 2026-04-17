import Foundation

// MARK: - WishlistItem

struct WishlistItem: Identifiable, Codable, Equatable {
    let id: UUID
    let product: ProductResult
    let clothingItem: ClothingItem?
    let savedAt: Date
    var notes: String
    var priceAtSave: Double
    var isNotifyOnPriceDrop: Bool

    init(
        id: UUID = UUID(),
        product: ProductResult,
        clothingItem: ClothingItem? = nil,
        savedAt: Date = Date(),
        notes: String = "",
        isNotifyOnPriceDrop: Bool = false
    ) {
        self.id = id
        self.product = product
        self.clothingItem = clothingItem
        self.savedAt = savedAt
        self.notes = notes
        self.priceAtSave = product.price
        self.isNotifyOnPriceDrop = isNotifyOnPriceDrop
    }

    static func == (lhs: WishlistItem, rhs: WishlistItem) -> Bool {
        lhs.id == rhs.id
    }

    var priceDelta: Double? {
        let current = product.price
        guard current != priceAtSave else { return nil }
        return current - priceAtSave
    }

    var priceDropped: Bool {
        guard let delta = priceDelta else { return false }
        return delta < 0
    }

    var formattedSavedDate: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return formatter.localizedString(for: savedAt, relativeTo: Date())
    }
}

// MARK: - Mock Data

extension WishlistItem {
    static let mockItems: [WishlistItem] = ProductResult.mockResults.prefix(3).map {
        WishlistItem(product: $0)
    }
}
