import SwiftUI

// MARK: - WishlistView

struct WishlistView: View {
    @EnvironmentObject var wishlistVM: WishlistViewModel

    @State private var selectedItem: WishlistItem?
    @State private var showClearConfirm = false
    @State private var editMode: EditMode = .inactive

    var body: some View {
        NavigationStack {
            Group {
                if wishlistVM.items.isEmpty {
                    EmptyStateView(
                        icon: "heart",
                        title: "Your wishlist is empty",
                        body: "Save items from search results and they'll appear here"
                    )
                } else {
                    wishlistContent
                }
            }
            .navigationTitle("Wishlist")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                if !wishlistVM.items.isEmpty {
                    ToolbarItem(placement: .navigationBarLeading) {
                        sortMenu
                    }
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Button(role: .destructive) {
                            showClearConfirm = true
                        } label: {
                            Image(systemName: "trash")
                        }
                    }
                }
            }
            .confirmationDialog("Clear Wishlist", isPresented: $showClearConfirm, titleVisibility: .visible) {
                Button("Clear All Items", role: .destructive) {
                    wishlistVM.clearAll()
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will remove all \(wishlistVM.items.count) saved items.")
            }
            .sheet(item: $selectedItem) { item in
                ProductDetailView(product: item.product, clothingItem: item.clothingItem)
                    .environmentObject(wishlistVM)
            }
        }
    }

    // MARK: - Content

    private var wishlistContent: some View {
        ScrollView {
            VStack(spacing: 0) {
                // Summary header
                summaryHeader
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
                    .padding(.bottom, 16)

                // Items
                LazyVStack(spacing: 12) {
                    ForEach(wishlistVM.sortedItems) { item in
                        WishlistItemRow(item: item)
                            .padding(.horizontal, 16)
                            .onTapGesture { selectedItem = item }
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    withAnimation {
                                        wishlistVM.remove(id: item.id)
                                    }
                                } label: {
                                    Label("Remove", systemImage: "heart.slash.fill")
                                }
                            }
                    }
                }
                .padding(.bottom, 40)
            }
        }
    }

    // MARK: - Summary Header

    private var summaryHeader: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 4) {
                Text("\(wishlistVM.items.count) Items")
                    .font(.headline)
                    .fontWeight(.bold)
                Text("Total value")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
            Text(formattedTotal)
                .font(.system(.title2, design: .rounded))
                .fontWeight(.bold)
                .foregroundStyle(
                    LinearGradient(colors: [.indigo, .purple], startPoint: .leading, endPoint: .trailing)
                )
        }
        .padding(16)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var formattedTotal: String {
        "$\(String(format: "%.2f", wishlistVM.totalValue))"
    }

    // MARK: - Sort Menu

    private var sortMenu: some View {
        Menu {
            ForEach(WishlistViewModel.WishlistSortOption.allCases, id: \.rawValue) { option in
                Button {
                    wishlistVM.sortOption = option
                } label: {
                    HStack {
                        Text(option.rawValue)
                        if wishlistVM.sortOption == option {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }
        } label: {
            Label("Sort", systemImage: "arrow.up.arrow.down")
                .font(.subheadline)
        }
    }
}

// MARK: - WishlistItemRow

struct WishlistItemRow: View {
    let item: WishlistItem
    @EnvironmentObject var wishlistVM: WishlistViewModel

    var body: some View {
        HStack(spacing: 12) {
            // Product image
            AsyncImage(url: URL(string: item.product.imageURL)) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().scaledToFill()
                default:
                    Color(.tertiarySystemGroupedBackground)
                        .overlay(Image(systemName: "tshirt").foregroundColor(.secondary))
                }
            }
            .frame(width: 80, height: 90)
            .clipShape(RoundedRectangle(cornerRadius: 12))

            // Info
            VStack(alignment: .leading, spacing: 5) {
                Text(item.product.title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .lineLimit(2)

                Text(item.product.storeName)
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer(minLength: 0)

                HStack(alignment: .firstTextBaseline) {
                    Text(item.product.formattedPrice)
                        .font(.system(.headline, design: .rounded))
                        .fontWeight(.bold)

                    Spacer()

                    // Price change indicator
                    if let delta = item.priceDelta {
                        HStack(spacing: 2) {
                            Image(systemName: delta < 0 ? "arrow.down" : "arrow.up")
                            Text("$\(String(format: "%.0f", abs(delta)))")
                        }
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundColor(delta < 0 ? .green : .red)
                    }
                }

                Text("Saved \(item.formattedSavedDate)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            // Remove button
            Button {
                withAnimation(.spring(response: 0.3)) {
                    wishlistVM.remove(id: item.id)
                }
            } label: {
                Image(systemName: "heart.fill")
                    .font(.title3)
                    .foregroundColor(.red)
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
    }
}

#Preview {
    WishlistView()
        .environmentObject({
            let vm = WishlistViewModel()
            return vm
        }())
}
