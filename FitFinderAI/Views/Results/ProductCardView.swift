import SwiftUI

// MARK: - ProductCardView (full width list card)

struct ProductCardView: View {
    let product: ProductResult
    let clothingItem: ClothingItem?

    @EnvironmentObject var wishlistVM: WishlistViewModel

    var isSaved: Bool { wishlistVM.isSaved(productURL: product.purchaseURL) }

    var body: some View {
        HStack(spacing: 12) {
            // Product image
            AsyncImage(url: URL(string: product.imageURL)) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    fallbackImage
                case .empty:
                    ProgressView()
                @unknown default:
                    fallbackImage
                }
            }
            .frame(width: 90, height: 100)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color(.separator), lineWidth: 0.5)
            )

            // Info
            VStack(alignment: .leading, spacing: 5) {
                // Title
                Text(product.title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                // Store + brand
                HStack(spacing: 4) {
                    Text(product.storeName)
                        .font(.caption)
                        .foregroundColor(.secondary)
                    if let brand = product.brand {
                        Text("• \(brand)")
                            .font(.caption)
                            .foregroundColor(.indigo)
                            .fontWeight(.medium)
                    }
                }

                // Rating
                if let rating = product.rating {
                    StarRatingView(rating: rating, count: product.reviewCount)
                }

                Spacer(minLength: 0)

                // Price row
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text(product.formattedPrice)
                        .font(.system(.headline, design: .rounded))
                        .fontWeight(.bold)
                        .foregroundColor(.primary)

                    if let original = product.formattedOriginalPrice {
                        Text(original)
                            .font(.caption)
                            .strikethrough()
                            .foregroundColor(.secondary)
                    }

                    if let pct = product.discountPercentage {
                        Text("-\(pct)%")
                            .font(.caption2)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 2)
                            .background(Color.red)
                            .clipShape(Capsule())
                    }

                    Spacer()

                    // Availability badge
                    availabilityBadge
                }

                // Shipping
                if let shipping = product.shipping {
                    Label(shipping, systemImage: "shippingbox")
                        .font(.caption2)
                        .foregroundColor(.green)
                }
            }

            // Heart button
            VStack {
                wishlistButton
                Spacer()
            }
        }
        .padding(12)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }

    private var fallbackImage: some View {
        ZStack {
            Color(.tertiarySystemGroupedBackground)
            Image(systemName: "tshirt")
                .font(.largeTitle)
                .foregroundColor(.secondary)
        }
    }

    private var availabilityBadge: some View {
        Group {
            switch product.availability {
            case .inStock:
                EmptyView()
            case .limitedStock:
                Text("Low stock")
                    .font(.caption2)
                    .foregroundColor(.orange)
            case .outOfStock:
                Text("Out of stock")
                    .font(.caption2)
                    .foregroundColor(.red)
            case .unknown:
                EmptyView()
            }
        }
    }

    private var wishlistButton: some View {
        Button {
            withAnimation(.spring(response: 0.3)) {
                wishlistVM.toggle(product: product, clothingItem: clothingItem)
            }
        } label: {
            Image(systemName: isSaved ? "heart.fill" : "heart")
                .font(.title3)
                .foregroundColor(isSaved ? .red : .secondary)
                .scaleEffect(isSaved ? 1.1 : 1.0)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - CompactProductCard (for horizontal scroll)

struct CompactProductCard: View {
    let product: ProductResult
    @EnvironmentObject var wishlistVM: WishlistViewModel

    var isSaved: Bool { wishlistVM.isSaved(productURL: product.purchaseURL) }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack(alignment: .topTrailing) {
                AsyncImage(url: URL(string: product.imageURL)) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().scaledToFill()
                    default:
                        Color(.tertiarySystemGroupedBackground)
                            .overlay(Image(systemName: "tshirt").foregroundColor(.secondary))
                    }
                }
                .frame(width: 130, height: 150)
                .clipShape(RoundedRectangle(cornerRadius: 14))

                Button {
                    withAnimation(.spring(response: 0.3)) {
                        wishlistVM.toggle(product: product)
                    }
                } label: {
                    Image(systemName: isSaved ? "heart.fill" : "heart")
                        .font(.subheadline)
                        .foregroundColor(isSaved ? .red : .white)
                        .padding(7)
                        .background(.ultraThinMaterial)
                        .clipShape(Circle())
                        .padding(6)
                }
                .buttonStyle(.plain)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(product.formattedPrice)
                    .font(.system(.subheadline, design: .rounded))
                    .fontWeight(.bold)
                    .foregroundColor(.indigo)

                Text(product.storeName)
                    .font(.caption2)
                    .foregroundColor(.secondary)

                Text(product.title)
                    .font(.caption2)
                    .foregroundColor(.primary)
                    .lineLimit(2)
                    .frame(width: 130, alignment: .leading)
            }
        }
        .frame(width: 130)
    }
}

// MARK: - StarRatingView

struct StarRatingView: View {
    let rating: Double
    let count: Int?

    var body: some View {
        HStack(spacing: 3) {
            ForEach(0..<5, id: \.self) { index in
                Image(systemName: starIcon(for: index))
                    .font(.system(size: 10))
                    .foregroundColor(.orange)
            }
            if let count = count {
                Text("(\(count))")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
    }

    private func starIcon(for index: Int) -> String {
        let threshold = Double(index) + 1
        if rating >= threshold {
            return "star.fill"
        } else if rating >= threshold - 0.5 {
            return "star.leadinghalf.filled"
        } else {
            return "star"
        }
    }
}
