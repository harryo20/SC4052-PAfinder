import Foundation

// MARK: - SearchError

enum SearchError: LocalizedError {
    case invalidURL
    case apiError(String)
    case noResults
    case notConfigured

    var errorDescription: String? {
        switch self {
        case .invalidURL:         return "Invalid search URL."
        case .apiError(let msg):  return "Search failed: \(msg)"
        case .noResults:          return "No products found for this item."
        case .notConfigured:      return "Please add your SerpAPI key in APIConfiguration.swift"
        }
    }
}

// MARK: - ProductSearchService

final class ProductSearchService {

    // Primary entry point: searches for exact + similar + cheaper results
    func search(for item: ClothingItem) async throws -> [ProductResult] {
        if APIConfiguration.useMockData {
            try await Task.sleep(nanoseconds: 2_000_000_000)
            return ProductResult.mockResults
        }

        guard APIConfiguration.serpAPIKey != "YOUR_SERPAPI_KEY" else {
            throw SearchError.notConfigured
        }

        async let exactResults   = searchProducts(query: item.searchQuery, item: item)
        async let cheaperResults = searchProducts(query: "affordable \(item.searchQuery)", item: item, matchType: .cheaper)

        var results: [ProductResult] = []

        do {
            let exact = try await exactResults
            results.append(contentsOf: exact)
        } catch { }

        do {
            let cheaper = try await cheaperResults
            let cheaperFiltered = cheaper
                .filter { $0.price < (results.first?.price ?? .infinity) }
                .map { product in
                    var p = product
                    // Already tagged as .cheaper above but re-confirm
                    return p
                }
            results.append(contentsOf: cheaperFiltered)
        } catch { }

        if results.isEmpty {
            throw SearchError.noResults
        }

        return deduplicated(results)
    }

    // Targeted search with a specific query string (callable from UI for re-search)
    func search(query: String, item: ClothingItem? = nil) async throws -> [ProductResult] {
        if APIConfiguration.useMockData {
            try await Task.sleep(nanoseconds: 1_000_000_000)
            return ProductResult.mockResults
        }

        guard APIConfiguration.serpAPIKey != "YOUR_SERPAPI_KEY" else {
            throw SearchError.notConfigured
        }

        return try await searchProducts(query: query, item: item)
    }

    // MARK: - SerpAPI Call

    private func searchProducts(
        query: String,
        item: ClothingItem? = nil,
        matchType: ProductResult.MatchType = .similar
    ) async throws -> [ProductResult] {

        var components = URLComponents(string: APIConfiguration.serpAPIBaseURL)!
        components.queryItems = [
            URLQueryItem(name: "engine",  value: "google_shopping"),
            URLQueryItem(name: "q",       value: query),
            URLQueryItem(name: "api_key", value: APIConfiguration.serpAPIKey),
            URLQueryItem(name: "num",     value: String(APIConfiguration.maxSearchResults)),
            URLQueryItem(name: "gl",      value: "us"),
            URLQueryItem(name: "hl",      value: "en")
        ]

        guard let url = components.url else { throw SearchError.invalidURL }

        let (data, response) = try await URLSession.shared.data(from: url)

        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw SearchError.apiError("HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0): \(body)")
        }

        let serpResponse = try JSONDecoder().decode(SerpAPIShoppingResponse.self, from: data)
        guard let products = serpResponse.shoppingResults, !products.isEmpty else {
            return []
        }

        return products.enumerated().compactMap { (index, product) -> ProductResult? in
            let price = product.extractedPrice ?? parsePrice(product.price ?? "")
            guard price > 0 else { return nil }

            // Score similarity: first results from Google are most relevant
            let similarity = max(0.5, 1.0 - (Double(index) * 0.04))

            let isExact = matchType == .exact ||
                (item?.brand != nil && (product.title.lowercased().contains(item?.brand?.lowercased() ?? "")))

            return ProductResult(
                title: product.title,
                price: price,
                currency: "USD",
                storeName: product.source,
                imageURL: product.thumbnail ?? "",
                purchaseURL: product.link,
                similarity: similarity,
                isExactMatch: isExact,
                isOnSale: false,
                rating: product.rating,
                reviewCount: product.reviews,
                shipping: product.delivery,
                availability: .inStock,
                matchType: isExact ? .exact : matchType
            )
        }
    }

    // MARK: - Helpers

    private func parsePrice(_ string: String) -> Double {
        let cleaned = string
            .replacingOccurrences(of: "$", with: "")
            .replacingOccurrences(of: ",", with: "")
            .trimmingCharacters(in: .whitespaces)
        return Double(cleaned) ?? 0
    }

    private func deduplicated(_ results: [ProductResult]) -> [ProductResult] {
        var seen = Set<String>()
        return results.filter { product in
            let key = "\(product.storeName)|\(product.title)"
            if seen.contains(key) { return false }
            seen.insert(key)
            return true
        }
    }
}
