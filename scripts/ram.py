# -*- coding: utf-8 -*-
"""v14 (04/10/2026): regra da RAM livre. Quantos `claude -p` (juiz, dupla, fecho, criterio do portao)
cabem juntos AGORA. Medido em 04/10/2026 numa máquina: cada `claude -p` ~330 MB + MCPs herdados
(dois MCPs) ~400 MB; o portao grande morreu 2x por memoria com 1,2 GB livres.

Uso: python ram.py [--por MB] [--teto N]   -> imprime a linha `RAM livre` do ESTADO; exit 0.
"""
import argparse
import ctypes
import sys

RESERVA_MB = 1500   # Windows + o que o dono esta usando
POR_MB = 750        # um claude -p com MCPs
APERTO_MB = 3000    # abaixo disso o juiz sobe sem MCP (OCOMBO_SEM_MCP=1)
TETO = 4            # nunca mais trabalhadores do que o juiz consegue julgar (paralelismo.md)


def vagas(livre_mb, por=POR_MB, teto=TETO):
    """Quantos trabalhadores pesados ao mesmo tempo; nunca menos de 1 (um por vez)."""
    return max(1, min(teto, int((livre_mb - RESERVA_MB) // por)))


def sem_mcp(livre_mb):
    return livre_mb < APERTO_MB


def linha(livre_mb, por=POR_MB, teto=TETO):
    n = vagas(livre_mb, por, teto)
    modo = 'um por vez (--so=cN)' if n == 1 else 'paralelo'
    extra = '; juiz sem MCP (OCOMBO_SEM_MCP=1)' if sem_mcp(livre_mb) else ''
    return 'RAM livre   : %d MB -> vagas %d, %s%s' % (livre_mb, n, modo, extra)


def livre_mb():
    """RAM fisica livre agora. Windows: GlobalMemoryStatusEx; fora dele, /proc/meminfo."""
    if sys.platform == 'win32':
        class MS(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullAvailPhys // (1024 * 1024))
    with open('/proc/meminfo') as f:
        for l in f:
            if l.startswith('MemAvailable:'):
                return int(l.split()[1]) // 1024
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='Regra da RAM livre do ocombo (v14)')
    ap.add_argument('--por', type=int, default=POR_MB)
    ap.add_argument('--teto', type=int, default=TETO)
    a = ap.parse_args(argv)
    print(linha(livre_mb(), a.por, a.teto))
    return 0


if __name__ == '__main__':
    sys.exit(main())
