# -*- coding: utf-8 -*-
"""Prova AO VIVO do hook Stop (custa alguns centavos, Haiku): cria um projeto temporario com o portao-hook
instalado via --settings, um portao que SEMPRE falha e um log; roda `claude -p` e confere que o Stop
disparou, bloqueou (exit 2 / decision block) e o Claude continuou (mais de 1 turno).

Doc: "Without --bare, a -p session runs the hooks in a project's .claude/settings.json" e --settings
"Values you set here override the same keys ... for this session" (code.claude.com/docs/en/headless,
cli-reference). Uso: python prova_hook_vivo.py [modelo]   (exit 0 = provado)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(AQUI, '..', 'assets', 'portao-hook.py')


def main(modelo='claude-haiku-4-5-20251001'):
    d = tempfile.mkdtemp(prefix='ocombo-hook-')
    try:
        os.makedirs(os.path.join(d, '.claude', 'hooks'))
        shutil.copyfile(HOOK, os.path.join(d, '.claude', 'hooks', 'portao-hook.py'))
        log = os.path.join(d, 'hook.log')
        # `python` do PATH e barras normais: o comando do hook roda num shell e caminho Windows com
        # barra invertida (sys.executable) nao chegou a executar (2a tentativa, 05/09/2026)
        settings = {'hooks': {'Stop': [{'hooks': [{'type': 'command',
                    'command': 'python .claude/hooks/portao-hook.py stop'}]}]}}
        # Historico (05/09/2026): 1a tentativa com `--settings <arquivo>` e 2a com .claude/settings.json do
        # projeto, ambas com o comando em sys.executable (barra invertida) -> log vazio. A 3a, com
        # `python` do PATH, bloqueou. Causa provada = o caminho; `--settings` nao foi retestado.
        sp = os.path.join(d, '.claude', 'settings.json')
        with open(sp, 'w', encoding='utf-8') as f:
            json.dump(settings, f)
        env = dict(os.environ, OCOMBO_PORTAO=sys.executable + ' -c "print(\'PORTAO FALSO VERMELHO\');raise SystemExit(1)"',
                   OCOMBO_HOOK_LOG=log)
        cmd = os.path.join(os.environ.get('APPDATA', ''), 'npm', 'claude.cmd')
        cmd = cmd if os.path.exists(cmd) else 'claude'
        r = subprocess.run([cmd, '-p', 'Responda apenas a palavra: ok', '--model', modelo,
                            '--max-turns', '3', '--output-format', 'json', '--no-session-persistence',
                            '--debug', 'hooks'],
                           cwd=d, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           errors='replace', timeout=600)
        try:
            resp = json.loads(r.stdout)
        except ValueError:
            resp = {'raw': r.stdout[-500:], 'stderr': r.stderr[-500:]}
        registro = open(log, encoding='utf-8').read() if os.path.exists(log) else ''
        bloqueou = 'stop 2' in registro
        print('[hook-vivo] modelo=%s turnos=%s subtype=%s usd=%s' % (
            modelo, resp.get('num_turns'), resp.get('subtype'), resp.get('total_cost_usd')))
        print('[hook-vivo] log do hook:\n' + (registro.strip() or '(vazio)'))
        print('[hook-vivo] Stop bloqueou com exit 2: %s' % ('SIM' if bloqueou else 'NAO'))
        if not bloqueou:
            print('[hook-vivo] resposta bruta:', json.dumps(resp)[:400])
            print('[hook-vivo] stderr (--debug hooks), cauda:\n' + r.stderr[-1500:])
        return 0 if bloqueou else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'claude-haiku-4-5-20251001'))
