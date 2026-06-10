import type { Interaction } from '@/lib/types';

type InteractionStatusDisplay = {
  value?: string | null;
  label?: string;
};

function payloadString(interaction: Interaction, key: string) {
  const value = interaction.payload_json?.[key];
  return typeof value === 'string' ? value : undefined;
}

function isExpandiLinkedInDelegated(interaction: Interaction) {
  const status = (interaction.status ?? interaction.interaction_status ?? '').toLowerCase();
  const provider = (interaction.linkedin_provider ?? payloadString(interaction, 'linkedin_provider') ?? '').toLowerCase();
  const executed = interaction.provider_executed ?? interaction.payload_json?.provider_executed;

  return interaction.channel === 'linkedin' && ['sent', 'queued', 'paused', 'failed', 'replied'].includes(status) && provider === 'expandi' && executed === true;
}

export function interactionDisplayStatus(interaction: Interaction): InteractionStatusDisplay {
  const providerStatus = interaction.provider_status ?? payloadString(interaction, 'provider_status');
  const providerStatusLabel = interaction.provider_status_label ?? payloadString(interaction, 'provider_status_label');
  if (interaction.channel === 'linkedin' && providerStatus) {
    return { value: `expandi_${providerStatus}`, label: providerStatusLabel };
  }

  if (isExpandiLinkedInDelegated(interaction)) {
    return { value: 'expandi_delegated', label: 'Entregue ao Expandi' };
  }

  return { value: interaction.status ?? interaction.interaction_status };
}

export function providerConfirmationLabel(interaction: Interaction) {
  const providerStatusLabel = interaction.provider_status_label ?? payloadString(interaction, 'provider_status_label');
  const providerStatusReason = interaction.provider_status_reason ?? payloadString(interaction, 'provider_status_reason');
  const providerStatusSyncedAt = interaction.provider_status_synced_at ?? payloadString(interaction, 'provider_status_synced_at');
  if (interaction.channel === 'linkedin' && providerStatusLabel) {
    return [
      `Expandi: ${providerStatusLabel}.`,
      providerStatusReason ? `Motivo: ${providerStatusReason}.` : '',
      providerStatusSyncedAt ? `Sincronizado em: ${new Date(providerStatusSyncedAt).toLocaleString('pt-BR')}.` : '',
    ]
      .filter(Boolean)
      .join(' ');
  }

  if (isExpandiLinkedInDelegated(interaction)) {
    return 'O CRM entregou este contato ao Expandi. A confirmação final depende da fila e dos limites do LinkedIn no Expandi.';
  }

  if (interaction.provider_message_id && interaction.channel === 'email') {
    return `Resend ID: ${interaction.provider_message_id}`;
  }

  return null;
}
