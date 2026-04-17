import Foundation
import UIKit
import Combine

// MARK: - AppState

enum AppState: Equatable {
    case idle
    case analyzing
    case searching
    case results
    case error(String)
}

// MARK: - MainViewModel

@MainActor
final class MainViewModel: ObservableObject {

    // Published state
    @Published var appState: AppState = .idle
    @Published var capturedImage: UIImage?
    @Published var identifiedItem: ClothingItem?
    @Published var manualKeywords: String = ""
    @Published var showCamera = false
    @Published var showImagePicker = false
    @Published var showResults = false
    @Published var errorMessage: String?
    @Published var analysisProgress: Double = 0

    // Services
    let recognitionService = ImageRecognitionService()
    let searchService = ProductSearchService()
    let searchViewModel = SearchViewModel()

    // MARK: - Public Actions

    func handleImage(_ image: UIImage) {
        capturedImage = image
        showCamera = false
        showImagePicker = false
        Task { await analyze(image: image) }
    }

    func retryWithKeywords() {
        guard let item = identifiedItem else { return }
        let enhanced = manualKeywords.isEmpty ? item : enhancedItem(item)
        Task { await performSearch(for: enhanced) }
    }

    func startOver() {
        capturedImage = nil
        identifiedItem = nil
        manualKeywords = ""
        showResults = false
        errorMessage = nil
        appState = .idle
        analysisProgress = 0
        searchViewModel.reset()
    }

    // MARK: - Private Pipeline

    private func analyze(image: UIImage) async {
        appState = .analyzing
        errorMessage = nil
        analysisProgress = 0.2

        do {
            let item = try await recognitionService.analyze(image: image)
            analysisProgress = 0.6
            identifiedItem = item

            // Merge manual keywords if provided
            let searchItem = manualKeywords.isEmpty ? item : enhancedItem(item)
            await performSearch(for: searchItem)

        } catch {
            appState = .error(error.localizedDescription)
            errorMessage = error.localizedDescription
            analysisProgress = 0
        }
    }

    private func performSearch(for item: ClothingItem) async {
        appState = .searching
        analysisProgress = 0.8

        do {
            let results = try await searchService.search(for: item)
            searchViewModel.load(results: results, for: item)
            analysisProgress = 1.0
            appState = .results
            showResults = true
        } catch {
            appState = .error(error.localizedDescription)
            errorMessage = error.localizedDescription
            analysisProgress = 0
        }
    }

    private func enhancedItem(_ item: ClothingItem) -> ClothingItem {
        var enhanced = item
        let extra = manualKeywords.components(separatedBy: " ").filter { !$0.isEmpty }
        var terms = enhanced.searchTerms
        terms.append(contentsOf: extra)
        enhanced.searchTerms = Array(Set(terms))
        // If user typed a brand, pick it up
        if let firstWord = extra.first, firstWord.count > 2 {
            enhanced.brand = firstWord.capitalized
        }
        return enhanced
    }
}
