# Fluxo de Trabalho Git e Versionamento - GeoCad

Este guia documenta o fluxo de trabalho Git oficial adotado no desenvolvimento do **GeoCad**. Ele visa padronizar o histórico de desenvolvimento, garantir a estabilidade das versões em produção e orientar sobre lançamentos de releases, criação de tags e recuperação/rollbacks.

---

## 📌 Estrutura de Branches

Adotamos uma variação simplificada e segura do Git Flow:

1. **`main` (Branch de Produção / Versões Estáveis)**
   * Representa a versão em execução oficial.
   * Contém apenas snapshots de versões testadas e certificadas (ex: `v0.1.0`).
   * **Bloqueada:** Commits diretos nunca são permitidos nesta branch. Mudanças entram exclusivamente via Pull Requests aprovados a partir de `dev`.

2. **`dev` (Branch de Desenvolvimento e Integração)**
   * Onde todas as novas features e bugfixes se encontram para testes de integração.
   * É a branch base para o trabalho cotidiano.

3. **`feature/...` (Branches de Novas Funcionalidades)**
   * Criadas a partir de `dev` para desenvolver novas rotinas sem poluir a branch principal de trabalho.
   * Convenção de nome: `feature/nome-da-melhoria`.

4. **`bugfix/...` (Branches de Correções Rápidas)**
   * Criadas a partir de `dev` para resolver problemas identificados que afetam a estabilidade.
   * Convenção de nome: `bugfix/nome-do-problema`.

---

## 🚀 Como Executar Tarefas Comuns

### 1. Criar uma Nova Branch para Trabalho
Para iniciar uma nova funcionalidade, parta sempre da `dev` atualizada:
```bash
# 1. Garanta que está na branch dev e atualizado
git checkout dev
git pull origin dev

# 2. Crie e acesse a nova branch
git checkout -b feature/nome-da-funcionalidade
```

### 2. Salvar Versões (Fazer Commits)
Commits devem ser atômicos e claros. Prefira mensagens de commit no imperativo ou indicando a ação realizada:
```bash
# Adiciona as alterações
git add .

# Faz o commit com mensagem clara
git commit -m "feat: adiciona centralizacao de versao no modulo version"
```

### 3. Como Criar uma Release Estável (Merge de `dev` para `main`)
Quando a branch `dev` acumular melhorias estáveis e testadas que merecem um novo lançamento (ex: `0.1.0` -> `0.2.0`):

1. Atualize a versão localmente em `geocad/version.py` e compile a versão final com `build.bat` para testar.
2. Atualize o arquivo `CHANGELOG.md` descrevendo as novidades sob o título da nova versão.
3. Faça commit destas alterações na `dev`.
4. Abra um Pull Request de `dev` para `main`.
5. Com o Pull Request aprovado e mergeado na `main`:
   ```bash
   # Vá para a main local e atualize
   git checkout main
   git pull origin main
   ```

### 4. Como Criar Tags Semânticas (Releases do GitHub)
As tags representam fotos estáticas e imutáveis daquele commit específico na `main`, garantindo que versões anteriores nunca sejam perdidas.
```bash
# Cria uma tag anotada local na branch main
git tag -a v0.1.0 -m "Versao de Release 0.1.0 - GeoCad"

# Envia a tag para o repositorio remoto no GitHub
git push origin v0.1.0
```
Isso fará com que o GitHub reconheça o snapshot e crie uma nova Release na página oficial do repositório, permitindo anexar o instalador `.exe` correspondente nela.

---

## 🛡️ Segurança: Como Voltar Versões e Restaurar Estabilidade

Se uma versão implantada apresentar um bug crítico em produção ou se você precisar reverter alterações locais não salvas, siga os procedimentos descritos abaixo.

### 1. Descartar Alterações Locais Não Salvas
Se você fez modificações de teste e quer retornar ao estado do último commit:
```bash
# Descarta modificações em arquivos específicos
git checkout -- caminho/do/arquivo.py

# Descarta TODAS as modificações locais não salvas no diretório
git reset --hard HEAD
```
*⚠️ Atenção: O comando `git reset --hard` apaga de forma irrecuperável tudo o que não foi commitado.*

### 2. Voltar a uma Versão Estável Anterior (Rollback de commits locais)
Se você comitou alterações que quebraram o código e deseja retornar ao commit anterior:
```bash
# Volta a cabeça (HEAD) ao commit anterior preservando os arquivos modificados na staging area
git reset --soft HEAD~1

# Volta a cabeça ao commit anterior DESCARTANDO totalmente as alterações do commit ruim
git reset --hard HEAD~1
```

### 3. Restaurar um Snapshot a partir de uma Tag de Versão
Caso precise recuperar o estado exato de uma versão estável lançada anteriormente para auditoria ou compilação de emergência:
```bash
# 1. Obtenha a lista de tags do servidor
git fetch --all --tags

# 2. Crie uma branch temporária de verificação baseada na tag desejada (ex: v0.1.0)
git checkout tags/v0.1.0 -b restore-v0.1.0
```
Você estará em uma branch estável contendo exatamente o código da tag `v0.1.0`, de onde poderá compilar o executável portátil ou realizar correções pontuais em caso de falha.
