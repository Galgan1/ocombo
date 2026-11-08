# -*- coding: utf-8 -*-
"""Testes puros da v10: porta de entrada (quais laminas) e papeis como subagentes.

Nao chamam `claude`, nao pedem rede e nao tocam ~/.claude (o destino da instalacao e um tmpdir).
"""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import instalar_agentes as ia
import porta

AQUI = os.path.dirname(os.path.abspath(__file__))


class TestPorta(unittest.TestCase):
    def test_reparo_pontual_dispensa_a_grelha(self):
        d = porta.decidir(pedido='conserta o acento do relatorio', reparo=True, arquivos=1)
        self.assertFalse(d['grelha'])
        self.assertEqual(d['laminas'], ['executor', 'juiz'])
        self.assertEqual(d['papeis']['grelha'], 'dispensada')
        self.assertIn('1 arquivo(s)', '; '.join(d['motivos']))

    def test_peca_nova_obriga_grelha(self):
        d = porta.decidir(pedido='criar um painel novo do zero', arquivos=2)
        self.assertTrue(d['grelha'])
        self.assertEqual(d['laminas'][0], 'grelha')

    def test_palavra_de_producao_levanta_regua_e_lamina(self):
        d = porta.decidir(pedido='deploy do bot na VPS', reparo=True, arquivos=1)
        self.assertIn('producao', d['regua'])
        self.assertTrue(d['grelha'])
        self.assertIn('producao', d['laminas'])

    def test_escopo_largo_obriga_grelha(self):
        d = porta.decidir(pedido='ajusta os modulos', reparo=True, arquivos=porta.LIMIAR_ARQUIVOS)
        self.assertTrue(d['grelha'])

    def test_sem_criterio_de_pronto_obriga_grelha(self):
        d = porta.decidir(pedido='melhora isso ai', reparo=True, arquivos=1, criterio_de_pronto=False)
        self.assertTrue(d['grelha'])

    def test_decisao_em_aberto_obriga_grelha(self):
        d = porta.decidir(pedido='troca a fila', reparo=True, arquivos=1, decisoes_abertas=1)
        self.assertTrue(d['grelha'])

    def test_ordem_nao_desliga_portao_quando_a_regua_e_tocada(self):
        d = porta.decidir(pedido='apagar o backup velho', reparo=True, arquivos=1, forcar='sem-grelha')
        self.assertFalse(d['valida'])
        self.assertTrue(d['grelha'])
        self.assertIn('Portao nao se desliga', d['recusa'])

    def test_ordem_dispensa_mas_fica_escrito_o_que_ela_venceu(self):
        d = porta.decidir(pedido='reescrever o parser', arquivos=2, forcar='sem-grelha')
        self.assertFalse(d['grelha'])
        self.assertIn('apesar de', '; '.join(d['motivos']))

    def test_forcar_grelha_vence_reparo(self):
        d = porta.decidir(pedido='troca o timeout', reparo=True, arquivos=1, forcar='grelha')
        self.assertTrue(d['grelha'])

    def test_regua_desconhecida_invalida(self):
        d = porta.decidir(pedido='x', reparo=True, arquivos=1, regua=['banana'])
        self.assertFalse(d['valida'])

    def test_bloco_do_estado_tem_as_tres_linhas(self):
        linhas = porta.decidir(pedido='x', reparo=True, arquivos=1)['estado'].split('\n')
        self.assertEqual(len(linhas), 3)
        self.assertTrue(linhas[0].startswith('Porta: GRELHA='))
        self.assertTrue(linhas[1].startswith('Laminas: '))
        self.assertTrue(linhas[2].startswith('Papeis: '))

    def test_main_exit_0_e_2(self):
        self.assertEqual(porta.main(['--pedido', 'conserta o typo', '--reparo', '--arquivos', '1']), 0)
        self.assertEqual(porta.main(['--pedido', 'x', '--regua', 'dinheiro', '--forcar', 'sem-grelha']), 2)

    def test_pistas_ignoram_acento(self):
        self.assertIn('producao', porta.pistas('sobe para producao')['regua'])
        self.assertIn('producao', porta.pistas('sobe para produção')['regua'])


# 07/11/2026, o pedido real do experimento do dono: abriu 4 pesquisas e a grelha para uma pagina de uma frase.
PEDIDO_EXPERIMENTO = 'opala. crie um site... www.exemplo.com.br/olamundo.html'


