import XCTest
@testable import Notas

final class NotesStoreTests: XCTestCase {
    private var directory: URL!
    private var url: URL { directory.appendingPathComponent("notes.json") }

    override func setUpWithError() throws {
        directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    }
    override func tearDownWithError() throws { try FileManager.default.removeItem(at: directory) }

    func testAddEditAndReload() throws {
        let store = NotesStore(url: url)
        XCTAssertTrue(store.beginNew())
        var draft = try XCTUnwrap(store.draft)
        draft.title = " Planejamento "
        draft.body = "Próximos passos"
        XCTAssertTrue(store.save(draft))
        let reloaded = NotesStore(url: url)
        XCTAssertEqual(reloaded.notes.first?.title, "Planejamento")
        let note = try XCTUnwrap(reloaded.notes.first)
        XCTAssertTrue(reloaded.beginEdit(note))
        var edit = try XCTUnwrap(reloaded.draft)
        edit.body = "Revisado"
        XCTAssertTrue(reloaded.save(edit))
        XCTAssertEqual(NotesStore(url: url).notes, [Note(id: note.id, title: "Planejamento", body: "Revisado")])
    }

    func testInvalidJSONIsPreservedAndBlocksWrites() throws {
        let bytes = Data("{broken".utf8)
        try bytes.write(to: url)
        let store = NotesStore(url: url)
        XCTAssertNotNil(store.error)
        XCTAssertFalse(store.beginNew())
        XCTAssertFalse(store.discard())
        XCTAssertEqual(try Data(contentsOf: url), bytes)
    }

    func testSemanticallyInvalidEnvelopesArePreservedAndBlockWrites() throws {
        let id = UUID().uuidString
        let other = UUID().uuidString
        let note = "{\"id\":\"\(id)\",\"title\":\"A\",\"body\":\"B\"}"
        let invalid = [
            "{\"notes\":[\(note),\(note)]}",
            "{\"notes\":[\(note)],\"draft\":{\"id\":\"\(id)\",\"title\":\"A\",\"body\":\"B\",\"isNew\":true}}",
            "{\"notes\":[\(note)],\"draft\":{\"id\":\"\(other)\",\"title\":\"A\",\"body\":\"B\",\"isNew\":false}}"
        ]
        for json in invalid {
            let bytes = Data(json.utf8)
            try bytes.write(to: url)
            let store = NotesStore(url: url)
            XCTAssertNotNil(store.error)
            XCTAssertFalse(store.beginNew())
            XCTAssertFalse(store.discard())
            XCTAssertEqual(try Data(contentsOf: url), bytes)
        }
    }

    func testValidationAndRepeatedSaveDoNotDuplicate() throws {
        let store = NotesStore(url: url)
        XCTAssertTrue(store.beginNew())
        var draft = try XCTUnwrap(store.draft)
        XCTAssertFalse(store.save(draft))
        XCTAssertEqual(store.error, "Informe um título.")
        draft.title = "Título"
        XCTAssertFalse(store.save(draft))
        XCTAssertEqual(store.error, "Escreva o conteúdo da nota.")
        draft.body = "Conteúdo"
        XCTAssertTrue(store.save(draft))
        XCTAssertFalse(store.save(draft))
        XCTAssertEqual(NotesStore(url: url).notes.count, 1)
    }

    func testDraftSurvivesReloadAndDiscardPreservesNotes() throws {
        let store = NotesStore(url: url)
        XCTAssertTrue(store.beginNew())
        var draft = try XCTUnwrap(store.draft)
        draft.title = "Rascunho"
        XCTAssertTrue(store.updateDraft(draft))
        let restored = NotesStore(url: url)
        XCTAssertEqual(restored.draft, draft)
        XCTAssertTrue(restored.discard())
        XCTAssertNil(NotesStore(url: url).draft)
    }
}
