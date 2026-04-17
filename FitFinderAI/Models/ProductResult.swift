import Foundation

// MARK: - ProductResult

struct ProductResult: Identifiable, Codable, Equatable {
    let id: UUID
    var title: String
    var price: Double
    var originalPrice: Double?
    var currency: String
    var storeName: String
    var storeLogoURL: String?
    var imageURL: String
    var purchaseURL: String
    var brand: String?
    var similarity: Double         // 0.0–1.0 match confidence
    var isExactMatch: Bool
    var isOnSale: Bool
    var rating: Double?            // 0.0–5.0
    var reviewCount: Int?
    var shipping: String?
    var availability: Availability
    var matchType: MatchType

    enum Availability: String, Codable {
        case inStock     = "In Stock"
        case limitedStock = "Limited Stock"
        case outOfStock  = "Out of Stock"
        case unknown     = "Unknown"
    }

    enum MatchType: String, Codable {
        case exact       = "Exact Match"
        case similar     = "Similar Style"
        case cheaper     = "Cheaper Alternative"
        case branded     = "Same Brand"
    }

    init(
        id: UUID = UUID(),
        title: String,
        price: Double,
        originalPrice: Double? = nil,
        currency: String = "USD",
        storeName: String,
        storeLogoURL: String? = nil,
        imageURL: String,
        purchaseURL: String,
        brand: String? = nil,
        similarity: Double = 1.0,
        isExactMatch: Bool = false,
        isOnSale: Bool = false,
        rating: Double? = nil,
        reviewCount: Int? = nil,
        shipping: String? = nil,
        availability: Availability = .unknown,
        matchType: MatchType = .similar
    ) {
        self.id = id
        self.title = title
        self.price = price
        self.originalPrice = originalPrice
        self.currency = currency
        self.storeName = storeName
        self.storeLogoURL = storeLogoURL
        self.imageURL = imageURL
        self.purchaseURL = purchaseURL
        self.brand = brand
        self.similarity = similarity
        self.isExactMatch = isExactMatch
        self.isOnSale = isOnSale
        self.rating = rating
        self.reviewCount = reviewCount
        self.shipping = shipping
        self.availability = availability
        self.matchType = matchType
    }

    var formattedPrice: String {
        let symbol = currencySymbol(for: currency)
        return "\(symbol)\(String(format: "%.2f", price))"
    }

    var formattedOriginalPrice: String? {
        guard let original = originalPrice else { return nil }
        let symbol = currencySymbol(for: currency)
        return "\(symbol)\(String(format: "%.2f", original))"
    }

    var discountPercentage: Int? {
        guard let original = originalPrice, original > price else { return nil }
        return Int(((original - price) / original) * 100)
    }

    var similarityLabel: String {
        switch similarity {
        case 0.9...1.0: return "Exact Match"
        case 0.7..<0.9: return "Very Similar"
        case 0.5..<0.7: return "Similar Style"
        default:        return "Related"
        }
    }

    private func currencySymbol(for code: String) -> String {
        let locale = Locale(identifier: Locale.identifier(fromComponents: [NSLocale.Key.currencyCode.rawValue: code]))
        return locale.currencySymbol ?? "$"
    }
}

// MARK: - SerpAPI Response Models

struct SerpAPIShoppingResponse: Codable {
    let shoppingResults: [SerpAPIProduct]?

    enum CodingKeys: String, CodingKey {
        case shoppingResults = "shopping_results"
    }
}

struct SerpAPIProduct: Codable {
    let title: String
    let link: String
    let source: String
    let price: String?
    let extractedPrice: Double?
    let thumbnail: String?
    let rating: Double?
    let reviews: Int?
    let delivery: String?

    enum CodingKeys: String, CodingKey {
        case title, link, source, price, thumbnail, rating, reviews, delivery
        case extractedPrice = "extracted_price"
    }
}

// MARK: - Claude API Models

struct ClaudeAPIRequest: Codable {
    let model: String
    let maxTokens: Int
    let messages: [ClaudeMessage]

    enum CodingKeys: String, CodingKey {
        case model
        case maxTokens = "max_tokens"
        case messages
    }
}

