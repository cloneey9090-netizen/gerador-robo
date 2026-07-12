import os
import re
import threading
import flet as ft
import requests

# =====================================================================
#                PAINEL DE CONTROLE DO COMANDANTE (FLET)
# =====================================================================

PASTA_DESTINO = "resultado"

CANAIS_ALVO = [
    "Premiere", "Globoplay Novelas", "Gloob", "Globo SP",
    "Sportv 1", "Sportv 2", "Sportv 3", "ESPN 1", "ESPN 2",
    "PremiereFC 1", "PremiereFC 2", "PremiereFC 3", "PremiereFC 4", "PremiereFC 5",
    "Sportv 4", "ESPN 3", "ESPN 4", "BandSports", "Nosso Futebol",
    "Telecine Premium", "Telecine Action", "Telecine Touch", "Telecine Pipoca", "Telecine Fun", "Telecine Cult",
    "HBO", "HBO 2", "HBO Plus", "HBO Family", "Warner Channel", "Sony Channel", "AXN",
    "Universal TV", "Studio Universal", "TNT", "Space", "Megapix",
    "Discovery Turbo Tv", "Discovery Channel", "Discovery Home & Health", "Discovery ID",
    "National Geographic", "History Channel", "History 2", "Animal Planet", "TLC", "GNT", "Viva",
    "Gloob", "Globinho", "Disney Channel", "Cartoon Network",
    "Discovery Kids", "Nickelodeon", "Nick Jr", "Tooncast",
    "Globo SP", "Globo RJ", "Globo Minas", "Record TV", "SBT", "Band", "RedeTV"
]

def limpar_nome(texto):
    texto_limpo = re.sub(r'\s*\([^)]*\)', '', texto)
    return re.sub(r'\s+', ' ', texto_limpo).strip().lower()

def injetar_marcador_vlc(linha, url_link=""):
    if not linha.startswith("#EXTINF"):
        return linha
        
    # Se o link for HTTP puro, ele vai falhar no Clappr (precisa de VLC/externo)
    eh_http_inseguro = url_link.lower().startswith("http://")
    
    # Verifica também se tem tokens pesados ou portas incomuns de painel
    tem_tokens_pesados = any(param in url_link for param in ["token=", "key=", "auth=", "secure=", "sig="])
    tem_porta_incomum = bool(re.search(r':\d{4,5}/', url_link))
    
    # Se for HTTP, pesado ou com porta restrita, injeta o marcador VLC
    if (eh_http_inseguro or tem_tokens_pesados or tem_porta_incomum) and 'marcador=' not in linha:
        return re.sub(r'(#EXTINF:[-\d]+)', r'\1 marcador="VLC"', linha)
        
    return linha
def testar_link_ativo(url):
    try:
        resposta = requests.head(url, timeout=4, allow_redirects=True)
        if resposta.status_code < 400:
            return True
        resp_get = requests.get(url, timeout=3, stream=True)
        if resp_get.status_code < 400:
            resp_get.close()
            return True
    except:
        pass
    return False

