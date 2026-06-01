const connectors = [
  {
    name: 'Apollo.io',
    role: 'Busca e enriquecimento de candidatos',
    description: 'Fonte principal para encontrar pessoas por cargo, empresa, senioridade, localização e sinais B2B.',
  },
  {
    name: 'Hunter.io',
    role: 'Encontrar e validar e-mails',
    description: 'Complementa o Apollo com busca e verificação de e-mails profissionais antes de qualquer contato.',
  },
  {
    name: 'OpenAI / Claude',
    role: 'Classificação e copy',
    description: 'Gera score, justificativa, resumo do perfil e mensagens sugeridas para revisão humana.',
  },
  {
    name: 'Expandi',
    role: 'Outreach no LinkedIn',
    description: 'Executa convite, mensagem e follow-up no LinkedIn somente depois da aprovação no CRM.',
  },
  {
    name: 'Resend / SendGrid',
    role: 'Envio de e-mail',
    description: 'Envia e-mails aprovados e retorna status para histórico e auditoria do candidato.',
  },
  {
    name: 'Temporal',
    role: 'Controle operacional',
    description: 'Orquestra retries, limites, cadência, auditoria e bloqueios de segurança por tenant.',
  },
];

export function ConnectorStackPanel() {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Stack definida</p>
          <h2 className="mt-2 font-display text-2xl font-black text-stone-950">Conectores de produção planejados</h2>
          <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-stone-600">
            Estes conectores serão usados na próxima fase. As mensagens abaixo viram a biblioteca aprovada para as automações.
          </p>
        </div>
        <span className="rounded-full bg-stone-950 px-3 py-1 text-xs font-bold text-stone-50">6 blocos</span>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {connectors.map((connector) => (
          <article key={connector.name} className="rounded-lg border border-stone-200 bg-stone-50 p-4">
            <p className="font-display text-xl font-black text-stone-950">{connector.name}</p>
            <p className="mt-2 text-sm font-black text-amber-800">{connector.role}</p>
            <p className="mt-2 text-sm font-medium leading-6 text-stone-600">{connector.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
