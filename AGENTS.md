# AGENTS.md

## Objetivo do projeto

Este repositório contém o protótipo de uma linguagem compilada, fortemente tipada e estruturada, inspirada em Pascal e especializada para desenvolvimento de jogos para o Nintendo Entertainment System.

A linguagem compila para Assembly compatível com ca65. O ca65 e o ld65 são responsáveis por produzir a ROM final no formato iNES.

O objetivo não é implementar Pascal completo nem criar inicialmente uma linguagem de propósito geral.

## Filosofia

A linguagem deve:

* ser fácil de ler;
* ter tipagem forte;
* evitar conversões implícitas;
* gerar código previsível;
* expor custos relevantes do hardware;
* impedir construções perigosas sempre que possível;
* produzir mensagens de erro didáticas;
* gerar Assembly ca65 legível;
* permitir que o programador compreenda a relação entre o código-fonte e o Assembly produzido.

A linguagem não deve esconder completamente o funcionamento do NES.

## Restrições iniciais

Na primeira versão:

* use Python 3.11 ou superior para implementar o compilador;
* gere Assembly compatível com ca65;
* gere ROM para NES NTSC;
* use apenas instruções do processador Ricoh 2A03/6502;
* não use instruções exclusivas do 65C02;
* utilize inicialmente o mapper 0, NROM;
* utilize 32 KiB de PRG-ROM;
* utilize 8 KiB de CHR-ROM;
* não implemente memória dinâmica;
* não implemente recursão;
* não implemente orientação a objetos;
* não implemente strings em runtime;
* não implemente otimizações avançadas prematuramente;
* não gere C intermediário.

## Primeiro marco

O primeiro marco deve aceitar exatamente um programa mínimo como:

```pascal
program Minimal;

begin
    nes.set_background_color($21);
    nes.run;
end.
```

O compilador deve gerar Assembly ca65, montar e vincular uma ROM `.nes` válida.

Ao abrir a ROM em um emulador, o NES deve:

1. inicializar corretamente;
2. aguardar o momento seguro para acessar a PPU;
3. configurar a cor universal de fundo como `$21`;
4. habilitar a renderização;
5. permanecer em um loop estável.

Não implemente ainda variáveis, procedimentos definidos pelo usuário, expressões gerais, sprites, leitura de controle ou áudio.

## Pipeline esperado

```text
examples/minimal.nsp
        ↓
lexer
        ↓
parser
        ↓
AST
        ↓
backend ca65
        ↓
build/minimal.asm
        ↓
ca65
        ↓
ld65
        ↓
build/minimal.nes
```

## Arquitetura do compilador

Mantenha componentes separados:

* `lexer.py`: converte caracteres em tokens;
* `parser.py`: converte tokens em uma árvore sintática;
* `ast.py`: contém os nós da AST;
* `backend_ca65.py`: converte a AST em Assembly ca65;
* `cli.py`: coordena compilação, geração de arquivos e execução das ferramentas externas.

Não traduza diretamente texto-fonte para Assembly por substituição de strings.

Mesmo no protótipo, use uma AST mínima.

## Regras do backend NES

* O código gerado deve usar sintaxe ca65.
* O header iNES deve ser produzido explicitamente.
* O programa deve fornecer vetores NMI, RESET e IRQ.
* O RESET deve desabilitar interrupções, inicializar a pilha e estabilizar a PPU.
* Escritas na PPU devem acontecer somente em momentos seguros.
* O primeiro protótipo deve usar uma CHR-ROM vazia de 8 KiB.
* O Assembly gerado deve conter comentários indicando a origem de cada bloco.
* Não introduza uma engine de jogo genérica.
* Não copie uma biblioteca extensa para resolver o programa mínimo.

## Tipagem e sintaxe futura

A linguagem será fortemente tipada, mas somente implemente tipos quando uma tarefa solicitar explicitamente.

Tipos planejados:

* `byte`: 0..255;
* `signed_byte`: -128..127;
* `word`: 0..65535;
* `boolean`;
* tipos definidos por intervalo;
* tipos semânticos específicos do NES.

Não implemente esses tipos antecipadamente no primeiro marco.

## Diagnósticos

Todo erro do compilador deve, quando possível, informar:

* arquivo;
* linha;
* coluna;
* código do erro;
* descrição clara;
* trecho relacionado;
* sugestão de correção, quando houver.

Exemplo:

```text
E1001 examples/minimal.nsp:4:5

Comando desconhecido: nes.background

Talvez você quisesse usar:
    nes.set_background_color(valor);
```

Não exponha stack traces Python para erros comuns do código-fonte.

## Qualidade

Antes de concluir uma tarefa:

1. execute os testes;
2. compile o exemplo mínimo;
3. confirme que a ROM possui header iNES válido;
4. confirme que o tamanho produzido corresponde à configuração NROM;
5. informe os comandos executados;
6. descreva limitações conhecidas;
7. não altere golden tests apenas para fazer uma falha desaparecer.

## Testes

Utilize:

* testes unitários para lexer e parser;
* golden tests para o Assembly gerado;
* teste de integração que invoque ca65 e ld65;
* validação do header e do tamanho da ROM;
* testes de erro para sintaxe inválida.

Os testes que dependem de ca65 devem ser ignorados com uma mensagem clara quando o toolchain não estiver instalado.

## Estilo de implementação

* Prefira código simples e explícito.
* Use type hints no código Python.
* Evite dependências externas quando a biblioteca padrão for suficiente.
* Não use geradores de parser no primeiro protótipo.
* Use exceções próprias para erros de compilação.
* Documente decisões arquiteturais importantes.
* Não faça grandes refatorações fora do escopo da tarefa.
* Não implemente recursos futuros sem solicitação.

## Processo de trabalho

Antes de escrever código:

1. leia este arquivo;
2. leia os documentos relevantes em `docs/`;
3. inspecione a estrutura existente;
4. apresente um plano curto;
5. implemente apenas o marco solicitado.

Quando houver dúvida entre uma solução genérica e uma solução pequena e previsível, escolha a solução pequena e previsível.
