# Estrutura do programa

[English](../../language/program-structure.md) | Português (Brasil)

Um programa contém:

1. a palavra-chave `program`;
2. um nome de programa;
3. um ponto e vírgula;
4. uma seção opcional `const`;
5. uma seção opcional `var`;
6. zero ou mais declarações de procedimentos;
7. um bloco que se inicia com `begin`;
8. uma sequência de instruções;
9. a palavra-chave `end`;
10. um ponto final.

Exemplo:

```pascal
program Minimal;

const
    DefaultBackgroundColor: nes_color = $21;

var
    BackgroundColor: nes_color;
    FrameCounter: byte;
    RenderingEnabled: boolean;

procedure Initialize(Start: byte; Enabled: boolean);
begin
    FrameCounter := Start;
    RenderingEnabled := Enabled;
end;

begin
    BackgroundColor := DefaultBackgroundColor;
    Initialize($00, true);
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
```

As seções de declaração devem aparecer nesta ordem. O bloco principal contém
a sequência de inicialização de nível superior e pode continuar com a lógica
da thread principal sincronizada por quadros após `nes.run`.

Os registros estáticos `nes.on_update(Procedure)` e `nes.on_vblank(Procedure)`,
quando presentes, pertencem à sequência incondicional de inicialização de nível
superior antes de `nes.run`. Consulte [Callbacks de quadro](../runtime/frame-callbacks.md).

O comando opcional `nes.load_background()` também é uma instrução incondicional
de inicialização de nível superior antes de `nes.run`. Ele não recebe argumentos
e requer [dados de nametable](../runtime/background-loading.md) configurados.

[Atualizações de fundo em runtime](../runtime/background-updates.md) limitadas
podem ser preparadas a partir do código principal ou de procedimentos. Suas
operações que modificam a fila não são permitidas no caminho de um callback
de VBlank; a consulta simples de estouro é segura nesse contexto.
