import SwiftUI

struct HomeView: View {
    @EnvironmentObject var mainVM: MainViewModel
    @EnvironmentObject var wishlistVM: WishlistViewModel

    var body: some View {
        NavigationStack {
            ZStack {
                background

                ScrollView {
                    VStack(spacing: 28) {
                        headerSection
                        capturedImageSection
                        actionButtons
                        keywordInputSection
                        if !APIConfiguration.isConfigured {
                            configWarningBanner
                        }
                        recentSection
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 8)
                    .padding(.bottom, 40)
                }
            }
            .navigationTitle("")
            .navigationBarHidden(true)
            .sheet(isPresented: $mainVM.showCamera) {
                CameraView(onCapture: { image in
                    mainVM.handleImage(image)
                })
                .ignoresSafeArea()
            }
            .sheet(isPresented: $mainVM.showImagePicker) {
                ImagePickerView(onSelect: { image in
                    mainVM.handleImage(image)
                })
            }
            .overlay {
                if mainVM.appState == .analyzing || mainVM.appState == .searching {
                    AnalysisOverlayView(
                        state: mainVM.appState,
                        progress: mainVM.analysisProgress,
                        image: mainVM.capturedImage
                    )
                }
            }
            .alert("Something went wrong", isPresented: .constant(mainVM.errorMessage != nil)) {
                Button("Try Again") { mainVM.startOver() }
                Button("Dismiss", role: .cancel) { mainVM.errorMessage = nil }
            } message: {
                Text(mainVM.errorMessage ?? "")
            }
        }
    }

    // MARK: - Subviews

