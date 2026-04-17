import Foundation
import UIKit

// MARK: - ClothingType

enum ClothingType: String, Codable, CaseIterable, Identifiable {
    case shirt       = "Shirt"
    case tshirt      = "T-Shirt"
    case pants       = "Pants"
    case jeans       = "Jeans"
    case dress       = "Dress"
    case skirt       = "Skirt"
    case jacket      = "Jacket"
    case coat        = "Coat"
    case hoodie      = "Hoodie"
    case sweater     = "Sweater"
    case shoes       = "Shoes"
    case sneakers    = "Sneakers"
    case boots       = "Boots"
    case bag         = "Bag"
    case accessory   = "Accessory"
    case hat         = "Hat"
    case other       = "Other"

    var id: String { rawValue }

    var systemIcon: String {
        switch self {
        case .shirt, .tshirt:        return "tshirt"
        case .pants, .jeans:         return "rectangle.portrait"
        case .dress, .skirt:         return "person.dress"
        case .jacket, .coat, .hoodie, .sweater: return "wind"
        case .shoes, .sneakers, .boots: return "shoeprints.fill"
        case .bag:                   return "bag"
        case .hat:                   return "crown"
        case .accessory:             return "eyeglasses"
        case .other:                 return "questionmark.circle"
        }
    }
}

// MARK: - ClothingStyle

enum ClothingStyle: String, Codable, CaseIterable {
    case casual      = "Casual"
    case formal      = "Formal"
    case sporty      = "Sporty"
    case streetwear  = "Streetwear"
    case business    = "Business"
    case bohemian    = "Bohemian"
    case vintage     = "Vintage"
    case minimalist  = "Minimalist"
    case luxury      = "Luxury"
    case unknown     = "Unknown"
}

// MARK: - ClothingItem

struct ClothingItem: Identifiable, Codable {
    let id: UUID
    var name: String
    var type: ClothingType
    var primaryColor: String
    var colors: [String]
    var style: ClothingStyle
    var brand: String?
    var description: String
    var searchTerms: [String]
    var confidence: Double
    var analysisSource: AnalysisSource
    var imageData: Data?
    var capturedAt: Date

    enum AnalysisSource: String, Codable {
        case onDevice   = "On-Device Vision"
        case claudeAI   = "Claude AI"
        case mock       = "Mock"
    }

    init(
        id: UUID = UUID(),
        name: String,
        type: ClothingType,
        primaryColor: String,
        colors: [String] = [],
        style: ClothingStyle = .unknown,
        brand: String? = nil,
        description: String = "",
        searchTerms: [String] = [],
        confidence: Double = 1.0,
        analysisSource: AnalysisSource = .onDevice,
        imageData: Data? = nil,
        capturedAt: Date = Date()
    ) {
        self.id = id
        self.name = name
        self.type = type
        self.primaryColor = primaryColor
        self.colors = colors.isEmpty ? [primaryColor] : colors
        self.style = style
        self.brand = brand
        self.description = description
        self.searchTerms = searchTerms.isEmpty ? [name, type.rawValue, primaryColor] : searchTerms
        self.confidence = confidence
        self.analysisSource = analysisSource
        self.imageData = imageData
        self.capturedAt = capturedAt
    }

    // Human-readable summary for search query construction
    var searchQuery: String {
        var parts: [String] = []
        if let brand = brand { parts.append(brand) }
        parts.append(type.rawValue.lowercased())
        parts.append(primaryColor.lowercased())
        if style != .unknown { parts.append(style.rawValue.lowercased()) }
        return parts.joined(separator: " ")
    }

    var uiImage: UIImage? {
        guard let data = imageData else { return nil }
        return UIImage(data: data)
    }
}

// MARK: - Mock Data

extension ClothingItem {
    static let mockItems: [ClothingItem] = [
        ClothingItem(
            name: "White Oxford Shirt",
            type: .shirt,
            primaryColor: "White",
            colors: ["White"],
            style: .formal,
            brand: nil,
            description: "Classic white button-up oxford shirt with spread collar",
            searchTerms: ["white oxford shirt", "men's dress shirt", "formal shirt"],
            confidence: 0.94,
            analysisSource: .claudeAI
        ),
        ClothingItem(
            name: "Blue Slim Jeans",
            type: .jeans,
            primaryColor: "Blue",
            colors: ["Blue", "Dark Blue"],
            style: .casual,
            brand: "Levi's",
            description: "Classic slim-fit blue denim jeans",
            searchTerms: ["slim jeans", "blue denim", "levi's jeans"],
            confidence: 0.91,
            analysisSource: .claudeAI
        )
    ]

    static var mock: ClothingItem { mockItems[0] }
}
