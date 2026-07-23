# LANGUAGE.md

## Estado

Esta especificação descreve somente o marco inicial da linguagem.

A sintaxe é inspirada em Pascal, mas a linguagem não pretende ser compatível com Pascal ou Free Pascal.

## Estrutura mínima

Um programa contém:

1. a palavra-chave `program`;
2. o nome do programa;
3. ponto e vírgula;
4. um bloco iniciado por `begin`;
5. uma sequência de comandos;
6. a palavra-chave `end`;
7. um ponto final.

Exemplo:

```pascal
program Minimal;

begin
    nes.set_background_color($21);
    nes.run;
end.
```

## Identificadores

Identificadores:

* começam com letra;
* podem conter letras, números e `_`;
* não diferenciam maiúsculas e minúsculas no primeiro protótipo;
* devem preservar a grafia original para mensagens de erro.

## Literais hexadecimais

Valores hexadecimais utilizam o prefixo `$`.

Exemplos:

```pascal
$00
$21
$FF
```

No marco inicial, `nes.set_background_color` aceita somente valores constantes de `$00` a `$3F`.

Valores fora desse intervalo devem produzir erro de compilação.

## Comandos iniciais

### `nes.set_background_color`

Configura a cor universal de fundo da paleta do NES.

Sintaxe:

```pascal
nes.set_background_color(valor);
```

O valor deve ser um literal hexadecimal entre `$00` e `$3F`.

Exemplo válido:

```pascal
nes.set_background_color($21);
```

Exemplo inválido:

```pascal
nes.set_background_color($80);
```

Diagnóstico esperado:

```text
E2001: a cor de paleta $80 está fora do intervalo permitido.

Uma cor de paleta do NES deve estar entre $00 e $3F.
```

### `nes.run`

Finaliza a configuração inicial e mantém o programa em execução.

Sintaxe:

```pascal
nes.run;
```

No marco inicial:

* deve aparecer exatamente uma vez;
* deve ser o último comando do bloco;
* comandos depois de `nes.run` devem gerar erro.

## Recursos ainda não suportados

O primeiro marco não aceita:

* declarações `var`;
* declarações `const`;
* declarações `type`;
* procedimentos;
* funções;
* parâmetros definidos pelo usuário;
* expressões aritméticas;
* `if`;
* `while`;
* `for`;
* `case`;
* arrays;
* records;
* código Assembly embutido.

Esses recursos serão adicionados incrementalmente.
