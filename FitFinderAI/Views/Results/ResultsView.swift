import SwiftUI

// MARK: - ResultsView

struct ResultsView: View {
    @EnvironmentObject var mainVM: MainViewModel
    @EnvironmentObject var searchVM: SearchViewModel
    @EnvironmentObject var wishlistVM: WishlistViewModel

    @Environment(\.dismiss) private var dismiss
    @State private var showFilter = false
    @State private var selectedProduct: ProductResult?
    @State private var searchText = ""
    @State private var scrollOffset: CGFloat = 0

    var body: some View {
        NavigationStack {
            ZStack(alignment: .top) {
                Color(.systemGroupedBackground).ignoresSafeArea()

                ScrollView {
                    LazyVStack(spacing: 0, pinnedViews: [.sectionHeaders]) {
                        // Clothing item header
                        clothingHeader
                            .padding(.horizontal, 16)
                            .padding(.top, 8)

                        // Search bar
                        searchBar
                            .padding(.horizontal, 16)
                            .padding(.top, 12)

                        // Summary chips
                        summaryChips
                            .padding(.horizontal, 16)
                            .padding(.top, 10)

                        // Exact matches
                        if !searchVM.exactMatches.isEmpty {
                            resultsSection(
                                title: "Exact Matches",
                                icon: "checkmark.seal.fill",
                                color: .green,
                                results: searchVM.exactMatches
                            )
                        }

                        // Similar style
                        if !searchVM.similarResults.isEmpty {
                            resultsSection(
                                title: "Similar Style",
                                icon: "sparkles",
                                color: .indigo,
                                results: searchVM.similarResults
                            )
                        }

                        // Cheaper alternatives
                        if !searchVM.cheaperAlternatives.isEmpty {
                            cheaperSection
                        }

                        if !searchVM.hasResults {
                            EmptyStateView(
                                icon: "magnifyingglass",
                                title: "No results found",
                                body: "Try different keywords or adjust your filters"
                            )
                            .padding(.top, 60)
                        }

                        Spacer(minLength: 40)
                    }
                }
                .searchable(text: $searchVM.searchText, prompt: "Filter results…")
            }
            .navigationTitle("Results")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        dismiss()
                        mainVM.startOver()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "camera.viewfinder")
                            Text("New Scan")
                        }
                        .font(.subheadline)
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    filterButton
                }
            }
            .sheet(isPresented: $showFilter) {
                FilterSortView(filter: $searchVM.filter, stores: searchVM.availableStores)
            }
            .sheet(item: $selectedProduct) { product in
                ProductDetailView(product: product, clothingItem: searchVM.currentItem)
                    .environmentObject(wishlistVM)
            }
        }
    }

    // MARK: - Clothing Header

    private var clothingHeader: some View {
        HStack(spacing: 14) {
            if let image = mainVM.capturedImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(width: 72, height: 72)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }

            if let item = searchVM.currentItem {
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.name)
                        .font(.headline)
                        .lineLimit(2)

                    HStack(spacing: 6) {
                        Label(item.type.rawValue, systemImage: item.type.systemIcon)
                        Text("•")
                        Text(item.primaryColor)
                        if let brand = item.brand {
                            Text("• \(brand)")
                                .fontWeight(.semibold)
                        }
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)

                    HStack(spacing: 4) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text("\(Int(item.confidence * 100))% confidence")
                            .foregroundColor(.secondary)
                        Text("via \(item.analysisSource.rawValue)")
                            .foregroundColor(.secondary)
                    }
                    .font(.caption2)
                }
                Spacer()
            }
        }
        .padding(14)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Search Bar

    private var searchBar: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .foregroundColor(.secondary)
            TextField("Search within results…", text: $searchVM.searchText)
            if !searchVM.searchText.isEmpty {
                Button { searchVM.searchText = "" } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(12)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Summary Chips

    private var summaryChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ResultChip(
                    label: "\(searchVM.filteredResults.count) items",
                    icon: "list.bullet",
                    color: .indigo
                )
                if let min = searchVM.filteredResults.map({ $0.price }).min() {
                    ResultChip(
                        label: "From $\(String(format: "%.0f", min))",
                        icon: "tag.fill",
                        color: .green
                    )
                }
                if !searchVM.filter.isDefault {
                    ResultChip(
                        label: "Filtered",
                        icon: "line.3.horizontal.decrease.circle.fill",
                        color: .orange
                    )
                }
            }
        }
    }

    // MARK: - Results Section

    private func resultsSection(
        title: String,
        icon: String,
        color: Color,
        results: [ProductResult]
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label(title, systemImage: icon)
                    .font(.headline)
                    .foregroundColor(color)
                Spacer()
                Text("\(results.count)")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color(.tertiarySystemGroupedBackground))
                    .clipShape(Capsule())
            }
            .padding(.horizontal, 16)
            .padding(.top, 20)

            ForEach(results) { product in
                ProductCardView(product: product, clothingItem: searchVM.currentItem)
                    .padding(.horizontal, 16)
                    .onTapGesture { selectedProduct = product }
                    .environmentObject(wishlistVM)
            }
        }
    }

    // MARK: - Cheaper Section

    private var cheaperSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Cheaper Alternatives", systemImage: "arrow.down.circle.fill")
                    .font(.headline)
                    .foregroundColor(.orange)
                Spacer()
                Text("\(searchVM.cheaperAlternatives.count)")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color(.tertiarySystemGroupedBackground))
                    .clipShape(Capsule())
            }
            .padding(.horizontal, 16)
            .padding(.top, 20)

            // Horizontal scroll for cheaper alternatives
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(searchVM.cheaperAlternatives) { product in
                        CompactProductCard(product: product)
                            .onTapGesture { selectedProduct = product }
                            .environmentObject(wishlistVM)
                    }
                }
                .padding(.horizontal, 16)
            }
        }
    }

    // MARK: - Filter Button

    private var filterButton: some View {
        Button {
            showFilter = true
        } label: {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "line.3.horizontal.decrease.circle")
                    .font(.title3)
                if !searchVM.filter.isDefault {
                    Circle()
                        .fill(.orange)
                        .frame(width: 8, height: 8)
                        .offset(x: 4, y: -4)
                }
            }
        }
    }
}

// MARK: - ResultChip

struct ResultChip: View {
    let label: String
    let icon: String
    let color: Color

    var body: some View {
        Label(label, systemImage: icon)
            .font(.caption)
            .fontWeight(.medium)
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(color.opacity(0.12))
            .clipShape(Capsule())
    }
}

#Preview {
    let mainVM = MainViewModel()
    let searchVM = SearchViewModel()
    searchVM.load(results: ProductResult.mockResults, for: ClothingItem.mock)
    mainVM.capturedImage = UIImage(systemName: "tshirt.fill")

    return ResultsView()
        .environmentObject(mainVM)
        .environmentObject(searchVM)
        .environmentObject(WishlistViewModel())
}