    private var background: some View {
        LinearGradient(
            colors: [
                Color(.systemBackground),
                Color.indigo.opacity(0.04)
            ],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("FitFinder AI")
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                        .foregroundStyle(
                            LinearGradient(colors: [.indigo, .purple], startPoint: .leading, endPoint: .trailing)
                        )
                    Text("Snap a look, find it instantly")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                Spacer()
                Image(systemName: "tshirt.fill")
                    .font(.system(size: 36))
                    .foregroundStyle(LinearGradient(colors: [.indigo, .purple], startPoint: .top, endPoint: .bottom))
            }
        }
        .padding(.top, 20)
    }

    @ViewBuilder
    private var capturedImageSection: some View {
        if let image = mainVM.capturedImage {
            ZStack(alignment: .topTrailing) {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(maxWidth: .infinity)
                    .frame(height: 260)
                    .clipShape(RoundedRectangle(cornerRadius: 20))
                    .shadow(color: .black.opacity(0.15), radius: 10, y: 5)

                Button {
                    mainVM.startOver()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title2)
                        .foregroundStyle(.white, .black.opacity(0.6))
                        .padding(12)
                }
            }
        }
    }

    private var actionButtons: some View {
        HStack(spacing: 14) {
            // Camera button
            Button {
                mainVM.showCamera = true
            } label: {
                VStack(spacing: 8) {
                    ZStack {
                        Circle()
                            .fill(
                                LinearGradient(colors: [.indigo, .purple], startPoint: .topLeading, endPoint: .bottomTrailing)
                            )
                            .frame(width: 68, height: 68)
                            .shadow(color: .indigo.opacity(0.4), radius: 10, y: 5)
                        Image(systemName: "camera.fill")
                            .font(.title2)
                            .foregroundColor(.white)
                    }
                    Text("Camera")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.primary)
                }
            }
            .buttonStyle(.plain)

            Spacer()

            // Gallery button
            Button {
                mainVM.showImagePicker = true
            } label: {
                VStack(spacing: 8) {
                    ZStack {
                        Circle()
                            .fill(Color(.secondarySystemBackground))
                            .frame(width: 68, height: 68)
                            .shadow(color: .black.opacity(0.08), radius: 8, y: 4)
                        Image(systemName: "photo.on.rectangle.angled")
                            .font(.title2)
                            .foregroundColor(.indigo)
                    }
                    Text("Gallery")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.primary)
                }
            }
            .buttonStyle(.plain)

            Spacer()

            // Barcode button
            Button {
                mainVM.showCamera = true   // CameraView handles barcode mode internally
            } label: {
                VStack(spacing: 8) {
                    ZStack {
                        Circle()
                            .fill(Color(.secondarySystemBackground))
                            .frame(width: 68, height: 68)
                            .shadow(color: .black.opacity(0.08), radius: 8, y: 4)
                        Image(systemName: "barcode.viewfinder")
                            .font(.title2)
                            .foregroundColor(.indigo)
                    }
                    Text("Barcode")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.primary)
                }
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 8)
    }

    private var keywordInputSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Add keywords (optional)", systemImage: "text.cursor")
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)

            HStack(spacing: 10) {
                TextField("Brand, style, color…", text: $mainVM.manualKeywords)
                    .textFieldStyle(.plain)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))

                if !mainVM.manualKeywords.isEmpty {
                    Button {
                        mainVM.retryWithKeywords()
                    } label: {
                        Image(systemName: "arrow.right.circle.fill")
                            .font(.title2)
                            .foregroundStyle(
                                LinearGradient(colors: [.indigo, .purple], startPoint: .top, endPoint: .bottom)
                            )
                    }
                }
            }
        }
    }

    private var configWarningBanner: some View {
        HStack(spacing: 12) {
            Image(systemName: "key.fill")
                .foregroundColor(.orange)
            VStack(alignment: .leading, spacing: 2) {
                Text("API Keys Not Configured")
                    .font(.caption)
                    .fontWeight(.semibold)
                Text("Add keys in APIConfiguration.swift for live results")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            Spacer()
        }
        .padding(12)
        .background(Color.orange.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.orange.opacity(0.3), lineWidth: 1)
        )
    }

    @ViewBuilder
    private var recentSection: some View {
        if !wishlistVM.items.isEmpty {
            VStack(alignment: .leading, spacing: 14) {
                Text("Recently Saved")
                    .font(.headline)
                    .fontWeight(.bold)

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(wishlistVM.items.prefix(5)) { item in
                            MiniProductCard(product: item.product)
                        }
                    }
                    .padding(.horizontal, 2)
                }
            }
        } else {
            // Tip cards
            VStack(alignment: .leading, spacing: 14) {
                Text("How it works")
                    .font(.headline)
                    .fontWeight(.bold)

                ForEach(tips) { tip in
                    TipRow(tip: tip)
                }
            }
        }
    }

    // MARK: - Tips

    struct Tip: Identifiable {
        let id = UUID()
        let icon: String
        let color: Color
        let title: String
        let body: String
    }

    let tips: [Tip] = [
        Tip(icon: "camera.fill",         color: .indigo, title: "Snap a photo",     body: "Point camera at any clothing item"),
        Tip(icon: "sparkles",            color: .purple, title: "AI identifies it",  body: "Claude Vision recognizes style, color & brand"),
        Tip(icon: "magnifyingglass",     color: .blue,   title: "Find it online",    body: "Searches hundreds of stores instantly"),
        Tip(icon: "tag.fill",            color: .green,  title: "Best price wins",   body: "Compare prices and discover cheaper alternatives")
    ]
}

// MARK: - TipRow

struct TipRow: View {
    let tip: HomeView.Tip

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(tip.color.opacity(0.15))
                    .frame(width: 42, height: 42)
                Image(systemName: tip.icon)
                    .foregroundColor(tip.color)
                    .font(.system(size: 18, weight: .semibold))
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(tip.title)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text(tip.body)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
        }
        .padding(12)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

// MARK: - MiniProductCard

struct MiniProductCard: View {
    let product: ProductResult

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            AsyncImage(url: URL(string: product.imageURL)) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().scaledToFill()
                default:
                    Color(.tertiarySystemBackground)
                        .overlay(Image(systemName: "tshirt").foregroundColor(.secondary))
                }
            }
            .frame(width: 100, height: 100)
            .clipShape(RoundedRectangle(cornerRadius: 12))

            Text(product.formattedPrice)
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(.indigo)

            Text(product.title)
                .font(.caption2)
                .foregroundColor(.secondary)
                .lineLimit(2)
                .frame(width: 100, alignment: .leading)
        }
        .frame(width: 100)
    }
}

#Preview {
    HomeView()
        .environmentObject(MainViewModel())
        .environmentObject(WishlistViewModel())
}
