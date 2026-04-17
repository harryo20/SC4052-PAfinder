import Foundation
import UIKit
import Vision

// MARK: - Errors

enum RecognitionError: LocalizedError {
    case invalidImage
    case noResults
    case apiError(String)
    case parseError(String)
    case notConfigured

    var errorDescription: String? {
        switch self {
        case .invalidImage:        return "Could not process the image. Please try again."
        case .noResults:           return "No clothing was detected in this image."
        case .apiError(let msg):   return "Analysis failed: \(msg)"
        case .parseError(let msg): return "Could not read analysis results: \(msg)"
        case .notConfigured:       return "Please add your Claude API key in APIConfiguration.swift"
        }
    }
}

// MARK: - ImageRecognitionService

final class ImageRecognitionService {

    // Entry point: tries Claude first, falls back to Vision if key not set
    func analyze(image: UIImage) async throws -> ClothingItem {
        if APIConfiguration.useMockData {
            try await Task.sleep(nanoseconds: 1_500_000_000)
            return ClothingItem.mock
        }

        let compressed = resized(image, maxDimension: APIConfiguration.maxImageDimension)

        if APIConfiguration.claudeAPIKey != "YOUR_CLAUDE_API_KEY" {
            return try await analyzeWithClaude(compressed)
        } else {
            return try await analyzeWithVision(compressed)
        }
    }

    // MARK: - Claude Vision

    private func analyzeWithClaude(_ image: UIImage) async throws -> ClothingItem {
        guard let imageData = image.jpegData(compressionQuality: APIConfiguration.imageCompressionQuality) else {
            throw RecognitionError.invalidImage
        }
        let base64 = imageData.base64EncodedString()

        let prompt = """
        Analyze this clothing item image and return ONLY a JSON object (no markdown, no extra text) with these exact keys:
        {
          "type": one of: shirt|tshirt|pants|jeans|dress|skirt|jacket|coat|hoodie|sweater|shoes|sneakers|boots|bag|hat|accessory|other,
          "color": "primary color name",
          "colors": ["list", "of", "all", "visible", "colors"],
          "style": one of: casual|formal|sporty|streetwear|business|bohemian|vintage|minimalist|luxury|unknown,
          "brand": "brand name if clearly visible in the image, or null",
          "description": "one-sentence description of the item",
          "searchTerms": ["3-6 search keywords to find this item online"],
          "confidence": 0.0 to 1.0
        }
        Focus on identifying the garment type, colors, cut, material texture, and any logos.
        """

        let body = ClaudeAPIRequest(
            model: APIConfiguration.claudeModel,
            maxTokens: 512,
            messages: [
                ClaudeMessage(role: "user", content: [
                    ClaudeContent(type: "image", source: ClaudeImageSource(
                        type: "base64",
                        mediaType: "image/jpeg",
                        data: base64
                    )),
                    ClaudeContent(type: "text", text: prompt)
                ])
            ]
        )

        guard let url = URL(string: APIConfiguration.claudeBaseURL) else {
            throw RecognitionError.apiError("Invalid endpoint URL")
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.allHTTPHeaderFields = APIConfiguration.claudeHeaders
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            let body = String(data: data, encoding: .utf8) ?? "unknown"
            throw RecognitionError.apiError("HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0): \(body)")
        }

        let claudeResponse = try JSONDecoder().decode(ClaudeAPIResponse.self, from: data)
        guard let text = claudeResponse.content.first?.text else {
            throw RecognitionError.noResults
        }

        return try parseClaudeAnalysis(text, imageData: imageData)
    }

    private func parseClaudeAnalysis(_ json: String, imageData: Data?) throws -> ClothingItem {
        // Strip potential markdown fences
        var cleaned = json.trimmingCharacters(in: .whitespacesAndNewlines)
        if cleaned.hasPrefix("```") {
            cleaned = cleaned
                .replacingOccurrences(of: "```json", with: "")
                .replacingOccurrences(of: "```", with: "")
                .trimmingCharacters(in: .whitespacesAndNewlines)
        }

        guard let data = cleaned.data(using: .utf8) else {
            throw RecognitionError.parseError("Invalid UTF-8 in response")
        }

        let analysis: ClaudeClothingAnalysis
        do {
            analysis = try JSONDecoder().decode(ClaudeClothingAnalysis.self, from: data)
        } catch {
            throw RecognitionError.parseError(error.localizedDescription)
        }

        let type = ClothingType(rawValue: analysis.type.capitalized)
            ?? ClothingType.allCases.first { $0.rawValue.lowercased() == analysis.type.lowercased() }
            ?? .other

        let style = ClothingStyle.allCases.first {
            $0.rawValue.lowercased() == analysis.style.lowercased()
        } ?? .unknown

        return ClothingItem(
            name: buildName(analysis: analysis, type: type),
            type: type,
            primaryColor: analysis.color.capitalized,
            colors: analysis.colors.map { $0.capitalized },
            style: style,
            brand: analysis.brand,
            description: analysis.description,
            searchTerms: analysis.searchTerms,
            confidence: analysis.confidence,
            analysisSource: .claudeAI,
            imageData: imageData
        )
    }

