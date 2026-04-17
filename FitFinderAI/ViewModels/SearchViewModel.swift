import Foundation
import Combine

// MARK: - SearchViewModel

@MainActor
final class SearchViewModel: ObservableObject {

    @Published var allResults: [ProductResult] = []
    @Published var filteredResults: [ProductResult] = []
    @Published var filter = SearchFilter()
    @Published var currentItem: ClothingItem?
    @Published var isSearching = false
    @Published var searchText = ""

    private let searchService = ProductSearchService()
    private var cancellables = Set<AnyCancellable>()

    init() {
        // Re-filter whenever filter or searchText changes
        Publishers.CombineLatest($filter, $searchText)
            .debounce(for: .milliseconds(200), scheduler: RunLoop.main)
            .sink { [weak self] filter, text in
                self?.applyFilter(filter: filter, text: text)
            }
            .store(in: &cancellables)
    }

    // MARK: - Accessors

    var exactMatches: [ProductResult] {
        filteredResults.filter { $0.isExactMatch }
    }

    var similarResults: [ProductResult] {
        filteredResults.filter { !$0.isExactMatch && $0.matchType == .similar }
    }

    var cheaperAlternatives: [ProductResult] {
        filteredResults.filter { $0.matchType == .cheaper }
    }

    var availableStores: [String] {
        Array(Set(allResults.map { $0.storeName })).sorted()
    }

    var priceRange: ClosedRange<Double> {
        guard let min = allResults.map({ $0.price }).min(),
              let max = allResults.map({ $0.price }).max(),
              min < max else {
            return 0...500
        }
        return min...max
    }

    var hasResults: Bool { !filteredResults.isEmpty }

    // MARK: - Public

    func load(results: [ProductResult], for item: ClothingItem) {
        allResults = results
        currentItem = item
        applyFilter(filter: filter, text: searchText)
    }

    func reSearch(query: String) async {
        guard let item = currentItem else { return }
        isSearching = true
        defer { isSearching = false }

        do {
            let results = try await searchService.search(query: query, item: item)
            load(results: results, for: item)
        } catch { }
    }

    func reset() {
        allResults = []
        filteredResults = []
        currentItem = nil
        filter = SearchFilter()
        searchText = ""
    }

    // MARK: - Private

    private func applyFilter(filter: SearchFilter, text: String) {
        var results = filter.apply(to: allResults)

        if !text.isEmpty {
            let lowered = text.lowercased()
            results = results.filter {
                $0.title.lowercased().contains(lowered) ||
                ($0.brand?.lowercased().contains(lowered) ?? false) ||
                $0.storeName.lowercased().contains(lowered)
            }
        }

        filteredResults = results
    }
}
