import Foundation

// MARK: - APIConfiguration
//
// Fill in your API keys here before building.
// Keys are stored in code for simplicity; for production use
// an environment variable, encrypted plist, or Keychain.

enum APIConfiguration {

    // -------------------------------------------------------------------------
    // REQUIRED: Claude Vision API
    // Get your key at https://console.anthropic.com
    // Used for precise clothing identification from photos.
    // -------------------------------------------------------------------------
    static let claudeAPIKey: String = "YOUR_CLAUDE_API_KEY"

    // -------------------------------------------------------------------------
    // REQUIRED: SerpAPI (Google Shopping search)
    // Get your key at https://serpapi.com  (100 free searches/month)
    // Used to find product listings matching the identified clothing item.
    // -------------------------------------------------------------------------
    static let serpAPIKey: String = "YOUR_SERPAPI_KEY"

    // -------------------------------------------------------------------------
    // Development: set true to skip API calls and use built-in mock data.
    // -------------------------------------------------------------------------
    static let useMockData: Bool = false

    // -------------------------------------------------------------------------
    // Endpoints (change only if you proxy through your own backend)
    // -------------------------------------------------------------------------
    static let claudeBaseURL   = "https://api.anthropic.com/v1/messages"
    static let serpAPIBaseURL  = "https://serpapi.com/search.json"
    static let claudeModel     = "claude-sonnet-4-6"
    static let claudeVersion   = "2023-06-01"

    // -------------------------------------------------------------------------
    // Search settings
    // -------------------------------------------------------------------------
    static let maxSearchResults = 20
    static let imageCompressionQuality: CGFloat = 0.75  // JPEG quality sent to Claude
    static let maxImageDimension: CGFloat = 1024         // Resize before sending

    // -------------------------------------------------------------------------
    // Computed helpers
    // -------------------------------------------------------------------------
    static var isConfigured: Bool {
        claudeAPIKey != "YOUR_CLAUDE_API_KEY" && serpAPIKey != "YOUR_SERPAPI_KEY"
    }

    static var claudeHeaders: [String: String] {
        [
            "x-api-key": claudeAPIKey,
            "anthropic-version": claudeVersion,
            "Content-Type": "application/json"
        ]
    }
}

// MARK: - CGFloat

import CoreGraphics
