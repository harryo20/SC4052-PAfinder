import SwiftUI

struct ContentView: View {
    @EnvironmentObject var mainVM: MainViewModel
    @EnvironmentObject var wishlistVM: WishlistViewModel
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem {
                    Label("Scan", systemImage: "camera.viewfinder")
                }
                .tag(0)

            WishlistView()
                .tabItem {
                    Label("Wishlist", systemImage: "heart.fill")
                }
                .badge(wishlistVM.items.isEmpty ? 0 : wishlistVM.items.count)
                .tag(1)
        }
        .tint(.indigo)
        .fullScreenCover(isPresented: $mainVM.showResults) {
            ResultsView()
                .environmentObject(mainVM)
                .environmentObject(mainVM.searchViewModel)
                .environmentObject(wishlistVM)
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(MainViewModel())
        .environmentObject(WishlistViewModel())
}
