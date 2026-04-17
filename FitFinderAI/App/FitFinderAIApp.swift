import SwiftUI

@main
struct FitFinderAIApp: App {

    @StateObject private var mainViewModel   = MainViewModel()
    @StateObject private var wishlistViewModel = WishlistViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(mainViewModel)
                .environmentObject(wishlistViewModel)
        }
    }
}
