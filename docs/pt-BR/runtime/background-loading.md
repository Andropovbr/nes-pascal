# Carregamento de fundo

[English](../../runtime/background-loading.md) | Português (Brasil)

`nes.load_background()` transfere um fundo estático completo durante a inicialização
do programa:

```pascal
begin
    nes.load_background();
    nes.set_background_color($0F);
    nes.run;
end.
```

O comando não recebe argumentos, é opcional e pode aparecer no máximo uma vez.
Ele deve ser uma instrução incondicional de nível superior antes de `nes.run`; não
pode ser usado em procedimentos, condicionais, laços ou após o início da renderização.

## Asset combinado de 1 KiB

Configure uma nametable bruta de 1024 bytes com `--nametable`:

```text
python -m nes_pascal.cli examples/nametable_loading.nsp -o build/nametable_loading.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
```

Os primeiros 960 bytes são os índices de tiles 32 por 30 em ordem de linhas (row-major)
para os endereços `$2000-$23BF` da PPU. Os 64 bytes finais são a tabela de atributos nativa
do hardware para `$23C0-$23FF`. Não há cabeçalho, compressão, conversão ou metadados.

## Arquivos separados de tiles e atributos

Os mesmos bytes podem ser configurados separadamente. O repositório não contém
arquivos separados de tiles/atributos (o exemplo incluído `examples/nametable_loading.nsp`
usa a forma combinada `--nametable` acima), então a forma dividida é mostrada abaixo
com caminhos de espaço reservado explícitos:

```text
# Exemplo ilustrativo: substitua os caminhos de espaço reservado pelos seus
# próprios arquivos de mapa de tiles de 960 bytes e tabela de atributos de 64 bytes.
python -m nes_pascal.cli <seu-programa>.nsp -o build/<seu-programa>.nes --nametable-tiles <seu-mapa-de-tiles>.tiles --nametable-attributes <sua-tabela-de-atributos>.attributes
```

O arquivo de tiles deve conter exatamente 960 bytes e o arquivo de atributos exatamente
64 bytes. Ambas as opções são obrigatórias em conjunto. Elas não podem ser combinadas
com `--nametable`.

Todos os caminhos de assets são resolvidos a partir do diretório que contém o código-fonte
`.nsp`, e não a partir do diretório de trabalho do processo do compilador. Componentes
relativos `.` e `..`, separadores nativos da plataforma e caminhos absolutos são suportados.
Configurações ausentes, ilegíveis, conflitantes, incompletas ou com tamanho incorreto
interrompem a compilação; o compilador nunca substitui dados de fundo vazios.

## Comportamento gerado e limites

Os 1024 bytes validados são embutidos inalterados uma vez na PRG-ROM. Durante a
inicialização no RESET, o código gerado mantém a renderização explicitamente desabilitada,
redefine o latch de endereçamento da PPU, seleciona `$2000` e copia todas as quatro
páginas de 256 bytes através de `$2007`. Comandos posteriores de inicialização podem
configurar paletas. `nes.run` aguarda o VBlank, restaura o estado atual da PPU e,
em seguida, habilita a renderização.

Esta operação permanece como a transferência em lote exclusiva de inicialização para
a nametable 0. Após `nes.run`, alterações limitadas de um único byte de tile ou atributo
utilizam as [APIs de atualização de fundo em runtime](background-updates.md). Valores
estáticos de rolagem e espelhamento horizontal ou vertical no cabeçalho estão documentados
em [Rolagem e estado da PPU](scrolling-and-ppu-state.md). Múltiplas telas, streaming e
conversão de assets continuam não suportados.
Se `nes.get_tile` for incluído sem este comando, o RESET preenche a nametable 0 com zeros
para que o shadow confirmado em RAM comece consistente com a PPU.
