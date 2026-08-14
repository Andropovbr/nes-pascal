# Atribuições

[English](../../language/assignments.md) | Português (Brasil)

A atribuição utiliza `:=`:

```pascal
BackgroundColor := $21;
Counter := $FF;
Enabled := true;
```

O lado direito pode ser:

- um literal hexadecimal;
- `true` ou `false`;
- uma referência a uma constante;
- uma referência a uma variável previamente atribuída;
- um membro de enumeração ou variável de enumeração previamente atribuída do
  mesmo tipo exato;
- um campo tipado de um record ou elemento de array de records previamente
  atribuído;
- uma expressão aritmética de `byte`;
- uma comparação ou expressão booleana cujo resultado seja `boolean`.

Ambos os lados devem ter exatamente o mesmo tipo. Não há conversões implícitas.
Ler uma variável antes de uma atribuição prévia é um erro de compilação.
Constantes não podem ser alvos de atribuição.

Um campo individual de record pode ser alvo de atribuição e preserva seu tipo
declarado exato. Atribuição do record inteiro não é suportada; atribua os campos
individualmente. Consulte [Records](records.md).

Parâmetros de valor são cópias locais inicializadas e também podem ser alvos de
atribuição dentro do procedimento em que foram declarados. Atribuir a um parâmetro
não modifica o argumento do chamador.

A análise de atribuição definitiva segue o fluxo de controle estruturado. As regras
detalhadas para desvios, laços e chamadas de procedimento estão documentadas com essas estruturas.

Os diagnósticos de atribuição preservam o erro primário mais inicial:

- E4002 reporta um valor de `nes_color` fora de `$00..$3F`;
- E4004 reporta tipos de origem e destino incompatíveis, incluindo literais
  hexadecimais atribuídos a `boolean`;
- E3008 reporta uma variável lida antes da atribuição.

Verificações de programa completo, como E3003, são executadas apenas após o sucesso
da análise semântica em nível de instrução. Consulte a
[referência de diagnósticos](../reference/diagnostics/index.md) para o índice completo,
explicações, exemplos e correções sugeridas.

Variáveis `byte` inicializadas também podem ser alteradas com
[`inc` e `dec`](increment-and-decrement.md).
