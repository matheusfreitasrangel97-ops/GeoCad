# GeoCAD Bridge - Plano de Implementação (Modo Tolerante & Recuperação)

Este plano descreve as melhorias de robustez e tolerância a falhas estruturais para arquivos CAD imperfeitos, proxies e tabelas corrompidas.

## Revisão Requerida pelo Usuário

> [!IMPORTANT]
> **Tolerância Estrutural Completa**:
> O parsing passará a utilizar a API `ezdxf.recover` para tentar reparar automaticamente qualquer inconsistência física nos arquivos CAD. 
> Todos os loops de leitura vetorial e recursão de blocos serão envolvidos em blocos `try-except` para isolar erros individuais e evitar a interrupção da execução completa.

> [!WARNING]
> **Preservação de DXF Temporário sob Falhas**:
> Se ocorrer um erro crítico que impeça a leitura completa do DWG/DXF, o arquivo DXF convertido temporário não será excluído da máquina do usuário, facilitando auditoria e depuração. O caminho completo será impresso nos logs.

---

## Alterações Propostas

### 1. [MODIFY] [parser.py](file:///c:/Users/estagiario/.gemini/antigravity-ide/scratch/QFieldLiteWorkspace/cad/parser.py)
* Substitui `ezdxf.readfile(dxf_path)` por `ezdxf.recover.readfile(dxf_path)`.
* Registra todas as inconsistências corrigidas pelo Auditor em pt-BR.
* Envolve a leitura de geometrias individuais de cada entidade e sub-elementos de blocos (`INSERT`) em blocos de exceção genéricos, incrementando contadores de falhas.
* Retorna estatísticas de auditoria (geometrias lidas com sucesso, ignoradas por erro e corrigidas) ao final do processo.

### 2. [MODIFY] [parser_worker.py](file:///c:/Users/estagiario/.gemini/antigravity-ide/scratch/QFieldLiteWorkspace/workers/parser_worker.py)
* Rastreia o sucesso operacional do parser.
* Se falhar, preserva o arquivo DXF temporário no sistema e imprime o caminho no console de logs. Se funcionar, limpa o arquivo temporário normalmente.

### 3. [MODIFY] [main_window.py](file:///c:/Users/estagiario/.gemini/antigravity-ide/scratch/QFieldLiteWorkspace/ui/main_window.py)
* Caso ocorra uma falha crítica insolúvel no worker, exibe a caixa de diálogo amigável obrigatória:
  ```text
  Não foi possível interpretar este arquivo DWG automaticamente.

  O desenho pode conter estruturas incompatíveis ou corrompidas.

  Deseja tentar abrir uma versão DXF manualmente?
  ```
* Se o usuário aceitar, abre o seletor de arquivos filtrado apenas para arquivos `.dxf`.

---

## Plano de Validação

### Testes Automatizados
* Executar o script de teste de integração local `test_pipeline.py` para garantir que o pipeline de recover e exportação continue gerando os mesmos resultados corretos de Shapefile.

### Verificação Manual
* Simular erros de estrutura ou tentar carregar desenhos pesados com entidades corrompidas para certificar que a interface continua responsiva e que entidades problemáticas são descartadas silenciosamente no console.
