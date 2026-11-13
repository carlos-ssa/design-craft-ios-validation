import SwiftUI

private let noteActionTint = Color(uiColor: UIColor { traits in
    traits.userInterfaceStyle == .dark
        ? UIColor(red: 0.44, green: 0.72, blue: 1, alpha: 1)
        : UIColor(red: 0, green: 0.35, blue: 0.78, alpha: 1)
})

@main
struct NotasApp: App {
    @StateObject private var store: NotesStore
    private let largeType: Bool

    init() {
        let args = ProcessInfo.processInfo.arguments
        let url = NotesStore.defaultURL()
        if args.contains("--uitesting") && args.contains("--fixture-reset") {
            try? FileManager.default.removeItem(at: url)
        }
        _store = StateObject(wrappedValue: NotesStore(url: url))
        largeType = args.contains("--uitesting") && args.contains("--fixture-large-type")
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if largeType {
                    NotesHome(store: store).dynamicTypeSize(.accessibility3)
                } else {
                    NotesHome(store: store)
                }
            }
            .tint(noteActionTint)
        }
    }
}

private struct NotesHome: View {
    @ObservedObject var store: NotesStore
    @State private var editorVisible = false

    var body: some View {
        NavigationStack {
            List {
                if let error = store.error {
                    Text(error).foregroundStyle(.primary).accessibilityIdentifier("notes.status")
                }
                if store.notes.isEmpty {
                    ContentUnavailableView("Nenhuma nota", systemImage: "note.text", description: Text("Crie uma nota para começar.").foregroundStyle(.primary))
                }
                ForEach(store.notes) { note in
                    Button {
                        if store.beginEdit(note) { editorVisible = true }
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(note.title).font(.headline)
                            Text(note.body).font(.subheadline).foregroundStyle(.primary).lineLimit(2)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(note.title)
                    .accessibilityValue(note.body)
                    .accessibilityIdentifier("notes.row.\(note.id.uuidString)")
                }
            }
            .navigationTitle("Notas de trabalho")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Nova nota", systemImage: "plus") {
                        if store.beginNew() { editorVisible = true }
                    }.accessibilityIdentifier("notes.new")
                }
            }
            .onAppear { if store.draft != nil { editorVisible = true } }
            .sheet(isPresented: $editorVisible) {
                if let draft = store.draft {
                    NoteEditor(store: store, initialDraft: draft, visible: $editorVisible)
                        .interactiveDismissDisabled()
                }
            }
        }
    }
}

private struct NoteEditor: View {
    @ObservedObject var store: NotesStore
    @State private var draft: NoteDraft
    @State private var confirmDiscard = false
    @Binding var visible: Bool

    init(store: NotesStore, initialDraft: NoteDraft, visible: Binding<Bool>) {
        self.store = store
        _draft = State(initialValue: initialDraft)
        _visible = visible
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("", text: $draft.title)
                        .accessibilityLabel("Título")
                        .accessibilityIdentifier("notes.title")
                } header: {
                    Text("Título").foregroundStyle(.primary)
                }
                Section {
                    TextEditor(text: $draft.body)
                        .frame(minHeight: 150)
                        .accessibilityLabel("Conteúdo")
                        .accessibilityIdentifier("notes.body")
                } header: {
                    Text("Conteúdo").foregroundStyle(.primary)
                }
                if let error = store.error {
                    Section { Text(error).accessibilityIdentifier("notes.status") }
                }
            }
            .navigationTitle(draft.isNew ? "Nova nota" : "Editar nota")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar") { confirmDiscard = true }.accessibilityIdentifier("notes.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Salvar") { if store.save(draft) { visible = false } }
                        .accessibilityIdentifier("notes.save")
                }
            }
            .onChange(of: draft) { _, value in _ = store.updateDraft(value) }
            .confirmationDialog("Descartar alterações?", isPresented: $confirmDiscard, titleVisibility: .visible) {
                Button("Descartar", role: .destructive) {
                    if store.discard() { visible = false }
                }.accessibilityIdentifier("notes.discard")
                Button("Continuar editando", role: .cancel) { }
            } message: { Text("O rascunho será apagado.") }
        }
    }
}

