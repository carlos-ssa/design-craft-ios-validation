import XCTest

final class NotasUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--uitesting", "--fixture-reset"]
        app.launch()
    }

    private var rows: XCUIElementQuery {
        app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "notes.row."))
    }

    private func assertRow(title: String, body: String) {
        let row = rows.firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(row.label, title)
        XCTAssertEqual(row.value as? String, body)
    }

    private func createNote() {
        app.buttons["notes.new"].tap()
        let title = app.textFields["notes.title"]
        XCTAssertTrue(title.waitForExistence(timeout: 5))
        title.tap(); title.typeText("Reunião")
        let body = app.textViews["notes.body"]
        body.tap(); body.typeText("Próximos passos")
        app.buttons["notes.save"].tap()
    }

    func testCreatePersistsAcrossRelaunch() {
        createNote()
        assertRow(title: "Reunião", body: "Próximos passos")
        app.terminate()
        app.launchArguments = ["--uitesting"]
        app.launch()
        assertRow(title: "Reunião", body: "Próximos passos")
    }

    func testEditNote() {
        createNote()
        rows.firstMatch.tap()
        let body = app.textViews["notes.body"]
        body.tap(); body.typeText(" atualizado")
        app.buttons["notes.save"].tap()
        let row = rows.firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(row.label, "Reunião")
        XCTAssertTrue((row.value as? String ?? "").contains("atualizado"))
    }

    func testValidationRecovery() {
        app.buttons["notes.new"].tap()
        app.buttons["notes.save"].tap()
        XCTAssertTrue(app.staticTexts["notes.status"].waitForExistence(timeout: 5))
        let title = app.textFields["notes.title"]
        title.tap(); title.typeText("Teste")
        let body = app.textViews["notes.body"]
        body.tap(); body.typeText("Conteúdo")
        app.buttons["notes.save"].tap()
        assertRow(title: "Teste", body: "Conteúdo")
    }

    func testDiscardDraft() {
        app.buttons["notes.new"].tap()
        let title = app.textFields["notes.title"]
        title.tap(); title.typeText("Descartar")
        app.buttons["notes.cancel"].tap()
        app.buttons["notes.discard"].tap()
        XCTAssertTrue(app.buttons["notes.new"].waitForExistence(timeout: 5))
        XCTAssertEqual(rows.count, 0)
    }

    func testAccessibleNamesAndRoles() {
        XCTAssertEqual(app.buttons["notes.new"].label, "Nova nota")
        app.buttons["notes.new"].tap()
        XCTAssertEqual(app.textFields["notes.title"].label, "Título")
        XCTAssertEqual(app.textViews["notes.body"].label, "Conteúdo")
        XCTAssertEqual(app.buttons["notes.save"].label, "Salvar")
        XCTAssertEqual(app.buttons["notes.cancel"].label, "Cancelar")
    }

    func testInjectedLargeTypeCanCreate() {
        app.terminate()
        app.launchArguments = ["--uitesting", "--fixture-reset", "--fixture-large-type"]
        app.launch()
        createNote()
        assertRow(title: "Reunião", body: "Próximos passos")
    }
}