def main(page: ft.Page):
    page.title = "Painel de Controle Tático - Comandante"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.bgcolor = "#1a1a1a"
    page.window_width = 750
    page.window_height = 700

    txt_drive = ft.TextField(
        label="Link do Google Drive (Base):",
        value="https://drive.google.com/uc?id=1kk-OsN3R02flYm2Nl0kYZ7qI3JdzhwB_&export=download",
        text_size=12,
        color="#00ffcc",
        border_color="#00ffcc",
        focused_border_color="#00ffcc",
        label_style=ft.TextStyle(color="white")
    )

    txt_mestre = ft.TextField(
        label="Link da Fonte Mestre (br.m3u):",
        value="https://raw.githubusercontent.com/iptv-org/iptv/master/streams/br.m3u",
        text_size=12,
        color="#00ffcc",
        border_color="#00ffcc",
        focused_border_color="#00ffcc",
        label_style=ft.TextStyle(color="white")
    )

    log_lv = ft.ListView(expand=1, spacing=5, auto_scroll=True)
    log_container = ft.Container(
        content=log_lv,
        bgcolor="#111111",
        border_radius=8,
        padding=10,
        height=250
    )

    def registrar_log(mensagem):
        log_lv.controls.append(ft.Text(mensagem, color="#33ff33", font_family="Consolas", size=11))
        page.update()

    def baixar_lista_do_drive(link_drive):
        registrar_log("A ligar ao Google Drive do Comandante...")
        try:
            resposta = requests.get(link_drive, timeout=15)
            if resposta.status_code == 200:
                registrar_log("Lista do Drive descarregada com sucesso!")
                return resposta.text.splitlines()
            else:
                registrar_log(f"Erro ao aceder ao Drive (Estado: {resposta.status_code})")
                return []
        except Exception as e:
            registrar_log(f"Falha na ligação com o Drive: {e}")
            return []

    def caçar_links_iptv_org(link_mestre):
        links_finais = {}
        registrar_log("Caçador focado no repositório mestre com Teste de Pulso Resiliente...")
        try:
            resposta = requests.get(link_mestre, timeout=20)
            if resposta.status_code != 200:
                registrar_log(f"❌ Erro ao aceder à fonte mestre (Estado: {resposta.status_code})")
                return links_finais
                
            linhas = resposta.text.splitlines()
            for idx, linha in enumerate(linhas):
                if linha.startswith("#EXTINF"):
                    match = re.search(r',(.+)$', linha)
                    if not match: continue
                    nome_bruto_git = match.group(1).strip()
                    nome_limpo_git = limpar_nome(nome_bruto_git)
                    
                    for alvo in CANAIS_ALVO:
                        if alvo in links_finais: continue
                        alvo_limpo = limpar_nome(alvo)
                        
                        match_exato = False
                        if alvo_limpo == "viva":
                            if nome_limpo_git == "viva":
                                match_exato = True
                        else:
                            if alvo_limpo == nome_limpo_git or (len(alvo_limpo) > 3 and alvo_limpo in nome_limpo_git):
                                match_exato = True
                                
                        if match_exato:
                            if idx + 1 < len(linhas):
                                link_candidato = linhas[idx + 1].strip()
                                if link_candidato.startswith("http"):
                                    registrar_log(f"[TESTANDO] Pulso de {alvo}...")
                                    if testar_link_ativo(link_candidato):
                                        links_finais[alvo] = {
                                            "link": link_candidato,
                                            "extinf_original": injetar_marcador_vlc(linha, link_candidato),
                                            "nome_bruto": nome_bruto_git
                                        }
                                        registrar_log(f"✅ [VALIDADO] Canal {alvo} operacional")
                                    else:
                                        registrar_log(f"⚠️ [MORTO] Link de {alvo} sem resposta, ignorado.")
                                    break
        except Exception as e:
            registrar_log(f"Erro durante a caçada: {e}")
        return links_finais

    def gerenciar_fortaleza():
        btn_disparar.disabled = True
        page.update()
        try:
            link_drive_atual = txt_drive.value.strip()
            link_mestre_atual = txt_mestre.value.strip()

            os.makedirs(PASTA_DESTINO, exist_ok=True)
            
            conteudo_base = baixar_lista_do_drive(link_drive_atual)
            if not conteudo_base and os.path.exists("lista.txt"):
                registrar_log("A usar a lista local de segurança.")
                with open("lista.txt", "r", encoding="utf-8") as f:
                    conteudo_base = f.read().splitlines()

            if not conteudo_base:
                registrar_log("Sem dados para processar.")
                btn_disparar.disabled = False
                page.update()
                return
            
            novos_links = caçar_links_iptv_org(link_mestre_atual)
            lista_canais_atualizada = []
            canais_encontrados_na_base = set()
            
            i = 0
            while i < len(conteudo_base):
                linha = conteudo_base[i].strip()
                if not linha:
                    lista_canais_atualizada.append("\n")
                    i += 1
                    continue
                    
                if linha.upper().startswith("IMG="):
                    lista_canais_atualizada.append(f"{linha}\n")
                    i += 1
                    continue

                if linha.startswith("#EXTINF"):
                    if ", AUTO" in linha or ",AUTO" in linha:
                        # Pega o link da linha seguinte para checagem do marcador
                        proximo_link = conteudo_base[i+1].strip() if i + 1 < len(conteudo_base) else ""
                        lista_canais_atualizada.append(f"{injetar_marcador_vlc(linha, proximo_link)}\n")
                        if i + 1 < len(conteudo_base):
                            lista_canais_atualizada.append(f"{proximo_link}\n")
                        i += 2
                        continue
                    
                    match = re.search(r'#EXTINF:.*,\s*(.*)', linha)
                    if match:
                        nome_canal_lista = match.group(1).strip()
                        if nome_canal_lista in CANAIS_ALVO:
                            canais_encontrados_na_base.add(nome_canal_lista)
                            proximo_link = ""
                            if nome_canal_lista in novos_links:
                                proximo_link = novos_links[nome_canal_lista]['link']
                            elif i + 1 < len(conteudo_base):
                                proximo_link = conteudo_base[i+1].strip()
                                
                            lista_canais_atualizada.append(f"{injetar_marcador_vlc(linha, proximo_link)}\n")
                            lista_canais_atualizada.append(f"{proximo_link}\n")
                            i += 2
                            continue

                # Linha genérica restante
                proximo_link_gen = conteudo_base[i+1].strip() if i + 1 < len(conteudo_base) else ""
                lista_canais_atualizada.append(f"{injetar_marcador_vlc(linha, proximo_link_gen)}\n")
                i += 1

            adicionados_novos = 0
            for canal, dados in novos_links.items():
                if canal not in canais_encontrados_na_base:
                    lista_canais_atualizada.append(f"\n{dados['extinf_original']}\n")
                    lista_canais_atualizada.append(f"{dados['link']}\n")
                    adicionados_novos += 1
                    registrar_log(f"➕ [ADICIONADO] Novo canal: {canal}")

            caminho_arquivo_final = os.path.join(PASTA_DESTINO, "lista.txt")
            with open(caminho_arquivo_final, "w", encoding="utf-8") as f:
                f.writelines(lista_canais_atualizada)
                
            registrar_log(f"Sincronização concluída! {adicionados_novos} novos canais adicionados. Salvo em: {caminho_arquivo_final}")
        except Exception as e:
            registrar_log(f"Erro crítico no processo: {e}")
        
        btn_disparar.disabled = False
        page.update()

    def iniciar_tarefa(e):
        log_lv.controls.clear()
        threading.Thread(target=gerenciar_fortaleza, daemon=True).start()

    def abrir_pasta(e):
        caminho_pasta = os.path.abspath(PASTA_DESTINO)
        if os.path.exists(caminho_pasta):
            os.startfile(caminho_pasta)
        else:
            registrar_log("A pasta de resultado ainda não foi criada.")

    btn_disparar = ft.ElevatedButton(
        content=ft.Text("🚀 Disparar Robô (Caça & Teste de Pulso)", color="white"),
        on_click=iniciar_tarefa,
        bgcolor="#00a86b"
    )

    btn_pasta = ft.ElevatedButton(
        content=ft.Text("📂 Abrir Pasta 'resultado'", color="white"),
        on_click=abrir_pasta,
        bgcolor="#0066cc"
    )

    page.add(
        ft.Text("Painel do Comandante - Sincronizador IPTV (Flet)", size=16, weight="bold", color="#00ffcc"),
        ft.Divider(color="#333333"),
        txt_drive,
        txt_mestre,
        ft.Row([btn_disparar, btn_pasta], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        ft.Text("Logs da Operação:", size=12, color="#ffaa00", weight="bold"),
        log_container
    )

if __name__ == "__main__":
    ft.app(target=main)