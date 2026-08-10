# Identificadores e literais

[English](../../language/identifiers-and-literals.md) | Português (Brasil)

## Identificadores

Identificadores:

- iniciam com uma letra;
- podem conter letras, dígitos e `_`;
- não diferenciam maiúsculas de minúsculas (case-insensitive);
- preservam sua grafia original para diagnósticos.

Constantes, variáveis e procedimentos compartilham um único namespace case-insensitive.

## Literais hexadecimais

Valores hexadecimais utilizam o prefixo `$`:

```pascal
$00
$21
$FF
```

Literais hexadecimais inicializam valores de `nes_color` e `byte`. Valores booleanos
utilizam as palavras-chave `true` e `false`.

O intervalo numérico válido depende do tipo esperado. Consulte [Tipos embutidos](types.md).