class TestTamanhoV17(unittest.TestCase):
    """v17: o tamanho do pedido vem antes do modo; pedido SIMPLES roda no maximo como modo 1."""

    def test_o_pedido_do_experimento_e_simples(self):
        d = porta.decidir(pedido=PEDIDO_EXPERIMENTO)
        self.assertEqual(d['tamanho'], 'SIMPLES')
        self.assertFalse(d['grelha'])
        self.assertEqual(d['alvos'], ['www.exemplo.com.br/olamundo.html'])

    def test_simples_com_producao_dispensa_a_grelha_e_mantem_a_regua(self):
        d = porta.decidir(pedido=PEDIDO_EXPERIMENTO, novo=True, regua=['producao'])
        self.assertEqual(d['tamanho'], 'SIMPLES')
        self.assertFalse(d['grelha'])
        self.assertTrue(d['valida'])
        self.assertEqual(d['regua'], ['producao'])
        self.assertEqual(d['laminas'], ['executor', 'juiz', 'producao'])
        self.assertIn('ledger', d['estado'])
        self.assertEqual(len(d['estado'].split('\n')), 3)

    def test_modo_alto_vale_1_no_simples(self):
        for pedido_modo in ('10', 'opala', '7', '3+2'):
            self.assertEqual(porta.decidir(pedido=PEDIDO_EXPERIMENTO, modo=pedido_modo)['modo_efetivo'], 1)
        self.assertEqual(porta.decidir(pedido=PEDIDO_EXPERIMENTO, modo='0')['modo_efetivo'], 0)
        self.assertEqual(porta.decidir(pedido=PEDIDO_EXPERIMENTO, modo='f1')['modo_efetivo'], 'f1')
        self.assertIn('modo pedido 10 vale 1', porta.decidir(pedido=PEDIDO_EXPERIMENTO, modo='opala')['estado'])

    def test_modo_fica_inteiro_no_normal(self):
        d = porta.decidir(pedido='criar um painel novo do zero', arquivos=2, modo='opala')
        self.assertEqual(d['tamanho'], 'NORMAL')
        self.assertEqual(d['modo_efetivo'], 10)

    def test_modo_invalido_recusa(self):
        self.assertFalse(porta.decidir(pedido=PEDIDO_EXPERIMENTO, modo='11')['valida'])

    def test_regua_sem_volta_vira_normal(self):
        for r in ('dinheiro', 'apagar', 'terceiro', 'decisao'):
            d = porta.decidir(pedido=PEDIDO_EXPERIMENTO, regua=[r])
            self.assertEqual(d['tamanho'], 'NORMAL', r)
            self.assertTrue(d['grelha'], r)
            self.assertIsNone(d['aviso'], r)

    def test_fatos_declarados_vencem_a_pista_e_avisam(self):
        # os fatos que eu declarei em 07/11: andaime contado como entrega e pronto dado como ausente
        d = porta.decidir(pedido=PEDIDO_EXPERIMENTO, novo=True, arquivos=4, regua=['producao'],
                          criterio_de_pronto=False)
        self.assertEqual(d['tamanho'], 'NORMAL')
        self.assertTrue(d['grelha'])
        self.assertIn('andaime', d['aviso'])
        self.assertIn('linha', d['aviso'])

    def test_sem_alvo_concreto_e_normal_salvo_declarado(self):
        self.assertEqual(porta.decidir(pedido='melhora o desempenho do painel')['tamanho'], 'NORMAL')
        d = porta.decidir(pedido='troca a cor do botao de compra para verde', simples=True, arquivos=1)
        self.assertEqual(d['tamanho'], 'SIMPLES')
        self.assertFalse(d['grelha'])

    def test_dois_alvos_ou_escopo_largo_e_normal(self):
        self.assertEqual(porta.decidir(pedido='crie a.html e b.html')['tamanho'], 'NORMAL')
        self.assertEqual(porta.decidir(pedido='migre o painel inteiro para painel.js')['tamanho'], 'NORMAL')

    def test_forcar_grelha_leva_o_simples_ao_caminho_completo(self):
        d = porta.decidir(pedido=PEDIDO_EXPERIMENTO, forcar='grelha')
        self.assertEqual(d['tamanho'], 'NORMAL')
        self.assertTrue(d['grelha'])

    def test_alvos_ignoram_tecnologia_email_e_numero(self):
        self.assertEqual(porta.alvos('crie um app em node.js'), [])
        self.assertEqual(porta.alvos('mande para joao@' + 'exemplo.com.br'), [])
        self.assertEqual(porta.alvos('suba para a versao 3.5'), [])
        self.assertEqual(porta.alvos('conserta o porta.py e o porta.py'), ['porta.py'])

    def test_cli_imprime_o_caminho_simples_e_o_modo(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            rc = porta.main(['--pedido', PEDIDO_EXPERIMENTO, '--modo', 'opala', '--regua', 'producao'])
        self.assertEqual(rc, 0)
        self.assertIn('Porta: GRELHA=NAO - tamanho SIMPLES', saida.getvalue())
        self.assertIn('--modo 1', saida.getvalue())

    # Rodada 2 (juiz Sonnet r1, 08/11/2026): cada achado virou caso vermelho antes do conserto.
    def test_regua_no_imperativo_nao_passa_como_simples(self):
        casos = [('paga a fatura.pdf', 'dinheiro'), ('apague o antigo.html', 'apagar'), ('rm -rf build.js', 'apagar'),
                 ('exclua o velho.html', 'apagar'), ('manda o relatorio.pdf para o cliente', 'terceiro'),
                 ('envia o relatorio.pdf pro contador', 'terceiro'), ('posta o banner.png', 'terceiro')]
        for pedido, tipo in casos:
            d = porta.decidir(pedido=pedido)
            self.assertIn(tipo, d['regua'], pedido)
            self.assertEqual(d['tamanho'], 'NORMAL', pedido)

    def test_publicar_no_imperativo_levanta_producao_e_fica_simples(self):
        d = porta.decidir(pedido='publique o olamundo.html')
        self.assertEqual(d['regua'], ['producao'])
        self.assertEqual(d['tamanho'], 'SIMPLES')

    def test_gatilho_e_palavra_inteira(self):
        for pedido in ('conserta o typo no arquivo leitor.py', 'ajusta o dropdown em menu.js',
                       'reforce o contraste em estilo.css', 'corrija a pagina sobre.html'):
            d = porta.decidir(pedido=pedido)
            self.assertEqual(d['regua'], [], pedido)
            self.assertEqual(d['tamanho'], 'SIMPLES', pedido)

    def test_gatilho_nao_le_o_alvo(self):
        self.assertEqual(porta.decidir(pedido='revise a tela em www.x.com.br/apagar.html')['regua'], [])

    def test_lista_de_funcionalidades_e_normal(self):
        p = ('crie o painel de vendas em https://a.com.br/painel.html com login, graficos de receita por mes '
             'e exportacao para excel')
        self.assertEqual(porta.decidir(pedido=p)['tamanho'], 'NORMAL')

    def test_causa_a_descobrir_e_normal(self):
        for p in ('descubra por que o checkout.js quebra no safari e conserte', 'por que o menu.js quebra?'):
            self.assertEqual(porta.decidir(pedido=p)['tamanho'], 'NORMAL', p)

    def test_dominio_ou_secao_nao_e_alvo_concreto(self):
        for p in ('traduza o site exemplo.com.br para ingles', 'refaca exemplo.com.br/blog'):
            self.assertEqual(porta.decidir(pedido=p)['tamanho'], 'NORMAL', p)

    def test_jogo_em_um_arquivo_e_simples(self):
        # o tamanho mede a entrega, nao o assunto: um arquivo, pronto claro, com volta
        self.assertEqual(porta.decidir(pedido='crie um jogo da velha em velha.html')['tamanho'], 'SIMPLES')

    def test_arquivos_sozinho_empurra_e_avisa(self):
        self.assertEqual(porta.decidir(pedido=PEDIDO_EXPERIMENTO, arquivos=2)['tamanho'], 'SIMPLES')
        d = porta.decidir(pedido=PEDIDO_EXPERIMENTO, arquivos=3)
        self.assertEqual(d['tamanho'], 'NORMAL')
        self.assertIn('andaime', d['aviso'])

    def test_modo_invalido_e_coerente_na_cli(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            rc = porta.main(['--pedido', 'crie olamundo.html', '--modo', 'x'])
        self.assertEqual(rc, 2)
        self.assertNotIn('Caminho SIMPLES', saida.getvalue())
        self.assertEqual(saida.getvalue().count('modo invalido'), 1)

    def test_f1_no_normal_fica_f1(self):
        self.assertEqual(porta.decidir(pedido='criar um painel novo do zero', arquivos=2, modo='f1')['modo_efetivo'], 'f1')

    def test_json_traz_os_campos_novos(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            porta.main(['--pedido', PEDIDO_EXPERIMENTO, '--modo', 'opala', '--json'])
        d = json.loads(saida.getvalue())
        self.assertEqual(d['tamanho'], 'SIMPLES')
        self.assertEqual(d['alvos'], ['www.exemplo.com.br/olamundo.html'])
        self.assertEqual(d['modo_efetivo'], 1)
        self.assertIsNone(d['aviso'])

    def test_barra_final_e_abreviacao_nao_contam_como_alvo(self):
        self.assertEqual(porta.alvos('veja x.com.br/a.html e x.com.br/a.html/'), ['x.com.br/a.html'])
        self.assertEqual(porta.alvos('use e.g. isso'), [])

    def test_palavra_comum_de_regua_avisa_e_simples_rebaixa(self):
        p = 'crie um plano de aula em aula.html'
        d = porta.decidir(pedido=p)
        self.assertEqual(d['tamanho'], 'NORMAL')
        self.assertIn('--simples', d['aviso'])
        d = porta.decidir(pedido=p, simples=True)
        self.assertEqual(d['tamanho'], 'SIMPLES')
        self.assertEqual(d['regua'], [])
        self.assertIn('descartou', d['aviso'])

    def test_regua_declarada_vence_o_simples_e_producao_nunca_cai(self):
        p = 'crie um plano de aula em aula.html'
        self.assertEqual(porta.decidir(pedido=p, simples=True, regua=['dinheiro'])['tamanho'], 'NORMAL')
        self.assertEqual(porta.decidir(pedido='publique o rodape novo', simples=True)['regua'], ['producao'])

    def test_simples_diz_que_so_o_juiz_fecha_e_pede_conferencia(self):
        # decisao do dono em 08/11/2026: "Só o juiz Sonnet (Recomendado)"
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            porta.main(['--pedido', PEDIDO_EXPERIMENTO, '--regua', 'producao'])
        self.assertIn('sem dupla e sem Fable', saida.getvalue())
        self.assertIn('Confira', saida.getvalue())


class TestPapeis(unittest.TestCase):
    def test_os_tres_papeis_existem_e_sao_validos(self):
        probs, _ = ia.estado(destino=tempfile.mkdtemp())
        self.assertEqual(probs, [], '; '.join(probs))

    def test_juiz_sem_ferramenta_de_escrita(self):
        ruim = ('---\nname: ocombo-juiz\ndescription: Papel juiz do combo com uma descricao longa o '
                'bastante para passar do limite de oitenta caracteres exigido. Use sempre.\n'
                'tools: Read, Write, Bash\nmodel: sonnet\n---\ncorpo\n')
        probs = ia.validar(ruim, 'ocombo-juiz')
        self.assertTrue(any('escrita' in p for p in probs), probs)
        self.assertTrue(any('negar explicitamente' in p for p in probs), probs)

    def test_juiz_nao_pode_herdar_o_modelo_do_executor(self):
        ruim = ('---\nname: ocombo-juiz\ndescription: Papel juiz do combo com uma descricao longa o '
                'bastante para passar do limite de oitenta caracteres exigido. Use sempre.\n'
                'tools: Read, Bash\ndisallowedTools: Edit, Write, NotebookEdit\nmodel: inherit\n---\nx\n')
        self.assertTrue(any('cross-model' in p for p in ia.validar(ruim, 'ocombo-juiz')))

    def test_name_tem_de_bater_com_o_arquivo(self):
        ruim = ('---\nname: outro\ndescription: Descricao longa o bastante para passar do limite de '
                'oitenta caracteres exigido pelo portao. Use quando quiser.\nmodel: inherit\n---\nx\n')
        self.assertTrue(any('name do frontmatter' in p for p in ia.validar(ruim, 'ocombo-grelha')))

    def test_instalar_e_verificar(self):
        dest = tempfile.mkdtemp()
        try:
            probs, escritos = ia.instalar(dest)
            self.assertEqual(probs, [])
            self.assertEqual(sorted(escritos), sorted(ia.PAPEIS))
            self.assertEqual(ia.main(['--destino', dest, '--verificar']), 0)
            self.assertEqual(ia.instalar(dest)[1], [])  # idempotente
            with open(os.path.join(dest, 'ocombo-juiz.md'), 'ab') as f:
                f.write(b'mexeram aqui\n')
            self.assertEqual(ia.main(['--destino', dest, '--verificar']), 1)
        finally:
            shutil.rmtree(dest, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
