# -*- coding: utf-8 -*-
"""Hook-portao do ocombo (zero tokens): roda o portao do projeto e BLOQUEIA com exit 2.

Instalar por projeto (o dono decide): copie para .claude/hooks/portao-hook.py e cole
assets/hooks.exemplo.json em .claude/settings.json (ou passe por `claude --settings hooks.json`).
O comando do portao vem da variavel OCOMBO_PORTAO (padrao: `python prova.py`).
OCOMBO_HOOK_LOG (opcional): arquivo onde cada disparo anota "<modo> <exit>" — e a prova ao vivo.

Modos:  pre   (PreToolUse Bash(git commit*): exit 2 impede o commit; v4)
        post  (PostToolUse Edit|Write: a saida vermelha cai no contexto do agente na hora;
              a doc avisa que PostToolUse nao desfaz a edicao, so realimenta)
        stop  (Stop: impede o agente de terminar com o portao vermelho; exit 2 + JSON
              {"decision":"block","reason":...}; respeita stop_hook_active para nao entrar em laco)
Regra da doc: exit 2 bloqueia; exit 1 e "non-blocking" e o agente para do mesmo jeito.
"""
import json
import os
import subprocess
import sys


def _log(modo, code):
    arq = os.environ.get('OCOMBO_HOOK_LOG')
    if arq:
        with open(arq, 'a', encoding='utf-8') as f:
            f.write('%s %d\n' % (modo, code))


def main(modo):
    try:
        entrada = json.load(sys.stdin)
    except ValueError:
        entrada = {}
    if modo == 'stop' and entrada.get('stop_hook_active'):
        _log(modo, 0)
        return 0  # ja estamos dentro de um bloqueio anterior: nao insistir
    cmd = os.environ.get('OCOMBO_PORTAO', 'python prova.py')
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, errors='replace')
    if r.returncode == 0:
        _log(modo, 0)
        return 0
    cauda = ((r.stdout or '') + (r.stderr or '')).strip()[-1500:]
    if modo == 'stop':
        print(json.dumps({'decision': 'block',
                          'reason': 'Portao VERMELHO (exit %d). Corrija antes de terminar:\n%s'
                                    % (r.returncode, cauda)}))
    else:
        sys.stderr.write('Portao VERMELHO apos a edicao (exit %d):\n%s\n' % (r.returncode, cauda))
    _log(modo, 2)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'post'))
