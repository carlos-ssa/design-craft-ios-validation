import Foundation
import Combine

struct Note: Codable, Identifiable, Equatable {
    var id: UUID
    var title: String
    var body: String
}

struct NoteDraft: Codable, Equatable {
    var id: UUID
    var title: String
    var body: String
    var isNew: Bool
}

private struct NotesEnvelope: Codable {
    var notes: [Note] = []
    var draft: NoteDraft? = nil

    var isValid: Bool {
        let ids = Set(notes.map(\.id))
        guard ids.count == notes.count else { return false }
        guard let draft = draft else { return true }
        return draft.isNew ? !ids.contains(draft.id) : ids.contains(draft.id)
    }
}

final class NotesStore: ObservableObject {
    @Published private(set) var notes: [Note] = []
    @Published private(set) var draft: NoteDraft?
    @Published private(set) var error: String?
    private let url: URL
    private var blocked = false

    init(url: URL) {
        self.url = url
        guard FileManager.default.fileExists(atPath: url.path) else { return }
        do {
            let envelope = try JSONDecoder().decode(NotesEnvelope.self, from: Data(contentsOf: url))
            guard envelope.isValid else {
                blocked = true
                self.error = "Não foi possível ler as notas. O arquivo original foi preservado."
                return
            }
            notes = envelope.notes
            draft = envelope.draft
        } catch {
            blocked = true
            self.error = "Não foi possível ler as notas. O arquivo original foi preservado."
        }
    }

    static func defaultURL() -> URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("NotasFixture", isDirectory: true)
            .appendingPathComponent("notes.json")
    }

    private func commit(notes: [Note], draft: NoteDraft?) -> Bool {
        guard !blocked else { return false }
        do {
            let data = try JSONEncoder().encode(NotesEnvelope(notes: notes, draft: draft))
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: url, options: .atomic)
            self.notes = notes
            self.draft = draft
            error = nil
            return true
        } catch {
            self.error = "Não foi possível gravar. Tente novamente; suas alterações continuam na tela."
            return false
        }
    }

    @discardableResult func beginNew() -> Bool {
        guard draft == nil else { return false }
        return commit(notes: notes, draft: NoteDraft(id: UUID(), title: "", body: "", isNew: true))
    }

    @discardableResult func beginEdit(_ note: Note) -> Bool {
        guard draft == nil, notes.contains(where: { $0.id == note.id }) else { return false }
        return commit(notes: notes, draft: NoteDraft(id: note.id, title: note.title, body: note.body, isNew: false))
    }

    @discardableResult func updateDraft(_ value: NoteDraft) -> Bool {
        guard let current = draft, current.id == value.id, current.isNew == value.isNew else { return false }
        return commit(notes: notes, draft: value)
    }

    static func validationMessage(title: String, body: String) -> String? {
        if title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return "Informe um título." }
        if body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return "Escreva o conteúdo da nota." }
        return nil
    }

    @discardableResult func save(_ value: NoteDraft) -> Bool {
        guard let current = draft, current.id == value.id, current.isNew == value.isNew else { return false }
        if let message = Self.validationMessage(title: value.title, body: value.body) {
            error = message
            return false
        }
        var updated = notes
        let note = Note(id: value.id, title: value.title.trimmingCharacters(in: .whitespacesAndNewlines), body: value.body)
        if value.isNew {
            guard !updated.contains(where: { $0.id == value.id }) else { return false }
            updated.append(note)
        } else {
            guard let index = updated.firstIndex(where: { $0.id == value.id }) else { return false }
            updated[index] = note
        }
        return commit(notes: updated, draft: nil)
    }

    @discardableResult func discard() -> Bool { commit(notes: notes, draft: nil) }
}

