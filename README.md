# Interface Forge — teste complementar iOS

> A skill completa de front-end, UI e UX para **web, Android e iOS** está em [carlos-ssa/interface-forge](https://github.com/carlos-ssa/interface-forge).

Este repositório contém apenas o app nativo SwiftUI para validar a parte iOS da Interface Forge, anteriormente chamada Design Craft. O destino deste fixture é iPhone/iPad. Inclui notas, criação/edição, validação, persistência atômica de notas e rascunho, recuperação e preservação de arquivo inválido.

**Estado: rodada encerrada pelo usuário, com iOS não aprovado e reteste pendente.** A primeira execução em Simulator passou em9/12 e a última em10/12, sem skips. As últimas correções estão salvas no commit4b33075, mas o GitHub bloqueou o reteste antes de iniciar o runner por cobrança/limite da conta. Gerar um `.xcodeproj` ou fazer análise de código no Windows não aprova o iOS.

## Estrutura

- `Notas/`: app SwiftUI, sem pacotes externos; iOS17 e Swift5.
- `NotasTests/`: cinco métodos XCTest de estado, validação e persistência.
- `NotasUITests/`: sete métodos XCUITest de fluxos, nomes/papéis, texto grande injetado e auditoria automática de acessibilidade em tela vazia, formulário e lista preenchida, com screenshots preservados.
- `Notas.xcodeproj`: projeto gerado com esquema compartilhado, app e dois targets de teste.
- `tools/generate-project.py`: gerador determinístico e verificação do grafo de referências.
- `tools/run-native.py`: runner que exige macOS/Xcode e um Simulator real, guarda log e `.xcresult` e só aprova após ler contagens e identidades estruturadas contra `tools/benchmark-test-plan.json`.

## Rodar num Mac com Xcode

```text
python3 tools/generate-project.py
python3 tools/run-native.py
```

O runner escolhe um iPhone Simulator disponível da versão do SDK ativo, inicializa-o quando necessário, executa `xcodebuild test` e grava evidências em `evidence/`. `IOS_RUNTIME` permite definir outra versão explicitamente; `TEST_OUTPUT` escolhe outro diretório. A seleção nova ainda precisa de execução nativa. Não usa Apple Developer account ou assinatura de distribuição: o alvo de execução é Simulator.

Erros de build, testes falhos, ausência de runtime ou resultado ilegível não viram aprovação. Os doze métodos planejados não entram no denominador de testes aprovados até serem executados e verificados.

## Execução remota preparada

O workflow em `.github/workflows/ios-validation.yml` usa runner macOS15 Intel e ações fixadas por commit. Ele aceita o fixture na raiz de um repositório de testes ou dentro deste workspace e só tem disparo manual. O usuário autorizou criar o repositório inicialmente privado [carlos-ssa/design-craft-ios-validation](https://github.com/carlos-ssa/design-craft-ios-validation). A primeira tentativa terminou sem runner por capacidade ARM64, sem executar o código. A primeira execução Intel compilou e executou12 casos, com9 aprovados. O consumo de runner depende da conta/plano do provedor.

O repositório foi posteriormente tornado público a pedido do usuário. Actions está habilitado; o último reteste foi bloqueado antes de iniciar o runner, conforme o estado registrado acima. O artefato `ios-native-evidence` contém os resultados de cada execução; não se deve confiar apenas no check verde sem conferir `run.json`, identidades e `.xcresult`. `inspect-evidence.yml` extrai resumos e anexos de uma execução anterior em macOS quando necessário. Se o resumo principal estiver ilegível, o runner pode encerrar antes da exportação de anexos; o bundle bruto continua no upload para esse diagnóstico separado.

## Limites dos testes

`--fixture-large-type` injeta uma categoria de Dynamic Type no app somente quando combinado a `--uitesting`; não é alteração da preferência do sistema. `--fixture-reset` apaga somente o arquivo desse app de teste e não deve ser usado com notas a preservar.

A última execução real, commit886c9a8, aponta texto recortado no estado vazio e ausência do sufixo digitado na edição. O commit4b33075 usa layout vazio de altura flexível, confere valor exato antes de salvar e após relançar e escolhe runtime correspondente ao SDK. Não foi demonstrada uma causa isolada para a entrada ausente; essas correções não estão aprovadas sem reteste.

A execução cobre Simulator e entrada automatizada. VoiceOver com avaliação auditiva, aparelho físico, teclado físico e preferências reais do sistema não foram avaliados. Relançamento limpo não representa toda forma de morte de processo ou recuperação do sistema. O caso de fonte ampliada confirma o fluxo de criação; a captura mostra título de navegação elidido, não uma auditoria visual completa de texto grande.
