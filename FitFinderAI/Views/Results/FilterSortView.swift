import SwiftUI

// MARK: - FilterSortView

struct FilterSortView: View {
    @Binding var filter: SearchFilter
    let stores: [String]

    @Environment(\.dismiss) private var dismiss
    @State private var localFilter: SearchFilter

    init(filter: Binding<SearchFilter>, stores: [String]) {
        _filter = filter
        self.stores = stores
        _localFilter = State(initialValue: filter.wrappedValue)
    }

    var body: some View {
        NavigationStack {
            List {
                // Sort section
                Section {
                    ForEach(SortOption.allCases) { option in
                        Button {
                            localFilter.sortOption = option
                        } label: {
                            HStack {
                                Label(option.rawValue, systemImage: option.systemIcon)
                                    .foregroundColor(.primary)
                                Spacer()
                                if localFilter.sortOption == option {
                                    Image(systemName: "checkmark")
                                        .foregroundColor(.indigo)
                                        .fontWeight(.bold)
                                }
                            }
                        }
                    }
                } header: {
                    Text("Sort By")
                }

                // Match type section
                Section {
                    ForEach(MatchFilter.allCases) { matchFilter in
                        Button {
                            localFilter.matchFilter = matchFilter
                        } label: {
                            HStack {
                                Text(matchFilter.rawValue)
                                    .foregroundColor(.primary)
                                Spacer()
                                if localFilter.matchFilter == matchFilter {
                                    Image(systemName: "checkmark")
                                        .foregroundColor(.indigo)
                                        .fontWeight(.bold)
                                }
                            }
                        }
                    }
                } header: {
                    Text("Match Type")
                }

                // Price range section
                Section {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text("Max Price")
                                .font(.subheadline)
                            Spacer()
                            if let max = localFilter.maxPrice {
                                Text("$\(Int(max))")
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(.indigo)
                            } else {
                                Text("Any")
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                            }
                        }

                        Slider(
                            value: Binding(
                                get: { localFilter.maxPrice ?? 500 },
                                set: { localFilter.maxPrice = $0 < 500 ? $0 : nil }
                            ),
                            in: 10...500,
                            step: 10
                        )
                        .tint(.indigo)

                        Text("Drag left to set a price cap")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.vertical, 4)
                } header: {
                    Text("Price Range")
                }

                // Stores section
                if !stores.isEmpty {
                    Section {
                        ForEach(stores, id: \.self) { store in
                            Button {
                                if localFilter.selectedStores.contains(store) {
                                    localFilter.selectedStores.remove(store)
                                } else {
                                    localFilter.selectedStores.insert(store)
                                }
                            } label: {
                                HStack {
                                    Text(store)
                                        .foregroundColor(.primary)
                                    Spacer()
                                    if localFilter.selectedStores.contains(store) {
                                        Image(systemName: "checkmark")
                                            .foregroundColor(.indigo)
                                            .fontWeight(.bold)
                                    }
                                }
                            }
                        }
                    } header: {
                        Text("Stores (\(localFilter.selectedStores.isEmpty ? "All" : "\(localFilter.selectedStores.count) selected"))")
                    }
                }

                // Toggles section
                Section {
                    Toggle("On Sale Only", isOn: $localFilter.showOnSaleOnly)
                        .tint(.indigo)
                    Toggle("In Stock Only", isOn: $localFilter.showInStockOnly)
                        .tint(.indigo)
                } header: {
                    Text("Availability")
                }
            }
            .navigationTitle("Filter & Sort")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Reset") {
                        localFilter.reset()
                    }
                    .foregroundColor(.orange)
                    .disabled(localFilter.isDefault)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Apply") {
                        filter = localFilter
                        dismiss()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
    }
}
