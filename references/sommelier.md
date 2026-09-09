# Sommelier de modelos (movido do SKILL.md em 06/09/2026, v5; texto original)

Destilado dos vídeos do Mano Deyvin (transcrições auditadas; ver memória
`claude-code-vazamento-2026-03`) + a rodada Odisséia desta casa:

- **Modelo por papel, não por fé.** Executor caro onde há densidade
  (arquitetura, backend, refatoração); juiz/tarefa simples em tier barato.
  Já provado aqui: juiz Sonnet acha o que o executor Fable não acha.
  Apostar tudo num modelo único = refém de um provedor.
- **Benchmark = o SEU caso de uso.** Benchmark público (ou da própria
  vendedora do modelo) não decide nada; antes de promover modelo novo a um
  papel da esteira, rode UM ciclo do combo com ele e compare medições.
- **ROI medido, não sentido.** Custo é evidência como exit code: tokens de
  input/output da sessão (`/usage`, `custo.log`), nunca "pareceu barato".
- **Rúbrica sempre tem critério de regressão**: "o que já passava continua
  passando" — acrescentar feature sem destruir o pronto é o que separa
  modelo utilizável de brinquedo.
- **A responsabilidade é de quem assina.** "A m* é sua, não da Anthropic":
  revisão final humana (ou do dono da esteira) antes do carimbo, sempre.
