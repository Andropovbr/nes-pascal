# `nes.set_background_color`

[English](../../runtime/set-background-color.md) | Português (Brasil)

`nes.set_background_color` define a cor de fundo universal da paleta do NES.

## Sintaxe

Uma referência a constante pode ser passada:

```pascal
nes.set_background_color(BackgroundColor);
```

Literais hexadecimais diretos permanecem suportados:

```pascal
nes.set_background_color($21);
```

O argumento deve resolver para um `nes_color` válido. Ele também pode ser uma
variável `nes_color` previamente atribuída:

```pascal
BackgroundColor := $21;
nes.set_background_color(BackgroundColor);
```

Consulte [`nes_color`](../language/types.md#nes_color) para seu intervalo `$00..$3F` e
[Atribuições](../language/assignments.md) para as regras de atribuição definitiva.

## Comportamento de inicialização e runtime

Um programa válido deve estabelecer sua cor de fundo inicial com exatamente uma
chamada de nível superior antes de `nes.run`. Essa chamada escreve diretamente em
`$3F00` enquanto a renderização estiver desabilitada.

Chamadas após `nes.run` ou dentro de procedimentos atualizam o shadow canônico da
paleta e publicam a alteração para o próximo VBlank. Elas nunca escrevem em
`$2006/$2007` a partir do código de runtime normal. Alterações pendentes repetidas
seguem o comportamento de a última escrita prevalece (last-write-wins). Consulte
[API de paleta](palettes.md) para o espelhamento da cor zero e detalhes da fila.
