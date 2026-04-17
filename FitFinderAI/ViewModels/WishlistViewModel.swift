import Foundation
import Combine

// MARK: - WishlistViewModel

@MainActor
final class WishlistViewModel: ObservableObject {

    @Published var items: [WishlistItem] = []
    @Published var sortOption: WishlistSortOption = .dateAdded

    private let service = WishlistService()

    enum WishlistSortOption: String, CaseIterable {
        case dateAdded = "Date Added"
        case priceAsc  = "Price: Low to High"
        case priceDesc = "Price: High to Low"
        case name      = "Name"
    }

    init() {
        reload()
    }

    // MARK: - Read

    var sortedItems: [WishlistItem] {
        switch sortOption {
        case .dateAdded: return items.sorted { $0.savedAt > $1.savedAt }
        case .priceAsc:  return items.sorted { $0.product.price < $1.product.price }
        case .priceDesc: return items.sorted { $0.product.price > $1.product.price }
        case .name:      return items.sorted { $0.product.title < $1.product.title }
        }
    }

    var totalValue: Double {
        items.reduce(0) { $0 + $1.product.price }
    }

    func isSaved(productURL: String) -> Bool {
        items.contains { $0.product.purchaseURL == productURL }
    }

    // MARK: - Write

    func add(product: ProductResult, clothingItem: ClothingItem? = nil) {
        guard !isSaved(productURL: product.purchaseURL) else { return }
        let wishlistItem = WishlistItem(product: product, clothingItem: clothingItem)
        service.save(wishlistItem)
        reload()
    }

    func remove(id: UUID) {
        service.remove(id: id)
        reload()
    }

    func toggle(product: ProductResult, clothingItem: ClothingItem? = nil) {
        if let existing = items.first(where: { $0.product.purchaseURL == product.purchaseURL }) {
            remove(id: existing.id)
        } else {
            add(product: product, clothingItem: clothingItem)
        }
    }

    func updateNotes(id: UUID, notes: String) {
        guard var item = items.first(where: { $0.id == id }) else { return }
        item.notes = notes
        service.update(item)
        reload()
    }

    func clearAll() {
        service.clearAll()
        reload()
    }

    // MARK: - Private

    private func reload() {
        items = service.loadAll()
    }
}
