import SwiftUI

// MARK: - EmptyStateView

struct EmptyStateView: View {
    let icon: String
    let title: String
    let body: String
    var action: (() -> Void)? = nil
    var actionLabel: String = "Try Again"

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: icon)
                .font(.system(size: 56))
                .foregroundStyle(
                    LinearGradient(colors: [.indigo.opacity(0.5), .purple.opacity(0.5)], startPoint: .top, endPoint: .bottom)
                )

            VStack(spacing: 8) {
                Text(title)
                    .font(.headline)
                    .fontWeight(.semibold)
                Text(body)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            if let action {
                Button(action: action) {
                    Text(actionLabel)
                        .fontWeight(.semibold)
                        .padding(.horizontal, 24)
                        .padding(.vertical, 12)
                        .background(
                            LinearGradient(colors: [.indigo, .purple], startPoint: .leading, endPoint: .trailing)
                        )
                        .foregroundColor(.white)
                        .clipShape(Capsule())
                }
                .padding(.top, 4)
            }
        }
        .padding(32)
        .frame(maxWidth: .infinity)
    }
}
