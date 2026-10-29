# -*- coding: utf-8 -*-
"""Gera o espelho publico da skill ocombo a partir da copia de trabalho (fonte unica).

Uso: python tools/publicar.py [--origem <pasta da skill>] [--mapa <json>] [--checar]

- copia SKILL.md, prova.py, scripts/, assets/, references/ da origem para a raiz deste repo,
  normalizando CRLF -> LF e pulando caches (__pycache__, .ruff_cache);
- aplica, na ordem, as substituicoes do mapa (arquivo JSON LOCAL, fora do repo: por padrao
  ~/.claude/ocombo-publicar.json) — e assim que nomes, caminhos e projetos privados ficam de fora;
  a lista 'excluir' do mapa deixa arquivos inteiros fora do espelho (dossies de projeto) e a lista 'cortar'
  (regex por linha, so .md/.txt) tira entradas de lista privadas com as continuacoes indentadas;
- o commit e do autor: identidade LOCAL do repo (git config user.email = noreply do GitHub) e mensagem
  sem trailer de sessao — tools/prova_repo.py reprova a historia se algum commit fugir disso;
- espelha de verdade: arquivo que sumiu da origem some do repo;
- imprime caminho + sha256 de cada arquivo e sai 1 se alguma substituicao nao casou em lugar nenhum
  (mapa desatualizado) ou se sobrou termo proibido (a varredura e a mesma de tools/prova_repo.py).
- `--checar` nao grava nada: so compara e sai 0 (igual) ou 1 (repo atrasado).

Quem nao tem o mapa (qualquer pessoa que clonou o repo) nao precisa deste script: ele existe para o
autor republicar com um comando. Sem o mapa ele copia sem substituir.
"""
import hashlib
import json
import os
import re
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
MAPA_PADRAO = os.path.join(os.path.expanduser('~'), '.claude', 'ocombo-publicar.json')
ORIGEM_PADRAO = os.path.join(os.path.expanduser('~'), '.claude', 'skills', 'ocombo')
GERENCIADOS = ('SKILL.md', 'prova.py', 'scripts', 'assets', 'references')
TEXTO = ('.md', '.py', '.txt', '.json', '.js', '.mjs', '.bat', '.sh', '.yml', '.yaml', '.cfg', '.toml')
IGNORAR_PASTAS = ('__pycache__', '.ruff_cache', '.pytest_cache', 'node_modules', '.git')


def sha256(dados):
    return hashlib.sha256(dados).hexdigest()


def listar(origem, excluir=()):
    """Arquivos gerenciados relativos a origem (sem caches, sem os 'excluir' do mapa), ordenados."""
    achados = []
    for g in GERENCIADOS:
        cam = os.path.join(origem, g)
        if os.path.isfile(cam):
            achados.append(g)
        elif os.path.isdir(cam):
            for raiz, pastas, arqs in os.walk(cam):
                pastas[:] = [p for p in pastas if p not in IGNORAR_PASTAS]
                for a in arqs:
                    achados.append(os.path.relpath(os.path.join(raiz, a), origem).replace('\\', '/'))
    return sorted(a for a in achados if a not in set(excluir))


def cortar(texto, cortes, usadas):
    """Tira do texto cada linha que casa um regex de 'cortar' e as continuacoes indentadas logo abaixo
    (uma entrada de lista em varias linhas sai inteira). usadas recebe o indice de cada regex que casou."""
    rxs = [re.compile(c) for c in cortes]
    saida, pulando = [], False
    for linha in texto.split('\n'):
        if pulando and linha[:1] in (' ', '\t'):
            continue
        pulando = False
        for i, rx in enumerate(rxs):
            if rx.search(linha):
                usadas.add(i)
                pulando = True
                break
        if not pulando:
            saida.append(linha)
    return '\n'.join(saida)


def transformar(dados, rel, substituicoes, usadas, cortes=(), cortes_usados=None):
    """Aplica LF + cortes (so .md/.txt) + substituicoes num arquivo de texto; binarios passam intactos."""
    if not rel.endswith(TEXTO):
        return dados
    texto = dados.decode('utf-8').replace('\r\n', '\n')
    if cortes and rel.endswith(('.md', '.txt')):
        texto = cortar(texto, cortes, cortes_usados if cortes_usados is not None else set())
    for i, (de, para) in enumerate(substituicoes):
        if de in texto:
            texto = texto.replace(de, para)
            usadas.add(i)
    return texto.encode('utf-8')


