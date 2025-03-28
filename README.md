# CPUFriendFriend Interativo

Uma versão interativa do script CPUFriendFriend que permite personalizar facilmente os parâmetros de energia e performance do processador em sistemas macOS/Hackintosh.

## O que é o CPUFriendFriend Interativo?

Este script é uma versão aprimorada do [CPUFriendFriend original](https://github.com/corpnewt/CPUFriendFriend) ao qual está dando erro na geração correta. Foi modificado para facilitar o ajuste dos parâmetros de energia e performance do processador. Ele permite configurar com um clique para performance máxima ou personalizar individualmente cada configuração, tudo através de uma interface interativa passo a passo.

## Pré-requisitos

Antes de usar este script, você precisa ter:

- macOS 10.13 (High Sierra) ou superior
- Python 3.x 
- [CPUFriend.kext](https://github.com/acidanthera/CPUFriend/releases) v1.1.0 ou superior
- Acesso à pasta EFI do seu sistema

## Guia Completo de Uso

### 1. Preparação

- Baixe [CPUFriend.kext](https://github.com/acidanthera/CPUFriend/releases) (se já não estiver instalado)

### 2. Baixe e Execute o Script CPUFriendFriend Interativo

```bash
git clone https://github.com/ricardo-landim/CPUFriendFriend-Interactive.git
cd CPUFriendFriend-Interactive
./CPUFriendFriend.command
```

### 3. Configure Seus Parâmetros

O script irá guiá-lo através de opções interativas:

- Opção de usar configuração padrão para performance máxima
- Ou personalizar individualmente cada parâmetro:
  - Frequência Mínima (LFM)
  - Energy Performance Preference (EPP)
  - Performance Bias
  - CPU Floor
  - Boost Limit
  - Otimizações de Economia de Energia
  - Curvas de Esforço
  - QOS Thermal Thresholds

### 4. Geração dos Arquivos

Após a configuração, o script irá gerar vários arquivos na pasta `Results`:
- `CPUFriendDataProvider.kext` - O kext personalizado para seu processador
- `Mac-XXXXXXXX.plist` - Arquivo PLIST personalizado com suas configurações
- `ssdt_data.aml` - Arquivo ACPI compilado que pode ser usado como alternativa ao kext
- `ssdt_data.dsl` - Código fonte do SSDT para personalização adicional

### 5. Instalação dos Arquivos Gerados

Você pode escolher entre dois métodos de instalação:

#### Método 1: Usando o kext (Recomendado)

1. Monte sua partição EFI:
   ```bash
   Use o MountEFI
   ```
   
2. Copie o `CPUFriendDataProvider.kext` para:
   - OpenCore: `EFI/OC/Kexts/` 
   - Clover: `EFI/CLOVER/kexts/Other/`

3. Configuração do bootloader:

   **Para OpenCore:**
   - Edite seu config.plist
   - Adicione CPUFriendDataProvider.kext na seção Kernel -> Add
   - **IMPORTANTE**: Certifique-se que CPUFriend.kext está listado ANTES de CPUFriendDataProvider.kext

   **Para Clover:**
   - Certifique-se que CPUFriend.kext e CPUFriendDataProvider.kext estejam em `EFI/CLOVER/kexts/Other/`
   - **IMPORTANTE**: CPUFriend.kext deve ser carregado antes de CPUFriendDataProvider.kext

#### Método 2: Usando o SSDT (Alternativo)

Como alternativa, você pode usar o arquivo SSDT gerado:

1. Copie o arquivo `ssdt_data.aml` para:
   - OpenCore: `EFI/OC/ACPI/`
   - Clover: `EFI/CLOVER/ACPI/patched/`

2. Configuração do bootloader:

   **Para OpenCore:**
   - Adicione o arquivo SSDT em config.plist na seção ACPI -> Add
   
   **Para Clover:**
   - O SSDT será carregado automaticamente da pasta patched

3. **IMPORTANTE**: Ao usar o método SSDT, você ainda precisa do CPUFriend.kext, mas não precisa do CPUFriendDataProvider.kext

4. Reinicie seu computador para aplicar as alterações
## Solução de Problemas

### Erro ao Determinar o Board ID
- Verifique se sua SMBIOS está corretamente configurada
- Certifique-se de que você está usando uma SMBIOS adequada para seu hardware

### Erro ao Carregar Arquivo PLIST
- Verifique se o X86PlatformPlugin está instalado em seu sistema
- Algumas versões do macOS podem ter caminhos diferentes para este arquivo

### Erro ao Compilar
- Verifique se o script conseguiu baixar o ResourceConverter.sh
- Verifique se você tem permissões de escrita na pasta do script

### Kernel Panic após Instalação
- Remova temporariamente CPUFriendDataProvider.kext
- Tente configurações menos agressivas
- Verifique se a versão do CPUFriend é compatível com sua versão do macOS

## Créditos

- [Acidanthera](https://github.com/acidanthera) - Pelo CPUFriend original
- [PMHeart](https://github.com/PMheart) - Contribuições ao CPUFriend
- [CorpNewt](https://github.com/corpnewt) - Pelo CPUFriendFriend original
- [Ricardo Landim](https://github.com/ricardo-landim) - Por esta versão interativa

## Licença

Este projeto está licenciado sob a Licença MIT.
