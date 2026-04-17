import SwiftUI
import SafariServices

// MARK: - ProductDetailView

struct ProductDetailView: View {
    let product: ProductResult
    let clothingItem: ClothingItem?

    @EnvironmentObject var wishlistVM: WishlistViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var showSafari = false
    @State private var shareURL: URL?

    var isSaved: Bool { wishlistVM.isSaved(productURL: product.purchaseURL) }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    // Hero image
                    heroSection

                    // Details
                    VStack(alignment: .leading, spacing: 20) {
                        titleSection
                        priceSection
                        storeSection

                        if let rating = product.rating {
                            ratingSection(rating)
                        }

                        matchSection
                        shippingSection
                        actionButtons
                    }
                    .padding(20)
                }
            }
            .ignoresSafeArea(edges: .top)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button { dismiss() } label: {
                        Image(systemName: "chevron.down")
                            .font(.title3)
                            .padding(8)
                            .background(.ultraThinMaterial)
                            .clipShape(Circle())
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    HStack(spacing: 12) {
                        // Share
                        if let url = URL(string: product.purchaseURL) {
                            ShareLink(item: url) {
                                Image(systemName: "square.and.arrow.up")
                                    .font(.title3)
                            }
                        }
                        // Wishlist
                        Button {
                            withAnimation(.spring(response: 0.3)) {
                                wishlistVM.toggle(product: product, clothingItem: clothingItem)
                            }
                        } label: {
                            Image(systemName: isSaved ? "heart.fill" : "heart")
                                .font(.title3)
                                .foregroundColor(isSaved ? .red : .primary)
                        }
                    }
                }
            }
            .sheet(isPresented: $showSafari) {
                if let url = URL(string: product.purchaseURL) {
                    SafariView(url: url)
                        .ignoresSafeArea()
                }
            }
        }
    }

    // MARK: - Sections

    private var heroSection: some View {
        AsyncImage(url: URL(string: product.imageURL)) { phase in
            switch phase {
            case .success(let image):
                image
                    .resizable()
                    .scaledToFit()
                    .frame(maxWidth: .infinity)
                    .frame(height: 340)
            default:
                Color(.secondarySystemBackground)
                    .frame(height: 340)
                    .overlay(
                        Image(systemName: "tshirt")
                            .font(.system(size: 60))
                            .foregroundColor(.secondary)
                    )
            }
        }
        .frame(maxWidth: .infinity)
        .background(Color(.secondarySystemBackground))
    }

    private var titleSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let brand = product.brand {
                Text(brand.uppercased())
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(.indigo)
                    .tracking(1)
            }
            Text(product.title)
                .font(.title3)
                .fontWeight(.semibold)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var priceSection: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(product.formattedPrice)
                .font(.system(size: 32, weight: .bold, design: .rounded))
                .foregroundStyle(
                    LinearGradient(colors: [.indigo, .purple], startPoint: .leading, endPoint: .trailing)
                )

            if let original = product.formattedOriginalPrice {
                Text(original)
                    .font(.title3)
                    .strikethrough()
                    .foregroundColor(.secondary)
            }

            if let pct = product.discountPercentage {
                Spacer()
                Text("Save \(pct)%")
                    .font(.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.red)
                    .clipShape(Capsule())
            }
        }
    }

    private var storeSection: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(.tertiarySystemGroupedBackground))
                    .frame(width: 44, height: 44)
                Text(String(product.storeName.prefix(1)))
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(.indigo)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(product.storeName)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text(product.availability.rawValue)
                    .font(.caption)
                    .foregroundColor(product.availability == .inStock ? .green : .orange)
            }
            Spacer()
        }
        .padding(12)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func ratingSection(_ rating: Double) -> some View {
        HStack(spacing: 10) {
            StarRatingView(rating: rating, count: product.reviewCount)
            Text(String(format: "%.1f", rating))
                .font(.subheadline)
                .fontWeight(.semibold)
            Spacer()
        }
    }

    private var matchSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Match Info", systemImage: "sparkles")
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)

            HStack(spacing: 10) {
                MatchBadge(
                    label: product.matchType.rawValue,
                    icon: "checkmark.circle.fill",
                    color: product.matchType == .exact ? .green : .indigo
                )
                MatchBadge(
                    label: "\(Int(product.similarity * 100))% Similar",
                    icon: "slider.horizontal.3",
                    color: .purple
                )
            }
        }
    }

    private var shippingSection: some View {
        Group {
            if let shipping = product.shipping {
                HStack(spacing: 8) {
                    Image(systemName: "shippingbox.fill")
                        .foregroundColor(.green)
                    Text(shipping)
                        .font(.subheadline)
                        .foregroundColor(.green)
                }
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.green.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
        }
    }

    private var actionButtons: some View {
        VStack(spacing: 12) {
            // Primary buy button
            Button {
                showSafari = true
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "cart.fill")
                    Text("Buy on \(product.storeName)")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(
                    LinearGradient(colors: [.indigo, .purple], startPoint: .leading, endPoint: .trailing)
                )
                .foregroundColor(.white)
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .shadow(color: .indigo.opacity(0.3), radius: 8, y: 4)
            }

            // Wishlist toggle
            Button {
                withAnimation(.spring(response: 0.3)) {
                    wishlistVM.toggle(product: product, clothingItem: clothingItem)
                }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: isSaved ? "heart.fill" : "heart")
                    Text(isSaved ? "Saved to Wishlist" : "Save to Wishlist")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(Color(.secondarySystemGroupedBackground))
                .foregroundColor(isSaved ? .red : .indigo)
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(isSaved ? Color.red.opacity(0.3) : Color.indigo.opacity(0.3), lineWidth: 1.5)
                )
            }
        }
    }
}

// MARK: - MatchBadge

struct MatchBadge: View {
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
            .background(color.opacity(0.1))
            .clipShape(Capsule())
    }
}

// MARK: - SafariView

struct SafariView: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        SFSafariViewController(url: url)
    }

    func updateUIViewController(_ vc: SFSafariViewController, context: Context) {}
}
