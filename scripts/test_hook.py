# -*- coding: utf-8 -*-
"""Prova deterministica do assets/portao-hook.py (sem chamar `claude`): alimenta o hook com o JSON
que o Claude Code envia por stdin e um portao falso via OCOMBO_PORTAO."""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'portao-hook.py')
FALHA = sys.executable + ' -c "import sys;print(\'x FAIL y\');sys.exit(1)"'
PASSA = sys.executable + ' -c "import sys;sys.exit(0)"'


def _roda(modo, portao, entrada):
    env = dict(os.environ, OCOMBO_PORTAO=portao)
    r = subprocess.run([sys.executable, HOOK, modo], input=json.dumps(entrada), env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


class TestHook(unittest.TestCase):
    def test_stop_bloqueia_com_exit_2_e_json(self):
        code, out, err = _roda('stop', FALHA, {'stop_hook_active': False})
        self.assertEqual(code, 2)
        j = json.loads(out)
        self.assertEqual(j['decision'], 'block')
        self.assertIn('x FAIL y', j['reason'])

    def test_stop_respeita_stop_hook_active(self):
        code, out, err = _roda('stop', FALHA, {'stop_hook_active': True})
        self.assertEqual(code, 0)

    def test_post_realimenta_por_stderr_exit_2(self):
        code, out, err = _roda('post', FALHA, {'tool_name': 'Edit'})
        self.assertEqual(code, 2)
        self.assertIn('x FAIL y', err)

    def test_verde_sai_0(self):
        self.assertEqual(_roda('stop', PASSA, {})[0], 0)
        self.assertEqual(_roda('post', PASSA, {})[0], 0)


if __name__ == '__main__':
    unittest.main()