def carregar_mapa(caminho):
    if not caminho or not os.path.exists(caminho):
        return {'substituicoes': [], 'proibidos': [], 'excluir': [], 'cortar': []}
    with open(caminho, encoding='utf-8') as f:
        m = json.load(f)
    return {'substituicoes': [tuple(p) for p in m.get('substituicoes', [])],
            'proibidos': list(m.get('proibidos', [])),
            'excluir': list(m.get('excluir', [])),
            'cortar': list(m.get('cortar', []))}


def publicar(origem, repo, mapa, checar=False):
    """Devolve (linhas_relatorio, problemas). problemas vazio = verde."""
    problemas, linhas, usadas, cortes_usados = [], [], set(), set()
    subs = mapa['substituicoes']
    cortes = list(mapa.get('cortar', []))
    excluir = list(mapa.get('excluir', []))
    for rel in excluir:  # 'excluir' aponta arquivo REAL da origem; nome errado = mapa desatualizado
        if not os.path.isfile(os.path.join(origem, rel)):
            problemas.append('arquivo de "excluir" nao existe na origem (mapa desatualizado): ' + rel)
    relativos = listar(origem, excluir)
    if not relativos:
        return linhas, ['origem sem arquivos gerenciados: ' + origem]
    gerados = {}
    for rel in relativos:
        with open(os.path.join(origem, rel), 'rb') as f:
            bruto = f.read()
        gerados[rel] = transformar(bruto, rel, subs, usadas, cortes, cortes_usados)
    for i, (de, _) in enumerate(subs):
        if i not in usadas:
            problemas.append('substituicao nao casou em nenhum arquivo (mapa desatualizado): %r' % de)
    for i, c in enumerate(cortes):
        if i not in cortes_usados:
            problemas.append('corte nao casou em nenhuma linha (mapa desatualizado): %r' % c)
    # espelho: o que esta no repo dentro das pastas gerenciadas e nao veio da origem, sai
    atuais = set(listar(repo))
    sobras = sorted(atuais - set(gerados))
    diferentes = []
    for rel, dados in gerados.items():
        alvo = os.path.join(repo, rel)
        igual = os.path.exists(alvo) and open(alvo, 'rb').read() == dados
        if not igual:
            diferentes.append(rel)
        linhas.append('%s  %s  %d bytes%s' % (sha256(dados)[:16], rel, len(dados), '' if igual else '  (novo/alterado)'))
    if checar:
        if diferentes or sobras:
            problemas.append('repo atrasado: %d alterado(s), %d sobra(s): %s' % (
                len(diferentes), len(sobras), ', '.join(diferentes + sobras)[:400]))
        return linhas, problemas
    for rel in diferentes:
        alvo = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(alvo), exist_ok=True)
        with open(alvo, 'wb') as f:
            f.write(gerados[rel])
    for rel in sobras:
        os.remove(os.path.join(repo, rel))
        linhas.append('removido (sumiu da origem): ' + rel)
    for g in GERENCIADOS:
        for raiz, pastas, _ in os.walk(os.path.join(repo, g)):
            for p in list(pastas):
                if p in IGNORAR_PASTAS:
                    shutil.rmtree(os.path.join(raiz, p), ignore_errors=True)
                    pastas.remove(p)
    return linhas, problemas


def main(argv):
    origem, mapa_cam, checar = ORIGEM_PADRAO, MAPA_PADRAO, False
    a = list(argv)
    while a:
        x = a.pop(0)
        if x == '--origem':
            origem = a.pop(0)
        elif x == '--mapa':
            mapa_cam = a.pop(0)
        elif x == '--checar':
            checar = True
        else:
            print(__doc__)
            return 2
    mapa = carregar_mapa(mapa_cam)
    print('[publicar] origem=%s  mapa=%s (%d substituicoes)  %s' % (
        origem, mapa_cam if os.path.exists(mapa_cam) else '(sem mapa)', len(mapa['substituicoes']),
        'CHECAR' if checar else 'GRAVAR'))
    linhas, problemas = publicar(origem, REPO, mapa, checar=checar)
    for ln in linhas:
        print('  ' + ln)
    if not checar and not problemas:
        # varredura final com o mesmo portao do repo (termos proibidos + dados pessoais)
        sys.dont_write_bytecode = True
        sys.path.insert(0, AQUI)
        import prova_repo
        problemas += prova_repo.varrer(REPO, mapa['proibidos'])
    for p in problemas:
        print('  FAIL ' + p)
    print('[publicar] %d arquivo(s), %d problema(s)' % (len(linhas), len(problemas)))
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
