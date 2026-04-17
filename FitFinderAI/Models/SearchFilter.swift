import Foundation

// MARK: - SortOption

enum SortOption: String, CaseIterable, Identifiable {
    case similarity    = "Best Match"
    case priceLow      = "Price: Low to High"
    case priceHigh     = "Price: High to Low"
    case rating        = "Top Rated"
    case brand         = "Brand"

    var id: String { rawValue }

    var systemIcon: String {
        switch self {
        case .similarity:  return "star.fill"
        case .priceLow:    return "arrow.up.circle"
        case .priceHigh:   return "arrow.down.circle"
        case .rating:      return "hand.thumbsup.fill"
        case .brand:       return "tag.fill"
        }
    }
}

// MARK: - MatchFilter

enum MatchFilter: String, CaseIterable, Identifiable {
    case all           = "All Results"
    case exactOnly     = "Exact Matches"
    case similar       = "Similar Style"
    case cheaper       = "Cheaper Options"

    var id: String { rawValue }
}

// MARK: - SearchFilter

struct SearchFilter: Equatable {
    var sortOption: SortOption = .similarity
    var matchFilter: MatchFilter = .all
    var maxPrice: Double? = nil
    var minPrice: Double? = nil
    var selectedStores: Set<String> = []
    var showOnSaleOnly: Bool = false
    var showInStockOnly: Bool = true

    var isDefault: Bool {
        sortOption == .similarity &&
        matchFilter == .all &&
        maxPrice == nil &&
        minPrice == nil &&
        selectedStores.isEmpty &&
        !showOnSaleOnly &&
        showInStockOnly
    }

    mutating func reset() {
        sortOption = .similarity
        matchFilter = .all
        maxPrice = nil
        minPrice = nil
        selectedStores = []
        showOnSaleOnly = false
        showInStockOnly = true
    }

    func apply(to results: [ProductResult]) -> [ProductResult] {
        var filtered = results

        // Match type filter
        switch matchFilter {
        case .all:       break
        case .exactOnly: filtered = filtered.filter { $0.isExactMatch }
        case .similar:   filtered = filtered.filter { $0.matchType == .similar }
        case .cheaper:   filtered = filtered.filter { $0.matchType == .cheaper }
        }

        // Price range
        if let minP = minPrice {
            filtered = filtered.filter { $0.price >= minP }
        }
        if let maxP = maxPrice {
            filtered = filtered.filter { $0.price <= maxP }
        }

        // Store filter
        if !selectedStores.isEmpty {
            filtered = filtered.filter { selectedStores.contains($0.storeName) }
        }

        // Sale filter
        if showOnSaleOnly {
            filtered = filtered.filter { $0.isOnSale }
        }

        // Stock filter
        if showInStockOnly {
            filtered = filtered.filter { $0.availability != .outOfStock }
        }

        // Sort
        switch sortOption {
        case .similarity:
            filtered.sort { $0.similarity > $1.similarity }
        case .priceLow:
            filtered.sort { $0.price < $1.price }
        case .priceHigh:
            filtered.sort { $0.price > $1.price }
        case .rating:
            filtered.sort { ($0.rating ?? 0) > ($1.rating ?? 0) }
        case .brand:
            filtered.sort { ($0.brand ?? $0.storeName) < ($1.brand ?? $1.storeName) }
        }

        return filtered
    }
}
