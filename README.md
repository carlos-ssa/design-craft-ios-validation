# Notas de trabalho — fixture iOS preparado

App nativo SwiftUI para exercitar a Design Craft em iPhone/iPad. Inclui notas, criação/edição, validação, persistência atômica de notas e rascunho, recuperação e preservação de arquivo inválido.

**Estado: código e projeto preparados; build e execução nativa pendentes.** Gerar um `.xcodeproj`, conferir referências ou passar por análise de código no Windows não aprova o iOS.

## Estrutura

- `Notas/`: app SwiftUI, sem pacotes externos; iOS17 e Swift5.
- `NotasTests/`: cinco métodos XCTest de estado, validação e persistência.
- `NotasUITests/`: seis métodos XCUITest de fluxos, nomes/papéis e texto grande injetado.
- `Notas.xcodeproj`: projeto gerado com esquema compartilhado, app e dois targets de teste.
- `tools/generate-project.py`: gerador determinístico e verificação do grafo de referências.
- `tools/run-native.py`: runner que exige macOS/Xcode e um Simulator real, guarda log e `.xcresult` e só aprova após ler contagens estruturadas.

## Rodar num Mac com Xcode

```text
python3 tools/generate-project.py
python3 tools/run-native.py
```

O runner escolhe um iPhone Simulator disponível, inicializa-o quando necessário, executa `xcodebuild test` e grava evidências em `evidence/`. `TEST_OUTPUT` permite escolher outro diretório. Não usa Apple Developer account ou assinatura de distribuição: o alvo de execução é Simulator.

Erros de build, testes falhos, ausência de runtime ou resultado ilegível não viram aprovação. Os onze métodos planejados não entram no denominador de testes aprovados até serem executados e verificados.

## Execução remota preparada

O workflow em `.github/workflows/ios-validation.yml` usa runner macOS e ações fixadas por commit. Ele aceita o fixture na raiz de um repositório de testes ou dentro deste workspace. Só tem disparo manual; nenhuma execução remota, publicação ou criação de repositório foi realizada nesta preparação. O consumo de runner depende da conta/plano do provedor.

Para usá-lo, será necessário um repositório GitHub indicado pelo usuário e Actions habilitado. O artefato `ios-native-evidence` contém os resultados de cada execução; não se deve confiar apenas no check verde do job sem conferir `run.json` e `.xcresult`.

## Limites dos testes

`--fixture-large-type` injeta uma categoria de Dynamic Type no app somente quando combinado a `--uitesting`; não é alteração da preferência do sistema. `--fixture-reset` apaga somente o arquivo desse app de teste e não deve ser usado com notas a preservar.

Ainda faltam confirmação de compilação, comportamento de seletores XCUI, teclado real, VoiceOver, preferências reais e inspeção visual no Simulator. Não se promete resultado de plataforma com base nessa preparação.