struct ClaudeMessage: Codable {
    let role: String
    let content: [ClaudeContent]
}

struct ClaudeContent: Codable {
    let type: String
    let text: String?
    let source: ClaudeImageSource?

    init(type: String = "text", text: String) {
        self.type = type
        self.text = text
        self.source = nil
    }

    init(type: String = "image", source: ClaudeImageSource) {
        self.type = type
        self.text = nil
        self.source = source
    }
}

struct ClaudeImageSource: Codable {
    let type: String
    let mediaType: String
    let data: String

    enum CodingKeys: String, CodingKey {
        case type
        case mediaType = "media_type"
        case data
    }
}

struct ClaudeAPIResponse: Codable {
    let content: [ClaudeResponseContent]
    let usage: ClaudeUsage?
}

struct ClaudeResponseContent: Codable {
    let type: String
    let text: String?
}

struct ClaudeUsage: Codable {
    let inputTokens: Int
    let outputTokens: Int

    enum CodingKeys: String, CodingKey {
        case inputTokens  = "input_tokens"
        case outputTokens = "output_tokens"
    }
}

// MARK: - Claude Clothing Analysis Response

struct ClaudeClothingAnalysis: Codable {
    let type: String
    let color: String
    let colors: [String]
    let style: String
    let brand: String?
    let description: String
    let searchTerms: [String]
    let confidence: Double

    enum CodingKeys: String, CodingKey {
        case type, color, colors, style, brand, description, confidence
        case searchTerms = "searchTerms"
    }
}

// MARK: - Mock Data

extension ProductResult {
    static let mockResults: [ProductResult] = [
        ProductResult(
            title: "Classic White Oxford Dress Shirt - Slim Fit",
            price: 49.99,
            originalPrice: 79.99,
            currency: "USD",
            storeName: "Nordstrom",
            imageURL: "https://example.com/shirt1.jpg",
            purchaseURL: "https://nordstrom.com/shirt1",
            brand: "Calvin Klein",
            similarity: 0.97,
            isExactMatch: true,
            isOnSale: true,
            rating: 4.5,
            reviewCount: 234,
            shipping: "Free Shipping",
            availability: .inStock,
            matchType: .exact
        ),
        ProductResult(
            title: "Men's Oxford Shirt Regular Fit",
            price: 34.99,
            currency: "USD",
            storeName: "ASOS",
            imageURL: "https://example.com/shirt2.jpg",
            purchaseURL: "https://asos.com/shirt2",
            brand: "ASOS Design",
            similarity: 0.88,
            isExactMatch: false,
            rating: 4.2,
            reviewCount: 89,
            shipping: "$5.99",
            availability: .inStock,
            matchType: .similar
        ),
        ProductResult(
            title: "Premium Oxford Button-Down - White",
            price: 29.99,
            currency: "USD",
            storeName: "H&M",
            imageURL: "https://example.com/shirt3.jpg",
            purchaseURL: "https://hm.com/shirt3",
            similarity: 0.82,
            isExactMatch: false,
            rating: 3.9,
            reviewCount: 156,
            shipping: "Free over $40",
            availability: .inStock,
            matchType: .cheaper
        ),
        ProductResult(
            title: "White Poplin Dress Shirt",
            price: 19.99,
            currency: "USD",
            storeName: "Zara",
            imageURL: "https://example.com/shirt4.jpg",
            purchaseURL: "https://zara.com/shirt4",
            similarity: 0.75,
            isExactMatch: false,
            rating: 4.0,
            reviewCount: 412,
            shipping: "Free over $50",
            availability: .limitedStock,
            matchType: .cheaper
        ),
        ProductResult(
            title: "Oxford Cloth Button Down Shirt",
            price: 128.00,
            currency: "USD",
            storeName: "Ralph Lauren",
            imageURL: "https://example.com/shirt5.jpg",
            purchaseURL: "https://ralphlauren.com/shirt5",
            brand: "Polo Ralph Lauren",
            similarity: 0.93,
            isExactMatch: false,
            rating: 4.8,
            reviewCount: 1024,
            shipping: "Free Shipping",
            availability: .inStock,
            matchType: .branded
        )
    ]
}
