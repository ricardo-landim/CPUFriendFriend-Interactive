#!/usr/bin/env python
import os, sys, plistlib, zipfile, tempfile, binascii, shutil
from Scripts import *

class CPUFF:
    def __init__(self):
        self.u = utils.Utils("CPUFriendFriend")
        self.dl = downloader.Downloader()
        self.r = run.Run()
        self.scripts = os.path.join(os.path.dirname(os.path.realpath(__file__)),"Scripts")
        self.out     = os.path.join(os.path.dirname(os.path.realpath(__file__)),"Results")
        self.processor = self.r.run({"args":['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]})[0].strip()
        self.plist = None
        self.plist_data = None
        self.rc_url = "https://raw.githubusercontent.com/acidanthera/CPUFriend/master/Tools/ResourceConverter.sh"
        self.iasl_url = "https://raw.githubusercontent.com/acidanthera/MaciASL/master/Dist/iasl-stable"
        self.iasl = self.check_iasl()
        self.freq_path = "/System/Library/Extensions/IOPlatformPluginFamily.kext/Contents/PlugIns/X86PlatformPlugin.kext/Contents/Resources"
        self.has_epp  = False
        self.epp_find = "6570700000000000000000000000000000000000"
        self.has_perfbias = False
        self.perfbias_find = "706572662D626961730000000000000000000000"
        self.board = self._get_current_board()
        self.smbios = self._get_current_smbios()
        self.rc_path = self._check_rc(self.rc_url)
        self.mylfm = None
        self.myepp = None
        self.myperfbias = None
        self.cpu_floor = None
        self.boost_limit = None
        self.disable_power_optimizations = None
        self.max_effort_curves = None
        self.qos_thresholds = None
        self.use_defaults = False

    def check_iasl(self,try_downloading=True):
        targets = (
            os.path.join(self.scripts, "iasl-dev"),
            os.path.join(self.scripts, "iasl-stable"),
            os.path.join(self.scripts, "iasl-legacy"),
            os.path.join(self.scripts, "iasl")
        )
        target = next((t for t in targets if os.path.exists(t)),None)
        if target or not try_downloading:
            # Either found it - or we didn't, and have already tried downloading
            return target
        # Need to download
        temp = tempfile.mkdtemp()
        try:
            self._download_and_extract(temp,self.iasl_url)
        except Exception as e:
            print("An error occurred :(\n - {}".format(e))
        shutil.rmtree(temp, ignore_errors=True)
        # Check again after downloading
        return self.check_iasl(try_downloading=False)

    def _download_and_extract(self, temp, url):
        ztemp = tempfile.mkdtemp(dir=temp)
        zfile = os.path.basename(url)
        print("Downloading {}".format(os.path.basename(url)))
        self.dl.stream_to_file(url, os.path.join(ztemp,zfile), False)
        search_dir = ztemp
        if zfile.lower().endswith(".zip"):
            print(" - Extracting")
            search_dir = tempfile.mkdtemp(dir=temp)
            # Extract with built-in tools \o/
            with zipfile.ZipFile(os.path.join(ztemp,zfile)) as z:
                z.extractall(search_dir)
        for x in os.listdir(search_dir):
            if x.lower().startswith(("iasl","acpidump")):
                # Found one
                print(" - Found {}".format(x))
                print("   - Chmod +x")
                self.r.run({"args":["chmod","+x",os.path.join(search_dir,x)]})
                print("   - Copying to {} directory".format(os.path.basename(self.scripts)))
                shutil.copy(os.path.join(search_dir,x), os.path.join(self.scripts,x))

    def _get_rc(self, url):
        self.u.head("Downloading ResourceConverter")
        print("")
        target = os.path.join(self.scripts,os.path.basename(url))
        print("Downloading {} from:\n{}".format(os.path.basename(url),url))
        return self.dl.stream_to_file(url, target)

    def _check_rc(self, url):
        target = os.path.join(self.scripts,os.path.basename(url))
        if os.path.exists(target):
            return target
        return self._get_rc(url)

    def _decode(self, var):
        if sys.version_info >= (3,0) and isinstance(var, bytes):
            var = var.decode("utf-8","ignore")
        return var

    def _get_value(self,value):
        out = self._decode(self.r.run({"args":["ioreg","-p","IODeviceTree","-d","2","-k",value]})[0])
        v = "Unknown"
        try:
            v = out.split('{}" = '.format(value))[1].split('<"')[1].split('">')[0]
        except:
            pass
        return v

    def _get_current_board(self):
        return self._get_value("board-id")

    def _get_current_smbios(self):
        return self._get_value("product-name")

    def _get_epp_desc(self,epp):
        epp_int = epp if isinstance(epp,int) else int(epp,16)
        epp_desc = "Unknown"
        if epp_int < 64:
            epp_desc = "Performance"
        elif epp_int < 128:
            epp_desc = "Balanced Performance"
        elif epp_int < 192:
            epp_desc = "Balanced Power Savings"
        else:
            epp_desc = "Maximize Power Savings"
        return epp_desc

    def _get_freq_info(self,x):
        freq = epp = perfbias = None
        data = plist.extract_data(x)
        str_data = self._decode(binascii.hexlify(data)).upper()
        # Verificar se o formato tem pelo menos 8 caracteres
        if len(str_data) >= 10:
            freq = str_data[8:10]
        else:
            freq = "0D"  # Definir valor padrão se não encontrar
            
        if self.epp_find in str_data:
            try:
                epp = str_data.split(self.epp_find)[1][:2]
            except:
                epp = "00"  # Valor padrão para performance máxima
        
        if self.perfbias_find in str_data:
            try:
                perfbias = str_data.split(self.perfbias_find)[1][:2]
            except:
                perfbias = "00"  # Valor padrão para performance máxima
                
        return (freq,epp,perfbias)

    def _display_desc(self,desc):
        self.u.head("CPUFriendFriend - Configuração Atual")
        print("")
        print("CPU: {}".format(self.processor))
        print("Board: {}".format(self.board))
        print("SMBIOS: {}".format(self.smbios))
        print("")
        
        if self.mylfm:
            print("- Frequência mínima (LFM): {}00MHz (0x{})".format(int(self.mylfm,16), self.mylfm))
        else:
            print("- Frequência mínima (LFM): Não configurada")
            
        if self.myepp:
            print("- EPP: 0x{} ({})".format(self.myepp, self._get_epp_desc(self.myepp)))
        else:
            print("- EPP: Não configurado")
            
        if self.myperfbias:
            print("- Perf Bias: 0x{}".format(self.myperfbias))
        else:
            print("- Perf Bias: Não configurado")
            
        if self.cpu_floor:
            print("- CPU Floor: {}MHz".format(self.cpu_floor))
        else:
            print("- CPU Floor: Não configurado")
            
        if self.boost_limit is not None:
            print("- Boost Limit: {}".format(self.boost_limit))
        else:
            print("- Boost Limit: Não configurado")
            
        if self.disable_power_optimizations is not None:
            print("- Otimizações de energia desativadas: {}".format("Sim" if self.disable_power_optimizations else "Não"))
        else:
            print("- Otimizações de energia desativadas: Não configurado")
            
        if self.max_effort_curves is not None:
            print("- Curvas de esforço máximo: {}".format("Sim" if self.max_effort_curves else "Não"))
        else:
            print("- Curvas de esforço máximo: Não configurado")
            
        if self.qos_thresholds is not None:
            print("- QOS Thermal Thresholds aumentados: {}".format("Sim" if self.qos_thresholds else "Não"))
        else:
            print("- QOS Thermal Thresholds aumentados: Não configurado")
        
        print("")

    def setup_default_config(self):
        self.u.head("Usar Configuração Padrão de Performance Máxima?")
        print("")
        print("Essa configuração irá definir todos os valores para performance máxima:")
        print("- Frequência mínima (LFM): 1300MHz (0x0D)")
        print("- EPP: 0x00 (Performance Máxima)")
        print("- Perf Bias: 0x00 (Performance Máxima)")
        print("- CPU Floor: 1300MHz")
        print("- Boost Limit: 10000")
        print("- Desativar otimizações de economia de energia: Sim")
        print("- Curvas de esforço máximo: Sim")
        print("- QOS Thermal Thresholds aumentados: Sim")
        print("")
        
        while True:
            choice = self.u.grab("Usar configuração padrão (S/n)? ").lower()
            if choice == "" or choice == "s":
                self.mylfm = "0D"  # 1300MHz
                self.myepp = "00"  # Performance máxima
                self.myperfbias = "00"  # Performance máxima
                self.cpu_floor = 1300
                self.boost_limit = 10000
                self.disable_power_optimizations = True
                self.max_effort_curves = True
                self.qos_thresholds = True
                self.use_defaults = True
                return True
            elif choice == "n":
                self.use_defaults = False
                return False
            elif choice == "q":
                self.u.custom_quit()

    def configure_frequency(self):
        self.u.head("Configuração de Frequência Mínima (LFM)")
        print("")
        print("A frequência mínima (LFM) é o menor valor de frequência em que o processador operará.")
        print("Valores comuns são:")
        print("  800MHz      :     0x08")
        print("  900MHz      :     0x09")
        print("  1000MHz     :     0x0A")
        print("  1100MHz     :     0x0B")
        print("  1200MHz     :     0x0C")
        print("  1300MHz     :     0x0D")
        print("")
        
        default = "0D"  # 1300MHz por padrão
        
        while True:
            choice = self.u.grab("Inserir valor em hex (padrão 0x0D - 1300MHz): ").upper()
            if choice == "":
                self.mylfm = default
                break
            elif choice == "Q":
                self.u.custom_quit()
            else:
                choice = choice.replace("0X","")
                choice = "".join([x for x in choice if x in "0123456789ABCDEF"])
                if len(choice) != 2:
                    print("Erro: Inserir um valor hexadecimal de 2 dígitos (ex: 0D)")
                    continue
                self.mylfm = choice
                break
        
        # Configurar CPU Floor para o mesmo valor que LFM
        mhz_value = int(self.mylfm, 16) * 100
        
        self.u.head("Configuração de CPU Floor")
        print("")
        print("O valor CPU Floor é a frequência base mínima em MHz.")
        print("Recomendado usar o mesmo valor que a frequência LFM: {}MHz".format(mhz_value))
        print("")
        
        while True:
            choice = self.u.grab("Inserir CPU Floor em MHz (padrão {}MHz): ".format(mhz_value))
            if choice == "":
                self.cpu_floor = mhz_value
                break
            elif choice == "q":
                self.u.custom_quit()
            else:
                try:
                    value = int(choice)
                    if value < 0:
                        print("Erro: Inserir um valor positivo")
                        continue
                    self.cpu_floor = value
                    break
                except ValueError:
                    print("Erro: Inserir um valor numérico válido")
                    continue

    def configure_epp(self):
        self.u.head("Configuração de Energy Performance Preference (EPP)")
        print("")
        print("EPP controla o equilíbrio entre performance e economia de energia.")
        print("Faixas de EPP:")
        print("  0x00-0x3F    :    Performance")
        print("  0x40-0x7F    :    Balanced Performance")
        print("  0x80-0xBF    :    Balanced Power Savings")
        print("  0xC0-0xFF    :    Power")
        print("")
        print("Valores comuns encontrados em Macs:")
        print("  0x00         :    iMac moderno (Performance máxima)")
        print("  0x20         :    Mac Mini moderno")
        print("  0x80         :    MacBook Air moderno")
        print("  0x90         :    MacBook Pro moderno")
        print("")
        
        default = "00"  # Performance máxima por padrão
        
        while True:
            choice = self.u.grab("Inserir valor EPP em hex (padrão 0x00 - Performance máxima): ").upper()
            if choice == "":
                self.myepp = default
                break
            elif choice == "Q":
                self.u.custom_quit()
            else:
                choice = choice.replace("0X","")
                choice = "".join([x for x in choice if x in "0123456789ABCDEF"])
                if len(choice) != 2:
                    print("Erro: Inserir um valor hexadecimal de 2 dígitos (ex: 00)")
                    continue
                self.myepp = choice
                break

    def configure_perfbias(self):
        self.u.head("Configuração de Performance Bias")
        print("")
        print("Perf Bias é uma dica de preferência de performance e energia.")
        print("Faixa de 0 a 15, onde 0 representa preferência por performance máxima")
        print("e 15 representa preferência por economia de energia máxima.")
        print("")
        print("Valores comuns encontrados em Macs:")
        print("  0x01              :    iMac moderno")
        print("  0x05              :    MacBook Pro & Mac Mini modernos")
        print("  0x07              :    MacBook Air moderno")
        print("")
        
        default = "00"  # Performance máxima por padrão
        
        while True:
            choice = self.u.grab("Inserir valor Perf Bias em hex (padrão 0x00 - Performance máxima): ").upper()
            if choice == "":
                self.myperfbias = default
                break
            elif choice == "Q":
                self.u.custom_quit()
            else:
                choice = choice.replace("0X","")
                choice = "".join([x for x in choice if x in "0123456789ABCDEF"])
                if len(choice) != 2:
                    print("Erro: Inserir um valor hexadecimal de 2 dígitos (ex: 00)")
                    continue
                self.myperfbias = choice
                break

    def configure_boost_limit(self):
        self.u.head("Configuração de Boost Limit")
        print("")
        print("Boost Limit controla o quanto o processador pode aumentar sua frequência acima do base.")
        print("Valores altos permitem mais boost de frequência (maior performance)")
        print("Valor padrão 0 (limitado) - Recomendado 10000 (ilimitado)")
        print("")
        
        default = 10000
        
        while True:
            choice = self.u.grab("Inserir Boost Limit (padrão 10000): ")
            if choice == "":
                self.boost_limit = default
                break
            elif choice == "q":
                self.u.custom_quit()
            else:
                try:
                    value = int(choice)
                    if value < 0:
                        print("Erro: Inserir um valor positivo")
                        continue
                    self.boost_limit = value
                    break
                except ValueError:
                    print("Erro: Inserir um valor numérico válido")
                    continue

    def configure_power_optimizations(self):
        self.u.head("Configuração de Otimizações de Economia de Energia")
        print("")
        print("Desativar as otimizações de economia de energia pode melhorar a performance")
        print("mas aumentará o consumo de energia. Útil para desktops ou quando conectado à energia.")
        print("")
        print("Otimizações que podem ser desativadas:")
        print("  * Power Reduced Video Playback")
        print("  * Thermally Optimized Xcode")
        print("  * Power Optimized Screensavers")
        print("  * Power Optimized Slideshows")
        print("  * Power Optimized PhotoBooth")
        print("  * Power Optimized Visualizers")
        print("")
        
        while True:
            choice = self.u.grab("Desativar otimizações de economia de energia? (S/n): ").lower()
            if choice == "" or choice == "s":
                self.disable_power_optimizations = True
                break
            elif choice == "n":
                self.disable_power_optimizations = False
                break
            elif choice == "q":
                self.u.custom_quit()

    def configure_effort_curves(self):
        self.u.head("Configuração de Curvas de Esforço")
        print("")
        print("As curvas de esforço controlam como o sistema aloca recursos de CPU para diferentes tarefas.")
        print("Definir todas as curvas para 100% de esforço maximiza a performance à custa de eficiência energética.")
        print("")
        print("Isso irá maximizar a performance para:")
        print("  * Aplicativos em App Nap")
        print("  * Tarefas em segundo plano")
        print("  * Tarefas de manutenção")
        print("  * Tarefas de baixa prioridade")
        print("")
        
        while True:
            choice = self.u.grab("Configurar todas as curvas de esforço para 100%? (S/n): ").lower()
            if choice == "" or choice == "s":
                self.max_effort_curves = True
                break
            elif choice == "n":
                self.max_effort_curves = False
                break
            elif choice == "q":
                self.u.custom_quit()

    def configure_qos_thresholds(self):
        self.u.head("Configuração de QOS Thermal Thresholds")
        print("")
        print("QOS Thermal Thresholds são os limites em que o sistema começa a reduzir")
        print("o desempenho para controlar a temperatura. Valores mais altos permitem")
        print("que o processador opere em temperaturas mais altas antes de throttling.")
        print("")
        print("AVISO: Isso pode aumentar a temperatura do processador!")
        print("")
        
        while True:
            choice = self.u.grab("Aumentar QOS Thermal Thresholds para 500? (s/N): ").lower()
            if choice == "s":
                self.qos_thresholds = True
                break
            elif choice == "" or choice == "n":
                self.qos_thresholds = False
                break
            elif choice == "q":
                self.u.custom_quit()

    def configure_all_settings(self):
        if not self.setup_default_config():
            self.configure_frequency()
            self.configure_epp()
            self.configure_perfbias()
            self.configure_boost_limit()
            self.configure_power_optimizations()
            self.configure_effort_curves()
            self.configure_qos_thresholds()
        
        # Mostrar resumo final das configurações
        self._display_desc([])
        
        while True:
            choice = self.u.grab("Proceder com essas configurações? (S/n): ").lower()
            if choice == "" or choice == "s":
                break
            elif choice == "n":
                return self.configure_all_settings()
            elif choice == "q":
                self.u.custom_quit()

    def main(self):
        if self.board.lower() == "unknown":
            self.u.head("CPUFriendFriend")
            print("")
            print("Não foi possível determinar o board id!")
            print("Abortando!\n")
            exit(1)
            
        if not self.plist:
            self.plist = os.path.join(self.freq_path,self.board+".plist")
            try:
                with open(self.plist,"rb") as f:
                    self.plist_data = plist.load(f)
            except Exception as e:
                self.u.head("CPUFriendFriend")
                print("")
                print("Não foi possível carregar {}!\nAbortando!\n".format(self.board+".plist"))
                print(e)
                print("")
                exit(1)
                
        if self.plist_data.get("IOPlatformPowerProfile",{}).get("FrequencyVectors",None) == None:
            self.u.head("CPUFriendFriend")
            print("")
            print("FrequencyVectors não encontrados em {}!\nAbortando!\n".format(self.board+".plist"))
            exit(1)
        
        # Configure all settings interactively
        self.configure_all_settings()
        
        # Apply settings
        new_freq = []
        new_desc = []
        
        # Modificar configurações do perfil de energia
        profile = self.plist_data.get("IOPlatformPowerProfile", {})
        
        # Definir valores conforme configuração
        if isinstance(profile, dict):
            # Configurar CPU Floor
            if self.cpu_floor is not None:
                profile["CPUFloor"] = self.cpu_floor
            
            # Configurar Boost Limit
            if self.boost_limit is not None:
                profile["BoostLimit"] = self.boost_limit
            
            # Modificar configurações de SFI para performance máxima
            if self.max_effort_curves and "ThermalConfiguration" in profile and isinstance(profile["ThermalConfiguration"], dict):
                thermal = profile["ThermalConfiguration"]
                if "Domain" in thermal and isinstance(thermal["Domain"], dict):
                    domains = thermal["Domain"]
                    
                    # Otimizar configurações de CPU
                    if "CPU" in domains and isinstance(domains["CPU"], dict):
                        cpu = domains["CPU"]
                        
                        # Modificar todas as curvas de esforço para 100%
                        if "SFIAppNap" in cpu and isinstance(cpu["SFIAppNap"], dict):
                            cpu["SFIAppNap"]["EffortCurve"] = "0=100%"
                        
                        if "SFIDarwinBG" in cpu and isinstance(cpu["SFIDarwinBG"], dict):
                            cpu["SFIDarwinBG"]["EffortCurve"] = "0=100%"
                        
                        if "SFIMaintenance" in cpu and isinstance(cpu["SFIMaintenance"], dict):
                            cpu["SFIMaintenance"]["EffortCurve"] = "0=100%"
                        
                        if "SFIReducedUtility" in cpu and isinstance(cpu["SFIReducedUtility"], dict):
                            cpu["SFIReducedUtility"]["EffortCurve"] = "0=100%"
                        
                        if "SFIUtility" in cpu and isinstance(cpu["SFIUtility"], dict):
                            cpu["SFIUtility"]["EffortCurve"] = "0=100%"
                        
                        # Definir QOSThermalThresholds para valores altos
                        if self.qos_thresholds and "QOSThermalThresholds" in cpu and isinstance(cpu["QOSThermalThresholds"], dict):
                            cpu["QOSThermalThresholds"]["NonFocal"] = 500
                            cpu["QOSThermalThresholds"]["Utility"] = 500
            
            # Configurar otimizações de energia
            if self.disable_power_optimizations:
                profile["power_reduced_playback"] = False
                profile["thermally_optimized_xcode"] = False
                profile["optimized_screensavers"] = False
                profile["optimized_slideshows"] = False
                profile["optimized_photobooth"] = False
                profile["optimized_visualizers"] = False
            else:
                profile["power_reduced_playback"] = True
                profile["thermally_optimized_xcode"] = True
                profile["optimized_screensavers"] = True
                profile["optimized_slideshows"] = True
                profile["optimized_photobooth"] = True
                profile["optimized_visualizers"] = True
            
            # Garantir que as alterações sejam salvas
            self.plist_data["IOPlatformPowerProfile"] = profile
        
        # Processar FrequencyVectors
        print("\nProcessando vetores de frequência...")
        for i,x in enumerate(self.plist_data.get("IOPlatformPowerProfile",{}).get("FrequencyVectors",[])):
            freq,epp,perfbias = self._get_freq_info(x)
            data = plist.extract_data(x)
            str_data = self._decode(binascii.hexlify(data)).upper()
            
            # Apply frequency settings
            if len(str_data) >= 10 and self.mylfm:
                str_data = str_data[:8] + self.mylfm + str_data[10:]
            
            # Apply EPP settings
            if self.myepp and self.epp_find in str_data:
                ind = str_data.find(self.epp_find)
                if ind >= 0:
                    str_data = str_data[:ind+len(self.epp_find)] + self.myepp + str_data[ind+len(self.epp_find)+2:]
            
            # Apply PerfBias settings
            if self.myperfbias and self.perfbias_find in str_data:
                ind = str_data.find(self.perfbias_find)
                if ind >= 0:
                    str_data = str_data[:ind+len(self.perfbias_find)] + self.myperfbias + str_data[ind+len(self.perfbias_find)+2:]
            
            # Convert and store the updated data
            try:
                new_freq.append(plist.wrap_data(binascii.unhexlify(str_data) if sys.version_info > (3,0) else binascii.unhexlify(str_data)))
                print("- Atualizado FrequencyVector {} com sucesso".format(i+1))
            except Exception as e:
                print("- Erro ao processar FrequencyVector {}: {}".format(i+1, e))
                
        # Save the changes
        print("\nSalvando configurações em {}...".format(self.board+".plist"))
        self.plist_data["IOPlatformPowerProfile"]["FrequencyVectors"] = new_freq
        if os.path.exists(self.out):
            print("Encontradas configurações anteriores - removendo...")
            shutil.rmtree(self.out,ignore_errors=True)
        os.makedirs(self.out)
        target_plist = os.path.join(self.out,self.board+".plist")
        with open(target_plist,"wb") as f:
            plist.dump(self.plist_data,f)
        
        # Run the script if found
        if self.rc_path and os.path.exists(self.rc_path):
            print("Executando {}...".format(os.path.basename(self.rc_path)))
            cwd = os.getcwd()
            os.chdir(self.out)
            out = self.r.run({"args":["bash",self.rc_path,"-a",target_plist]})
            if out[2] != 0:
                print(out[1])
            out = self.r.run({"args":["bash",self.rc_path,"-k",target_plist]})
            if out[2] != 0:
                print(out[1])
            if self.iasl:
                print("Compilando SSDTs...")
                for x in os.listdir(self.out):
                    if x.startswith(".") or not x.lower().endswith(".dsl"):
                        continue
                    print(" - {}".format(x))
                    out = self.r.run({"args":[self.iasl,x]})
                    if out[2] != 0:
                        print(out[1])
            os.chdir(cwd)
            self.r.run({"args":["open",self.out]})
        print("")
        print("Configuração concluída com sucesso!")
        print("Os arquivos foram salvos no diretório Results")
        exit()

c = CPUFF()
c.main()