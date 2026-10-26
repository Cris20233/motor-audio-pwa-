


{
  "cena_1": {
    "fundo_visual": "floresta_dia.mp4",
    "som_ambiente": "passaros_e_vento",
    "volume_ambiente": 0.2,
    "fala": {
      "tipo": "narrador",
      "voz": "voz_masculina_1",
      "texto": "O dia começava tranquilo na floresta."
    }
  },
  "cena_2": {
    "fundo_visual": "raposa_olhando.mp4",
    "som_ambiente": "passaros_e_vento",
    "fala": {
      "tipo": "personagem",
      "voz": "voz_feminina_jovem",
      "texto": "Quem está se aproximando?"
    }
  }
}
Quando o backend lê esse arquivo, ele:
Gera a fala do narrador (descobre que durou 4,2 segundos).
Corta o vídeo de fundo para exatamente 4,2 segundos.
Aplica o som de pássaros com volume mais baixo durante a fala.
Passa para a próxima cena e, no final, concatena tudo em um único .mp4.
Quer que eu monte o script em Python que faz essa junção automática de uma cena teste (áudio + vídeo + som de fundo) para você ver o motor funcionando na prática?
Sim


Thoughts
Aqui está a estrutura prática do script em Python que funciona como o motor desse backend.
A lógica é exatamente a que você pensou: ele lê os blocos do roteiro, gera a voz (usando Edge-TTS, que é gratuito e de altíssima qualidade), descobre a duração exata da fala, ajusta o som ambiente com redução automática de volume (audio ducking) e monta o clipe final em MP4 via FFmpeg.
Dependências necessárias
Para rodar este teste na sua máquina ou servidor:
pip install edge-tts
# Certifique-se de ter o FFmpeg instalado no sistema operacional (ex: apt install ffmpeg ou brew install ffmpeg)
O Script do Motor (engine_cena.py)
import asyncio
import json
import os
import subprocess
import edge_tts

# 1. Configuração das vozes gratuitas em Português (Brasil)
# Você pode variar tom (pitch) e velocidade (rate) para criar idades/estilos diferentes
VOZES = {
    # Masculinas
    "homem_narrador": {"voice": "pt-BR-AntonioNeural", "rate": "+0%", "pitch": "-5Hz"},
    "homem_jovem": {"voice": "pt-BR-AntonioNeural", "rate": "+5%", "pitch": "+15Hz"},
    # Femininas
    "mulher_narradora": {"voice": "pt-BR-FranciscaNeural", "rate": "+0%", "pitch": "+0Hz"},
    "mulher_jovem": {"voice": "pt-BR-FranciscaNeural", "rate": "+8%", "pitch": "+20Hz"},
}


async def gerar_audio_fala(texto: str, perfil_voz: str, output_path: str):
    """Gera o áudio da fala/narração usando Edge-TTS gratuito."""
    config = VOZES.get(perfil_voz, VOZES["homem_narrador"])
    communicate = edge_tts.Communicate(
        text=texto,
        voice=config["voice"],
        rate=config["rate"],
        pitch=config["pitch"],
    )
    await communicate.save(output_path)


