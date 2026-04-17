import SwiftUI

// MARK: - AnalysisOverlayView

struct AnalysisOverlayView: View {
    let state: AppState
    let progress: Double
    let image: UIImage?

    @State private var pulseScale: CGFloat = 1.0
    @State private var shimmerOffset: CGFloat = -200

    var body: some View {
        ZStack {
            // Blurred background
            Color.black.opacity(0.55)
                .ignoresSafeArea()
                .background(.ultraThinMaterial)

            VStack(spacing: 28) {
                // Captured image thumbnail
                if let image {
                    ZStack {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFill()
                            .frame(width: 130, height: 150)
                            .clipShape(RoundedRectangle(cornerRadius: 18))
                            .shadow(color: .black.opacity(0.3), radius: 12)

                        // Scan line shimmer
                        RoundedRectangle(cornerRadius: 18)
                            .fill(
                                LinearGradient(
                                    colors: [.clear, .white.opacity(0.25), .clear],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )
                            .frame(width: 130, height: 40)
                            .offset(y: shimmerOffset)
                            .clipShape(RoundedRectangle(cornerRadius: 18))
                            .onAppear {
                                withAnimation(.linear(duration: 1.5).repeatForever(autoreverses: false)) {
                                    shimmerOffset = 200
                                }
                            }

                        // Scan corners
                        ScanCorners()
                            .stroke(Color.indigo, lineWidth: 2.5)
                            .frame(width: 134, height: 154)
                    }
                }

                // Status message
                VStack(spacing: 10) {
                    Text(statusTitle)
                        .font(.headline)
                        .fontWeight(.bold)
                        .foregroundColor(.white)

                    Text(statusSubtitle)
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.7))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 30)
                }

                // Progress bar
                VStack(spacing: 8) {
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Capsule()
                                .fill(Color.white.opacity(0.2))
                                .frame(height: 6)
                            Capsule()
                                .fill(
                                    LinearGradient(colors: [.indigo, .purple], startPoint: .leading, endPoint: .trailing)
                                )
                                .frame(width: geo.size.width * progress, height: 6)
                                .animation(.easeInOut(duration: 0.4), value: progress)
                        }
                    }
                    .frame(height: 6)
                    .frame(maxWidth: 200)

                    Text("\(Int(progress * 100))%")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.6))
                }

                // Animated dots
                dotsRow
            }
            .padding(32)
        }
    }

    // MARK: - Computed

    private var statusTitle: String {
        switch state {
        case .analyzing: return "Identifying Clothing"
        case .searching: return "Searching Stores"
        default:         return "Processing…"
        }
    }

    private var statusSubtitle: String {
        switch state {
        case .analyzing: return "Claude AI is examining the style,\ncolor, and brand details"
        case .searching: return "Finding exact matches and\ncheaper alternatives for you"
        default:         return "Please wait"
        }
    }

    private var dotsRow: some View {
        HStack(spacing: 6) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(Color.white.opacity(0.5))
                    .frame(width: 8, height: 8)
                    .scaleEffect(pulseScale)
                    .animation(
                        .easeInOut(duration: 0.6)
                            .repeatForever(autoreverses: true)
                            .delay(Double(i) * 0.2),
                        value: pulseScale
                    )
            }
        }
        .onAppear { pulseScale = 1.4 }
    }
}

// MARK: - ScanCorners

struct ScanCorners: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let cornerLen: CGFloat = 22
        let r: CGFloat = 8

        // Top-left
        path.move(to: CGPoint(x: rect.minX + r, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.minX + cornerLen, y: rect.minY))
        path.move(to: CGPoint(x: rect.minX, y: rect.minY + r))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.minY + cornerLen))

        // Top-right
        path.move(to: CGPoint(x: rect.maxX - cornerLen, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX - r, y: rect.minY))
        path.move(to: CGPoint(x: rect.maxX, y: rect.minY + r))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.minY + cornerLen))

        // Bottom-left
        path.move(to: CGPoint(x: rect.minX, y: rect.maxY - cornerLen))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY - r))
        path.move(to: CGPoint(x: rect.minX + r, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.minX + cornerLen, y: rect.maxY))

        // Bottom-right
        path.move(to: CGPoint(x: rect.maxX - cornerLen, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.maxX - r, y: rect.maxY))
        path.move(to: CGPoint(x: rect.maxX, y: rect.maxY - cornerLen))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY - r))

        return path
    }
}