    private func buildName(analysis: ClaudeClothingAnalysis, type: ClothingType) -> String {
        var parts: [String] = []
        if let brand = analysis.brand { parts.append(brand) }
        parts.append(analysis.color.capitalized)
        parts.append(type.rawValue)
        return parts.joined(separator: " ")
    }

    // MARK: - On-Device Vision Fallback

    private func analyzeWithVision(_ image: UIImage) async throws -> ClothingItem {
        guard let cgImage = image.cgImage else {
            throw RecognitionError.invalidImage
        }

        return try await withCheckedThrowingContinuation { continuation in
            let request = VNClassifyImageRequest { request, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                guard let observations = request.results as? [VNClassificationObservation],
                      !observations.isEmpty else {
                    continuation.resume(throwing: RecognitionError.noResults)
                    return
                }

                let result = self.buildClothingItem(from: observations, imageData: image.jpegData(compressionQuality: 0.8))
                continuation.resume(returning: result)
            }

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }

    private func buildClothingItem(from observations: [VNClassificationObservation], imageData: Data?) -> ClothingItem {
        // Map Vision identifiers to our clothing types
        let clothingKeywords: [String: ClothingType] = [
            "shirt": .shirt, "t-shirt": .tshirt, "tshirt": .tshirt,
            "pants": .pants, "jeans": .jeans, "trousers": .pants,
            "dress": .dress, "skirt": .skirt,
            "jacket": .jacket, "coat": .coat,
            "hoodie": .hoodie, "sweatshirt": .hoodie, "sweater": .sweater,
            "shoe": .shoes, "sneaker": .sneakers, "boot": .boots,
            "bag": .bag, "handbag": .bag, "backpack": .bag,
            "hat": .hat, "cap": .hat
        ]

        var detectedType: ClothingType = .other
        var confidence: Double = 0
        var colorGuess = "Unknown"

        let colorKeywords: [String: String] = [
            "black": "Black", "white": "White", "red": "Red", "blue": "Blue",
            "green": "Green", "yellow": "Yellow", "orange": "Orange",
            "purple": "Purple", "pink": "Pink", "gray": "Gray", "grey": "Gray",
            "brown": "Brown", "navy": "Navy", "beige": "Beige"
        ]

        for obs in observations.prefix(20) {
            let identifier = obs.identifier.lowercased()

            for (keyword, type) in clothingKeywords {
                if identifier.contains(keyword) && obs.confidence > Float(confidence) {
                    detectedType = type
                    confidence = Double(obs.confidence)
                }
            }

            for (keyword, color) in colorKeywords {
                if identifier.contains(keyword) {
                    colorGuess = color
                }
            }
        }

        let name = "\(colorGuess) \(detectedType.rawValue)"

        return ClothingItem(
            name: name,
            type: detectedType,
            primaryColor: colorGuess,
            colors: [colorGuess],
            style: .unknown,
            description: "Identified via on-device Vision analysis",
            searchTerms: [name, detectedType.rawValue],
            confidence: confidence,
            analysisSource: .onDevice,
            imageData: imageData
        )
    }

    // MARK: - Image Utility

    private func resized(_ image: UIImage, maxDimension: CGFloat) -> UIImage {
        let size = image.size
        guard max(size.width, size.height) > maxDimension else { return image }

        let scale = maxDimension / max(size.width, size.height)
        let newSize = CGSize(width: size.width * scale, height: size.height * scale)

        UIGraphicsBeginImageContextWithOptions(newSize, false, 1.0)
        image.draw(in: CGRect(origin: .zero, size: newSize))
        let resized = UIGraphicsGetImageFromCurrentImageContext() ?? image
        UIGraphicsEndImageContext()
        return resized
    }
}