def obter_duracao_audio(audio_path: str) -> float:
    """Usa o FFprobe para pegar a duração exata do áudio gerado."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    resultado = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(resultado.stdout.strip())


def montar_cena_mp4(
    video_fundo: str,
    audio_fala: str,
    som_natureza: str,
    output_mp4: str,
    duracao: float,
):
    """Junta o vídeo, a fala e o som de fundo com ajuste de volume (ducking)

    cortando exatamente no tempo da fala (com margem de 0.5s de respiro).
    """
    duracao_total = duracao + 0.5  # pequeno respiro ao final da fala

    # Comando FFmpeg que:
    # 1. Corta o vídeo de fundo no tempo exato da fala
    # 2. Reduz o volume do som de natureza para 15% (volume=0.15)
    # 3. Sobrepõe a fala (volume 100%) com a natureza (amix)
    # 4. Gera o MP4 sincronizado
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "0",
        "-t",
        str(duracao_total),
        "-i",
        video_fundo,  # [0:v]
        "-i",
        audio_fala,  # [1:a] fala
        "-stream_loop",
        "-1",
        "-i",
        som_natureza,  # [2:a] natureza em loop
        "-filter_complex",
        (
            f"[2:a]volume=0.15[bg];"  # Abaixa o som da natureza
            f"[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"  # Mixa os áudios
        ),
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        output_mp4,
    ]

    subprocess.run(cmd, check=True)
    print(f"✅ Cena gerada com sucesso: {output_mp4} ({duracao_total:.2f}s)")


async def processar_bloco_cena(cena_config: dict, output_dir: str = "temp"):
    os.makedirs(output_dir, exist_ok=True)

    fala_path = os.path.join(output_dir, "fala_temp.mp3")
    video_final_cena = os.path.join(output_dir, "cena_final.mp4")

    # 1. Gera a fala do personagem ou narrador
    print(f"🎙️ Gerando voz ({cena_config['voz']}): \"{cena_config['texto']}\"")
    await gerar_audio_fala(
        cena_config["texto"], cena_config["voz"], fala_path
    )

    # 2. Descobre a duração exata da fala
    duracao = obter_duracao_audio(fala_path)
    print(f"⏱️ Duração calculada automaticamente: {duracao:.2f} segundos")

    # 3. Renderiza a cena sincronizada
    montar_cena_mp4(
        video_fundo=cena_config["video_fundo"],
        audio_fala=fala_path,
        som_natureza=cena_config["som_natureza"],
        output_mp4=video_final_cena,
        duracao=duracao,
    )


# --- TESTE PRÁTICO ---
if __name__ == "__main__":
    # Exemplo do JSON que o seu PWA enviaria para o backend:
    bloco_teste = {
        "texto": "No coração da floresta, o silêncio só é quebrado pelo cantar dos pássaros e o vento entre as folhas.",
        "voz": "homem_narrador",  # Opções: homem_narrador, homem_jovem, mulher_narradora, mulher_jovem
        "video_fundo": "assets/floresta.mp4",  # Vídeo bruto de fundo
        "som_natureza": "assets/passaros_e_vento.mp3",  # Efeito de ambiente
    }

    asyncio.run(processar_bloco_cena(bloco_teste))
O que esse script resolve automaticamente:
Elimina a régua manual de tempo: Você não precisa cortar o vídeo de fundo na mão. O código mede a fala e diz ao FFmpeg: "corte o vídeo exatamente no segundo em que a fala terminar".
Resolve o conflito de áudio (Ducking): A linha volume=0.15 garante que os sons da natureza fiquem sutis ao fundo, sem cobrir a narração.
Escalável para múltiplos personagens: Mudando apenas o parâmetro "voz", o sistema altera a persona do áudio sem que o usuário precise abrir outro gerador de voz.
Para transformar isso em um vídeo longo com várias cenas, basta colocar esse processo em um laço de repetição (for cena in cenas:) e, no final, usar o FFmpeg para concatenar todos os arquivos .mp4 gerados em uma única chamada.
Quer que eu detalhe como o PWA no navegador se comunicaria com esse backend (por exemplo, a tela de blocos em HTML/JavaScript)?
Sim isso é importante


Thoughts
Para o seu PWA funcionar de forma fluida e sem atrito, a arquitetura é dividida em duas partes conectadas por uma API simples:
Frontend (PWA no navegador): Uma interface em blocos onde o criador monta a história sem pensar em linha do tempo.
Backend (API em Python com FastAPI): Recebe o JSON com os blocos, roda o motor com edge-tts e ffmpeg, junta todas as cenas e devolve o vídeo pronto.
Abaixo está a estrutura prática para o seu MVP.
1. O Backend: API em FastAPI (main.py)
O FastAPI recebe a lista de cenas do navegador, processa cada uma em fila e gera o MP4 concatenado final.
import os
import subprocess
from engine_cena import processar_bloco_cena
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# Permite que o PWA faça requisições para a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class BlocoCena(BaseModel):
    texto: str
    voz: str
    som_natureza: str
    video_fundo: str


class ProjetoRoteiro(BaseModel):
    cenas: list[BlocoCena]


@app.post("/api/gerar-video")
async def gerar_video_completo(projeto: ProjetoRoteiro):
    os.makedirs("output_temp", exist_ok=True)
    lista_cenas_mp4 = []

    # 1. Processa cada bloco de cena individualmente
    for i, cena in enumerate(projeto.cenas):
        nome_cena = f"output_temp/cena_{i}.mp4"
        cena_dict = cena.dict()

        # Chama a função que criamos no script anterior
        await processar_bloco_cena(cena_dict, output_dir=f"output_temp/bloco_{i}")
        # Move ou referencia o arquivo final gerado
        lista_cenas_mp4.append(f"output_temp/bloco_{i}/cena_final.mp4")

    # 2. Concatena todos os blocos em um único MP4
    concat_txt = "output_temp/concat_list.txt"
    with open(concat_txt, "w") as f:
        for caminho in lista_cenas_mp4:
            f.write(f"file '{os.path.abspath(caminho)}'\n")

    video_final = "output_temp/resultado_final.mp4"
    cmd_concat = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_txt,
        "-c",
        "copy",
        video_final,
    ]
    subprocess.run(cmd_concat, check=True)

    # 3. Retorna o MP4 final para download/pré-visualização no PWA
    return FileResponse(video_final, media_type="video/mp4", filename="meu_video.mp4")
2. O Frontend: Interface em Blocos (index.html)
Uma interface limpa focada em cards/blocos. Cada bloco representa uma cena com seus seletores de voz e ambiente.
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gerador Linear de Vídeo</title>
  <!-- Habilita recursos de PWA -->
  <link rel="manifest" href="manifest.json">
  <style>
    body { font-family: system-ui, sans-serif; background: #f4f6f8; padding: 20px; max-width: 700px; margin: auto; }
    .card { background: white; padding: 16px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    textarea { width: 100%; height: 70px; margin-top: 8px; box-sizing: border-box; }
    .grid { display: flex; gap: 10px; margin-top: 8px; }
    select { flex: 1; padding: 8px; }
    button { padding: 10px 16px; border-radius: 6px; cursor: pointer; border: none; font-weight: bold; }
    .btn-add { background: #e2e8f0; color: #1a202c; }
    .btn-render { background: #2b6cb0; color: white; width: 100%; font-size: 16px; margin-top: 15px; }
    #status { margin-top: 15px; font-weight: bold; text-align: center; }
  </style>
</head>
<body>

  <h2>Criador Linear de Cenas</h2>
  <div id="container-cenas"></div>

  <button class="btn-add" onclick="adicionarBloco()">+ Adicionar Bloco de Cena</button>
  <button class="btn-render" onclick="enviarParaRenderizar()">Gerar Vídeo Completo (MP4)</button>

  <p id="status"></p>
  <video id="player" controls style="width: 100%; display: none; margin-top: 15px;"></video>

  <script>
    let contadorCenas = 0;

    function adicionarBloco() {
      contadorCenas++;
      const div = document.createElement("div");
      div.className = "card";
      div.id = `cena-${contadorCenas}`;
      div.innerHTML = `
        <strong>Cena #${contadorCenas}</strong>
        <textarea placeholder="Digite a fala ou narração aqui..." class="texto-cena"></textarea>
        <div class="grid">
          <select class="voz-cena">
            <option value="homem_narrador">Voz: Narrador (Masculino)</option>
            <option value="homem_jovem">Voz: Jovem
